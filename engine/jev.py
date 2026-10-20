#!/usr/bin/env python3
"""DHAP GBP engine — optional JEV second opinion on post variety (offers / events).

The SCORE always uses the rule-based answer from the Maps collector, so the same evidence gives the same score every
run. JEV (TypeSafe's decision model, called directly on TypeSafe's System One API) reads each recent post on its own and
answers two yes/no questions. Where JEV and the rules disagree, or JEV is unsure, the post is listed for a person to
look at before the variety points are recorded. JEV never changes a number by itself.
Calls to action are not sent to JEV: they are button labels, which the rules read exactly.
Needs TYPESAFE_API_KEY in the environment (never in the repository). With no key, no network, a bad reply or a timeout, it returns
status "skipped" with the reason, and the audit goes on with the rules alone.
Usage: python3 jev.py posts.json      (posts.json = {"rules": {"offers":..,"events":..}, "posts": ["text", ...]})
"""
import json, os, sys, urllib.error, urllib.request

URL = "https://api.typesafe.ai/v1/systemone"
MODEL = "jev-1.14.0"          # pinned so answers do not drift when a new Jev is released
PRICE_PER_M_INPUT = 0.042     # US$ per million input tokens (docs.typesafe.ai/models); output tokens are not billed
YES, NO = 0.7, 0.3            # noul >= 0.7 is yes, <= 0.3 is no, anything between is "unsure"
MAX_POSTS, MAX_CHARS = 12, 1500
QUESTIONS = {
    "offer": ("Does this Google Business Profile post advertise a specific offer to customers?",
              "It names a price cut, discount, APR or financing rate, rebate, coupon, special, or something free with a purchase or visit.",
              "It is news, a community event, or a general message with no specific deal."),
    "event": ("Does this post invite people to a community event or happening at a set time?",
              "It promotes an event people can attend or join: a sponsored festival, party, raffle, open house, car show, or similar.",
              "It is a sale, a 'sales event' that is only a promotion, a service special, or general news."),
}

def _ask(posts, key, timeout, url):
    state = {f"post_{i}": p[:MAX_CHARS] for i, p in enumerate(posts)}
    qs = {}
    for i in range(len(posts)):
        for k, (ins, yes, no) in QUESTIONS.items():
            qs[f"p{i}_{k}"] = {"type": "noul", "instructions": f"About post_{i} only: {ins}", "criteria": {"true": yes, "false": no}}
    req = urllib.request.Request(url, data=json.dumps({"model": MODEL, "state": state, "questions": qs}).encode(),
                                 headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode())

def second_opinion(posts, rules, key=None, timeout=20, url=None):
    """posts: texts of the posts from the last 30 days; rules: {"offers": bool, "events": bool} from the collector."""
    key = key if key is not None else os.environ.get("TYPESAFE_API_KEY", "")
    out = {"status": "skipped", "model": MODEL, "rules": {k: rules.get(k) for k in ("offers", "events")}, "posts": [], "review": [], "cost_usd": 0.0}
    posts = [str(p) for p in posts if str(p).strip()][:MAX_POSTS]
    if not posts: out["reason"] = "no posts from the last 30 days"; return out
    if not key: out["reason"] = "TYPESAFE_API_KEY not set"; return out
    try: resp = _ask(posts, key, timeout, url or URL)
    except urllib.error.HTTPError as e: out["reason"] = f"HTTP {e.code}"; return out
    except Exception as e: out["reason"] = f"{type(e).__name__}: {str(e)[:120]}"; return out
    ans = resp.get("answers") if isinstance(resp, dict) else None
    if not isinstance(ans, dict): out["reason"] = "reply had no answers"; return out
    try:
        for i in range(len(posts)):
            row = {}
            for k in QUESTIONS:
                p = float(ans[f"p{i}_{k}"]["noul"])
                if not 0 <= p <= 1: raise ValueError(p)
                row[k] = {"p": round(p, 3), "says": "yes" if p >= YES else "no" if p <= NO else "unsure"}
            out["posts"].append(row)
    except (KeyError, TypeError, ValueError) as e:
        out["posts"] = []; out["reason"] = f"reply missing or bad answer ({type(e).__name__})"; return out
    out["status"] = "ok"; out["cost_usd"] = round(float((resp.get("usage") or {}).get("input_tokens") or 0) * PRICE_PER_M_INPUT / 1e6, 8)
    out["model_served"] = resp.get("model")
    # The rubric asks one thing per listing: is there ANY offer / ANY event in the last 30 days. Decide at that level:
    # one clear "yes" settles it, so a borderline post elsewhere does not raise a flag that cannot change the answer.
    out["listing"] = {}
    for k, field in (("offer", "offers"), ("event", "events")):
        says = [r[k]["says"] for r in out["posts"]]
        yes = [i + 1 for i, s in enumerate(says) if s == "yes"]
        unsure = [i + 1 for i, s in enumerate(says) if s == "unsure"]
        verdict = "yes" if yes else "unsure" if unsure else "no"
        out["listing"][field] = verdict
        rule = "yes" if rules.get(field) else "no"
        if verdict == "unsure":
            out["review"].append(f"{field}: rules say {rule}, JEV is unsure (post {', '.join(map(str, unsure))})")
        elif verdict != rule:
            out["review"].append(f"{field}: rules say {rule}, JEV says {verdict}" + (f" (post {', '.join(map(str, yes))})" if yes else ""))
    out["agree"] = not out["review"]
    return out

if __name__ == "__main__":
    d = json.load(open(sys.argv[1]))
    print(json.dumps(second_opinion(d["posts"], d["rules"]), indent=1))

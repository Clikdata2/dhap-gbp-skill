#!/usr/bin/env python3
"""DHAP GBP engine — JEV decides first, the fixed rules check it (v15).

Every yes/no judgment about TEXT in an audit goes to JEV (TypeSafe's decision model) first: is this post an offer or an
event, does this text offer delivery, does this sentence say which towns the dealer serves, does the site show real
reviews, could this listing be mistaken for the dealer's own. The fixed rule (a word pattern) answers the same question.
  - JEV sure (p >= 0.7 yes, p <= 0.3 no)  -> JEV's answer is used.
  - JEV unsure, or JEV unavailable        -> the rule's answer is used, and the item is listed for a person.
  - JEV sure and the rule disagrees       -> JEV's answer is used, and the item is listed for a person.
The decided answers are written into the evidence file with this ledger, so scoring stays the same every time the same
evidence is scored. Facts that are not judgments (phone digits, counts, dates) are never sent to JEV.
Key: team key service (DHAP_SERVICE_URL + DHAP_TEAM_CODE) or TYPESAFE_API_KEY. Never commit either.
Usage: python3 decide.py items.json   (items.json = {"items": [{"id": "...", "kind": "delivery", "text": "...", "rule": true}]})
"""
import json, os, sys, urllib.error, urllib.request

URL = "https://api.typesafe.ai/v1/systemone"
MODEL = "jev-1.14.0"          # pinned so answers do not drift when a new JEV is released
PRICE_PER_M_INPUT = 0.042
YES, NO = 0.7, 0.3
MAX_ITEMS, MAX_CHARS = 40, 1500

# kind -> (question, what counts as yes, what counts as no)
KINDS = {
    "post_offer": ("Does this Google Business Profile post advertise a specific offer to customers?",
                   "It names a price, discount, APR or financing rate, rebate, coupon, special, a dated offer (\"Valid ...\"), a \"View offer\" button, or something free with a purchase or visit.",
                   "It is news, a community event, or a general message with no specific deal."),
    "post_event": ("Does this post invite people to a community event or happening at a set time?",
                   "It promotes an event people can attend or join: a sponsored festival, party, raffle, open house, car show, or similar.",
                   "It is a sale, a 'sales event' that is only a promotion, a service special, or general news."),
    "delivery": ("Does this text say the business offers any delivery to customers?",
                 "It offers home, parts or vehicle delivery, pickup and delivery, valet pickup, mobile service, or shipping to the customer, or it is Google's 'Offers delivery' attribute. Free or no-charge delivery counts.",
                 "It only mentions delivery charges or fees, factory delivery to the dealer, taking delivery of a purchase, a car 'delivering' performance, or says delivery is not offered."),
    "serving": ("Does this sentence say the dealership serves, delivers to, or draws customers from the places it names?",
                "It names towns, cities, counties, ZIP codes or areas the dealership serves or where its customers come from.",
                "Places are named only as the dealership's address, driving directions, a landmark, a news item, a vehicle or event name, or a page title or list of place names with no words saying the dealership serves them."),
    "site_reviews": ("Does this website text show real customer reviews or testimonials to visitors on the page itself?",
                     "It shows review text from customers, testimonials, or a reviews widget with customer comments and ratings.",
                     "It only links out to a review site, asks visitors to leave a review, or mentions reviews without showing any."),
    "same_business": ("Is the business name shown on this directory listing the same dealership as the name on its website?",
                      "The names differ only by spelling, punctuation, abbreviations, the town or state, the brand order, or words like Inc, LLC, Sales or Dealership, or the listing shows the current name together with a former name, so a shopper would read them as the same dealership.",
                      "The listing names a different dealership, a different brand or a different location, only one department (for example a Parts or Service listing), or only a former name."),
    "lookalike": ("Could a shopper mistake this Google listing for the dealership's own listing or one of its departments?",
                  "Its name contains the dealership's name or a department of it (Parts, Service, Sales), and it is not the dealership's main listing or a department linked on the main listing.",
                  "It is clearly a different business, brand or location."),
}

def _service():
    url, code = os.environ.get("DHAP_SERVICE_URL", "").rstrip("/"), os.environ.get("DHAP_TEAM_CODE", "")
    if url and code: return url + "/jev", "team:" + code
    return URL, os.environ.get("TYPESAFE_API_KEY", "")

def _ask(items, context, key, url, timeout):
    state = {"context": context[:MAX_CHARS]} if context else {}
    qs = {}
    for i, it in enumerate(items):
        state[f"item_{i}"] = str(it["text"])[:MAX_CHARS]
        ins, yes, no = KINDS[it["kind"]]
        qs[f"q{i}"] = {"type": "noul", "instructions": f"About item_{i} only: {ins}", "criteria": {"true": yes, "false": no}}
    auth = {"X-DHAP-Code": key[5:]} if key.startswith("team:") else {"Authorization": f"Bearer {key}"}
    req = urllib.request.Request(url, data=json.dumps({"model": MODEL, "state": state, "questions": qs}).encode(),
                                 headers={**auth, "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode())

def decide(items, context="", key=None, url=None, timeout=30, ask=None):
    """items: [{"id", "kind", "text", "rule": bool}]. Returns the ledger; every item gets a 'final' answer."""
    out = {"status": "skipped", "model": MODEL, "items": [], "review": [], "cost_usd": 0.0}
    bad = [it for it in items if it.get("kind") not in KINDS or not isinstance(it.get("rule"), bool) or not str(it.get("text", "")).strip()]
    if bad: raise SystemExit(f"decide.py: {len(bad)} item(s) need kind (one of {sorted(KINDS)}), text and rule true/false: {bad[:2]}")
    if url is None and key is None: url, key = _service()
    resp, chunks = None, [items[i:i + MAX_ITEMS] for i in range(0, len(items), MAX_ITEMS)]
    answers, served, tokens = [], None, 0
    if not items: out["reason"] = "nothing to decide"
    elif not key: out["reason"] = "no JEV key (set DHAP_SERVICE_URL + DHAP_TEAM_CODE, or TYPESAFE_API_KEY)"
    else:
        try:
            for ch in chunks:
                resp = (ask or _ask)(ch, context, key, url, timeout)
                ans = resp.get("answers") if isinstance(resp, dict) else None
                if not isinstance(ans, dict): raise ValueError("reply had no answers")
                for i in range(len(ch)):
                    p = float(ans[f"q{i}"]["noul"])
                    if not 0 <= p <= 1: raise ValueError(f"probability out of range: {p}")
                    answers.append(p)
                tokens += float((resp.get("usage") or {}).get("input_tokens") or 0); served = resp.get("model")
            out["status"] = "ok"
        except urllib.error.HTTPError as e: out["reason"] = f"HTTP {e.code}"; answers = []
        except Exception as e: out["reason"] = f"{type(e).__name__}: {str(e)[:120]}"; answers = []
    for i, it in enumerate(items):
        row = {"id": it["id"], "kind": it["kind"], "rule": it["rule"], "text": str(it["text"])[:160]}
        if answers:
            p = answers[i]; says = "yes" if p >= YES else "no" if p <= NO else "unsure"
            row.update(p=round(p, 3), jev=says)
            if says == "unsure":
                row["final"], row["by"] = it["rule"], "rule (JEV unsure)"
                out["review"].append(f"{it['id']}: JEV unsure (p={p:.2f}); the rule's answer ({'yes' if it['rule'] else 'no'}) is used")
            else:
                row["final"], row["by"] = (says == "yes"), "jev"
                if (says == "yes") != it["rule"]:
                    out["review"].append(f"{it['id']}: JEV says {says}, the rule says {'yes' if it['rule'] else 'no'}; JEV's answer is used")
        else:
            row.update(final=it["rule"], by="rule (JEV unavailable)")
        out["items"].append(row)
    if out["status"] != "ok" and items: out["review"].append(f"JEV did not run ({out.get('reason')}); every answer came from the rules")
    out["cost_usd"] = round(tokens * PRICE_PER_M_INPUT / 1e6, 8)
    if served: out["model_served"] = served
    out["agree"] = not out["review"]
    return out

def final(ledger, prefix):
    """True when any decided item whose id starts with prefix is yes."""
    return any(r["final"] for r in ledger["items"] if r["id"].startswith(prefix))

if __name__ == "__main__":
    d = json.load(open(sys.argv[1]))
    print(json.dumps(decide(d["items"], d.get("context", "")), indent=1, ensure_ascii=False))

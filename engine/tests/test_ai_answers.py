#!/usr/bin/env python3
"""AI answer check (v15.1): required from Oct 24 2026, refuses gaps, flags lost calls and choices. Rounds: argv[1] (default 3)."""
import copy, json, pathlib, sys
ENG = pathlib.Path(__file__).resolve().parent.parent; sys.path.insert(0, str(ENG))
import ai_answers as A, score as S

def ans(tool, prompt, **k):
    a = dict(tool=tool, prompt=prompt, status="answered", asked=f"{prompt} question", when="2026-10-24 10:00", named=True, position=1,
             phone=None, rating=None, rating_source=None, sources=["example.com"], quote="test fixture words", proof=f"proof/ai_{tool}_{prompt}.jpg")
    a.update(k); return a
def full():
    return dict(method="test fixture", answers=[ans(t, p) for t, p in A.expected()])
VAC = json.loads((ENG / "examples/evidence-example-vacaville.json").read_text())
VAC["ledger"] = {g: {"method": "test fixture", "when": "2026-10-24"} for g in S.LEDGER_GROUPS}; VAC["listings"]["sales"]["last_post_days"] = 0

fails = 0
def ok(name, cond, extra=""):
    global fails
    print(("PASS " if cond else "FAIL ") + name + ("" if cond else f"  -> {extra}")); fails += 0 if cond else 1

def run_once():
    ev = copy.deepcopy(VAC); ev["audit_date"] = "2026-10-23"; ev.pop("ai_answers", None)
    ok("an audit dated before Oct 24 2026 does not need the check", not A.check(ev), A.check(ev))
    ev["audit_date"] = "2026-10-24"
    ok("from Oct 24 2026: no AI answers -> not scored", any(x.startswith("ai_answers: missing") for x in S.check(ev)), S.check(ev))
    ev["ai_answers"] = full()
    ok("all 7 tools x 3 prompts + 2 cards answered -> scored", not S.check(ev), S.check(ev))
    ok("the check never changes a score", S.score_rows(copy.deepcopy(ev))[1] == S.score_rows(dict(copy.deepcopy(ev), audit_date="2026-10-23"))[1])
    def broken(mut, needle, name):
        e = copy.deepcopy(ev); mut(e["ai_answers"]); p = A.check(e); ok("refuses: " + name, any(needle in x for x in p), p)
    broken(lambda a: a["answers"].pop(0), "google_ai/best not recorded", "a missing tool/prompt")
    broken(lambda a: a["answers"].append(ans("chatgpt", "best")), "recorded twice", "the same answer twice")
    broken(lambda a: a["answers"].append(ans("grok", "best")), "unknown tool", "a tool not on the list")
    broken(lambda a: a["answers"][0].update(quote=""), ".quote", "no word-for-word quote")
    broken(lambda a: a["answers"][0].update(proof=""), ".proof", "no screenshot")
    broken(lambda a: a["answers"][0].update(named="yes"), ".named", "named not true/false")
    broken(lambda a: a["answers"][0].update(named=False, position=2), ".position", "a position for a dealer not named")
    broken(lambda a: a["answers"][0].update(phone="555-0100"), ".phone_matches_site", "a phone with no match/mismatch")
    broken(lambda a: a["answers"][0].update(rating=4.4), ".rating_source", "a rating with no source")
    broken(lambda a: a["answers"][0].update(rating=6, rating_source="yelp"), ".rating:", "a rating above 5")
    broken(lambda a: a["answers"][0].update(sources=None), ".sources", "no sources list")
    broken(lambda a: a["answers"][0].update(status="blocked"), ".reason", "blocked with no reason")
    broken(lambda a: a.update(method=""), "ai_answers.method", "no method")
    broken(lambda a: [x.update(status="blocked", reason="sign-in wall") for x in a["answers"]], "no tool answered", "every tool blocked")
    e = copy.deepcopy(ev); e["ai_answers"]["answers"][3].update(status="blocked", reason="sign-in wall")
    ok("one tool blocked with a reason is accepted", not A.check(e), A.check(e))
    e = copy.deepcopy(ev); X = e["ai_answers"]["answers"]
    X[0].update(named=False, position=None, quote="not mentioned; named Rival Mitsubishi first")
    X[4].update(phone="(555) 010-0199", phone_matches_site=False); X[-1].update(rating=2.4, rating_source="yelp")
    X[5].update(status="blocked", reason="sign-in wall")
    f = A.flags(e)
    ok("flags: not named in a 'best' answer", any("Not named" in x and "Google AI Overview" in x for x in f), f)
    ok("flags: phone that does not match the website", any("does not match" in x and "(555) 010-0199" in x for x in f), f)
    ok("flags: a rating that is not Google's", any("not Google's" in x and "2.4 (yelp)" in x for x in f), f)
    ok("flags: blocked answers are listed", any("blocked" in x for x in f), f)
    b = A.brief(e)
    ok("brief: one table row per answer", b.count("\n| ") == len(X) + 1, b)
    ok("brief: a clean run says 'Flags: none.'", "**Flags:** none." in A.brief(ev))

for rnd in range(int(sys.argv[1]) if len(sys.argv) > 1 else 3):
    print(f"--- round {rnd + 1}"); run_once()
print(f"\n{'ALL PASSED' if fails == 0 else str(fails) + ' FAILED'}")
sys.exit(1 if fails else 0)

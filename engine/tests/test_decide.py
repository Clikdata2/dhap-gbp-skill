"""Stress test for decide.py (JEV decides first, the rule checks it) with a fake JEV. Run: python3 tests/test_decide.py"""
import pathlib, sys, urllib.error
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
import decide as D
fails = 0
def ok(name, cond, extra=""):
    global fails; fails += 0 if cond else 1; print(("PASS " if cond else "FAIL ") + name + ("" if cond else "  " + str(extra)[:300]))
def fake(ps, served="jev-1.14.0"):
    def ask(items, ctx, key, url, timeout):
        return {"answers": {f"q{i}": {"noul": ps.pop(0)} for i in range(len(items))}, "usage": {"input_tokens": 1000}, "model": served}
    return ask
IT = lambda n, rule=True, kind="delivery": [{"id": f"d{i}", "kind": kind, "text": f"text {i}", "rule": rule} for i in range(n)]

for rnd in range(3):
    print(f"--- round {rnd + 1}")
    L = D.decide(IT(4), key="k", url="u", ask=fake([0.9, 0.1, 0.5, 0.7]))
    f = [r["final"] for r in L["items"]]; by = [r["by"] for r in L["items"]]
    ok("sure yes -> JEV", f[0] is True and by[0] == "jev")
    ok("sure no overrides the rule -> JEV, flagged", f[1] is False and by[1] == "jev" and any("d1: JEV says no" in x for x in L["review"]))
    ok("unsure -> rule, flagged", f[2] is True and by[2].startswith("rule") and any("d2: JEV unsure" in x for x in L["review"]))
    ok("exactly 0.7 counts as yes", f[3] is True and by[3] == "jev")
    ok("agree is false when anything is flagged", L["agree"] is False and L["status"] == "ok")
    L = D.decide(IT(2, rule=False), key="k", url="u", ask=fake([0.3, 0.05]))
    ok("exactly 0.3 counts as no; JEV and rule agree -> nothing flagged", L["agree"] and [r["final"] for r in L["items"]] == [False, False])
    def boom(*a): raise urllib.error.HTTPError("u", 502, "bad", {}, None)
    L = D.decide(IT(3), key="k", url="u", ask=boom)
    ok("JEV unavailable -> every answer from the rule, flagged once", L["status"] == "skipped" and all(r["final"] and r["by"] == "rule (JEV unavailable)" for r in L["items"]) and any("JEV did not run" in x for x in L["review"]))
    L = D.decide(IT(2), key="k", url="u", ask=lambda *a: {"answers": {"q0": {"noul": 1.4}, "q1": {"noul": 0.9}}})
    ok("out-of-range probability -> whole reply rejected, rules used", L["status"] == "skipped" and all(r["by"].startswith("rule") for r in L["items"]))
    L = D.decide(IT(2), key="k", url="u", ask=lambda *a: {"oops": 1})
    ok("reply without answers -> rules used", L["status"] == "skipped" and "no answers" in L["reason"])
    L = D.decide(IT(2), key="", url="u")
    ok("no key -> rules used, reason given", L["status"] == "skipped" and "no JEV key" in L["reason"])
    L = D.decide(IT(95), key="k", url="u", ask=fake([0.95] * 95))
    ok("95 items are sent in chunks of 40 and all decided", L["status"] == "ok" and len(L["items"]) == 95 and all(r["by"] == "jev" for r in L["items"]) and L["cost_usd"] > 0)
    ok("final() helper finds any yes by id prefix", D.final(L, "d9") and not D.final({"items": []}, "d"))
    try: D.decide([{"id": "x", "kind": "weather", "text": "t", "rule": True}], key="k", url="u"); ok("unknown kind refused", False)
    except SystemExit: ok("unknown kind refused", True)
    try: D.decide([{"id": "x", "kind": "delivery", "text": "  ", "rule": True}], key="k", url="u"); ok("empty text refused", False)
    except SystemExit: ok("empty text refused", True)
    ok("every kind has a question and yes/no criteria", all(len(v) == 3 and all(x.strip() for x in v) for v in D.KINDS.values()))

print(f"\n{'ALL PASSED' if fails == 0 else str(fails) + ' FAILED'}")
sys.exit(1 if fails else 0)

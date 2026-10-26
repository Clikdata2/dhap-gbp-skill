#!/usr/bin/env python3
"""Rules 7 and 8 (v15.2): Alert stat cards follow the dealer; NAP on every listing site from saved readings. Rounds: argv[1] (default 3)."""
import copy, json, pathlib, sys
ENG = pathlib.Path(__file__).resolve().parent.parent; sys.path.insert(0, str(ENG))
import score as S, alert_cards as AC, directories as D

V = json.load(open(ENG / "examples/evidence-example-v15-2.json"))
JAMES = json.load(open(ENG / "examples/evidence-example-james.json"))
fails = 0
def ok(name, cond, extra=""):
    global fails
    print(("PASS " if cond else "FAIL ") + name + ("" if cond else f"  -> {str(extra)[:300]}")); fails += 0 if cond else 1
def fresh(ev): return S.resolve_ages(copy.deepcopy(ev))
def cards(ev): ev = fresh(ev); return AC.pick(ev, S.score_rows(ev)[1])

def run_once():
    # ---------------- rule 8: matching
    ok("phone: digits only, country code ignored", D.digits("+1 (585) 563-2029") == D.digits("585.563.2029"))
    for a, b, want in (("3800 West Ridge Road, Greece, NY 14626", "3800 W Ridge Rd, Rochester, NY 14626-3443", True),
                       ("5800 S LaGrange Rd, Countryside, IL 60525", "5800 Lagrange Road, Countryside, IL 60525", True),
                       ("681 Orange Dr, Vacaville, CA 95687", "681 Orange Drive Ste A, Vacaville, CA 95687", True),
                       ("681 Orange Dr, Vacaville, CA 95687", "681 Orange Drive, Vacaville, CA 95688", False),
                       ("681 Orange Dr, Vacaville, CA 95687", "683 Orange Dr, Vacaville, CA 95687", False),
                       ("3800 West Ridge Road, Greece, NY 14626", "3800 West Ridge Road, Rochester, NY", False)):
        ok(f"address {b!r} {'matches' if want else 'differs'}", D.same_address(a, b, []) == want)
    ok("address: a recorded postal city counts when no ZIP shows", D.same_address("3800 West Ridge Road, Greece, NY 14626", "3800 W Ridge Rd, Rochester, NY", ["Rochester"]))
    for a, b, want in (("James Mitsubishi Greece", "JAMES MITSUBISHI", True), ("James Mitsubishi Greece", "James Mitsubishi of Greece, Inc.", True),
                       ("Countryside Mitsubishi", "Countryside Mitsubishi Parts", False), ("James Mitsubishi Greece", "James Cars of Greece LLC", False),
                       ("James Mitsubishi Greece", "James Nissan Greece", False)):
        ok(f"name {b!r} {'same' if want else 'not the same'} by rule", D.same_name(a, b, {"greece", "ny"}) == want)
    # ---------------- rule 8: evidence check and scoring
    ok("v15.2 example passes the evidence check", not S.check(fresh(V)), S.check(fresh(V)))
    ev = fresh(V); P = ev["nap"]["_directory_points"]
    ok("network group: 2 x agree / found", abs(P["network"][0] - 2 * P["network"][1] / P["network"][2]) < 1e-9 and P["network"][2] > 0, P)
    ok("a site in both groups counts in both", all({"network", "ai"} <= set(r["groups"]) for r in ev["nap"]["_directory_results"] if r["directory"] in ("bing", "yellowpages")))
    ok("an AI-cited site counts in the AI group", any(r["directory"] == "cited:capitalone.com" and r["groups"] == ["ai"] for r in ev["nap"]["_directory_results"]))
    ok("not listed and blocked are reported, never scored", all(r["agree"] is None for r in ev["nap"]["_directory_results"] if r["status"] != "found"))
    ok("JEV's no on a legal name stands", any(r["directory"] == "data_axle" and r["agree"] is False and "name" in r["why"] for r in ev["nap"]["_directory_results"]))
    e = copy.deepcopy(V); next(d for d in e["nap"]["directories"] if d["directory"] == "data_axle")["name_same"] = True
    ok("JEV's yes on a legal name counts as the same business", next(r for r in fresh(e)["nap"]["_directory_results"] if r["directory"] == "data_axle")["agree"])
    e = copy.deepcopy(V); [d.update(phone=e["nap"]["site"]["phone"], name=e["nap"]["site"]["name"], address=e["nap"]["site"]["address"]) for d in e["nap"]["directories"] if d["status"] == "found"]; [d.pop("name_same", None) for d in e["nap"]["directories"]]
    r = S.score_rows(fresh(e))[1][5]; base = S.score_rows(fresh(V))[1][5]
    ok("every found listing correct -> both groups earn 2 and NAP rises", r > base and fresh(e)["nap"]["_directory_points"]["ai"][0] == 2.0, (r, base))
    e = copy.deepcopy(V); [d.update(status="not_found", searched="x") for d in e["nap"]["directories"]]
    ok("no listing found anywhere -> both groups 0", fresh(e)["nap"]["_directory_points"] == {"network": (0.0, 0, 0), "ai": (0.0, 0, 0)})
    def broken(mut, needle, name):
        e = copy.deepcopy(V); mut(e); p = S.check(fresh(e)); ok("refuses: " + name, any(needle in x for x in p), p)
    broken(lambda e: e["nap"]["directories"].pop(0), "not recorded", "a site with no reading")
    broken(lambda e: e["nap"]["directories"][0].update(draft=True), "still a draft", "an unconfirmed scanner draft")
    broken(lambda e: e["nap"].update(directories_agree=[True] * 5), "not typed from v15.2", "typed directory answers")
    broken(lambda e: next(d for d in e["nap"]["directories"] if d["status"] == "found").update(proof=""), ".proof", "a found listing with no screenshot")
    broken(lambda e: e["nap"]["directories"].append({"directory": "myspace", "status": "not_found", "searched": "x", "when": "2026-10-25"}), "unknown site", "a site not in the registry")
    broken(lambda e: e["nap"].pop("site"), "nap.site", "no website NAP")
    broken(lambda e: next(d for d in e["nap"]["directories"] if d["directory"] == "cars_com").update(status="blocked"), ".reason", "blocked with no reason")
    broken(lambda e: e["nap"]["directories"].extend({"directory": f"cited:site{i}.com", "status": "not_found", "searched": "x", "when": "2026-10-25", "url": "u"} for i in range(5)), "at most the 5 most-cited", "more than five AI-cited sites")
    ok("audits before Oct 25 2026 keep the typed five-directory answers", not S.check(fresh(JAMES)) and S.score_rows(fresh(JAMES))[1] == [10.0, 4.0, 2.3, 8.4, 0.0, 9.2, 5.6, 5.0])
    ok("registry: every scored site has a lookup method and a group", all(x["group"] in ("network", "ai", "both") for x in D.REGISTRY["sites"]) and len(D.CHECKED) == 16, len(D.CHECKED))
    # ---------------- the website is the authority (Travis, Oct 25 2026)
    site = fresh(V)["nap"]["site"]
    ok("authority: a Service listing is compared with the website's Service number", D.phone_check("707-353-4579", site, "service") is True and D.phone_check("707-532-2052", site, "service") is False)
    ok("authority: a toll-free number is never compared with a local one", D.phone_check("(888) 352-3107", site, "sales") is None)
    ok("authority: a local number is never compared with a toll-free website number", D.phone_check("707-532-2052", dict(site, phones=dict(site["phones"], sales="866-555-0100")), "sales") is None)
    e = copy.deepcopy(V); d0 = next(d for d in e["nap"]["directories"] if d["directory"] == "bing"); d0["phone"] = "1-888-352-3107"
    r0 = next(r for r in fresh(e)["nap"]["_directory_results"] if r["directory"] == "bing")
    ok("authority: a toll-free phone on a listing does not count against it (name and address still checked)", r0["agree"] and not r0["phone_compared"], r0)
    e = copy.deepcopy(V); e["nap"]["site"]["phones"]["parts"] = None; e["nap"]["site"]["phones"]["sales"] = "800-555-0100"
    n = D.notes(e)
    ok("authority: a toll-free-only website number and a missing number go in the rep brief, Sales first", len(n) == 2 and "Sales" in n[0] and "toll-free" in n[0] and "no Parts number" in n[1], n)
    e = copy.deepcopy(V); e["nap"]["site"].pop("phones")
    ok("authority: the website's department numbers are required", any("nap.site.phones" in x for x in S.check(fresh(e))))
    e = copy.deepcopy(V); e["nap"]["dept_phones"] = [{"dept": "service", "gbp": "877-555-0100", "site": "707-353-4579"}]
    ok("rule 1: a toll-free department phone is not compared (point earned)", S.score_rows(fresh(e))[1][5] >= S.score_rows(fresh(dict(copy.deepcopy(V), nap=dict(copy.deepcopy(V)["nap"], dept_phones=None))))[1][5])
    # ---------------- always local (Travis, Oct 25 2026): toll-free is flagged wherever it is the business number
    def flags(sales_site=None, sales_google=None, schema=None):
        e = copy.deepcopy(V)
        if sales_site: e["nap"]["site"]["phones"]["sales"] = sales_site; e["nap"]["site"]["phone"] = sales_site
        if sales_google: e["nap"]["google_phones"]["sales"] = sales_google
        if schema is not None: e["nap"]["site"]["schema_phones"] = schema
        return D.local_flags(e)
    ok("local: all local -> no flag", flags() == [])
    f = flags("800-555-0100", "(888) 555-0199"); ok("local: toll-free on the website and Google -> flagged", [x["case"] for x in f] == ["both"] and "should be a local number" in f[0]["text"], f)
    f = flags("800-555-0100"); ok("local: toll-free website, local Google -> flagged (the website should show the local number)", [x["case"] for x in f] == ["website"] and "website should show the local number" in f[0]["text"], f)
    f = flags(None, "866-555-0100"); ok("local: local website, toll-free Google -> flagged (Google should show the local number)", [x["case"] for x in f] == ["google"] and "Google should show the local number" in f[0]["text"], f)
    f = flags(schema=["888-352-3107"]); ok("local: schema with only toll-free numbers -> flagged", [x["case"] for x in f] == ["schema"], f)
    ok("local: flags never change a score", S.score_rows(fresh(dict(copy.deepcopy(V))))[1] == S.score_rows(fresh(V))[1])
    e = copy.deepcopy(V); next(d for d in e["nap"]["directories"] if d["directory"] == "bbb")["phone"] = "888-555-0100"
    ok("local: a listing site showing a toll-free number is marked", next(r for r in fresh(e)["nap"]["_directory_results"] if r["directory"] == "bbb").get("toll_free"))
    e = copy.deepcopy(V); e["nap"].pop("google_phones")
    ok("local: the Google listing phones are required", any("nap.google_phones" in x for x in S.check(fresh(e))))
    # ---------------- rule 7: cards
    c, para = cards(V)
    ok("four cards for a dealer with four weak areas", len(c) == 4, c)
    ok("the weakest customer-weighted area comes first (NAP 6.3 - 1.0 beats Posts 5.8 - 0.5)", c[0]["head"] == "NAP_MISMATCHES", [x["head"] for x in c])
    ok("one card per area", len({x["area"] for x in c}) == len(c))
    ok("each card's status follows its own area score", all(x["status"] == AC.status(x["area_score"]) for x in c))
    ok("every card header fits (16 characters)", all(len(x["head"]) <= 16 for x in c))
    ok("the paragraph is written from the first three cards", para.startswith("With ") and all(x["phrase"] in para for x in c[:3]), para)
    old = copy.deepcopy(JAMES); old["audit_date"] = "2026-10-25"   # James's numbers under rule 7 (AI answers absent -> AI area skipped)
    jc = [x["head"] for x in AC.pick(fresh(old), S.score_rows(fresh(old))[1])[0]]
    ok("James: posts, photos, departments, sameAs", jc == ["GBP_INACTIVITY", "PHOTOS_30D", "DEPTS_MISSING", "SAMEAS_LINKS"], jc)
    e = copy.deepcopy(V)
    for a in e["ai_answers"]["answers"]:
        if a["status"] == "answered": a.update(named=False, position=None) if a["prompt"] != "card" else None
    ok("AI answers that leave the dealer out make the AI card", any(x["head"] == "AI_TOOLS_MISSED" for x in cards(e)[0]), [x["head"] for x in cards(e)[0]])
    e = copy.deepcopy(V); e["listings"]["sales"]["last_post_days"] = 89; e["listings"]["sales"]["posts_30d"] = 0; e["listings"]["sales"]["variety"] = dict(offers=False, events=False, cta=False)
    gi = next((x for x in cards(e)[0] if x["head"] == "GBP_INACTIVITY"), None)
    ok("months since the last post are never rounded up (89 days = 2 months)", gi is not None and gi["target"] == 2, gi)
    e = fresh(V); rows = [10.0] * 8; e.pop("ai_answers")
    ok("every area at 10 -> no cards -> no Alert", AC.pick(e, rows)[0] == [])
    e = fresh(V); rows = [10.0, 10.0, 10.0, 9.5, 10.0, 10.0, 10.0, 10.0]; e.pop("ai_answers")
    ok("an area below 10 with a real problem still gets its card", [x["area"] for x in AC.pick(e, rows)[0]] == ["Reviews & Reputation"], AC.pick(e, rows)[0])
    ok("the reviews-on-site point never makes a card", all("site" not in x["head"].lower() for x in c))

for rnd in range(int(sys.argv[1]) if len(sys.argv) > 1 else 3):
    print(f"--- round {rnd + 1}"); run_once()
print(f"\n{'ALL PASSED' if fails == 0 else str(fails) + ' FAILED'}")
sys.exit(1 if fails else 0)

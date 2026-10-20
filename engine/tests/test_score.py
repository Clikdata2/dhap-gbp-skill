"""Stress tests for score.py: the repository's locked James reference, the two real audits, status edges, broken
evidence, a changed-rules guard, and 2,000 random evidence files. Run: python3 tests/test_score.py"""
import copy, json, pathlib, random, shutil, sys, tempfile
ENG = pathlib.Path(__file__).resolve().parent.parent; sys.path.insert(0, str(ENG))
import score as S
REPO = S.default_repo() if (S.default_repo() / "SKILL.md").exists() else ENG.parent / "repo"
LED = {g: {"method": "test fixture", "when": "2026-10-20"} for g in S.LEDGER_GROUPS}
def L(**k):
    base = dict(claimed_verified=1.0, checklist_done=7, checklist_total=7, photos_30d=0, logo=False, cover=True,
                coverage=dict(exterior=True, interior_or_team=True, department=False), posts_30d=0, last_post_days=None,
                variety=dict(offers=False, events=False, cta=False), newest_review_days=0)
    base.update(k); return base

# --- the locked reference in SKILL.md (James Mitsubishi Greece, Oct 19 2026): 10 / 4.0 / 2.3 / 8.4 / 0 / 9.2 / 5.6 / 5.0 -> 5.6 Critical
JAMES = dict(dealer="James Mitsubishi Greece", audit_date="2026-10-19", ledger=LED,
    listings=dict(sales=L(last_post_days=216, newest_review_days=2), service=None, parts=None, combined=None),
    claimed=dict(duplicate_or_unclaimed_found=False),
    reviews=dict(google_rating=4.5, owner_replies_of_10_newest=8, facebook=dict(mode="percent"), real_reviews_visible_on_site=False),
    nap=dict(google_vs_site_fields_matching=3, directories_agree=[True, True, True, True, False], dept_phones_ok=None, map_pin_ok=True),
    schema=dict(pages_with_jsonld=1, business_type_ok=True, department_entities=3, parses_cleanly=True, dept_own_page_address=0, dept_own_phone=0,
                core_fields=6, logo_or_image=True, sameas_google=False, sameas_other=True, areaserved=False, hasmap_or_map=False, services_or_offers=False))
VAC = json.loads((ENG / "examples/evidence-example-vacaville.json").read_text()); VAC["ledger"] = LED
VAC["listings"]["sales"]["last_post_days"] = 0
MUSIC = dict(dealer="Music City Mitsubishi", audit_date="2026-10-19", ledger=LED,
    listings=dict(sales=L(photos_30d=2, logo=True, posts_30d=1, last_post_days=4, variety=dict(offers=True, events=False, cta=True), newest_review_days=2),
                  service=None, parts=None,
                  combined=L(checklist_done=5, checklist_total=8, photos_30d=0, logo=False, cover=False, coverage=dict(exterior=False, interior_or_team=False, department=False),
                             posts_30d=0, last_post_days=None, newest_review_days=100)),
    claimed=dict(duplicate_or_unclaimed_found=True),
    reviews=dict(google_rating=4.8, owner_replies_of_10_newest=10, facebook=dict(mode="none"), real_reviews_visible_on_site=False),
    nap=dict(google_vs_site_fields_matching=2, directories_agree=[False, False, False, False, True], dept_phones_ok=False, map_pin_ok=True),
    schema=dict(pages_with_jsonld=5, business_type_ok=True, department_entities=3, parses_cleanly=False, dept_own_page_address=3, dept_own_phone=2,
                core_fields=6, logo_or_image=True, sameas_google=False, sameas_other=True, areaserved=False, hasmap_or_map=False, services_or_offers=False))

fails = 0
def ok(name, cond, extra=""):
    global fails; fails += 0 if cond else 1; print(("PASS " if cond else "FAIL ") + name + ("" if cond else "  " + str(extra)))

def run_once():
    for name, ev, rows, ov, lab in (("James reference (locked in SKILL.md)", JAMES, [10.0, 4.0, 2.3, 8.4, 0.0, 9.2, 5.6, 5.0], 5.6, "Critical"),
                                    ("Vacaville audit (Oct 20)", VAC, [10.0, 8.0, 6.4, 6.9, 5.8, 5.3, 8.0, 8.0], 7.3, "Major Issues")):
        p = S.check(ev); ok(name + " evidence passes the check", not p, p)
        raw, r = S.score_rows(ev); st = S.status(r)
        ok(name + " rows", r == rows, r); ok(name + " overall", S.overall(r) == ov, S.overall(r)); ok(name + " status", st["label"] == lab, st)
    jf = json.loads((ENG / "examples/evidence-example-james.json").read_text())
    ok("James example file passes the check and scores the locked reference", not S.check(jf) and S.score_rows(jf)[1] == [10.0, 4.0, 2.3, 8.4, 0.0, 9.2, 5.6, 5.0] and S.overall(S.score_rows(jf)[1]) == 5.6)
    p = S.check(MUSIC); raw, r = S.score_rows(MUSIC)
    ok("Music City evidence passes the check and scores 0..10", not p and all(0 <= x <= 10 for x in r), (p, r))
    ok("half-up rounding 5.85 -> 5.9", S.r1d(5.85) == 5.9 and S.r1d(46.8 / 8) == 5.9 and S.r1d(4.95) == 5.0)
    # status edges
    base = [9.5] * 8
    for low, lab in ((0.0, "Critical"), (5.0, "Critical"), (5.1, "Major Issues"), (6.9, "Major Issues"), (7.0, "Needs Improvement"), (8.9, "Needs Improvement"), (9.0, "Fully Optimized"), (10.0, "Fully Optimized")):
        rows = base[:]; rows[3] = low; ok(f"status edge lowest={low}", S.status(rows)["label"] == lab, S.status(rows))
    # broken evidence must be refused, with the right reason
    def broken(mut, needle):
        ev = copy.deepcopy(VAC); mut(ev); p = S.check(ev); ok("refuses: " + needle, any(needle in x for x in p), p)
    broken(lambda e: e.pop("ledger"), "ledger.website_schema")
    broken(lambda e: e["ledger"]["photos"].update(when="last week"), "ledger.photos")
    broken(lambda e: e["listings"]["combined"].update(checklist_total=7), "listings.combined.checklist_total")
    broken(lambda e: e["nap"].update(directories_agree=[True, True, False, False]), "nap.directories_agree")
    broken(lambda e: e["listings"]["sales"].update(last_post_days=40), "newest post is older than 30 days")
    broken(lambda e: e["listings"]["sales"].update(posts_30d=2.5), "listings.sales.posts_30d")
    broken(lambda e: e["reviews"].update(facebook={"mode": "stars"}), "reviews.facebook.within_half")
    broken(lambda e: e["schema"].update(dept_own_phone=3), "cannot be more than department_entities")
    broken(lambda e: e["listings"]["sales"].update(logo="maybe"), "listings.sales.logo")
    broken(lambda e: e["listings"].update(service=copy.deepcopy(e["listings"]["combined"])), "both given")
    broken(lambda e: e["listings"]["combined"].update(posts_30d=0, last_post_days=None), "variety is judged on posts from the last 30 days")
    # separate Service and Parts listings (no combined)
    ev = copy.deepcopy(VAC); c = ev["listings"].pop("combined"); ev["listings"]["combined"] = None
    ev["listings"]["service"] = copy.deepcopy(c); ev["listings"]["parts"] = dict(copy.deepcopy(c), checklist_total=7, checklist_done=4)
    ok("separate Service + Parts listings score", not S.check(ev) and S.score_rows(ev)[1][1] == S.r1d(4 + 2 + 2 * 4 / 8 + 2 * 4 / 7), S.score_rows(ev)[1])
    # no listings at all
    ev = copy.deepcopy(VAC); ev["listings"] = dict(sales=None, service=None, parts=None, combined=None); ev["listings_none"] = True
    raw, r = S.score_rows(ev); ok("no Google listings -> Profile Completeness 0, no crash", r[1] == 0 and r[0] == 2.0, r)
    # rules guard: a changed rubric text must stop scoring; the real repo must pass
    try: S.rules_guard(REPO); ok("rules guard accepts the current repository", True)
    except SystemExit as e: ok("rules guard accepts the current repository", False, e)
    tmp = pathlib.Path(tempfile.mkdtemp())
    (tmp / "VERSION").write_text("14.3"); s = (REPO / "SKILL.md").read_text().replace("Sales 15 days (1.5 pts)", "Sales 10 days (1.5 pts)")
    (tmp / "SKILL.md").write_text(s)
    try: S.rules_guard(tmp); ok("rules guard STOPS on a changed rubric", False)
    except SystemExit: ok("rules guard STOPS on a changed rubric", True)
    shutil.rmtree(tmp)
    # fuzz: 2,000 random valid evidence files -> every row 0..10, deterministic, never crashes
    rnd = random.Random(7); bad = 0
    for i in range(2000):
        ev = copy.deepcopy(VAC)
        for k in ("sales", "combined"):
            l = ev["listings"][k]
            l.update(claimed_verified=rnd.choice([0, .5, 1]), checklist_done=rnd.randint(0, l["checklist_total"]), photos_30d=rnd.randint(0, 30),
                     posts_30d=rnd.randint(0, 20), logo=rnd.random() < .5, cover=rnd.random() < .5, newest_review_days=rnd.choice([None, 0, 15, 16, 30, 31, 200]))
            l["last_post_days"] = rnd.randint(0, 30) if l["posts_30d"] else rnd.choice([None, 45, 400])
            if not l["posts_30d"]: l["variety"] = dict(offers=False, events=False, cta=False)
        ev["reviews"].update(google_rating=rnd.choice([None, 1.0, 3.4, 3.5, 4.0, 4.49, 4.5, 5.0]), owner_replies_of_10_newest=rnd.randint(0, 10),
                             facebook=rnd.choice([dict(mode="none"), dict(mode="percent"), dict(mode="stars", within_half=True), dict(mode="stars", within_half=False)]))
        ev["nap"]["directories_agree"] = [rnd.random() < .5 for _ in range(5)]
        p = S.check(ev)
        if p: bad += 1; continue
        raw1, r1 = S.score_rows(ev); raw2, r2 = S.score_rows(copy.deepcopy(ev))
        if not (r1 == r2 and all(0 <= x <= 10 for x in r1) and 0 <= S.overall(r1) <= 10): bad += 1
    ok("2,000 random evidence files: valid, 0..10, same answer twice", bad == 0, bad)

for rnd in range(3):
    print(f"--- round {rnd + 1}"); run_once()
print(f"\n{'ALL PASSED' if fails == 0 else str(fails) + ' FAILED'}")
sys.exit(1 if fails else 0)

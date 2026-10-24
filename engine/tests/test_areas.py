"""Stress test for areas.py (rule 4: areaServed both ways), offline with a fake Google Places. Live 4-dealer test: Oct 22 2026.
Run: python3 tests/test_areas.py"""
import pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
import areas as A
fails = 0
def ok(name, cond, extra=""):
    global fails; fails += 0 if cond else 1; print(("PASS " if cond else "FAIL ") + name + ("" if cond else "  " + str(extra)[:300]))

TOWNS = [  # sentence -> the names the rule pulls out (before Google Places confirms them)
    ("Proudly serving Vacaville, Fairfield, Dixon, Davis, Vallejo, Napa, Suisun City, Woodland, Winters, and the greater Solano County with exceptional service.",
     ["Vacaville", "Fairfield", "Dixon", "Davis", "Vallejo", "Napa", "Suisun City", "Woodland", "Winters", "Solano County"]),
    ("Browse online or visit us in Countryside serving Burr Ridge, La Grange, Hinsdale, and the southwest Chicago suburbs.", ["Burr Ridge", "La Grange", "Hinsdale"]),
    ("White Bear Mitsubishi proudly serves car buyers throughout Minneapolis, St. Paul, and Woodbury.", ["Minneapolis", "St. Paul", "Woodbury"]),
    ("Serving Naperville; Oak Brook; and Hinsdale", ["Naperville", "Oak Brook", "Hinsdale"]),
    ("Serving 60525 and 60526", ["60525", "60526"]),
    ("Serving Size: 2 cups of rice", ["Size"]),            # the pattern pulls "Size"; JEV says no and Google Places rejects it
    ("Napa Valley wine country tours start here", []),
    ("Find a Mitsubishi near you today", []),
    ("Call 708-354-1400 or serve yourself at 60525-1234", []),
    ("Mitsubishi Dealership Greece NY | Rochester | Irondequoit", []),
    ("Visit us at 3800 West Ridge Road, Greece, NY 14626.", []),
]
CODE = [("US", []), ("United States", []), ("Nationwide", []), ({"@type": "Country", "name": "United States"}, []),
        ({"@type": "GeoCircle", "geoRadius": 161000}, []), ("Greece, NY, Rochester, NY, Irondequoit, NY", ["Greece", "Rochester", "Irondequoit"]),
        ("US, Illinois", ["Illinois"]), ("Illinois, Indiana", ["Illinois", "Indiana"]), (["60525", "60526"], ["60525", "60526"]),
        ({"@type": "AdministrativeArea", "name": "Cook County"}, ["Cook County"]), ("Chicagoland", ["Chicagoland"]),
        ([{"@type": "GeoCircle"}, "Naperville"], ["Naperville"]), ("https://en.wikipedia.org/wiki/Des_Plaines,_Illinois", ["Des Plaines"]),
        ("St. Paul, MN", ["St. Paul"]), (None, []), (42, [])]
def place(name, types, lat=41.78, lng=-87.87): return {"displayName": {"text": name}, "types": types, "location": {"latitude": lat, "longitude": lng}}
CONFIRM = [  # (name, what fake Google returns, confirmed name or None)
    ("Hinsdale", place("Hinsdale", ["locality", "political"]), "Hinsdale"),
    ("Napervile", place("Naperville", ["locality"]), None),                         # misspelling: Google corrects it quietly
    ("60999", place("60999", ["postal_code"], 19.4, -99.1), None),                  # fake ZIP that lands in Mexico
    ("Springfield", place("Springfield", ["locality"], 39.8, -89.6), None),         # 300 km away: a different Springfield
    ("Illinois", place("Illinois", ["administrative_area_level_1"], 40.0, -89.0), "Illinois"),   # a state counts, however far its middle is
    ("Oak Brook Mall", place("Oakbrook Center", ["shopping_mall"]), None),          # not a town, county, state or ZIP
    ("Saint Charles", place("St. Charles", ["locality"]), "St. Charles"),           # Saint = St.
    ("Cook County", place("Cook County", ["administrative_area_level_2"]), "Cook County"),
    ("Nowhere", None, None),
    ("Size", place("Size Matters Boutique", ["store"]), None),
]
for rnd in range(3):
    print(f"--- round {rnd + 1}")
    for s, want in TOWNS: ok(f"towns: {s[:50]!r}", A.towns(s) == want and A.serving_rule(s) == bool(want), A.towns(s))
    for v, want in CODE: ok(f"code places: {str(v)[:50]!r}", A.schema_places(v) == want, A.schema_places(v))
    for name, reply, want in CONFIRM:
        got, why = A.confirm(name, "IL", 41.78, -87.87, search=lambda q, r=reply: r)
        ok(f"Places confirm {name!r} -> {want} ({why})", got == want, (got, why))
    pts, d = A.score(["Vacaville", "Sacramento", "Davis", "Fairfield", "Vallejo", "Stockton"],
                     ["Vacaville", "Fairfield", "Dixon", "Davis", "Vallejo", "Napa", "Suisun City", "Woodland", "Winters", "Solano County"],
                     ["Vacaville", "Fairfield", "Davis", "Vallejo"])
    ok("Vacaville live numbers (Oct 22): 4 of 12 -> 0.667", pts == 0.667 and d["code_not_page"] == ["Sacramento", "Stockton"] and len(d["page_not_code"]) == 6, (pts, d))
    ok("nothing named anywhere -> 0", A.score([], [], [])[0] == 0)
    ok("pages name towns, code names none -> 0 (White Bear, Countryside)", A.score([], ["Minneapolis", "Woodbury"], [])[0] == 0)
    ok("code and pages agree on everything -> 2", A.score(["Greece", "Rochester"], ["Rochester", "Greece"], ["Greece", "Rochester"])[0] == 2)
    ok("Saint Paul in code, St. Paul on the page -> one place, matched", A.score(["Saint Paul"], ["St. Paul"], ["Saint Paul"])[0] == 2)
    ok("a code place not on any page earns nothing", A.score(["Stockton"], [], [])[0] == 0)

print(f"\n{'ALL PASSED' if fails == 0 else str(fails) + ' FAILED'}")
sys.exit(1 if fails else 0)

"""Stress test for places.py: every way the lookup can fail, the address / phone / website matching rules, and live
lookups of James Mitsubishi Greece, Vacaville Mitsubishi and Music City Mitsubishi against the Chrome readings.
Live cases need GOOGLE_PLACES_API_KEY; without it they are reported as SKIPPED (never as passed).
Run: python3 tests/test_places.py [rounds]"""
import copy, http.server, json, os, pathlib, sys, threading, time
ENG = pathlib.Path(__file__).resolve().parent.parent; sys.path.insert(0, str(ENG))
import places as P

fails = 0; skipped = 0; calls = 0
def ok(name, cond, extra=""):
    global fails; fails += 0 if cond else 1; print(("PASS " if cond else "FAIL ") + name + ("" if cond else "  " + str(extra)[:400]))

READ = {k: v for k, v in json.loads((ENG / "examples/maps-readings-2026-10-20.json").read_text()).items() if not k.startswith("_")}
GOOD = {"id": "abc", "displayName": {"text": "Vacaville Mitsubishi"}, "formattedAddress": "681 Orange Dr, Vacaville, CA 95687, USA",
        "nationalPhoneNumber": "(707) 926-3135", "websiteUri": "https://www.vacavillemitsubishi.com/?utm_source=gbp", "rating": 4.9,
        "userRatingCount": 172, "businessStatus": "OPERATIONAL", "regularOpeningHours": {"weekdayDescriptions": ["Monday: 9:00 AM - 8:00 PM"]}}

class Fake(http.server.BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def reply(self, data, code=200):
        self.send_response(code); self.send_header("Content-Type", "application/json"); self.end_headers()
        try: self.wfile.write(data if isinstance(data, bytes) else json.dumps(data).encode())
        except BrokenPipeError: pass
    def do_POST(self):
        self.rfile.read(int(self.headers["Content-Length"])); mode = self.path.split("/")[1]
        Fake.mask = self.headers.get("X-Goog-FieldMask")
        if mode == "slow": time.sleep(3)
        if mode == "denied": return self.reply({"error": {"code": 403}}, 403)
        if mode == "garbage": return self.reply(b"<html>")
        if mode == "none": return self.reply({})
        self.reply({"places": [{"id": "abc"}, {"id": "def"}]})
    def do_GET(self):
        mode = self.path.split("/")[1]; Fake.dmask = self.headers.get("X-Goog-FieldMask")
        if mode == "noid": return self.reply({"displayName": {"text": "x"}})
        d = copy.deepcopy(GOOD)
        if mode == "closed": d["businessStatus"] = "CLOSED_TEMPORARILY"
        if mode == "other": d["displayName"]["text"] = "Vacaville Toyota"; d["nationalPhoneNumber"] = "(707) 555-0100"
        self.reply(d)
srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Fake); threading.Thread(target=srv.serve_forever, daemon=True).start()
F = f"http://127.0.0.1:{srv.server_address[1]}/"
VAC_Q = "Vacaville Mitsubishi, 681 Orange Dr, Vacaville, CA 95687"

def round_once(n):
    global skipped, calls
    print(f"--- round {n}")
    # matching rules
    ok("street: 'W Ridge Rd' = 'West Ridge Road'", P._street("3800 W Ridge Rd, Greece, NY 14626") == P._street("3800 West Ridge Road, Greece, NY 14626, USA"))
    ok("street: different number is different", P._street("3801 W Ridge Rd") != P._street("3800 W Ridge Rd"))
    ok("ZIP read from the end, not the street number", P._zip("12345 Main St, Town, NY 14626, USA") == "14626")
    ok("website: tracking tags and www ignored", P._domain("https://www.jamesmitsubishigreece.com/?utm_source=google") == P._domain("jamesmitsubishigreece.com"))
    ok("website: a different site is different", P._domain("factorypartsstore.com") != P._domain("vacavillemitsubishi.com"))
    ok("phone: format ignored", P._digits("(585) 563-2029") == P._digits("+1 585-563-2029"))
    # failure paths: always "skipped" with a reason, never a crash, never a comparison
    r = P.run(VAC_Q, READ[VAC_Q], key="")
    ok("no key -> skipped, audit goes on", r["status"] == "skipped" and "not set" in r["reason"] and "agree" not in r, r)
    r = P.run("  ", READ[VAC_Q], key="k", base=F + "ok")
    ok("empty search -> skipped without a call", r["status"] == "skipped" and r["calls"] == 0, r)
    for mode, needle in (("denied", "HTTP 403"), ("garbage", "JSONDecodeError"), ("none", "no listing found"), ("noid", "reply had no listing")):
        r = P.run(VAC_Q, READ[VAC_Q], key="k", base=F + mode)
        ok(f"bad reply ({mode}) -> skipped", r["status"] == "skipped" and needle in r["reason"] and "agree" not in r, r)
    t0 = time.time(); r = P.run(VAC_Q, READ[VAC_Q], key="k", base=F + "slow", timeout=1)
    ok("server hangs -> gives up after the timeout", r["status"] == "skipped" and time.time() - t0 < 2.5, r)
    # comparisons
    r = P.run(VAC_Q, READ[VAC_Q], key="k", base=F + "ok")
    ok("search asks only for IDs (the free tier)", Fake.mask == "places.id", Fake.mask)
    ok("details ask only for the listed fields", Fake.dmask == P.FIELDS, Fake.dmask)
    ok("same listing -> agree, one paid call, hours returned", r["status"] == "ok" and r["agree"] and r["calls"] == 1 and r["place"]["hours"], r)
    ok("a nearby second match is recorded, not flagged", r["other_matches"] == 1 and r["agree"], r)
    m = dict(READ[VAC_Q], rating=4.8, n_reviews=170)
    r = P.run(VAC_Q, m, key="k", base=F + "ok")
    ok("rating and review count differences are flagged", not r["agree"] and any(x.startswith("rating") for x in r["review"]) and any(x.startswith("review count") for x in r["review"]), r["review"])
    r = P.run(VAC_Q, READ[VAC_Q], key="k", base=F + "other")
    ok("wrong listing -> name and phone flagged", not r["agree"] and any(x.startswith("name") for x in r["review"]) and any(x.startswith("phone") for x in r["review"]), r["review"])
    r = P.run(VAC_Q, READ[VAC_Q], key="k", base=F + "closed")
    ok("temporarily closed -> flagged", any("CLOSED_TEMPORARILY" in x for x in r["review"]), r["review"])
    r = P.run(VAC_Q, None, key="k", base=F + "ok")
    ok("no Chrome reading -> lookup only, no comparison", r["status"] == "ok" and "compare" not in r, r)
    # live
    if not os.environ.get("GOOGLE_PLACES_API_KEY"):
        print("SKIPPED live Places cases (no GOOGLE_PLACES_API_KEY)"); skipped += 1; return None
    r = P.run(VAC_Q, READ[VAC_Q], key="AIza-not-a-real-key")
    ok("wrong key -> skipped (HTTP 400/403)", r["status"] == "skipped" and r["reason"].startswith("HTTP 4"), r)
    seen = {}
    for q, m in READ.items():
        r = P.run(q, m); calls += r["calls"]
        ok(f"{m['name']}: found", r["status"] == "ok", r)
        if r["status"] != "ok": continue
        stable = {x["field"]: x["match"] for x in r["compare"]}
        ok(f"{m['name']}: name, phone, street and website agree with Chrome", all(stable[f] for f in ("name", "phone", "street address", "website")), r["compare"])
        ok(f"{m['name']}: rating and review count agree, or the difference is flagged",
           all(stable[f] or any(x.startswith(f) for x in r["review"]) for f in ("rating", "review count")), r["compare"])
        ok(f"{m['name']}: weekly hours returned", len(r["place"]["hours"]) == 7, r["place"]["hours"])
        seen[m["name"]] = (r["place"]["id"], r["agree"], r["review"])
    return seen

rounds = int(sys.argv[1]) if len(sys.argv) > 1 else 3
res = [round_once(i + 1) for i in range(rounds)]
live = [x for x in res if x]
if len(live) > 1: ok("same listings and same answers in every round", all(x == live[0] for x in live), live)
if live: print("live results:", json.dumps(live[0]))
srv.shutdown()
print(f"\nlive Places detail calls: {calls} (first 1,000 a month free, then ${P.PRICE_DETAILS} each)")
print("ALL PASSED" if fails == 0 and not skipped else ("ALL OFFLINE CASES PASSED" if fails == 0 else f"{fails} FAILED") + f" ({skipped} rounds without live Places)"); sys.exit(1 if fails else 0)

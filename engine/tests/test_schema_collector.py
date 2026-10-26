"""Stress test for collectors/schema_collect.js. Serves each test site on its own local port, runs the
collector in headless Chromium, and checks every evidence field against the expected answer.
Run: <venv>/bin/python tests/test_schema_collector.py [repeats]"""
import asyncio, functools, http.server, json, pathlib, sys, threading, time
from playwright.async_api import async_playwright
ENG = pathlib.Path(__file__).resolve().parent.parent
JS = (ENG / "collectors" / "schema_collect.js").read_text()
SITES = ENG / "tests" / "sites"

def serve(folder):
    h = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(folder))
    class Q(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *a): pass
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(Q, directory=str(folder)))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, f"http://127.0.0.1:{srv.server_address[1]}"

CASES = [
  ("bad @context block + 3 departments (structure copied from a real dealer site, all values made up)", "synth_badctx",
   {"home": "/", "about": "/aboutus.html", "service": "/service.html", "parts": "/orderparts.html", "directions": "/hours.html"},
   dict(pages_with_jsonld=5, parses_cleanly=False, business_type_ok=True, department_entities=3, dept_own_page_address=3, dept_own_phone=2,
        core_fields=6, logo_or_image=True, sameas_google=False, sameas_other=True, hasmap_or_map=False, services_or_offers=False)),
  ("synthetic @graph + @id refs + array block + nav discovery", "synth_graph", None,
   dict(pages_with_jsonld=5, parses_cleanly=True, business_type_ok=True, department_entities=2, dept_own_page_address=2, dept_own_phone=1,
        core_fields=6, logo_or_image=True, sameas_google=True, sameas_other=False, hasmap_or_map=False, services_or_offers=True)),
  ("broken site (bad JSON, string fields, aggregateRating, 404s)", "synth_broken", None,
   dict(pages_with_jsonld=2, parses_cleanly=False, business_type_ok=True, department_entities=1, dept_own_page_address=0, dept_own_phone=0,
        core_fields=4, logo_or_image=False, sameas_google=False, sameas_other=True, hasmap_or_map=False, services_or_offers=False)),
  ("big site (60 extra blocks per page)", "synth_big", None,
   dict(pages_with_jsonld=5, parses_cleanly=True, business_type_ok=True, department_entities=2, dept_own_page_address=2, dept_own_phone=1,
        core_fields=6, logo_or_image=True, sameas_google=True, sameas_other=False, hasmap_or_map=False, services_or_offers=True)),
  ("menu trap (Parts link = homepage, Service link = promo page)", "synth_navtrap", None,
   dict(pages_with_jsonld=5, parses_cleanly=True, business_type_ok=True, department_entities=2, dept_own_page_address=2, dept_own_phone=1,
        core_fields=4, logo_or_image=False, sameas_google=False, sameas_other=False, hasmap_or_map=False, services_or_offers=False)),
]
CASES.append(("blocks added by JavaScript (Countryside pattern) + text JEV judges", "synth_jsonly", None,
   dict(pages_with_jsonld=5, parses_cleanly=True, business_type_ok=True, department_entities=0, dept_own_page_address=0, dept_own_phone=0,
        core_fields=6, logo_or_image=True, sameas_google=False, sameas_other=True, hasmap_or_map=False, services_or_offers=False)))
def _jsonly(o):
    g = o["evidence_schema_rendered"] or {}
    s = o["sentences"]
    return (g.get("department_entities") == 3 and g.get("dept_own_phone") == 2 and g.get("sameas_google") is True and g.get("hasmap_or_map") is True
            and any("department_entities: raw 0" in x for x in o["js_only"]) and o["area_served_raw"] == "US, Illinois"
            and any("Burr Ridge" in x["s"] for x in s["serving"]) and any("valet" in x["s"] for x in s["delivery"]) and any("Maria" in x["s"] for x in s["reviews"])
            and not any("LaGrange Road north" in x["s"] for x in s["serving"]))
EXTRA = {"synth_jsonly": _jsonly, "synth_navtrap": lambda o: o["js_only"] == [] and o["rendered_failed"] >= 1 and any("service /svc-dept.aspx" in x for x in o["pages"]) and any("parts /orderparts.aspx" in x for x in o["pages"]),"synth_graph": lambda o: o["schema_phones"] == ["(707) 532-2052", "(707) 353-4579"] and "about /contactus:" in " ".join(o["pages"]) and "service /service-department:" in " ".join(o["pages"]) and "parts /parts-department:" in " ".join(o["pages"]) and "directions /get-directions:" in " ".join(o["pages"]),
         "synth_broken": lambda o: any("RISK" in n for n in o["notes"]) and any("fail to parse" in n for n in o["notes"]),
         "synth_badctx": lambda o: any("non-schema.org" in n for n in o["notes"])}

async def main(repeats):
    fails = 0; times = []
    async with async_playwright() as p:
        b = await p.chromium.launch()
        for name, folder, paths, want in CASES:
            srv, base = serve(SITES / folder)
            for rnd in range(repeats):
                pg = await b.new_page(); await pg.goto(base + "/")
                t0 = time.perf_counter()
                raw = await pg.evaluate(JS + f"\n;dhapSchema({json.dumps(dict(paths or {}, wait=600))})")
                dt = time.perf_counter() - t0; times.append(dt)
                o = json.loads(raw); ev = o["evidence_schema"]
                if folder == "synth_jsonly": found = json.loads(await pg.evaluate(JS + "\n;dhapFind(['Burr Ridge','Countryside','Naperville','La Grange'])"))
                else: found = None
                bad = {k: (ev.get(k), v) for k, v in want.items() if ev.get(k) != v}
                extra_ok = EXTRA.get(folder, lambda o: o["js_only"] == [] and o["evidence_schema_rendered"] is not None)(o) and (found is None or found == ["Burr Ridge", "Countryside", "La Grange"])
                ok = not bad and extra_ok and "?" not in raw and "=" not in raw and "&" not in raw
                fails += 0 if ok else 1
                print(f"[{'PASS' if ok else 'FAIL'}] run {rnd+1} {name}: {dt*1000:.0f} ms" + ("" if ok else f"  diff={bad} extra_ok={extra_ok}"))
                await pg.close()
            srv.shutdown()
        await b.close()
    print(f"\n{len(CASES)*repeats - fails}/{len(CASES)*repeats} passed; slowest {max(times)*1000:.0f} ms")
    sys.exit(1 if fails else 0)

asyncio.run(main(int(sys.argv[1]) if len(sys.argv) > 1 else 3))

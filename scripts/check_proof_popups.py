#!/usr/bin/env python3
"""RULE K check: popups exist where the rule says and nowhere else, and they work on a phone.
Usage: python3 scripts/check_proof_popups.py report.html [report2.html ...]   (needs Playwright + Chromium)
1. Scope: every hero-fact number (DHAP Summary and the top of AI Visibility), Alert KPI tile (screen 2) and Alert stat card (screen 3)
   must have a popup; NO popup may exist on the bullets under the score or Key Gaps, nor in the DHAP Findings, Why Act Now, Scorecard, Opportunities, Solution, Investment tabs or on the
   AI Visibility cards below the key gaps.
2. Phone: at 390 and 360 px (touch), every popup is tapped: it must open as a pinned sheet fully inside the screen, show its text and
   loaded images, and close with the X; the page must not scroll sideways (scrollWidth vs the real viewport) on any screen or tab.
3. The hint line must be at least 14 px."""
import re, sys, pathlib
from playwright.sync_api import sync_playwright

SEL = ".hero-fact,.kpi-tile,.t-stat"
EXEMPT = re.compile(r"$^")   # nothing is exempt inside the scope
OUT_OF_SCOPE = ".score-desc>div[data-proof], #findings [data-proof], #whyact [data-proof], #scorecard [data-proof], #opportunities [data-proof], #solution [data-proof], #investment [data-proof], #aivisibility .finding-card[data-proof]"
POP_OK = """()=>{const p=document.getElementById('proof-pop');const r=p.getBoundingClientRect();const im=[...p.querySelectorAll('img')];
  return getComputedStyle(p).display!=='none'&&p.classList.contains('pinned')&&r.left>=0&&r.right<=document.documentElement.clientWidth&&r.top>=0&&r.bottom<=innerHeight+1
    &&im.every(i=>i.complete&&i.naturalWidth>0)&&(p.querySelector('.pp-n')||{textContent:''}).textContent.length>20}"""
OVERFLOW = "()=>document.documentElement.scrollWidth-document.documentElement.clientWidth"

def is_alert(path):
    return "hotsheet" in path or "health" in path

def scope_check(pg, path):
    bad = 0
    pg.goto(pathlib.Path(path).resolve().as_uri())
    pg.evaluate("document.querySelectorAll('.step,.screen').forEach(s=>s.style.display='block')" if is_alert(path) else "document.querySelectorAll('.tab-panel').forEach(s=>s.style.display='block')")
    rows = pg.evaluate("""(sel)=>[...document.querySelectorAll(sel)].map(e=>{const l=e.querySelector('.kpi-lbl');
        const c=(l||e).cloneNode(true); c.querySelectorAll('br').forEach(b=>b.replaceWith(' '));
        return [c.textContent.replace(/\\s+/g,' ').trim().slice(0,70), e.dataset.proof||'']})""", SEL)
    print("==", path, f"({len(rows)} tiles/facts/bullets)")
    for label, key in rows:
        if key: print(f"  ok   {key:<18} {label}")
        elif EXEMPT.search(label): print(f"  --   exempt             {label}")
        else: print(f"  MISSING            {label}"); bad += 1
    stray = pg.evaluate("(sel)=>[...document.querySelectorAll(sel)].map(e=>(e.querySelector('.finding-title')||e).textContent.replace(/\\s+/g,' ').trim().slice(0,60))", OUT_OF_SCOPE)
    for s in stray: print(f"  OUT OF SCOPE       popup on: {s}"); bad += 1
    hint = pg.evaluate("(()=>{const h=document.querySelector('.proof-hint');return h?parseFloat(getComputedStyle(h).fontSize):0})()")
    if hint < 14: print(f"  HINT TOO SMALL/MISSING ({hint}px)"); bad += 1
    return bad

def phone_check(b, path):
    bad = 0; alert = is_alert(path)
    for w, h in ((390, 844), (360, 740)):
        ctx = b.new_context(viewport={"width": w, "height": h}, device_scale_factor=2, is_mobile=True, has_touch=True)
        pg = ctx.new_page(); pg.goto(pathlib.Path(path).resolve().as_uri())
        if alert:   # walk the real screens in order and test each one while it is showing
            groups = [("s1", "#s1 [data-proof]", None), ("s2", "#s2 [data-proof]", "2"), ("s3", "#s3 [data-proof]", "3")]
        else:
            pg.evaluate("document.querySelectorAll('.tab-panel').forEach(s=>s.style.display='block')")
            groups = [("all tabs", "[data-proof]", None)]
        for name, sel, go in groups:
            if go:
                pg.evaluate("(n)=>{const b=document.querySelector('.step-btn[data-go=\"'+n+'\"]');b&&b.click()}", go); pg.wait_for_timeout(400)
            ov = pg.evaluate(OVERFLOW); els = pg.locator(sel); n = els.count(); ok = 0
            for i in range(n):
                el = els.nth(i); el.scroll_into_view_if_needed(); el.tap(); pg.wait_for_timeout(250)
                good = pg.evaluate(POP_OK); pg.locator("#proof-pop .pp-x").tap(); pg.wait_for_timeout(150)
                closed = pg.evaluate("getComputedStyle(document.getElementById('proof-pop')).display==='none'")
                if good and closed: ok += 1
                else: print(f"  PHONE FAIL {w}px {name} popup {i} ({el.get_attribute('data-proof')})"); bad += 1
            if ov > 1: print(f"  PHONE OVERFLOW {w}px {name}: page is {ov}px wider than the screen"); bad += 1
            print(f"  phone {w}x{h} {name}: {ok}/{n} popups open and close inside the screen; sideways overflow {max(ov, 0)}px")
        if not alert:   # every real tab, one at a time, for sideways overflow
            pg.reload()
            for t in pg.query_selector_all(".tab-btn"):
                t.click(); pg.wait_for_timeout(200); ov = pg.evaluate(OVERFLOW)
                if ov > 1: print(f"  PHONE OVERFLOW {w}px tab: {ov}px"); bad += 1
        ctx.close()
    return bad

def main(paths):
    bad = 0
    with sync_playwright() as p:
        b = p.chromium.launch(); pg = b.new_page(viewport={"width": 1200, "height": 900})
        for path in paths: bad += scope_check(pg, path)
        for path in paths:
            print("== phone test", path); bad += phone_check(b, path)
        b.close()
    print("RULE K:", "FAILED — fix the lines marked above" if bad else "PASSED")
    return 1 if bad else 0

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

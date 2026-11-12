#!/usr/bin/env python3
"""RULE K check: popups exist where the rule says and nowhere else, and they work on a phone.
Usage: python3 scripts/check_proof_popups.py report.html [report2.html ...]   (needs Playwright + Chromium)
1. Scope: every hero-fact number (DHAP Summary and the top of AI Visibility), Alert KPI tile (screen 2) and Alert stat card (screen 3)
   must have a popup; NO popup may exist on the bullets under the score or Key Gaps, nor in the DHAP Findings, Why Act Now, Scorecard, Opportunities, Solution, Investment tabs or on the
   AI Visibility cards below the key gaps.
2. Phone: at 390 and 360 px (touch), every popup is tapped: its side panel must open fully inside the screen, show its text and
   loaded images, and close with the X; the page must not scroll sideways (scrollWidth vs the real viewport) on any screen or tab.
3. The hint line must be at least 14 px.
4. Desktop (v16.8 side panel): every stat shows a pointing-hand cursor; hovering never opens the panel; a click opens the panel on
   the right over a 50% black shade; a click on the shade closes it and the page is back at exactly the same scroll position."""
import re, sys, pathlib
from playwright.sync_api import sync_playwright

SEL = ".hero-fact,.kpi-tile,.t-stat"
EXEMPT = re.compile(r"$^")   # nothing is exempt inside the scope
OUT_OF_SCOPE = ".score-desc>div[data-proof], #findings [data-proof], #whyact [data-proof], #scorecard [data-proof], #opportunities [data-proof], #solution [data-proof], #investment [data-proof], #aivisibility .finding-card[data-proof]"
POP_OK = """()=>{const p=document.getElementById('proof-pop');const r=p.getBoundingClientRect();const im=[...p.querySelectorAll('img')];
  return p.classList.contains('open')&&getComputedStyle(p).visibility==='visible'&&r.left>=0&&r.right<=document.documentElement.clientWidth&&r.top>=0&&r.bottom<=innerHeight+1
    &&im.every(i=>i.complete&&i.naturalWidth>0)&&(p.querySelector('.pp-n')||{textContent:''}).textContent.length>20}"""
IS_OPEN = "()=>document.getElementById('proof-pop').classList.contains('open')"
SHADE_OK = "()=>{const s=document.getElementById('proof-shade');const c=getComputedStyle(s).backgroundColor;return s.classList.contains('open')&&/rgba\\(0, 0, 0, 0?\\.5\\)/.test(c)}"
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
                el = els.nth(i); el.scroll_into_view_if_needed()
                try:
                    el.tap(timeout=4000)
                except Exception:
                    print(f"  PHONE FAIL {w}px {name} popup {i} ({el.get_attribute('data-proof')}): something on the page covers it, so it can't be tapped"); bad += 1; continue
                pg.wait_for_timeout(450)
                good = pg.evaluate(POP_OK); pg.locator("#proof-pop .pp-x").tap(); pg.wait_for_timeout(150)
                pg.wait_for_timeout(350); closed = not pg.evaluate(IS_OPEN)
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

def desktop_check(b, path):
    """Hover tints only; click opens the right-hand panel over the shade; a click on the shade closes it at the same scroll spot."""
    bad = 0; alert = is_alert(path)
    pg = b.new_page(viewport={"width": 1280, "height": 860}); pg.goto(pathlib.Path(path).resolve().as_uri())
    if alert:
        groups = [("s1", "#s1 [data-proof]", None), ("s2", "#s2 [data-proof]", "2"), ("s3", "#s3 [data-proof]", "3")]
    else:
        groups = [(t, f"#{t} [data-proof]", t) for t in pg.evaluate("[...document.querySelectorAll('.tab-panel')].filter(p=>p.querySelector('[data-proof]')).map(p=>p.id)")]
    ok = n_all = 0
    for name, sel, go in groups:
        if go and alert:
            pg.evaluate("(n)=>{const b=document.querySelector('.step-btn[data-go=\"'+n+'\"]');b&&b.click()}", go); pg.wait_for_timeout(400)
        elif go:
            pg.evaluate("(id)=>{const b=[...document.querySelectorAll('.tab-btn')].find(b=>(b.getAttribute('onclick')||'').includes(\"'\"+id+\"'\")||b.dataset.tab===id);b&&b.click();document.querySelectorAll('.tab-panel').forEach(p=>p.style.display=p.id===id?'block':'none')}", go); pg.wait_for_timeout(250)
        els = pg.locator(sel); n = els.count(); n_all += n
        for i in range(n):
            el = els.nth(i); el.scroll_into_view_if_needed(); pg.mouse.wheel(0, 40); pg.wait_for_timeout(120)
            el.hover(); pg.wait_for_timeout(250)
            fails = []
            if el.evaluate("e=>getComputedStyle(e).cursor") != "pointer": fails.append("cursor is not the pointing hand")
            if pg.evaluate(IS_OPEN): fails.append("hover opened the panel")
            y0 = pg.evaluate("window.pageYOffset")
            el.click(); pg.wait_for_timeout(400)
            if not pg.evaluate(POP_OK): fails.append("panel did not open with its text and images")
            if not pg.evaluate(SHADE_OK): fails.append("50% black shade missing")
            r = pg.evaluate("(()=>{const r=document.getElementById('proof-pop').getBoundingClientRect();return [r.left,r.right,r.top,r.bottom]})()")
            if abs(r[1] - 1280) > 1 or r[0] < 600 or r[2] > 1 or r[3] < 859: fails.append(f"panel not docked full-height on the right {r}")
            pg.mouse.click(40, 430); pg.wait_for_timeout(400)
            if pg.evaluate(IS_OPEN): fails.append("click on the shade did not close it")
            y1 = pg.evaluate("window.pageYOffset")
            if abs(y1 - y0) > 1: fails.append(f"scroll moved {y0} -> {y1}")
            if fails: print(f"  DESKTOP FAIL {name} {el.get_attribute('data-proof')}: " + "; ".join(fails)); bad += 1
            else: ok += 1
    print(f"  desktop 1280x860: {ok}/{n_all} stats tint on hover only, open the side panel on click and close back to the same spot")
    pg.close()
    return bad

def main(paths):
    bad = 0
    with sync_playwright() as p:
        b = p.chromium.launch(); pg = b.new_page(viewport={"width": 1200, "height": 900})
        for path in paths: bad += scope_check(pg, path)
        for path in paths:
            print("== desktop test", path); bad += desktop_check(b, path)
        for path in paths:
            print("== phone test", path); bad += phone_check(b, path)
        b.close()
    print("RULE K:", "FAILED — fix the lines marked above" if bad else "PASSED")
    return 1 if bad else 0

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

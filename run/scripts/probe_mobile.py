#!/usr/bin/env python3
"""Required mobile probe (SKILL.md RULE J): Playwright + headless Chromium at 360/390/430 (is_mobile, touch).
Clicks all 8 DHAP tabs and asserts scrollWidth == viewport and no element past the viewport; walks the three
hot sheet screens; waits for the count-up and prints the final stat values; saves screenshots at 390.
Usage: ~/.dhap-gbp-venv/bin/python probe_mobile.py DHAP.html HEALTH_ALERT.html [shots_dir]   (exit 1 on problems)"""
import asyncio, pathlib, sys
from playwright.async_api import async_playwright

async def main(dhap, hot, shots):
    D = pathlib.Path(dhap).resolve().as_uri(); H = pathlib.Path(hot).resolve().as_uri()
    shots = pathlib.Path(shots); shots.mkdir(parents=True, exist_ok=True)
    problems = []
    async with async_playwright() as p:
        b = await p.chromium.launch()
        for w in (360, 390, 430):
            ctx = await b.new_context(viewport={"width": w, "height": 800}, is_mobile=True, has_touch=True, device_scale_factor=2)
            pg = await ctx.new_page(); errs = []
            pg.on("pageerror", lambda e: errs.append(str(e)))
            pg.on("console", lambda m: errs.append(m.text) if m.type == "error" else None)
            await pg.goto(D); await pg.wait_for_timeout(600)
            tabs = await pg.query_selector_all(".tab-btn")
            if len(tabs) != 8: problems.append((w, "tab count", len(tabs)))
            for i, t in enumerate(tabs):
                await t.click(); await pg.wait_for_timeout(250)
                r = await pg.evaluate("""()=>{const vw=document.documentElement.clientWidth;const p=document.querySelector('.tab-panel.active');
                  const bad=[...p.querySelectorAll('*')].filter(e=>{const r=e.getBoundingClientRect();return r.width>0&&r.right>vw+1&&getComputedStyle(e).position!=='fixed'}).slice(0,4).map(e=>e.tagName+'.'+e.className);
                  return {id:p.id,sw:document.documentElement.scrollWidth,vw,bad}}""")
                if r["sw"] != r["vw"] or r["bad"]: problems.append((w, r))
                if w == 390: await pg.screenshot(path=str(shots / f"dhap_390_{i}_{r['id']}.png"))
            await pg.goto(H); await pg.wait_for_timeout(500)
            for sel in ("#s1 .step-btn", "#s2 .step-btn"):
                await pg.click(sel); await pg.wait_for_timeout(300)
                sw = await pg.evaluate("[document.documentElement.scrollWidth, document.documentElement.clientWidth]")
                if sw[0] != sw[1]: problems.append((w, "health-alert overflow", sw))
            if w == 390:
                await pg.evaluate("document.querySelector('.impact-box').scrollIntoView()"); await pg.wait_for_timeout(3500)
                print("count-up finals:", await pg.evaluate("[...document.querySelectorAll('.t-stat')].map(c=>c.querySelector('.t-head').textContent+'='+c.querySelector('.t-val').textContent+' '+c.querySelector('.t-status').textContent)"))
                await pg.screenshot(path=str(shots / "health_alert_screen3_390.png"))
                await pg.goto(H); await pg.wait_for_timeout(400)
                el = await pg.query_selector(".score-row"); await el.scroll_into_view_if_needed(); await el.screenshot(path=str(shots / "health_alert_slider_390.png"))
            if errs: problems.append((w, "console errors", errs[:3]))
            await ctx.close()
        await b.close()
    print("PROBLEMS:", problems or "none"); sys.exit(1 if problems else 0)

if __name__ == "__main__":
    if len(sys.argv) < 3: sys.exit(__doc__)
    asyncio.run(main(sys.argv[1], sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else "probe_shots"))

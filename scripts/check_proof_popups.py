#!/usr/bin/env python3
"""RULE K check: every tile, card and hero fact in a built DHAP or Digital Health Alert must have an evidence popup.
Usage: python3 scripts/check_proof_popups.py report.html [report2.html ...]   (needs Playwright + Chromium)
Prints each tile/card with its popup key; exits 1 if a non-exempt one has none. Exempt (no audit claim): omni-social pitch cards,
the methodology card, the CLIKsearch closing box, the MiDS reimbursement card, the competitor industry-pattern bullet, and blurred locked findings (not selected here)."""
import re, sys, pathlib
from playwright.sync_api import sync_playwright

SEL = ".hero-fact,.score-desc>div,.kpi-tile,.t-stat,.finding-card"
EXEMPT = re.compile(r"cross-platform social|6-platform social|how this assessment was built|closes every verified gap|mids reimbursement|competitors are posting", re.I)

def main(paths):
    bad = 0
    with sync_playwright() as p:
        b = p.chromium.launch(); pg = b.new_page(viewport={"width": 1200, "height": 900})
        for path in paths:
            pg.goto(pathlib.Path(path).resolve().as_uri())
            if "hotsheet" in path or "health" in path:
                pg.evaluate("document.querySelectorAll('.step').forEach(s=>s.style.display='block')")
            rows = pg.evaluate("""(sel)=>[...document.querySelectorAll(sel)].map(e=>{const l=e.querySelector('.kpi-lbl,.finding-title');
                return [(l?l.textContent:e.textContent).replace(/\\s+/g,' ').trim().slice(0,70), e.dataset.proof||'']})""", SEL)
            print("==", path, f"({len(rows)} tiles/cards)")
            for label, key in rows:
                if key: print(f"  ok   {key:<13} {label}")
                elif EXEMPT.search(label): print(f"  --   exempt        {label}")
                else: print(f"  MISSING       {label}"); bad += 1
        b.close()
    print("RULE K:", "FAILED — add evidence for the cards marked MISSING" if bad else "PASSED")
    return 1 if bad else 0

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

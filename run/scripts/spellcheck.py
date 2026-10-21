#!/usr/bin/env python3
"""Advisory spell check of the VISIBLE text of the report files (SKILL.md: 'Spell check before every delivery').
Run with the venv python: ~/.dhap-gbp-venv/bin/python spellcheck.py file1.html file2.html [--allow word ...]
Prints words the dictionary does not know (review them by hand), plus the MIDS and straight-apostrophe scans."""
import re, sys, html, pathlib
from spellchecker import SpellChecker

ALLOW = set("""clik clikdata cliksearch gbp seo aeo geo mids mmna areaserved sameas hasmap json ld autodealer autorepair
autopartsstore faqpage jsonld schema nap kpi omni outlander phev mirage mitsubishi eclipse ev depts dept pct url urls
cta ctas ai aio faq faqs tm std chatgpt perplexity gemini copilot bluesky pinterest linkedin instagram yelp bing carfax
locator unclaimed onboarding indexable unconfigured localbusiness mo""".split())

def main(argv):
    allow = set(ALLOW); files = []; i = 0
    while i < len(argv):
        if argv[i] == "--allow":
            i += 1
            while i < len(argv) and not argv[i].startswith("--"): allow.add(argv[i].lower()); i += 1
        else: files.append(argv[i]); i += 1
    sp = SpellChecker()
    for f in files:
        t = pathlib.Path(f).read_text(encoding="utf-8")
        t = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", t, flags=re.S)
        vis = html.unescape(re.sub(r"<[^>]+>", " ", t))
        out = set()
        for w in re.findall(r"[A-Za-z][A-Za-z'’]+", vis):
            b = re.sub(r"('s)$", "", w.replace("’", "'")).lower().strip("'")
            if len(b) < 4 or b in allow or w.isupper(): continue
            if sp.unknown([b]) and sp.unknown([b.rstrip("s")]) and sp.unknown([b[:-2]] if b.endswith("es") else [b]): out.add(w)
        mids = len(re.findall(r"\bMIDS\b", vis)); straight = vis.count(chr(39)); curly = vis.count(chr(8217))
        print(pathlib.Path(f).name + ": unknown words -> " + str(sorted(out) or "none"))
        print("   MIDS (must be 0): %d | straight apostrophes: %d | curly: %d" % (mids, straight, curly))

if __name__ == "__main__": main(sys.argv[1:])

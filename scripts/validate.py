#!/usr/bin/env python3
"""Consistency check for the DHAP GBP skill repository.
Fails (exit 1) if versions disagree, internal identifiers leak into this public repository,
or a reference template breaks a locked rule.
Run locally:  python3 scripts/validate.py
Runs automatically on every pull request and push (see .github/workflows/validate.yml)."""
import re
import sys
from pathlib import Path

root = Path(__file__).resolve().parent.parent
errors = []

def read(rel):
    p = root / rel
    if not p.exists():
        errors.append(f"missing file: {rel}")
        return ""
    return p.read_text(encoding="utf-8")

# ---- 1. one version, three places -------------------------------------------------
version = read("VERSION").strip()
skill = read("SKILL.md")
log = read("CHANGELOG.md")
m = re.match(r"# DHAP GBP — v(\d+(?:\.\d+)?)", skill)
if not m:
    errors.append('SKILL.md must start with "# DHAP GBP — vN" (first line)')
elif m.group(1) != version:
    errors.append(f"SKILL.md says v{m.group(1)} but VERSION says {version}")
m2 = re.search(r"^## v(\d+(?:\.\d+)?) ", log, re.M)
if not m2:
    errors.append('CHANGELOG.md needs a newest entry starting "## vN — date — ..."')
elif m2.group(1) != version:
    errors.append(f"newest CHANGELOG entry is v{m2.group(1)} but VERSION says {version}")
if f"Using DHAP GBP v{version}." not in skill:
    errors.append(f'SKILL.md governance rule must say: Using DHAP GBP v{version}.')

# ---- 2. public hygiene: nothing internal in a public repository ---------------------
LEAKS = ["H6HvdoUbQOSKh6FgJZBP", "17275944068", "sean@clikdata.com", '"locationId": "E1a3']
for f in root.rglob("*"):
    if f.is_file() and ".git/" not in str(f) and f.name != "validate.py":
        try:
            t = f.read_text(encoding="utf-8")
        except Exception:
            continue
        for leak in LEAKS:
            if leak in t:
                errors.append(f"{f.relative_to(root)}: internal value must not be public: {leak!r}")

# ---- 3. locked rules in the reference templates (skipped until templates are added) ----
BANNED = ["aggregateRating", "AggregateRating", "Review Markup", "REVIEWS_UNMARKED", "Markup Missing",
          "review-rating", "Review-rating", "machine-readable", "Schema-Invisible", "review guidelines",
          "reputation signal", "excluded from schema-based rich results", "invisible to Google",
          "review-enhanced", "highest-impact schema fix", "Deploy aggregateRating",
          "Reviews Out of Rich Results", "Review Schema Deployed", "4 cities", "SGE", "MIDS"]
EXEMPT = ["without any review markup in the structured data"]

def div_depth(t):
    return len(re.findall(r"<div[ >]", t)) - len(re.findall(r"</div>", t))

templates = sorted((root / "templates").glob("*.html")) if (root / "templates").exists() else []
if not templates:
    print("note: no templates found in templates/ — template checks skipped")
for f in templates:
    t = f.read_text(encoding="utf-8")
    chk = t
    for e in EXEMPT:
        chk = chk.replace(e, "")
    for b in BANNED:
        if b in chk:
            errors.append(f"{f.name}: banned text found: {b!r}")
    if div_depth(t) != 0:
        errors.append(f"{f.name}: unbalanced <div> tags")
    if "hotsheet" in f.name:
        if "noindex,nofollow" not in t:
            errors.append(f"{f.name}: missing noindex meta")
        if "CLIKsearch" in t:
            errors.append(f"{f.name}: hot sheet must not name CLIKsearch")
        if "color:#fbbf24;\">Digital Health Alert<" not in t:
            errors.append(f"{f.name}: header title must be yellow with no trademark mark")
        if "Critical Alerts Identified" not in t:
            errors.append(f"{f.name}: missing DOS card final line")
        if "SEE ALL ALERTS" not in t or "SEE REVENUE IMPACT" not in t or "ACCESS THE FULL REPORT" not in t:
            errors.append(f"{f.name}: missing a screen button")
    else:
        if "MOBILE LAYOUT" not in t:
            errors.append(f"{f.name}: missing mobile layout block (RULE J)")
        if "No areaServed in Site Schema" not in t:
            errors.append(f"{f.name}: missing the areaServed finding")
        if "mitsubishi" in f.name.lower():
            if "Jessica is an AI assistant" not in t or "Live Support" not in t:
                errors.append(f"{f.name}: Mitsubishi report needs the Live Support widget")
            if "__JESSICA" in t:
                errors.append(f"{f.name}: unfilled widget placeholder")

if errors:
    print("VALIDATION FAILED")
    for e in errors:
        print(" -", e)
    sys.exit(1)
print(f"OK — DHAP GBP v{version}: versions agree, no internal values leaked, {len(templates)} template(s) pass.")

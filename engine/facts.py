#!/usr/bin/env python3
"""DHAP GBP engine — facts gate ("never restate a number you can't source").
Every number and phone number written in content.json must be traceable to the evidence: a phone in evidence.facts.phones,
a number in evidence.facts.numbers or anywhere in the evidence values, a computed score, or a fixed program fact that the
repository/knowledge base states (listed below with its source). Anything else is reported as UNSOURCED and fails the build.
Usage: python3 facts.py evidence.json content.json"""
import json, re, sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent)); import score as S
# fixed program facts stated in SKILL.md / the knowledge base (not dealer facts)
PROGRAM = {"8": "posts a month, Sales (benchmark)", "4": "posts a month, Service/Parts; photos a month", "16": "posts + photos a month",
           "60": "60+ directories", "62.4": "results label", "47.8": "results", "28.7": "results", "29": "results", "21.7": "results",
           "21": "dealer locations", "72": "hours to go-live / months APR", "90": "days to results", "100": "% reimbursement", "24": "24/7",
           "7": "24/7, one photo per week (7 days)", "6": "6 social platforms", "10": "10 newest reviews", "30": "30-day window", "2024": "results year",
           "15": "Sales review window", "3": "3-Pack"}
def norm_phone(s): d = re.sub(r"\D", "", s); return d[-10:] if len(d) >= 10 else None
def strings(o):
    if isinstance(o, str): yield o
    elif isinstance(o, dict):
        for v in o.values(): yield from strings(v)
    elif isinstance(o, list):
        for v in o: yield from strings(v)
def numbers_in(o):
    out = set()
    for s in strings(o):
        for m in re.findall(r"(?<![\w.])\d+(?:\.\d+)?", s): out.add(m.lstrip("0") or "0")
    def walk(x):
        if isinstance(x, bool): return
        if isinstance(x, (int, float)): out.add(str(int(x)) if float(x).is_integer() else str(x))
        elif isinstance(x, dict): [walk(v) for v in x.values()]
        elif isinstance(x, list): [walk(v) for v in x]
    walk(o); return out
def check(ev, content):
    phones_ok = {norm_phone(p) for p in ev.get("facts", {}).get("phones", [])}
    allowed = numbers_in(ev) | set(PROGRAM)
    raw, rows = S.score_rows(ev); allowed |= {f"{x:.1f}" for x in rows} | {str(int(x)) for x in rows if float(x).is_integer()} | {f"{S.overall(rows):.1f}"}
    if S.ai_visibility.applies(ev):   # v16.0: the AI visibility counts and scores are computed from the evidence
        V = S.ai_visibility.scores(ev)
        allowed |= {str(V["named"]), str(V["answered"]), str(round(10 * V["row"]))} | {str(q[k]) for q in V["questions"].values() for k in ("named", "answered", "score")}
    allowed_f = set()
    for a in allowed:
        try: allowed_f.add(float(a))
        except ValueError: pass
    problems = []
    times_ok = set(ev.get("facts", {}).get("times", []))
    skip_keys = {"report_id", "dhap_url"}
    content = {k: v for k, v in content.items() if k not in skip_keys}
    for s in strings(content):
        for t in re.findall(r"\b\d{1,2}:\d{2}\b", s):
            if t not in times_ok: problems.append(f"time {t} is not in evidence.facts.times  <- {s.strip()[:70]!r}")
        s = re.sub(r"\b\d{1,2}:\d{2}\b", " ", s)
        text = re.sub(r"&#\d+;|&[a-z]+;|<[^>]+>", " ", s)
        for ph in re.findall(r"\(?\b\d{3}\)?[\s.-]\d{3}[\s.-]\d{4}\b", text):
            if norm_phone(ph) not in phones_ok: problems.append(f"phone {ph} is not in evidence.facts.phones  <- {text.strip()[:70]!r}")
        text = re.sub(r"\(?\b\d{3}\)?[\s.-]\d{3}[\s.-]\d{4}\b", " ", text)
        for n in re.findall(r"(?<![\w.,])\d{1,3}(?:,\d{3})+(?:\.\d+)?(?![\w,])|(?<![\w.,])\d+(?:\.\d+)?(?![\w])", text):   # 1,599 is one number
            if float(n.replace(",", "")) not in allowed_f: problems.append(f"number {n} is not in the evidence  <- {text.strip()[:70]!r}")
    return problems
if __name__ == "__main__":
    ev, c = json.load(open(sys.argv[1])), json.load(open(sys.argv[2]))
    p = check(ev, c)
    print("FACTS GATE: PASSED (every number and phone traces to the evidence)" if not p else "FACTS GATE: FAILED\n  - " + "\n  - ".join(dict.fromkeys(p)))
    sys.exit(1 if p else 0)

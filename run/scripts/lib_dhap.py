"""Helpers for the dhap-gbp-run skill.

NOTHING in here restates the DHAP GBP rules as the source of truth. The rules live in SKILL.md of the
Clikdata2/dhap-gbp-skill repository and are re-read on every run. This file only (a) turns recorded
audit evidence into the eight rubric rows exactly as the repository rubric describes them, so the
arithmetic is the same every run, (b) applies the status rule, (c) names output files, and (d) holds
small HTML helpers. If the repository rubric or status rule changes, update this file in the same
session and run `python3 lib_dhap.py selftest`.
"""
import json, re, sys, pathlib, datetime

# ----------------------------------------------------------------------------- naming
def slugify(name):
    """'Vacaville Mitsubishi' -> 'vacaville-mitsubishi' (dealership name only, lowercase, hyphens)."""
    s = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return s

def date_tag(d=None):
    """MM-DD-YY of the report/audit date, e.g. 10-20-26."""
    d = d or datetime.date.today()
    if isinstance(d, str):
        d = datetime.date.fromisoformat(d)
    return d.strftime("%m-%d-%y")

def file_names(dealer, d=None):
    s, t = slugify(dealer), date_tag(d)
    return {
        "dhap": f"{s}_dhap_{t}.html",
        "health_alert": f"{s}_health-alert_{t}.html",
        "evidence": f"audit_evidence_{s}_{t}.md",
    }

# ----------------------------------------------------------------------------- rubric
# One scorer only: the engine's (engine/score.py), so the non-Mitsubishi path can never score differently.
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "engine"))
import score as _S
ROW_NAMES = _S.ROW_NAMES

def score_rows(ev):
    """Return (rows_unrounded, rows_rounded) from the engine; Google's age labels are turned into day counts first."""
    return _S.score_rows(_S.resolve_ages(ev))

def overall(rows): return _S.overall(rows)

def status_from_lowest(rows):
    """Weakest-link status rule (repo v14): lowest <=5.0 Critical; >5.0 and <7.0 Major Issues; 7.0-8.9 Needs Improvement; >=9.0 Fully Optimized."""
    low = min(rows)
    name = ROW_NAMES[rows.index(low)]
    if low <= 5.0: label, icon, color = "Critical", "\U0001F534", "#dc2626"
    elif low < 7.0: label, icon, color = "Major Issues", "\U0001F7E0", "#ea580c"
    elif low < 9.0: label, icon, color = "Needs Improvement", "\U0001F7E1", "#ca8a04"
    else: label, icon, color = "Fully Optimized", "\U0001F7E2", "#15803d"
    return {"label": label, "icon": icon, "color": color, "lowest_row": name, "lowest_value": low}

# ----------------------------------------------------------------------------- HTML helpers
MITS_LOGO = "https://storage.googleapis.com/crm-conversations-ai-production/ask-ai-attachments/pD1xrcLAci2kVYlEsUSa/E1a3Kiox27Z6n5KNmx1O/kdKQLwzGTkPvz8og4h4y/c3567bcd-fe66-4a7e-b00d-119bd43fa5cd.png"

def mits_pill(label="CLIKsearch"):
    return f'<span class="pill pill-blue"><img src="{MITS_LOGO}" style="height:12px;vertical-align:middle;margin-right:3px;"> {label}</span>'

def verified_tag(date=None):
    return '<span class="tag-green-sm">Audit Verified' + (f' &middot; {date}' if date else '') + '</span>'

def inferred_tag():
    return '<span class="tag-amber-sm">Inferred</span>'

def swap(text, start_marker, end_marker, new):
    """Replace text[start_marker:end_marker) with `new` (markers are HTML comments in the template)."""
    i = text.index(start_marker); j = text.index(end_marker)
    return text[:i] + new + text[j:]

def card(kind, icon, title, body, pill="", tag=""):
    t = f"{title} &nbsp;{tag}" if tag else title
    p = f"\n    {pill}" if pill else ""
    return (f'  <div class="finding-card {kind}">\n    <div class="finding-header"><span class="finding-icon">{icon}</span>'
            f'<span class="finding-title">{t}</span></div>\n    <div class="finding-body">{body}</div>{p}\n  </div>\n')

def dot(color, text, last=False):
    mb = "" if last else "margin-bottom:7px;"
    return (f'<div style="display:flex;align-items:flex-start;gap:9px;{mb}"><span style="color:{color};font-weight:900;'
            f'font-size:1rem;flex-shrink:0;">&#9679;</span><span>{text}</span></div>')

def bar_color(v):
    return "#22c55e" if v >= 9 else "#f59e0b" if v >= 7 else "#f97316" if v > 5 else "#e82b39"

def score_bar(v):
    return f'<div class="bar-wrap"><div class="bar-fill" style="width:{round(v*10)}%;background:{bar_color(v)};"></div></div>{v:.1f}/10'

def div_depth(t):
    return len(re.findall(r"<div[ >]", t)) - len(re.findall(r"</div>", t))

# ----------------------------------------------------------------------------- self-test
def selftest():
    ref = json.loads((pathlib.Path(__file__).resolve().parent.parent / "references" / "evidence-example-vacaville.json").read_text())
    raw, rows = score_rows(ref)
    assert rows == [10.0, 8.0, 6.4, 6.9, 5.8, 5.3, 8.0, 6.7], rows     # v15: areaServed both ways (Oct 22 2026)
    assert overall(rows) == 7.1
    st = status_from_lowest(rows)
    assert st["label"] == "Major Issues" and st["lowest_row"] == "Google Maps / NAP Consistency", st
    assert file_names("Vacaville Mitsubishi", "2026-10-20") == {
        "dhap": "vacaville-mitsubishi_dhap_10-20-26.html",
        "health_alert": "vacaville-mitsubishi_health-alert_10-20-26.html",
        "evidence": "audit_evidence_vacaville-mitsubishi_10-20-26.md"}
    print("selftest OK:", rows, overall(rows), st["label"])

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "selftest": selftest()
    elif len(sys.argv) > 2 and sys.argv[1] == "names": print(json.dumps(file_names(sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else None), indent=2))
    elif len(sys.argv) > 2 and sys.argv[1] == "score":
        raw, rows = score_rows(json.load(open(sys.argv[2])))
        print(json.dumps({"rows": rows, "overall": overall(rows), "status": status_from_lowest(rows)}, indent=2, ensure_ascii=False))
    else: print("usage: lib_dhap.py selftest | names '<Dealer Name>' [YYYY-MM-DD] | score evidence.json")

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

# ----------------------------------------------------------------------------- rubric (v13 rubrics)
ROW_NAMES = ["GBP Claimed & Verified", "Profile Completeness", "Photos & Visual Presence", "Reviews & Reputation",
             "GBP Posts & Engagement", "Google Maps / NAP Consistency", "LocalBusiness Schema", "Schema Field Completeness"]
BENCH_POSTS = {"sales": 8, "service": 4, "parts": 4}
WEIGHT = {"sales": 50, "service": 25, "parts": 25}
REVIEW_WINDOW = {"sales": (15, 1.5), "service": (30, .75), "parts": (90, .75)}   # days, points

def _roles(ev):
    """Map each existing listing to the department roles it covers. A combined Service & Parts
    listing covers BOTH roles (same data counted for each)."""
    L = ev["listings"]
    roles = {}
    if L.get("sales"): roles["sales"] = L["sales"]
    if L.get("service"): roles["service"] = L["service"]
    if L.get("parts"): roles["parts"] = L["parts"]
    if L.get("combined"):
        roles["service"] = L["combined"]; roles["parts"] = L["combined"]
    return roles

def _w(roles):
    tot = sum(WEIGHT[r] for r in roles)
    return {r: WEIGHT[r] / tot for r in roles}

def score_rows(ev):
    """Return (rows_unrounded, rows_rounded). `ev` is the evidence dict (see references/evidence-template.json)."""
    roles = _roles(ev); w = _w(roles); L = ev["listings"]
    def wavg(f): return sum(w[r] * f(roles[r], r) for r in roles)

    # 1 Claimed & Verified: 8 = every listing claimed+verified (averaged) ; 2 = no duplicate/unclaimed listing in the audit search
    uniq = {id(v): v for v in roles.values()}.values()
    r1 = 8 * (sum(l.get("claimed_verified", 0) for l in uniq) / len(uniq)) + (0 if ev["claimed"].get("duplicate_or_unclaimed_found") else 2)

    # 2 Profile Completeness: structure 4 + information 6
    struct = (2 if L.get("sales") else 0) + (1 if (L.get("service") or L.get("combined")) else 0) + (1 if (L.get("parts") or L.get("combined")) else 0)
    def pct(l): return l["checklist_done"] / l["checklist_total"]
    info = 0
    if L.get("sales"): info += 2 * pct(L["sales"])
    if L.get("combined"): info += 4 * pct(L["combined"])
    else:
        if L.get("service"): info += 2 * pct(L["service"])
        if L.get("parts"): info += 2 * pct(L["parts"])
    r2 = 0 if not roles else struct + info

    # 3 Photos: 6 cadence + 2 logo/cover + 2 coverage (weighted 50/25/25 over existing, renormalised)
    cad = 6 * wavg(lambda l, r: min(l["photos_30d"] / 4, 1))
    lc = wavg(lambda l, r: (1 if l.get("logo") else 0) + (1 if l.get("cover") else 0))
    cov = wavg(lambda l, r: 2 * (sum(1 for k in ("exterior", "interior_or_team", "department") if l.get("coverage", {}).get(k)) / 3))
    r3 = cad + lc + cov

    # 4 Reviews & Reputation
    rt = ev["reviews"]["google_rating"]
    rating = 3 if rt >= 4.5 else 2 if rt >= 4.0 else 1 if rt >= 3.5 else 0
    earned = mx = 0
    for r in roles:
        days, pts = REVIEW_WINDOW[r]; d = roles[r]["newest_review_days"]
        mx += pts; earned += pts if d <= days else pts / 2 if d <= 2 * days else 0
    flow = 3 * earned / mx if mx else 0
    owner = 2 * ev["reviews"]["owner_replies_of_10_newest"] / 10
    fb = ev["reviews"]["facebook"]            # {"mode": "stars"|"percent"|"none", "within_half": bool}
    fbpt = 1 if (fb["mode"] == "stars" and fb.get("within_half")) else 0
    site = 1 if ev["reviews"]["real_reviews_visible_on_site"] else 0
    r4 = rating + flow + owner + fbpt + site
    if fb["mode"] == "percent":               # point dropped, row rescaled to 10
        r4 = (r4 - fbpt) / 9 * 10

    # 5 Posts: 6 cadence + 2 recency + 2 variety
    cad = 6 * wavg(lambda l, r: min(l["posts_30d"] / BENCH_POSTS[r], 1))
    rec = wavg(lambda l, r: 2 if l["last_post_days"] <= 7 else 1 if l["last_post_days"] <= 14 else 0)
    var = wavg(lambda l, r: 2 * (sum(1 for k in ("offers", "events", "cta") if l.get("variety", {}).get(k)) / 3))
    r5 = cad + rec + var

    # 6 NAP: 4 google-vs-site (name/address/phone) + 4 five-directory sample + 1 dept phones + 1 pin
    n = ev["nap"]
    r6 = 4 * (n["google_vs_site_fields_matching"] / 3) + 4 * (sum(1 for x in n["directories_agree"] if x) / 5) \
        + (1 if n["dept_phones_ok"] in (True, None) else 0) + (1 if n["map_pin_ok"] else 0)

    # 7 LocalBusiness Schema structure
    s = ev["schema"]
    r7 = 3 * (s["pages_with_jsonld"] / 5) + (1 if s["business_type_ok"] else 0) + s["department_entities"] \
        + (1 if s["parses_cleanly"] else 0) + s["dept_own_page_address"] / 3 + s["dept_own_phone"] / 3

    # 8 Schema fields
    r8 = 3 * (s["core_fields"] / 6) + (1 if s["logo_or_image"] else 0) + (1 if s["sameas_google"] else 0) + (1 if s["sameas_other"] else 0) \
        + (2 if s["areaserved"] else 0) + (1 if s["hasmap_or_map"] else 0) + (1 if s["services_or_offers"] else 0)

    raw = [r1, r2, r3, r4, r5, r6, r7, r8]
    return raw, [round(x, 1) for x in raw]

def overall(rows): return round(sum(rows) / len(rows), 1)

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
    assert rows == [10.0, 8.0, 6.4, 6.9, 5.8, 5.3, 8.0, 8.0], rows
    assert overall(rows) == 7.3
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

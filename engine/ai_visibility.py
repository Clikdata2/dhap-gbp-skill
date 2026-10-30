#!/usr/bin/env python3
"""DHAP GBP engine — AI visibility check (v16.0, mandatory on every audit dated on or after Oct 27 2026; decided by Travis).

Replaces the v15.1 AI answer check. The old check named the dealer in the question, which skews the answer (a false
positive). This one asks what shoppers actually ask, with only the dealer's city and state, and counts how often AI names
the dealer. No dealer name and no brand is added to a question.
  questions  v16.1 (audits dated Oct 28 2026 or later): the 5 in QUESTIONS (2 Sales — new and used, 2 Service, 1 Parts),
             word for word, {city_st} = the dealer's "City, ST". The same 5 every run. v16.0 audits (Oct 27 2026) keep
             the 7 in QUESTIONS_V160.
  tools      v16.1 (audits dated Oct 28 2026 or later): the 5 in TOOLS — ChatGPT, Gemini, Google AI (AI Overview or AI
             Mode), Claude, Brave — asked through their APIs (run/scripts/ai_api_runner.py): 125 answers. Copilot and
             Perplexity were dropped (robot checks and sign-in walls in the browser; decided by Travis Oct 27 2026).
             v16.0 audits (Oct 27 2026) keep the 7 in TOOLS_V160 asked in the browser: 490 answers.
             Each question is asked RUNS (5; 10 on v16.0) times on each tool, in a fresh chat each time.
  record     every answer word for word, every business it names with its type, and whether it names this dealer.
             v16.1: only the TOP (2) businesses each answer names first, in the answer's order, and whether this dealer
             is one of them (the answer text is kept as proof).
             A tool that will not answer (sign-in wall, error, nothing within 60 seconds) is recorded as blocked with the
             reason; never retried. (v16.1: an API's rate limit or server error is retried with backoff; that is the API
             asking us to slow down, not a robot check. An ask that still fails is recorded as blocked.)
  score      per question: answers naming the dealer (v16.1: in their top 2) / answers given for that question x 100.
             The category (scorecard row 9, "AI Answer Visibility"): answers naming the dealer / all answers given x 10
             (0..10; 10% = 1). Blocked answers are not counted on either side.
  outputs    the rep brief gets the business named most (v16.1: the 2 named most often in the top 2) for each question
             on each tool; the spreadsheet
             <slug>_ai-answers_<MM-DD-YY>.xlsx has one tab per tool and one row per answer.
Evidence: ai_visibility = {method, city_st, answers: [{tool, q, run, status: answered|blocked, asked, when,
          answer, businesses: [{name, type, brand?}], named, reason?, proof?}]}
Usage:
  python3 ai_visibility.py check evidence.json            -> the problems, or AI VISIBILITY OK
  python3 ai_visibility.py score evidence.json            -> per-question scores and the category score (JSON)
  python3 ai_visibility.py brief evidence.json            -> the rep-brief winners table (markdown)
  python3 ai_visibility.py sheet evidence.json OUT.xlsx   -> the spreadsheet, one tab per tool
  python3 ai_visibility.py questions "Greece, NY"         -> the 5 questions to ask (v16.1), word for word
"""
import collections, datetime, json, pathlib, re, sys

START = "2026-10-27"
START_161 = "2026-10-28"   # v16.1: 5 tools through their APIs
RUNS = 5         # v16.1
RUNS_V160 = 10
TOP = 2          # v16.1: only the first 2 businesses each answer names are recorded and scored
QUESTIONS = [   # v16.1 (id, department, question) — word for word; never add the dealer's name or a brand
    ("sales_new_family_suv", "sales", "best family SUV under 40k near {city_st}"),
    ("sales_used_midsize_suv", "sales", "used midsize SUV near {city_st}"),
    ("service_oil_change_near", "service", "oil change near {city_st}"),
    ("service_brake_job", "service", "brake job near {city_st}"),
    ("parts_brake_pads", "parts", "brake pads for my SUV near {city_st}"),
]
QUESTIONS_V160 = [
    ("sales_dealership", "sales", "What's the best car dealership near {city_st}?"),
    ("sales_new_suv", "sales", "Where can I get a good deal on a new SUV near {city_st}?"),
    ("sales_used_car", "sales", "Where's the best place to buy a used car near {city_st}?"),
    ("service_oil_change", "service", "Where's the cheapest place to get my oil changed today near {city_st}?"),
    ("service_tires", "service", "Where can I get a good deal on tires near {city_st}?"),
    ("parts_wipers", "parts", "Where can I buy windshield wipers for my car near {city_st}?"),
    ("parts_car_parts", "parts", "Where's the best place to buy car parts near {city_st}?"),
]
TOOLS = ("chatgpt", "gemini", "google_ai", "claude", "brave")   # v16.1
TOOLS_V160 = ("chatgpt", "gemini", "perplexity", "google_ai", "claude", "copilot", "brave")
NAME = {"chatgpt": "ChatGPT", "gemini": "Gemini", "perplexity": "Perplexity", "google_ai": "Google AI", "claude": "Claude",
        "copilot": "Copilot", "brave": "Brave"}
TYPES = ("dealership", "oil_change", "tire_shop", "parts_store", "repair_shop", "retailer", "other")
TYPE_LABEL = {"dealership": "dealership", "oil_change": "oil-change shop", "tire_shop": "tire shop", "parts_store": "parts store",
              "repair_shop": "repair shop", "retailer": "retailer", "other": "other"}
DEPT_LABEL = {"sales": "Sales", "service": "Service", "parts": "Parts"}

def applies(ev): return str(ev.get("audit_date", "")) >= START
def v161(ev): return str(ev.get("audit_date", "")) >= START_161
def tools(ev): return TOOLS if v161(ev) else TOOLS_V160
def questions(ev): return QUESTIONS if v161(ev) else QUESTIONS_V160
def runs(ev): return RUNS if v161(ev) else RUNS_V160
def ask(q_id, city_st): return next(q for i, _, q in QUESTIONS + QUESTIONS_V160 if i == q_id).format(city_st=city_st)
def fold(name): return " ".join(re.sub(r"[^a-z0-9&]+", " ", str(name).casefold().replace("&amp;", "&")).split())

def check(ev):
    """Problems with evidence.ai_visibility. Empty list = OK (or the audit predates v16)."""
    if not applies(ev): return []
    A = ev.get("ai_visibility")
    if not isinstance(A, dict) or not isinstance(A.get("answers"), list):
        return [f"ai_visibility: missing — every run asks the 7 questions 10 times on each of the {len(tools(ev))} AI tools (SKILL.md AI VISIBILITY CHECK)"]
    P = []; TOOLS, QUESTIONS, RUNS = tools(ev), questions(ev), runs(ev)
    if not str(A.get("method", "")).strip(): P.append("ai_visibility.method: say how the tools were asked (v16.1: each API, its model and the location set)")
    cs = str(A.get("city_st", "")).strip()
    if not re.match(r"^[^,]+, [A-Z]{2}$", cs): P.append("ai_visibility.city_st: the dealer's city and state as asked, e.g. 'Greece, NY'")
    ids = {i for i, _, _ in QUESTIONS}; seen = set()
    for n, a in enumerate(A["answers"]):
        p = f"ai_visibility.answers[{n}]"
        if not isinstance(a, dict): P.append(p + ": must be an object"); continue
        k = (a.get("tool"), a.get("q"), a.get("run"))
        if a.get("tool") not in TOOLS or a.get("q") not in ids or not (isinstance(a.get("run"), int) and not isinstance(a.get("run"), bool) and 1 <= a["run"] <= RUNS):
            P.append(f"{p}: unknown tool / question / run {k}"); continue
        if k in seen: P.append(f"{p}: {k} recorded twice"); continue
        seen.add(k); p = f"ai_visibility[{k[0]}/{k[1]}/{k[2]}]"
        if cs and a.get("asked") != ask(a["q"], cs): P.append(p + f".asked: must be the question word for word: {ask(a['q'], cs)!r}")
        if not re.match(r"^\d{4}-\d{2}-\d{2}", str(a.get("when", ""))): P.append(p + ".when: YYYY-MM-DD (and time) the answer was read")
        st = a.get("status")
        if st == "blocked":
            if not str(a.get("reason", "")).strip(): P.append(p + ".reason: why it could not be read (sign-in wall, error, no answer within 60 seconds)")
            continue
        if st != "answered": P.append(p + ".status: answered | blocked"); continue
        if not str(a.get("answer", "")).strip(): P.append(p + ".answer: the full answer, word for word")
        B = a.get("businesses")
        if not isinstance(B, list) or not all(isinstance(b, dict) and str(b.get("name", "")).strip() and b.get("type") in TYPES for b in B):
            P.append(p + f".businesses: every business the answer names, as {{name, type}} with type one of {', '.join(TYPES)} (empty list when it names none)")
        elif v161(ev) and len(B) > TOP:
            P.append(p + f".businesses: v16.1 records only the first {TOP} businesses the answer names, in its order")
        if not isinstance(a.get("named"), bool): P.append(p + ".named: true/false — does the answer name this dealer")
    missing = [(t, q, r) for t in TOOLS for q in ids for r in range(1, RUNS + 1) if (t, q, r) not in seen]
    if missing: P.append(f"ai_visibility: {len(missing)} of {len(TOOLS) * len(ids) * RUNS} answers not recorded (first: {missing[0]}); record each as answered or blocked")
    if seen and not any(isinstance(a, dict) and a.get("status") == "answered" for a in A["answers"]): P.append("ai_visibility: no tool answered — check the API keys (run/scripts/ai_api_runner.py --check-keys) and re-run the check")
    blocked = [(a.get("tool"), a.get("q"), a.get("run")) for a in A["answers"] if isinstance(a, dict) and a.get("status") == "blocked"]
    if blocked and v161(ev):   # v16.4: through the APIs every ask must be answered; a blocked one is asked again, never left out
        P.append(f"ai_visibility: {len(blocked)} of {len(A['answers'])} answers blocked (first: {blocked[0]}); run ai_api_runner.py again with the same arguments (it re-asks every blocked ask) until all are answered")
    return P

def _answered(ev): return [a for a in (ev.get("ai_visibility") or {}).get("answers", []) if a.get("status") == "answered"]

def scores(ev):
    """{'questions': {q_id: {'named', 'answered', 'score'}}, 'named', 'answered', 'row'} — score 0..100, row 0..10 (unrounded)."""
    A = _answered(ev); Q = {}
    for i, d, _ in questions(ev):
        x = [a for a in A if a["q"] == i]; n = sum(1 for a in x if a["named"])
        Q[i] = {"dept": d, "named": n, "answered": len(x), "score": round(100 * n / len(x)) if x else 0}
    n = sum(1 for a in A if a["named"])
    return {"questions": Q, "named": n, "answered": len(A), "row": 10 * n / len(A) if A else 0.0}

def winners(ev, n=1):
    """{(q_id, tool): (name, type, times, answered)} — the business named most for that question on that tool.
    n=2: {(q_id, tool): [(name, type, times, answered), ...]} — the 2 named most (v16.1 top 2)."""
    out = {}
    for i, _, _ in questions(ev):
        for t in tools(ev):
            x = [a for a in _answered(ev) if a["q"] == i and a["tool"] == t]
            c = collections.Counter(); first = {}
            for a in x:
                for b in {fold(b["name"]): b for b in a.get("businesses") or []}.values():
                    c[fold(b["name"])] += 1; first.setdefault(fold(b["name"]), b)
            top = [(first[k]["name"], first[k]["type"], times, len(x)) for k, times in sorted(c.items(), key=lambda kv: (-kv[1], kv[0]))[:n]]
            out[(i, t)] = top if n > 1 else (top[0] if top else (None, None, 0, len(x)))
    return out

def brief(ev):
    A = ev.get("ai_visibility") or {}; S = scores(ev); W = winners(ev)
    out = [f"### AI visibility check ({A.get('method', '')})", "",
           f"**{ev.get('dealer', 'The dealer')} was {'one of the top 2 named' if v161(ev) else 'named'} in {S['named']} of {S['answered']} answers — {round(10 * S['row'])}% ({S['row']:.1f}/10).**", ""]
    blocked = [a for a in A.get("answers", []) if a.get("status") == "blocked"]
    if blocked:
        by = collections.Counter(NAME[a["tool"]] for a in blocked)
        out += ["Not read (blocked, not counted): " + ", ".join(f"{t} {n}" for t, n in by.items()) + ".", ""]
    if v161(ev):
        T = winners(ev, TOP)
        for i, d, _ in questions(ev):
            q = S["questions"][i]
            out += [f"**{DEPT_LABEL[d]} — \"{ask(i, A.get('city_st', '[City, ST]'))}\"** — dealer in the top {TOP} {q['named']} of {q['answered']} ({q['score']}/100)", "",
                    "| Tool | Dealer in top 2 | #1 named most | #2 named most |", "|---|---|---|---|"]
            for t in tools(ev):
                w = T[(i, t)]; dn = sum(1 for a in _answered(ev) if a["q"] == i and a["tool"] == t and a["named"])
                n = sum(1 for a in _answered(ev) if a["q"] == i and a["tool"] == t)
                cell = lambda k: f"{w[k][0]} ({TYPE_LABEL[w[k][1]]}, {w[k][2]} of {w[k][3]})" if len(w) > k else "—"
                out.append(f"| {NAME[t]} | {dn} of {n} | {cell(0)} | {cell(1)} |")
            out.append("")
        return "\n".join(out)
    for i, d, _ in questions(ev):
        q = S["questions"][i]
        out += [f"**{DEPT_LABEL[d]} — \"{ask(i, A.get('city_st', '[City, ST]'))}\"** — dealer named {q['named']} of {q['answered']} ({q['score']}/100)", "",
                "| Tool | Dealer named | Named most | Type | Times |", "|---|---|---|---|---|"]
        for t in tools(ev):
            nm, ty, times, n = W[(i, t)]
            dn = sum(1 for a in _answered(ev) if a["q"] == i and a["tool"] == t and a["named"])
            out.append(f"| {NAME[t]} | {dn} of {n} | {nm or '— (none named)'} | {TYPE_LABEL.get(ty, '—') if ty else '—'} | {times} of {n} |")
        out.append("")
    return "\n".join(out)

def sheet(ev, path):
    """The spreadsheet: one tab per AI tool, one row per answer (blocked answers included, marked)."""
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font
    A = ev.get("ai_visibility") or {}; wb = Workbook(); wb.remove(wb.active)
    cols = ["Dealer", "City & State", "Department", "Question", "Run", "When", "Status", "Answer",
            "Top 2 Named" if v161(ev) else "Businesses Named", "Business Types", "Dealer in Top 2" if v161(ev) else "Dealer Named"]
    QUESTIONS = questions(ev)
    for t in tools(ev):
        ws = wb.create_sheet(NAME[t]); ws.append(cols)
        for c in ws[1]: c.font = Font(bold=True)
        rows = sorted((a for a in A.get("answers", []) if a.get("tool") == t), key=lambda a: ([i for i, _, _ in QUESTIONS].index(a["q"]), a["run"]))
        for a in rows:
            d = next(d for i, d, _ in QUESTIONS if i == a["q"]); B = a.get("businesses") or []
            ws.append([ev.get("dealer", ""), A.get("city_st", ""), DEPT_LABEL[d], a.get("asked", ""), a["run"], a.get("when", ""),
                       a.get("status", ""), a.get("answer", "") if a.get("status") == "answered" else "blocked: " + str(a.get("reason", "")),
                       "; ".join(b["name"] for b in B), "; ".join(TYPE_LABEL[b["type"]] for b in B),
                       ("Yes" if a.get("named") else "No") if a.get("status") == "answered" else ""])
        for col, w in zip("ABCDEFGHIJK", (24, 14, 11, 52, 6, 17, 10, 90, 48, 36, 12)): ws.column_dimensions[col].width = w
        for r in ws.iter_rows(min_row=2):
            for c in r: c.alignment = Alignment(wrap_text=True, vertical="top")
        ws.freeze_panes = "A2"
    wb.save(path); return path

def file_name(dealer, date):
    return f"{re.sub(r'[^a-z0-9]+', '-', dealer.lower()).strip('-')}_ai-answers_{datetime.date.fromisoformat(date).strftime('%m-%d-%y')}.xlsx"

if __name__ == "__main__":
    a = sys.argv[1:]
    if len(a) == 2 and a[0] == "questions":
        print("\n".join(f"{DEPT_LABEL[d]:8} {i:22} {q.format(city_st=a[1])}" for i, d, q in QUESTIONS)); sys.exit(0)
    if len(a) < 2 or a[0] not in ("check", "score", "brief", "sheet") or (a[0] == "sheet" and len(a) != 3): print(__doc__); sys.exit(2)
    ev = json.load(open(a[1]))
    if a[0] == "check":
        p = check(ev); print("AI VISIBILITY OK" if not p else "AI VISIBILITY INCOMPLETE:\n  - " + "\n  - ".join(p)); sys.exit(1 if p else 0)
    if a[0] == "score": print(json.dumps(scores(ev), indent=2)); sys.exit(0)
    if a[0] == "brief": print(brief(ev)); sys.exit(0)
    print(sheet(ev, a[2]))

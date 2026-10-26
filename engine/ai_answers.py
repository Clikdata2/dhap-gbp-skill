#!/usr/bin/env python3
"""DHAP GBP engine — AI answer check (v15.1, mandatory on every audit dated on or after Oct 24 2026).

Every run asks the AI tools shoppers use the same three questions about the dealer and saves each answer word for word,
with its sources and a screenshot. The answers are evidence for findings and the rep brief; they never change a score.
  tools   google_ai (AI Overview or AI Mode; covers Google's AI) · chatgpt · copilot (Copilot Search) · perplexity
          · claude (Claude's own web search) · brave (Ask Brave; Claude's search source) — each asked the three prompts
          below. v15.2 dropped Gemini (sign-in, slow) and the separate Bing and Apple Maps cards (read once, as NAP readings).
  prompts best     "best [Brand] dealer near [City, ST]"                                   (get chosen)
          contact  "[Dealer] [City] phone number for sales and service, address and hours" (get found)
          rating   "Is [Dealer] in [City] a good dealership? What is its rating?"          (get chosen)
Each answer: {tool, prompt, status: answered|blocked, asked, when, named, position, phone, phone_matches_site,
              rating, rating_source, sources, quote, proof}  — blocked needs a reason instead of the answer fields.
Usage:
  python3 ai_answers.py check evidence.json     -> the problems, or AI ANSWERS OK
  python3 ai_answers.py brief evidence.json     -> the rep-brief table and the flags (markdown)
"""
import json, pathlib, re, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import directories

START = "2026-10-24"                       # audits dated before this did not run the check
TOOLS = ("google_ai", "chatgpt", "copilot", "perplexity", "claude", "brave")   # v15.2: Gemini dropped (sign-in, hangs; Google AI Mode covers Google's AI)
PROMPTS = ("best", "contact", "rating")
CARDS = ()   # v15.2: Bing's card and the Apple Maps card are read once, as the bing and apple_maps NAP readings (rule 8)
SOURCES = ("google", "yelp", "facebook", "dealer_site", "other")
NAME = {"google_ai": "Google AI Overview / AI Mode", "gemini": "Gemini", "chatgpt": "ChatGPT", "copilot": "Microsoft Copilot",
        "perplexity": "Perplexity", "claude": "Claude (web search)", "brave": "Brave AI summary (Claude's source)",
        "bing_card": "Bing business card", "apple_maps": "Apple Maps card (Siri)"}

def required(ev):
    return str(ev.get("audit_date", "")) >= START

def expected():
    return [(t, p) for t in TOOLS for p in PROMPTS] + [(c, "card") for c in CARDS]

def check(ev):
    """Problems with evidence.ai_answers. Empty list = OK (or the audit predates the check)."""
    if not required(ev): return []
    A = ev.get("ai_answers")
    if not isinstance(A, dict) or not isinstance(A.get("answers"), list):
        return ["ai_answers: missing — every run asks the AI tools the three questions and saves each answer (SKILL.md AI ANSWER CHECK)"]
    P = []
    if not str(A.get("method", "")).strip(): P.append("ai_answers.method: say how the tools were asked (browser, signed in or out)")
    seen = {}
    for i, a in enumerate(A["answers"]):
        p = f"ai_answers.answers[{i}]"
        if not isinstance(a, dict): P.append(p + ": must be an object"); continue
        k = (a.get("tool"), a.get("prompt"))
        if k not in expected(): P.append(f"{p}: unknown tool/prompt {k}"); continue
        if k in seen: P.append(f"{p}: {k} recorded twice"); continue
        seen[k] = a; p = f"ai_answers[{k[0]}/{k[1]}]"
        if not re.match(r"^\d{4}-\d{2}-\d{2}", str(a.get("when", ""))): P.append(p + ".when: YYYY-MM-DD (and time) the answer was read")
        if not str(a.get("asked", "")).strip(): P.append(p + ".asked: the exact words typed (or the card searched)")
        st = a.get("status")
        if st == "blocked":
            if not str(a.get("reason", "")).strip(): P.append(p + ".reason: say why it could not be read (sign-in wall, error, no answer)")
            continue
        if st != "answered": P.append(p + ".status: answered | blocked"); continue
        if not isinstance(a.get("named"), bool): P.append(p + ".named: true/false — does the answer name this dealer")
        pos = a.get("position")
        if not (pos is None or (isinstance(pos, int) and not isinstance(pos, bool) and pos >= 1)): P.append(p + ".position: 1, 2, 3... where the dealer is listed, or null")
        if a.get("named") is False and pos is not None: P.append(p + ".position: must be null when the dealer is not named")
        if a.get("phone") is not None and not isinstance(a.get("phone_matches_site"), bool) and not (a.get("phone_matches_site") is None and directories.toll_free(a["phone"])):
            P.append(p + ".phone_matches_site: true/false when the answer shows a phone — compare with the WEBSITE's number for that department (the authority); null only for a toll-free number, which is never compared with a local one")
        r = a.get("rating")
        if r is not None:
            if isinstance(r, bool) or not isinstance(r, (int, float)) or not 1 <= r <= 5: P.append(p + ".rating: 1.0..5.0, or null when none is shown")
            if a.get("rating_source") not in SOURCES: P.append(p + f".rating_source: one of {', '.join(SOURCES)} (where the rating shown comes from)")
        if not isinstance(a.get("sources"), list): P.append(p + ".sources: list of the sites the answer cites (empty list when it cites none)")
        if not str(a.get("quote", "")).strip(): P.append(p + ".quote: the answer's words about the dealer, word for word (or 'not mentioned' plus who it named first)")
        if not str(a.get("proof", "")).strip(): P.append(p + ".proof: the screenshot file of the answer")
    for k in expected():
        if k not in seen: P.append(f"ai_answers: {k[0]}/{k[1]} not recorded (record it as blocked with a reason if it could not be read)")
    if seen and not any(a.get("status") == "answered" for a in seen.values()): P.append("ai_answers: no tool answered — re-run the check in the user's signed-in Chrome")
    return P

def flags(ev):
    """Plain-language flags for the rep brief: each one is a lost call, direction request or click."""
    A = ev.get("ai_answers") or {}; F = []
    ans = [a for a in A.get("answers", []) if a.get("status") == "answered"]
    best = [a for a in ans if a.get("prompt") == "best"]
    missed = [NAME[a["tool"]] for a in best if a.get("named") is False]
    if missed: F.append(f"Not named when asked for the best dealer nearby: {', '.join(missed)} ({len(missed)} of {len(best)} tools that answered).")
    wrong = [f"{NAME[a['tool']]} ({a['phone']})" for a in ans if a.get("phone") and a.get("phone_matches_site") is False]
    if wrong: F.append(f"Phone shown does not match the website: {', '.join(wrong)}.")
    other = [f"{NAME[a['tool']]} {a['rating']} ({a['rating_source']})" for a in ans if a.get("rating") is not None and a.get("rating_source") != "google"]
    if other: F.append(f"Rating shown is not Google's: {', '.join(other)}.")
    blocked = [f"{NAME[a['tool']]}/{a['prompt']}" for a in A.get("answers", []) if a.get("status") == "blocked"]
    if blocked: F.append(f"Not read (blocked): {', '.join(blocked)}.")
    return F

def brief(ev):
    A = ev.get("ai_answers") or {}
    yn = lambda x: "—" if x is None else ("yes" if x else "**no**")
    out = [f"### AI answer check ({A.get('method', '')})", "", "| Tool | Prompt | Named | Position | Phone (matches site) | Rating (source) | Sources cited |", "|---|---|---|---|---|---|---|"]
    for a in A.get("answers", []):
        if a.get("status") == "blocked":
            out.append(f"| {NAME.get(a.get('tool'), a.get('tool'))} | {a.get('prompt')} | blocked: {a.get('reason', '')} | | | | |"); continue
        ph = "—" if not a.get("phone") else f"{a['phone']} ({yn(a.get('phone_matches_site'))})"
        rt = "—" if a.get("rating") is None else f"{a['rating']} ({a.get('rating_source')})"
        out.append(f"| {NAME[a['tool']]} | {a['prompt']} | {yn(a.get('named'))} | {a.get('position') or '—'} | {ph} | {rt} | {', '.join(a.get('sources') or []) or '—'} |")
    out += ["", "**Flags:**"] + [f"- {f}" for f in flags(ev)] if flags(ev) else ["", "**Flags:** none."]
    return "\n".join(out)

if __name__ == "__main__":
    if len(sys.argv) != 3 or sys.argv[1] not in ("check", "brief"): print(__doc__); sys.exit(2)
    ev = json.load(open(sys.argv[2]))
    if sys.argv[1] == "check":
        p = check(ev); print("AI ANSWERS OK" if not p else "AI ANSWERS INCOMPLETE:\n  - " + "\n  - ".join(p)); sys.exit(1 if p else 0)
    print(brief(ev))

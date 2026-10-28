#!/usr/bin/env python3
"""DHAP GBP AI visibility check through official APIs (no browser windows, no robot checks).

Asks the 5 questions 5 times on each of the 5 tools (125 asks, v16.1), all in parallel, and saves every answer to
<out>/dhap_ai_<tool>.json in the same record format as ai_runner.py / aicap.js, so ai_merge.py reads it unchanged.
v16.1 keeps only the top 2: each answer is capped at OUTPUT_CAP tokens (the first names come first) and Claude Haiku
pulls the first 2 businesses it names, in its order, into "top2": [{name, type}]. The answer text is kept as proof.

  chatgpt    OpenAI Responses API + web_search tool, approximate user location = the dealer's city
  gemini     Gemini API + Grounding with Google Search
  google_ai  SerpApi: Google's AI Overview for the question as Google shows it in the dealer's city; AI Mode when no
             Overview shows (the rule: "the AI Overview, or AI Mode when no Overview shows")
  claude     Claude API (Anthropic SDK) + web search tool, approximate user location = the dealer's city
  brave      Brave Search API, AI Grounding (chat/completions)

Keys come from keys.env next to this script or ~/.dhap-gbp-local/keys.env (chmod 600; see keys.env.example; never
commit it), or the environment. A tool with no key is skipped and says so.
Rate limits and server errors are retried with backoff (an API asking us to slow down is not a robot check); an ask that
still fails is recorded as blocked with the reason, never counted.

Usage:
  ~/.dhap-gbp-venv/bin/python ai_api_runner.py --city "Greece, NY" --out <run>/ai [--tools chatgpt,gemini,...] [--runs 1-5]
  ~/.dhap-gbp-venv/bin/python ai_api_runner.py --check-keys
"""
import argparse, concurrent.futures as cf, datetime, json, os, pathlib, random, re, threading, time
import urllib.error, urllib.parse, urllib.request

HERE = pathlib.Path(__file__).resolve().parent
QUESTIONS = {   # v16.1, word for word (engine/ai_visibility.py QUESTIONS)
    "sales_new_family_suv": "best family SUV under 40k near {c}",
    "sales_used_midsize_suv": "used midsize SUV near {c}",
    "service_oil_change_near": "oil change near {c}",
    "service_brake_job": "brake job near {c}",
    "parts_brake_pads": "brake pads for my SUV near {c}",
}
TOP = 2
OUTPUT_CAP = 2500   # tokens, thinking included; an answer that comes back empty at the cap is asked once more without it
EXTRACT_MODEL = "claude-haiku-5-5"
TYPES = ["dealership", "oil_change", "tire_shop", "parts_store", "repair_shop", "retailer", "other"]
TOOLS = ("chatgpt", "gemini", "google_ai", "claude", "brave")
KEY = {"chatgpt": "OPENAI_API_KEY", "gemini": "GEMINI_API_KEY", "google_ai": "SERPAPI_API_KEY",
       "claude": "ANTHROPIC_API_KEY", "brave": "BRAVE_API_KEY"}
MODEL_DEFAULT = {"chatgpt": "gpt-5.4-mini", "gemini": "gemini-3.8-flash", "claude": "claude-sonnet-5-5"}   # the cheaper models (Travis, Oct 27 2026): only the top 2 names count
PARALLEL = {"chatgpt": 10, "gemini": 10, "google_ai": 10, "claude": 8, "brave": 2}   # Brave's base plan: 2 requests/second
STATES = dict(AL="Alabama", AK="Alaska", AZ="Arizona", AR="Arkansas", CA="California", CO="Colorado", CT="Connecticut",
              DE="Delaware", DC="District of Columbia", FL="Florida", GA="Georgia", HI="Hawaii", ID="Idaho", IL="Illinois",
              IN="Indiana", IA="Iowa", KS="Kansas", KY="Kentucky", LA="Louisiana", ME="Maine", MD="Maryland",
              MA="Massachusetts", MI="Michigan", MN="Minnesota", MS="Mississippi", MO="Missouri", MT="Montana",
              NE="Nebraska", NV="Nevada", NH="New Hampshire", NJ="New Jersey", NM="New Mexico", NY="New York",
              NC="North Carolina", ND="North Dakota", OH="Ohio", OK="Oklahoma", OR="Oregon", PA="Pennsylvania",
              RI="Rhode Island", SC="South Carolina", SD="South Dakota", TN="Tennessee", TX="Texas", UT="Utah",
              VT="Vermont", VA="Virginia", WA="Washington", WV="West Virginia", WI="Wisconsin", WY="Wyoming")


_u = threading.local()   # usage of the ask running on this thread: tokens, searches, calls (for the cost report)
def use(**n):
    d = getattr(_u, "d", None)
    if d is not None:
        for k, v in n.items():
            d[k] = d.get(k, 0) + int(v or 0)


class Blocked(Exception):
    """The tool gave no usable answer; the message is the reason recorded."""


def load_keys():
    for f in (HERE / "keys.env", pathlib.Path.home() / ".dhap-gbp-local" / "keys.env"):
        if not f.exists():
            continue
        for line in f.read_text().splitlines():
            k, sep, v = line.strip().partition("=")
            if sep and not k.startswith("#") and v.strip() and not os.environ.get(k.strip()):
                os.environ[k.strip()] = v.strip().strip('"').strip("'")


def http(method, url, headers=None, body=None, timeout=90):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method, headers={"Content-Type": "application/json", **(headers or {})})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode())


def with_retries(fn, tries=5):
    """Retry rate limits (429), server errors (5xx) and timeouts with backoff; anything else fails at once."""
    for n in range(tries):
        try:
            return fn()
        except urllib.error.HTTPError as e:
            msg = e.read().decode(errors="replace")[:300]
            if e.code != 429 and e.code < 500 or n == tries - 1:
                raise Blocked(f"API error {e.code}: {msg}")
        except (urllib.error.URLError, TimeoutError) as e:
            if n == tries - 1:
                raise Blocked(f"network error: {e}")
        except Exception as e:   # the Anthropic SDK retries on its own; its errors land here
            status = getattr(e, "status_code", None)
            if status is not None and status != 429 and status < 500 or n == tries - 1:
                raise Blocked(f"API error {status or type(e).__name__}: {str(e)[:300]}")
        time.sleep(2 ** n + random.random())


# ---- one function per tool: (question, place) -> (answer text, [source urls], via) ----

def ask_chatgpt(q, p, cap=OUTPUT_CAP):
    model = os.environ.get("DHAP_OPENAI_MODEL", MODEL_DEFAULT["chatgpt"])
    loc = {"type": "approximate", "country": "US", "city": p["city"], "region": p["state_name"]}
    r = with_retries(lambda: http("POST", "https://api.openai.com/v1/responses",
                                  {"Authorization": "Bearer " + os.environ["OPENAI_API_KEY"]},
                                  {"model": model, "input": q, "tools": [{"type": "web_search", "user_location": loc}],
                                   **({"max_output_tokens": cap} if cap else {})}))
    u = r.get("usage") or {}
    use(calls=1, input_tokens=u.get("input_tokens"), output_tokens=u.get("output_tokens"),
        searches=sum(i.get("type") == "web_search_call" for i in r.get("output", [])))
    text, src = [], []
    for item in r.get("output", []):
        if item.get("type") == "message":
            for c in item.get("content", []):
                if c.get("type") == "output_text":
                    text.append(c.get("text", ""))
                    src += [a.get("url") for a in c.get("annotations", []) if a.get("type") == "url_citation"]
    return "\n".join(text), src, f"OpenAI API {model} + web search, location {p['city_st']}"


def ask_gemini(q, p, cap=OUTPUT_CAP):
    model = os.environ.get("DHAP_GEMINI_MODEL", MODEL_DEFAULT["gemini"])
    r = with_retries(lambda: http("POST", f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
                                  {"x-goog-api-key": os.environ["GEMINI_API_KEY"]},
                                  {"contents": [{"parts": [{"text": q}]}], "tools": [{"google_search": {}}],
                                   **({"generationConfig": {"maxOutputTokens": cap}} if cap else {})}))
    cand = (r.get("candidates") or [{}])[0]
    u = r.get("usageMetadata") or {}
    use(calls=1, input_tokens=(u.get("promptTokenCount") or 0) + (u.get("toolUsePromptTokenCount") or 0),
        output_tokens=(u.get("candidatesTokenCount") or 0) + (u.get("thoughtsTokenCount") or 0),
        searches=len((cand.get("groundingMetadata") or {}).get("webSearchQueries") or []))
    text = "".join(part.get("text", "") for part in (cand.get("content") or {}).get("parts", []))
    src = [(c.get("web") or {}).get("uri") for c in (cand.get("groundingMetadata") or {}).get("groundingChunks", [])]
    if not text and cand.get("finishReason") and cand["finishReason"] != "MAX_TOKENS":
        raise Blocked(f"no answer (finishReason {cand['finishReason']})")
    return text, src, f"Gemini API {model} + Grounding with Google Search"


def _blocks_text(blocks, depth=0):
    """SerpApi text_blocks (paragraph / heading / list / table ...) -> plain text, keeping list nesting."""
    out = []
    for b in blocks or []:
        line = " ".join(str(b.get(k)) for k in ("title", "snippet") if b.get(k))
        if line:
            out.append(("  " * depth + "- " if depth else "") + line)
        for k in ("list", "text_blocks"):
            if isinstance(b.get(k), list):
                out += _blocks_text(b[k], depth + (k == "list"))
        if isinstance(b.get("table"), list):
            out += ["  " * depth + " | ".join(map(str, row)) for row in b["table"]]
    return out


def ask_google_ai(q, p, cap=None):   # SerpApi returns what Google showed; nothing to cap
    key = os.environ["SERPAPI_API_KEY"]
    serp = lambda **kw: (use(calls=1, searches=1), with_retries(lambda: http("GET", "https://serpapi.com/search.json?" + urllib.parse.urlencode({**kw, "api_key": key, "no_cache": "true"}))))[1]
    loc = f"{p['city']}, {p['state_name']}, United States"
    r = serp(engine="google", q=q, location=loc, gl="us", hl="en")
    ov = r.get("ai_overview") or {}
    if ov.get("page_token") and not ov.get("text_blocks"):   # full Overview needs a second call within 1 minute
        ov = serp(engine="google_ai_overview", page_token=ov["page_token"]).get("ai_overview") or {}
    via = "Google AI Overview via SerpApi"
    if not ov.get("text_blocks"):
        ov = serp(engine="google_ai_mode", q=q, location=loc, gl="us", hl="en")
        via = "Google AI Mode via SerpApi (no AI Overview shown)"
        if ov.get("reconstructed_markdown"):
            return ov["reconstructed_markdown"], [x.get("link") for x in ov.get("references", [])], f"{via}, location {loc}"
    text = "\n".join(_blocks_text(ov.get("text_blocks")))
    return text, [x.get("link") for x in ov.get("references", [])], f"{via}, location {loc}"


_claude = None
def ask_claude(q, p, cap=OUTPUT_CAP):
    global _claude
    import anthropic
    _claude = _claude or anthropic.Anthropic(max_retries=4)
    model = os.environ.get("DHAP_CLAUDE_MODEL", MODEL_DEFAULT["claude"])
    tool = {"type": "web_search_20260209", "name": "web_search", "max_uses": 5,
            "user_location": {"type": "approximate", "city": p["city"], "region": p["state_name"], "country": "US"}}
    messages = [{"role": "user", "content": q}]
    for _ in range(4):   # pause_turn: the server's search loop paused; send the turn back to let it finish
        r = with_retries(lambda: _claude.beta.messages.create(
            model=model, max_tokens=cap or 16000, messages=messages, tools=[tool],
            betas=["server-side-fallback-2026-07-01"], fallbacks="default"), tries=2)
        stu = getattr(r.usage, "server_tool_use", None)
        use(calls=1, input_tokens=r.usage.input_tokens + (r.usage.cache_read_input_tokens or 0) + (r.usage.cache_creation_input_tokens or 0),
            output_tokens=r.usage.output_tokens, searches=getattr(stu, "web_search_requests", 0) if stu else 0)
        if r.stop_reason != "pause_turn":
            break
        messages = [messages[0], {"role": "assistant", "content": r.content}]
    if r.stop_reason == "refusal":
        raise Blocked("Claude declined to answer (refusal)")
    text, src = [], []
    for b in r.content:
        if b.type == "text":
            text.append(b.text)
            src += [c.url for c in (b.citations or []) if getattr(c, "url", None)]
    return "".join(text), src, f"Claude API {r.model} + web search, location {p['city_st']}"


def ask_brave(q, p, cap=None):
    r = with_retries(lambda: http("POST", "https://api.search.brave.com/res/v1/chat/completions",
                                  {"X-Subscription-Token": os.environ["BRAVE_API_KEY"], "Accept": "application/json"},
                                  {"model": "brave", "stream": False, "country": "us", "language": "en",
                                   "messages": [{"role": "user", "content": q}]}))
    u = r.get("usage") or {}
    use(calls=1, input_tokens=u.get("prompt_tokens"), output_tokens=u.get("completion_tokens"),
        searches=u.get("search_requests") or u.get("searches"))   # Brave bills per search; recorded when its response reports it
    text = ((r.get("choices") or [{}])[0].get("message") or {}).get("content", "")
    src = re.findall(r"https?://[^\s\"'<>)\]]+", text)
    return text, src, "Brave Search API, AI Grounding"


_extractor = None
def top2(answer):
    """The first 2 businesses the answer names, in its order, as [{name, type}] (Claude Haiku, structured output)."""
    global _extractor
    import anthropic
    _extractor = _extractor or anthropic.Anthropic(max_retries=4)
    schema = {"type": "object", "additionalProperties": False, "required": ["businesses"], "properties": {
        "businesses": {"type": "array", "items": {"type": "object", "additionalProperties": False, "required": ["name", "type"],
                       "properties": {"name": {"type": "string"}, "type": {"type": "string", "enum": TYPES}}}}}}
    r = _extractor.messages.create(
        model=EXTRACT_MODEL, max_tokens=1024,
        output_config={"effort": "low", "format": {"type": "json_schema", "schema": schema}},
        messages=[{"role": "user", "content":
            "Below is an AI assistant's answer to a local shopper. List the first two businesses it names, in the order "
            "it names them, with each name written exactly as in the answer. Count only specific businesses or stores "
            "(not websites like Yelp or Google, and not generic advice). type: dealership, oil_change (quick lube), "
            "tire_shop, parts_store, repair_shop, retailer (big-box or general store), or other. Return fewer if it "
            "names fewer.\n\n<answer>\n" + answer[:12000] + "\n</answer>"}])
    use(extract_input_tokens=r.usage.input_tokens, extract_output_tokens=r.usage.output_tokens)
    text = next(b.text for b in r.content if b.type == "text")
    return json.loads(text)["businesses"][:TOP]


ASK = {"chatgpt": ask_chatgpt, "gemini": ask_gemini, "google_ai": ask_google_ai, "claude": ask_claude, "brave": ask_brave}


def parse_runs(s):
    a, _, b = s.partition("-")
    return list(range(int(a), int(b or a) + 1))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--city", help='the dealer\'s "City, ST"')
    ap.add_argument("--out", help="the run's ai/ folder")
    ap.add_argument("--tools", default=",".join(TOOLS))
    ap.add_argument("--questions", default=",".join(QUESTIONS))
    ap.add_argument("--runs", default="1-5")
    ap.add_argument("--check-keys", action="store_true")
    a = ap.parse_args()
    load_keys()
    tools = [t for t in a.tools.split(",") if t]
    missing = [t for t in tools if not os.environ.get(KEY[t])]
    if a.check_keys:
        for t in tools:
            print(f"{t:10} {KEY[t]:18} {'set' if t not in missing else 'MISSING'}")
        return
    if not (a.city and a.out):
        ap.error("--city and --out are required")
    m = re.match(r"^\s*(.+?),\s*([A-Z]{2})\s*$", a.city)
    if not m or m.group(2) not in STATES:
        ap.error('--city must look like "Greece, NY"')
    place = {"city": m.group(1), "state": m.group(2), "state_name": STATES[m.group(2)], "city_st": f"{m.group(1)}, {m.group(2)}"}
    for t in missing:
        print(f"SKIPPED {t}: {KEY[t]} is not set (keys.env)")
    tools = [t for t in tools if t not in missing]
    out = pathlib.Path(a.out); out.mkdir(parents=True, exist_ok=True)

    recs, done, lock = {}, set(), threading.Lock()
    for t in tools:
        f = out / f"dhap_ai_{t}.json"
        recs[t] = json.loads(f.read_text()) if f.exists() else []
        done |= {(t, r["q"], r["run"]) for r in recs[t]}

    def one(t, q, run):
        asked = QUESTIONS[q].format(c=place["city_st"])
        rec = {"tool": t, "q": q, "run": run, "asked": asked}
        _u.d, s0 = {}, time.time()
        try:
            text, src, via = ASK[t](asked, place)
            if len(text.strip()) < 40 and t in ("chatgpt", "gemini", "claude"):   # the cap cut it before any text: once more, uncapped
                text, src, via = ASK[t](asked, place, cap=None)
            if len(text.strip()) < 40:
                raise Blocked("empty or near-empty answer")
            rec.update(status="answered", answer=text.strip(), complete=True, via=via, sources=[s for s in src if s][:40])
            try:
                rec["top2"] = top2(rec["answer"])
            except Exception as e:   # ai_merge.py falls back to its own name list; the answer is still saved
                rec["top2_error"] = f"{type(e).__name__}: {str(e)[:200]}"
        except Blocked as e:
            rec.update(status="blocked", reason=str(e), via=f"{t} API")
        except KeyError as e:
            rec.update(status="blocked", reason=f"unexpected response shape (missing {e})", via=f"{t} API")
        rec["when"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
        rec["seconds"], rec["usage"] = round(time.time() - s0, 1), _u.d
        with lock:
            recs[t].append(rec)
            (out / f"dhap_ai_{t}.json").write_text(json.dumps(recs[t], indent=1, ensure_ascii=False))
            print(t, q, run, rec["status"], " | ".join(b["name"] for b in rec.get("top2", [])), rec.get("reason", "")[:80], flush=True)

    jobs = [(t, q, r) for t in tools for q in a.questions.split(",") for r in parse_runs(a.runs) if (t, q, r) not in done]
    pools = {t: cf.ThreadPoolExecutor(PARALLEL[t]) for t in tools}
    t0 = time.time()
    futs = [pools[t].submit(one, t, q, r) for t, q, r in jobs]
    for f in cf.as_completed(futs):
        f.result()
    for p in pools.values():
        p.shutdown()
    by = {t: sum(r["status"] == "answered" for r in recs[t]) for t in tools}
    rep = {"city": place["city_st"], "seconds_total": round(time.time() - t0), "models": {t: os.environ.get(f"DHAP_{ {'chatgpt': 'OPENAI', 'gemini': 'GEMINI', 'claude': 'CLAUDE'}[t]}_MODEL", MODEL_DEFAULT[t]) for t in tools if t in MODEL_DEFAULT}, "tools": {}}
    for t in tools:
        tot = {}
        for r in recs[t]:
            for k, v in (r.get("usage") or {}).items():
                tot[k] = tot.get(k, 0) + v
        rep["tools"][t] = {"asks": len(recs[t]), "answered": by[t] if t in by else None, "seconds_longest": max([r.get("seconds", 0) for r in recs[t]] or [0]), **tot}
    (out / "dhap_ai_usage.json").write_text(json.dumps(rep, indent=1))
    for t, d in rep["tools"].items():
        print(f"usage {t:10} " + ", ".join(f"{k} {v}" for k, v in d.items()))
    print(f"done in {time.time() - t0:.0f}s: " + ", ".join(f"{t} {n}/{len(recs[t])} answered" for t, n in by.items()))


if __name__ == "__main__":
    main()

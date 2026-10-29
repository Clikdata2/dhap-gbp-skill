#!/usr/bin/env python3
"""DHAP GBP engine — one command for every gate, in order. Stops at the first gate that fails.
  1 rules guard (scoring text unchanged)   2 evidence check   3 facts gate   4 build both pages
  5 repository assertion suite (read from SKILL.md at run time) + health-alert checklist + score consistency
  6 phone-width probe (360/390/430, all tabs, 3 screens)   7 spelling (advisory list)
  8 Markdown copies of the DHAP and the Alert (v16.5: seven files per dealer; engine/to_markdown.py)
A condition in the repository suite is skipped ONLY when the evidence proves the gap it asserts is absent
(Google link present in sameAs; areaServed present); every skip is printed.
Usage: python3 check_all.py [--repo REPO] --evidence ev.json --content content.json --out OUTDIR [--venv PATH]"""
import argparse, html as H, json, pathlib, re, subprocess, sys, time
ENG = pathlib.Path(__file__).resolve().parent; sys.path.insert(0, str(ENG))
import score as S, facts as F, build as B, alert_cards as AC, design as DS

def rule_l(D, ev, raw, rows, st):
    """RULE L (v16.3): status colours, tints and point breakdowns on the DHAP's tables."""
    tab = lambda a, b: D[D.find(f'id="{a}"'):D.find(f'id="{b}"')]
    sc = tab("scorecard", "aivisibility"); sc = sc[:sc.index("</table>")]
    trs = re.findall(r'<tr class="([^"]+)">(.*?)</tr>', sc, re.S)
    assert len(trs) == len(rows) + 1, ("RULE L: scorecard rows", len(trs))
    P = S.row_parts(ev)
    for i, (cls, body) in enumerate(trs[:-1]):
        k = DS.band(rows[i])
        assert cls == f"cc-{k}", ("RULE L: scorecard row colour", S.row_names(rows)[i], cls, k)
        assert abs(S.parts_total(P[i]) - raw[i]) < 1e-9, ("RULE L: the breakdown does not add up to the row", S.row_names(rows)[i])
        assert 'class="cc-pts"' in body and 'class="cc-why"' in body, ("RULE L: breakdown or why missing", S.row_names(rows)[i])
    assert trs[-1][0] == f"cc-total cc-t-{DS.STATUS_BAND[st['label']]}", ("RULE L: the OVERALL row must take the status colour (lowest category)", trs[-1][0])
    for t in re.findall(r"<table class=\"score-table[^\"]*\">.*?</table>", tab("scorecard", "opportunities"), re.S):
        assert 'tr style="background' not in t, "RULE L: rows are tinted only by class"
        for cls in re.findall(r'<tr class="([^"]+)"', t):
            assert cls.startswith(("cc-red", "cc-org", "cc-yel", "cc-grn", "cc-gry", "cc-total cc-t-")), ("RULE L: row without a status colour", cls)
    tinted = re.findall(r'<table class="score-table cc-tint-red">', D)
    assert len(tinted) == (1 if "_directory_results" in ev["nap"] else 0), "RULE L: only the CLIKsearch network table tints its red rows"
    if "_directory_results" in ev["nap"]:
        for t in re.findall(r'<tr class="cc-total[^"]*">.*?</tr>', D, re.S):
            if "of 2 points" in t:
                assert f"cc-t-{DS.band(rows[5])}" in t and f"Part of <b>NAP Consistency {rows[5]:.1f}/10</b>" in t, "RULE L: a listing-site total must say it is part of NAP Consistency, in its colour"

BAD_TEXT = [(r"\b[Nn]o of\b", '"no of" (write "none of")'), (r"\bundefined\b", '"undefined"'), (r"\bNaN\b", '"NaN"'),
            (r"\{[a-z_]{2,}\}", "an unfilled {placeholder}")]

def text_lint(pages):
    """v16.4: wording that is broken in every case never ships (a page with any of these fails the build)."""
    for name, page in pages.items():
        if not page: continue
        body = re.sub(r"<(script|style)\b.*?</\1>", " ", page, flags=re.S | re.I); body = H.unescape(re.sub(r"<[^>]+>", " ", body))
        for rx, what in BAD_TEXT:
            m = re.search(rx, body)
            assert not m, f"text lint: {name} contains {what}: ...{body[max(0, m.start() - 60):m.end() + 40].strip()}..."

def suite(repo, D, HS, ev, report_id, dealer_words):
    raw, rows = S.score_rows(ev); st = S.status(rows); ovr = S.overall(rows)
    skill = (repo / "SKILL.md").read_text(encoding="utf-8")
    blk = skill[skill.index("## Assertion suite"):]; s0 = blk.index("```python") + 9; blk = blk[s0: blk.index("```", s0)]
    skips = []
    if ev["schema"]["sameas_google"]: skips.append(("Google Link in", "the Google link IS in sameAs (evidence)"))
    A = ev["schema"]["areaserved"]
    if not A["delivery_offered"]: skips.append(("No areaServed in Site Schema", "the dealer offers no delivery (evidence), so areaServed is not checked (rule 4)"))
    elif A["code_places"]: skips.append(("No areaServed in Site Schema", "areaServed IS present on the dealership entity (evidence)"))
    elif ev["schema"].get("areaserved_elsewhere"): skips.append(("No areaServed in Site Schema", "areaServed appears in a block other than the dealership entity (evidence), so the finding is worded for the entity"))
    if ev["reviews"]["real_reviews_visible_on_site"]:
        pat = """ and "Google Reviews Aren't Shown" in html.replace('&rsquo;',"'")"""
        if pat not in blk: raise AssertionError("suite changed: the Google Reviews Aren't Shown check was not found")
        blk = blk.replace(pat, "", 1); print("   skipped repository condition \"Google Reviews Aren't Shown\": real reviews ARE shown on the website (evidence)")
    for tok, why in skips:
        pat = "'" + tok + "' in html"
        if pat not in blk: raise AssertionError(f"suite changed: {pat} not found")
        blk = re.sub(re.escape(pat) + r"\s+and\s+", "", blk, count=1) if re.search(re.escape(pat) + r"\s+and\s+", blk) else blk.replace(pat, "True", 1)
        print(f"   skipped repository condition {pat!r}: {why}")
    sd = float(re.search(r'<span class="score-num">([\d.]+)</span>', D).group(1)); sh = float(re.search(r'<span class="score-big">([\d.]+)</span>', HS).group(1)) if HS else sd
    m = (re.search(r'OVERALL</strong></td><td><span class="cc-big" data-fill="(\d+)">([\d.]+)/10', D)   # RULE L (v16.3)
         or re.search(r'OVERALL</strong></td><td><div class="bar-wrap"><div class="bar-fill" style="width:(\d+)%;[^"]*"></div></div>([\d.]+)/10', D))
    fill, sco = int(m.group(1)), float(m.group(2))
    if HS: assert int(re.search(r"\.score-fill\{height:100%;width:(\d+)%", HS).group(1)) == fill, "slider fill differs from the scorecard bar"
    try:
            exec(blk, {"re": re, "html": D, "div_depth": lambda t: len(re.findall(r"<div[ >]", t)) - len(re.findall(r"</div>", t)), "overall": lambda r: S.overall(r),
                       "rows": rows, "score": ovr, "score_dhap_banner": sd, "score_hotsheet_big": sh, "scorecard_overall_value": sco, "fill_width": fill})
    except AssertionError as e:   # the suite's bare asserts say nothing: name the failing line
        tb = e.__traceback__
        while tb and tb.tb_frame.f_code.co_filename != '<string>': tb = tb.tb_next
        line = blk.splitlines()[tb.tb_lineno - 1].strip() if tb else '?'
        raise AssertionError(f"{e or 'assertion failed'}  <- repository suite line {tb.tb_lineno if tb else '?'}: {line[:220]}")
    dd = lambda t: len(re.findall(r"<div[ >]", t)) - len(re.findall(r"</div>", t))
    BAN = ['aggregateRating','AggregateRating','Review Markup','REVIEWS_UNMARKED','Markup Missing','review-rating','Review-rating','machine-readable','Schema-Invisible',
           'review guidelines','reputation signal','excluded from schema-based rich results','invisible to Google','review-enhanced','highest-impact schema fix',
           'Deploy aggregateRating','Reviews Out of Rich Results','Review Schema Deployed','4 cities','review gate','Review gate','Increase in Website Traffic',
           'More Local Search Traffic','SGE','MIDS']
    for name, t in (("DHAP", D), ("health alert", HS or "")):
        if not t: continue
        chk = t.replace("without any review markup in the structured data", "")
        for b in BAN: assert b not in chk, (name, "banned phrase", b)
        assert dd(t) == 0 and "noindex,nofollow" in t, (name, "div depth / noindex")
        for w in dealer_words: assert w not in t, (name, "text left over from the template dealer", w)
    picked = AC.pick(ev, rows) if AC.applies(ev) else None
    if HS is None:
        assert picked is not None and not picked[0], "health alert missing"
        assert sd == sco == ovr and fill == round(ovr * 10), "score mismatch on the DHAP"
        rule_l(D, ev, raw, rows, st)
        return f"rows {rows} overall {ovr} {st['label']} | no Digital Health Alert: every area scored 10 (rule 7)"
    for k in ['id="s1"','id="s2"','id="s3"','id="crumbStep"','SEE ALL ALERTS','SEE REVENUE IMPACT','ACCESS THE FULL REPORT','score-method',
              'MASSIVE REVENUE LEAK','Every Alert on this page is Fixable'] + ([] if picked else ['SAMEAS_LINKS', 'AI_VIS_GAPS']):
        assert k in HS, ("health alert missing", k)
    assert HS.count('class="step-btn"') == 2 and HS.count('class="gap-item"><span class="gx"') == 6
    assert "CLIKsearch" not in HS and "&trade;" not in re.search(r'<div class="header-title"[^>]*>(.*?)</div>', HS).group(1)
    assert "KPI_DEFINITIONS.TXT_OF YOUR CRITICAL ISSUES IDENTIFIED</div>" in HS and ".term-line{font-size:.95rem;line-height:1.65;color:#fff;font-weight:400;" in HS, "Alert terminal card (v16.3)"
    assert 'Critical Alerts Identified</span><span class="term-cursor">' in HS and "local searches and revenue go to someone else.<br>" in HS
    for t in re.findall(r'class="t-head">(.*?)</div>', HS): assert len(H.unescape(t)) <= 18, ("stat header too long", t)
    tv = re.findall(r'data-target="(\d+)"', HS); heads = re.findall(r'class="t-head">&gt; (\w+)', HS)
    if "_directory_results" in ev["nap"]:   # rule 8: both NAP tables, one row per site in each group plus the summary row
        R = ev["nap"]["_directory_results"]; ai = D[D.find('id="aivisibility"'):D.find('id="findings"')]; fi = D[D.find('id="findings"'):D.find('id="opportunities"')]
        for part, g, head in ((ai, "ai", "Where AI Tools &amp; Car Shoppers Read Your Name"), (fi, "network", "Directory Network Check")):
            assert head in part, ("NAP table missing", head)
            t = part[part.index(head):]; t = t[:t.index("</table>")]
            assert len(re.findall(r"<tr[ >]", t)) == 1 + sum(1 for r in R if g in r["groups"]) + 1, ("NAP table rows", g)
    if picked:   # rule 7: exactly the engine's cards, in order, with their numbers and statuses
        assert heads == [x["head"] for x in picked[0]] and tv == [str(x["target"]) for x in picked[0]], ("stat cards differ from the engine's pick", heads, tv)
        assert re.findall(r'class="t-stat" data-status="([^"]+)"', HS) == [x["status"] for x in picked[0]], "stat card statuses differ from their area scores"
        assert picked[1] in HS, "Revenue Impact paragraph is not the engine's"
    else:
        ai = D[D.find('id="aivisibility"'):D.find('id="findings"')]
        gaps = len(re.findall(r'<div style="display:flex;align-items:flex-start;gap:9px;', ai.split("Key Gaps")[1].split("How This Assessment")[0]))
        assert gaps == int(tv[heads.index("AI_VIS_GAPS")]), ("AI_VIS_GAPS must equal the Key Gaps bullets", gaps, tv)
    assert report_id in HS and report_id not in D, "Report ID belongs on the health alert only"
    assert sd == sh == sco == ovr and fill == round(ovr * 10), "score mismatch between pages"
    low = st["lowest_row"].replace("&", "&amp;")
    assert st["label"] in D and f"Status set by the lowest category: <b>{low} {st['lowest_value']:.1f}/10</b>" in D, "status / lowest-row note missing on the DHAP"
    rule_l(D, ev, raw, rows, st)
    assert f"({low}: {st['lowest_value']:.1f}/10)" in HS, "health-alert method caption"
    if st["label"] == "Critical": assert "[</span>CRITICAL<" in HS
    else: assert f"[</span>{st['label'].upper()}<" in HS and "[</span>CRITICAL<" not in HS, "verdict label must follow the status"
    return f"rows {rows} overall {ovr} {st['label']} | stats {dict(zip(heads, tv))}"

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--repo", default=str(S.default_repo())); ap.add_argument("--evidence", required=True)
    ap.add_argument("--content", required=True); ap.add_argument("--out", required=True); ap.add_argument("--venv", default=None, help="python environment with Playwright; default: the one running this")
    ap.add_argument("--no-probe", action="store_true"); a = ap.parse_args()
    repo = pathlib.Path(a.repo).expanduser(); ev = json.load(open(a.evidence)); c = json.load(open(a.content))
    venv = a.venv or (str(pathlib.Path.home() / ".dhap-gbp-venv") if (pathlib.Path.home() / ".dhap-gbp-venv" / "bin" / "python").exists() else None)   # step 2 of the run routine creates this
    py = str(pathlib.Path(venv).expanduser() / "bin" / "python") if venv else sys.executable; T = {}
    def gate(name, fn):
        t0 = time.perf_counter()
        try: r = fn()
        except SystemExit as e: print(f"[FAIL] {name}: {e}"); sys.exit(1)
        except AssertionError as e: print(f"[FAIL] {name}: {e}"); sys.exit(1)
        T[name] = time.perf_counter() - t0; print(f"[PASS] {name} ({T[name]:.2f}s)" + (f": {r}" if r else "")); return r
    gate("1 rules guard", lambda: "SKILL.md v%s, scoring text matches" % S.rules_guard(repo)[0])
    def g2():
        p = S.check(ev)
        if p: raise SystemExit("evidence incomplete:\n  - " + "\n  - ".join(p))
    gate("2 evidence check", g2)
    def g3():
        p = F.check(ev, c)
        if p: raise SystemExit("unsourced numbers:\n  - " + "\n  - ".join(dict.fromkeys(p)))
    gate("3 facts gate", g3)
    def g4():
        r = subprocess.run([sys.executable, "-I", str(ENG / "build.py"), "--repo", str(repo), "--evidence", a.evidence, "--content", a.content, "--out", a.out], capture_output=True, text=True)
        if r.returncode: raise SystemExit(r.stdout + r.stderr)
        return json.loads(r.stdout)
    out = gate("4 build", g4)
    _strip = lambda t: re.sub(r"data:image/[a-z]+;base64,[A-Za-z0-9+/=]+", "data:image", t)   # RULE K: embedded evidence images must not trip text assertions
    D = _strip(pathlib.Path(out["dhap"]).read_text(encoding="utf-8")); HS = _strip(pathlib.Path(out["health_alert"]).read_text(encoding="utf-8")) if out["health_alert"] else None
    words = ["James Mitsubishi", "Greece, NY", "Greece NY", "Rochester", "GBP-JMGNY"] if "James" not in ev["dealer"] else []
    gate("5 repository assertions", lambda: (text_lint({"DHAP": D, "Digital Health Alert": HS}), suite(repo, D, HS, ev, c["report_id"], words))[1])
    procs = {}
    if not a.no_probe:
        procs["6 phone-width probe"] = subprocess.Popen([py, str(ENG / "probe_mobile.py"), out["dhap"], out["health_alert"] or "-", str(pathlib.Path(a.out) / "shots")], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    procs["7 spelling (advisory)"] = subprocess.Popen([py, str(ENG / "spellcheck.py"), out["dhap"], *([out["health_alert"]] if out["health_alert"] else [])], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    t0 = time.perf_counter(); fail = False
    for name, p in procs.items():
        o = p.communicate()[0].strip(); ok = p.returncode == 0 and "MIDS (must be 0): 0" in o if "spell" in name else p.returncode == 0
        if "spell" in name: ok = "MIDS (must be 0): 0" in o and o.count("MIDS (must be 0): 0") == (2 if out["health_alert"] else 1)
        print(f"[{'PASS' if ok else 'FAIL'}] {name}: " + " | ".join(l.strip() for l in o.splitlines()[-4:])); fail |= not ok
    print(f"   checks 6-7 ran side by side in {time.perf_counter() - t0:.1f}s")
    if not fail:
        def g8():
            pages = [out["dhap"]] + ([out["health_alert"]] if out["health_alert"] else [])
            r = subprocess.run([py, str(ENG / "to_markdown.py"), *pages], capture_output=True, text=True)
            if r.returncode: raise SystemExit(r.stdout + r.stderr)
            md = {pathlib.Path(x).with_suffix(".md"): x for x in pages}
            for m, page in md.items():
                t = m.read_text(encoding="utf-8")
                if page == out["dhap"]:
                    tabs = re.findall(r"(?m)^## (.+)$", t)
                    assert len(tabs) == 8, ("Markdown copy: the DHAP's 8 tabs", tabs)
                else:
                    assert re.search(r"(?m)^## Screen 3 of 3$", t), "Markdown copy: the Alert's 3 screens"
                    assert "Computing" not in t, "Markdown copy: an Alert stat card was read mid count-up"
                text_lint({m.name: t})
            return ", ".join(m.name for m in md)
        gate("8 Markdown copies (v16.5)", g8)
    if out.get("edge_warnings"): print("   EDGE WARNINGS (tell the user):", "; ".join(out["edge_warnings"]))
    print("ALL GATES PASSED" if not fail else "SOME GATES FAILED"); sys.exit(1 if fail else 0)

if __name__ == "__main__": main()

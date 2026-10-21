#!/usr/bin/env python3
"""DHAP GBP engine — one command for every gate, in order. Stops at the first gate that fails.
  1 rules guard (scoring text unchanged)   2 evidence check   3 facts gate   4 build both pages
  5 repository assertion suite (read from SKILL.md at run time) + health-alert checklist + score consistency
  6 phone-width probe (360/390/430, all tabs, 3 screens)   7 spelling (advisory list)
A condition in the repository suite is skipped ONLY when the evidence proves the gap it asserts is absent
(Google link present in sameAs; areaServed present); every skip is printed.
Usage: python3 check_all.py [--repo REPO] --evidence ev.json --content content.json --out OUTDIR [--venv PATH]"""
import argparse, html as H, json, pathlib, re, subprocess, sys, time
ENG = pathlib.Path(__file__).resolve().parent; sys.path.insert(0, str(ENG))
import score as S, facts as F, build as B

def suite(repo, D, HS, ev, report_id, dealer_words):
    raw, rows = S.score_rows(ev); st = S.status(rows); ovr = S.overall(rows)
    skill = (repo / "SKILL.md").read_text(encoding="utf-8")
    blk = skill[skill.index("## Assertion suite"):]; s0 = blk.index("```python") + 9; blk = blk[s0: blk.index("```", s0)]
    skips = []
    if ev["schema"]["sameas_google"]: skips.append(("Google Link in", "the Google link IS in sameAs (evidence)"))
    if ev["schema"]["areaserved"]: skips.append(("No areaServed in Site Schema", "areaServed IS present (evidence)"))
    elif ev["schema"].get("areaserved_elsewhere"): skips.append(("No areaServed in Site Schema", "areaServed appears in a block other than the dealership entity (evidence), so the finding is worded for the entity"))
    for tok, why in skips:
        pat = "'" + tok + "' in html"
        if pat not in blk: raise AssertionError(f"suite changed: {pat} not found")
        blk = re.sub(re.escape(pat) + r"\s+and\s+", "", blk, count=1) if re.search(re.escape(pat) + r"\s+and\s+", blk) else blk.replace(pat, "True", 1)
        print(f"   skipped repository condition {pat!r}: {why}")
    sd = float(re.search(r'<span class="score-num">([\d.]+)</span>', D).group(1)); sh = float(re.search(r'<span class="score-big">([\d.]+)</span>', HS).group(1))
    m = re.search(r'OVERALL</strong></td><td><div class="bar-wrap"><div class="bar-fill" style="width:(\d+)%;[^"]*"></div></div>([\d.]+)/10', D)
    fill, sco = int(m.group(1)), float(m.group(2))
    assert int(re.search(r"\.score-fill\{height:100%;width:(\d+)%", HS).group(1)) == fill, "slider fill differs from the scorecard bar"
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
    for name, t in (("DHAP", D), ("health alert", HS)):
        chk = t.replace("without any review markup in the structured data", "")
        for b in BAN: assert b not in chk, (name, "banned phrase", b)
        assert dd(t) == 0 and "noindex,nofollow" in t, (name, "div depth / noindex")
        for w in dealer_words: assert w not in t, (name, "text left over from the template dealer", w)
    for k in ['id="s1"','id="s2"','id="s3"','id="crumbStep"','SEE ALL ALERTS','SEE REVENUE IMPACT','ACCESS THE FULL REPORT','SAMEAS_LINKS','AI_VIS_GAPS','score-method',
              'MASSIVE REVENUE LEAK','Every Alert on this page is Fixable']:
        assert k in HS, ("health alert missing", k)
    assert HS.count('class="step-btn"') == 2 and HS.count('class="gap-item"><span class="gx"') == 6
    assert "CLIKsearch" not in HS and "&trade;" not in re.search(r'<div class="header-title"[^>]*>(.*?)</div>', HS).group(1)
    assert 'Critical Alerts Identified</span><span class="term-cursor">' in HS and "local searches and revenue go to someone else.<br>" in HS
    for t in re.findall(r'class="t-head">(.*?)</div>', HS): assert len(H.unescape(t)) <= 18, ("stat header too long", t)
    tv = re.findall(r'data-target="(\d+)"', HS); heads = re.findall(r'class="t-head">&gt; (\w+)', HS)
    ai = D[D.find('id="aivisibility"'):D.find('id="findings"')]
    gaps = len(re.findall(r'<div style="display:flex;align-items:flex-start;gap:9px;', ai.split("Key Gaps")[1].split("How This Assessment")[0]))
    assert gaps == int(tv[heads.index("AI_VIS_GAPS")]), ("AI_VIS_GAPS must equal the Key Gaps bullets", gaps, tv)
    assert report_id in HS and report_id not in D, "Report ID belongs on the health alert only"
    assert sd == sh == sco == ovr and fill == round(ovr * 10), "score mismatch between pages"
    low = st["lowest_row"].replace("&", "&amp;")
    assert st["label"] in D and f"{low} is {st['lowest_value']:.1f}/10" in D, "status / lowest-row note missing on the DHAP"
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
    D = _strip(pathlib.Path(out["dhap"]).read_text(encoding="utf-8")); HS = _strip(pathlib.Path(out["health_alert"]).read_text(encoding="utf-8"))
    words = ["James Mitsubishi", "Greece, NY", "Greece NY", "Rochester", "GBP-JMGNY"] if "James" not in ev["dealer"] else []
    gate("5 repository assertions", lambda: suite(repo, D, HS, ev, c["report_id"], words))
    procs = {}
    if not a.no_probe:
        procs["6 phone-width probe"] = subprocess.Popen([py, str(ENG / "probe_mobile.py"), out["dhap"], out["health_alert"], str(pathlib.Path(a.out) / "shots")], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    procs["7 spelling (advisory)"] = subprocess.Popen([py, str(ENG / "spellcheck.py"), out["dhap"], out["health_alert"]], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    t0 = time.perf_counter(); fail = False
    for name, p in procs.items():
        o = p.communicate()[0].strip(); ok = p.returncode == 0 and "MIDS (must be 0): 0" in o if "spell" in name else p.returncode == 0
        if "spell" in name: ok = "MIDS (must be 0): 0" in o and o.count("MIDS (must be 0): 0") == 2
        print(f"[{'PASS' if ok else 'FAIL'}] {name}: " + " | ".join(l.strip() for l in o.splitlines()[-4:])); fail |= not ok
    print(f"   checks 6-7 ran side by side in {time.perf_counter() - t0:.1f}s")
    if out.get("edge_warnings"): print("   EDGE WARNINGS (tell the user):", "; ".join(out["edge_warnings"]))
    print("ALL GATES PASSED" if not fail else "SOME GATES FAILED"); sys.exit(1 if fail else 0)

if __name__ == "__main__": main()

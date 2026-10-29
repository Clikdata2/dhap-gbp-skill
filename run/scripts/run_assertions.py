#!/usr/bin/env python3
"""Run the repository's assertion suite (SKILL.md '## Assertion suite') against the built files, plus the
hot sheet checklist, leftover-token checks and score-consistency checks.

The suite text is READ FROM THE REPOSITORY'S SKILL.md AT RUN TIME (never copied here), so it is always the
current one. Usage:
  python3 run_assertions.py --repo ~/.cache/dhap-gbp-skill --dhap X.html --health-alert Y.html --evidence ev.json \
      --report-id GBP-XXXXX-1026 --leftover "James" --leftover "Greece" \
      [--skip-cond "Google Link in=James-only gap; the Google link is present on this site"]
--skip-cond removes ONE condition (a `'TEXT' in html` test) from the repository suite and prints it as a
documented deviation. Only skip a condition when it asserts a gap this dealer does not have; report every skip to the user."""
import argparse, html as H, pathlib, re, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import lib_dhap as L
import alert_cards as AC   # the engine's rule 7 picker (lib_dhap puts engine/ on the path)

def remove_cond(blk, token):
    pat = "'" + token + "' in html"
    assert pat in blk, f"condition not found in repository suite: {pat}"
    # remove the condition together with a following ' and ' (or a preceding one); if it is the only test, make it True
    for rx in (re.escape(pat) + r"\s+and\s+", r"\s+and\s+" + re.escape(pat)):
        if re.search(rx, blk): return re.sub(rx, "", blk, count=1)
    return blk.replace(pat, "True", 1)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True); ap.add_argument("--dhap", required=True); ap.add_argument("--health-alert", required=True)
    ap.add_argument("--evidence", required=True); ap.add_argument("--report-id", required=True)
    ap.add_argument("--leftover", action="append", default=[]); ap.add_argument("--skip-cond", action="append", default=[])
    a = ap.parse_args()
    import json
    ev = json.load(open(a.evidence)); raw, rows = L.score_rows(ev); st = L.status_from_lowest(rows)
    skill = (pathlib.Path(a.repo).expanduser() / "SKILL.md").read_text(encoding="utf-8")
    blk = skill[skill.index("## Assertion suite"):]
    s0 = blk.index("```python") + 9; blk = blk[s0: blk.index("```", s0)]
    for sc in a.skip_cond:
        tok, _, why = sc.partition("="); blk = remove_cond(blk, tok); print(f"SKIPPED CONDITION: '{tok}' in html  -> {why}")
    STRIP_IMG = lambda t: re.sub(r"data:image/[a-z]+;base64,[A-Za-z0-9+/=]+", "data:image", t)
    D = STRIP_IMG(pathlib.Path(a.dhap).read_text(encoding="utf-8")); HS = STRIP_IMG(pathlib.Path(a.health_alert).read_text(encoding="utf-8"))
    sd = float(re.search(r'<span class="score-num">([\d.]+)</span>', D).group(1))
    sh = float(re.search(r'<span class="score-big">([\d.]+)</span>', HS).group(1))
    m = (re.search(r'OVERALL</strong></td><td><span class="cc-big" data-fill="(\d+)">([\d.]+)/10', D)   # RULE L (v16.3)
         or re.search(r'OVERALL</strong></td><td><div class="bar-wrap"><div class="bar-fill" style="width:(\d+)%;[^"]*"></div></div>([\d.]+)/10', D))
    fill, sc_overall = int(m.group(1)), float(m.group(2))
    fh = int(re.search(r"\.score-fill\{height:100%;width:(\d+)%", HS).group(1)); assert fh == fill, (fh, fill)
    env = {"re": re, "html": D, "div_depth": L.div_depth, "overall": L.overall, "rows": rows, "score": L.overall(rows),
           "score_dhap_banner": sd, "score_hotsheet_big": sh, "scorecard_overall_value": sc_overall, "fill_width": fill}
    exec(blk, env); print("repository DHAP assertion suite: PASSED")
    BAN = ['aggregateRating','AggregateRating','Review Markup','REVIEWS_UNMARKED','Markup Missing','review-rating','Review-rating','machine-readable',
           'Schema-Invisible','review guidelines','reputation signal','excluded from schema-based rich results','invisible to Google','review-enhanced',
           'highest-impact schema fix','Deploy aggregateRating','Reviews Out of Rich Results','Review Schema Deployed','4 cities','review gate','Review gate',
           'Increase in Website Traffic','More Local Search Traffic','SGE','MIDS']
    for name, t in (("DHAP", D), ("HEALTH-ALERT", HS)):
        chk = t.replace("without any review markup in the structured data", "")
        for b in BAN: assert b not in chk, (name, "banned phrase", b)
        assert L.div_depth(t) == 0 and "noindex,nofollow" in t, (name, "div depth / noindex")
        for old in a.leftover: assert old not in t, (name, "leftover from another dealer/run", old)
    picked = AC.pick(L._S.resolve_ages(ev), rows)[0] if AC.applies(ev) else None
    for k in ['id="s1"','id="s2"','id="s3"','id="crumbStep"','SEE ALL ALERTS','SEE REVENUE IMPACT','ACCESS THE FULL REPORT',
              'score-method','MASSIVE REVENUE LEAK','Every Alert on this page is Fixable', 'Reviews Not Shown on Website'] + ([] if picked else ['SAMEAS_LINKS', 'AI_VIS_GAPS']):
        assert k in HS, ("health-alert missing", k)
    assert HS.count('class="step-btn"') == 2 and HS.count('class="gap-item"><span class="gx"') == 6
    assert "CLIKsearch" not in HS and "&trade;" not in re.search(r'<div class="header-title"[^>]*>(.*?)</div>', HS).group(1)
    assert 'Critical Alerts Identified</span><span class="term-cursor">' in HS
    assert "local searches and revenue go to someone else.<br>" in HS
    for t in re.findall(r'class="t-head">(.*?)</div>', HS): assert len(H.unescape(t)) <= 18, ("t-head too long", t)
    tv = re.findall(r'data-target="(\d+)"', HS)
    ai = D[D.find('id="aivisibility"'):D.find('id="findings"')]
    gaps = len(re.findall(r'<div style="display:flex;align-items:flex-start;gap:9px;', ai.split("Key Gaps")[1].split("How This Assessment")[0]))
    if picked:   # rule 7 (v15.2): the stat cards are the engine's pick for this dealer
        heads = re.findall(r'class="t-head">&gt; (\w+)', HS)
        assert heads == [x["head"] for x in picked] and tv == [str(x["target"]) for x in picked], ("stat cards differ from engine/alert_cards.py", heads, tv)
    else: assert gaps == int(tv[3]), ("AI_VIS_GAPS must equal the Key Gaps bullets", gaps, tv)
    assert a.report_id in HS and a.report_id not in D, "Report ID belongs on the health alert only"
    assert sd == sh == sc_overall == L.overall(rows) and fill == round(L.overall(rows) * 10), "score mismatch"
    assert st["label"].upper() in HS and st["label"] in D and (f"{st['lowest_row'].replace('&','&amp;')} is {st['lowest_value']:.1f}/10" in D or f"Status set by the lowest category: <b>{st['lowest_row'].replace('&','&amp;')} {st['lowest_value']:.1f}/10</b>" in D), "status label / lowest-row note missing"
    assert f"({st['lowest_row'].replace('&','&amp;')}: {st['lowest_value']:.1f}/10)" in HS or f"({st['lowest_row']}: {st['lowest_value']:.1f}/10)" in HS, "health-alert method caption"
    print("rows", rows, "overall", L.overall(rows), "status", st["label"], "| stat targets", tv, "| AI Visibility gaps", gaps)
    print("ALL ASSERTIONS PASSED")

if __name__ == "__main__": main()

#!/usr/bin/env python3
"""DHAP GBP engine — Living Report design (v17.0, decided by Travis Nov 12 2026): the live DHAP and Digital Health Alert.

Turns a DHAP and a Digital Health Alert built by engine/build.py into the Living Report pages, in place, with the
same file names. It adds no facts and no wording about the dealer or the product: it reads the text out of the
built pages and lays the same text out again.

  DHAP   the eight tabs become eight chapters on one page, joined by a progress spine; the score is a gauge, the
         scorecard is a bar chart whose status pills filter it, findings and AI signals open on click, the
         Opportunities table reads as finding -> CLIKsearch action, and the proof opens in the RULE K side panel.
  Alert  the three screens stay, in the same order with the same words, as one monitored scroll: the 01/02/03
         breadcrumb follows the reader and is always clickable; the line above each old step button stays, as plain
         text at the button's size; heartbeat bands divide the screens.

The only text not taken from the built pages is the "Next steps" stepper (Mitsubishi only), which quotes
knowledge-base/jessica-kb-qa.json; it is left out if a sentence is no longer there.

An existing RULE K popup block on a page is kept and re-inserted, so already-delivered pages can be converted
without their screenshots. Pages already in the Living design are left alone.

Usage:
  python3 engine/living.py DHAP.html ALERT.html [--evidence EV.json] [--proof-spec SPEC.json --proof-images DIR]
  (ALERT.html = - when there is no Alert). Needs Playwright's Chromium (the engine already does).
"""
import argparse, html as H, json, math, pathlib, re, subprocess, sys, tempfile

HERE = pathlib.Path(__file__).resolve().parent / "living"
REPO = HERE.parents[1]
sys.path.insert(0, str(REPO / "scripts"))
import proof_popup  # noqa: E402  (RULE K side panel)

IDS = ["summary", "scorecard", "aivisibility", "findings", "opportunities", "solution", "whyact", "investment"]
COLORS = {"summary": "#e82b39", "scorecard": "#e82b39", "aivisibility": "#ea580c", "findings": "#ea580c",
          "opportunities": "#1d4ed8", "solution": "#1d4ed8", "whyact": "#16a34a", "investment": "#16a34a"}
BANDS = {"summary": "lr-dark", "aivisibility": "lr-white", "opportunities": "lr-white", "whyact": "lr-dark",
         "investment": "lr-white"}
HEX = {"red": "#dc2626", "org": "#ea580c", "yel": "#ca8a04", "grn": "#15803d", "gry": "#94a3b8"}
PLATFORMS = ["Facebook", "Instagram", "Threads", "LinkedIn", "Pinterest", "Bluesky"]
# Next steps: label, the text shown, and the knowledge-base sentences it must still be made of.
STEPS = [
    ("Get started", "There are two ways to get started. First, book a time now. Second, activate CLIKsearch in the MiDS Portal, and a dedicated optimization specialist will contact you directly.",
     ["There are two ways to get started. First, book a time now", "Second, activate CLIKsearch in the MiDS Portal, and a dedicated optimization specialist will contact you directly."]),
    ("Day one", "Initial profile setup, name, address, and phone consistency, categories, and nesting the Service and Parts profiles begin immediately.",
     ["Initial profile setup, name, address, and phone consistency, categories, and nesting the Service and Parts profiles begin immediately."]),
    ("First weeks", "Articles, GEO-optimized posts, and photos begin publishing in the first weeks after onboarding and compound over time.",
     ["Articles, GEO-optimized posts, and photos begin publishing in the first weeks after onboarding and compound over time."]),
    ("90 days", "CLIKsearch's commitment is go-live in 72 hours after onboarding and results within 90 days. Results vary by dealership.",
     ["CLIKsearch's commitment is go-live in 72 hours after onboarding and results within 90 days.", "Results vary by dealership"]),
]

EXTRACT = r"""() => {
const q=(r,s)=>r?r.querySelector(s):null, qa=(r,s)=>r?[...r.querySelectorAll(s)]:[];
const tx=e=>{if(!e)return '';const c=e.cloneNode(true);c.querySelectorAll('br').forEach(b=>b.replaceWith(' '));return c.textContent.replace(/\s+/g,' ').trim()};
const ih=e=>e?e.innerHTML.replace(/\s+/g,' ').trim():'';
const tone=e=>!e?'':(['red','orange','green'].find(k=>e.classList.contains(k))||'');
const facts=p=>qa(p,'.hero-fact').map(f=>({num:tx(q(f,'.hero-fact-num')),tone:tone(q(f,'.hero-fact-num')),lbl:tx(q(f,'.hero-fact-lbl'))}));
const bullets=p=>qa(p,'.score-desc>div').map(d=>{const c=d.cloneNode(true),f=c.firstElementChild;if(f&&tx(f)==='●')f.remove();return ih(c)});
const card=c=>{if(!c)return null;const t=q(c,'.finding-title'),tag=t?q(t,'[class*="tag-"]'):null;let title='';
  if(t){const k=t.cloneNode(true);qa(k,'[class*="tag-"]').forEach(x=>x.remove());title=ih(k)}
  return {kind:['critical','major','opportunity','working'].find(k=>c.classList.contains(k))||'note',icon:tx(q(c,'.finding-icon')),title,tag:tx(tag),
          tagTone:tag?(/green/.test(tag.className)?'green':'amber'):'',body:ih(q(c,'.finding-body')),pill:tx(q(c,'.pill'))}};
const groups=p=>{const out=[];let cur=null;for(const el of (p?p.children:[])){if(el.classList.contains('section-title')){cur={title:tx(el),cards:[]};out.push(cur)}
  else if(el.classList.contains('finding-card')&&cur){cur.cards.push(card(el))}}return out.filter(g=>g.cards.length)};
const rowTone=tr=>((tr.className.match(/cc-(?:t-)?(red|org|yel|grn|gry)/)||[])[1])||'';
const BANDS=[['Critical','red'],['Major Issues','org'],['Needs Improvement','yel'],['Fully Optimized','grn']];
const bandOf=v=>isNaN(v)?['','gry']:v<=5?BANDS[0]:v<7?BANDS[1]:v<9?BANDS[2]:BANDS[3];
const statusIn=t=>BANDS.find(b=>new RegExp(b[0],'i').test(t||''));
const sigTone=t=>/critical/i.test(t)?'red':/major/i.test(t)?'org':/partial/i.test(t)?'yel':/strength|strong|verified/i.test(t)?'grn':'gry';
const noEmoji=t=>(t||'').replace(/^[^A-Za-z0-9]+/,'').trim();
const num=t=>parseFloat(((t||'').match(/\d+(?:\.\d+)?/)||[''])[0]);
const roi=b=>b?{eyebrow:tx(q(b,'.roi-eyebrow')),amount:tx(q(b,'.roi-amount')),sub:ih(q(b,'.roi-sub')),cta:tx(q(b,'.roi-cta-btn')),href:(q(b,'.roi-cta-btn')||{}).href||''}:null;
const P=id=>document.getElementById(id);
const sum=P('summary'),sc=P('scorecard'),ai=P('aivisibility'),fi=P('findings'),op=P('opportunities'),so=P('solution'),wy=P('whyact'),inv=P('investment');
const st=q(sc,'table.score-table'),at=q(ai,'table.score-table'),ot=q(op,'table'),it=q(inv,'table');
const ab=q(ai,'.score-banner'),abl=ab?ab.firstElementChild:null,wst=qa(wy,':scope>.section-title'),inc=q(inv,'ul.feature-list');
const pimg=q(document,'.pill img');
return {
 title:document.title, logo:(q(document,'.nav-logo')||{}).src||'', pillLogo:pimg?pimg.src:'',
 tabs:qa(document,'.tab-btn').map(b=>({t:tx(b),id:((b.getAttribute('onclick')||'').match(/'([^']+)'/)||[])[1]||''})),
 summary:{eyebrow:tx(q(sum,'.hero-eyebrow')),title:ih(q(sum,'.hero-title')),sub:ih(q(sum,'.hero-sub')),facts:facts(sum),score:tx(q(sum,'.score-num')),
          denom:tx(q(sum,'.score-denom')),label:tx(q(sum,'.score-banner-context .score-label')),bullets:bullets(sum)},
 scorecard:{title:tx(q(sc,'.section-title')),intro:ih(q(sc,':scope>p')),head:qa(st,'thead th').map(tx),
  legend:(l=>l.length===4?l:['5.0 or below — Critical','above 5.0 to 6.9 — Major Issues','7.0 to 8.9 — Needs Improvement','9.0 or higher — Fully Optimized'])(qa(sc,'.cc-legend span').map(tx)),
  rows:qa(st,'tbody tr').map(tr=>{const td=tr.children;
   if(tr.classList.contains('cc-total')||/^OVERALL/i.test(tx(td[0]))){const st2=tx(q(td[2],'.cc-pill'))||((statusIn(tx(td[2]))||[''])[0]);
     const sub=q(td[2],'.cc-sub')?ih(q(td[2],'.cc-sub')):(()=>{const c=td[2].cloneNode(true);c.childNodes.forEach(n=>{if(n.nodeType===3)n.textContent=n.textContent.replace(/[^A-Za-z(]*(Critical|Major Issues|Needs Improvement|Fully Optimized)/i,'')});return ih(c)})();
     return {total:true,tone:rowTone(tr)||(statusIn(st2)||['','gry'])[1],name:tx(td[0]),score:tx(q(td[1],'.cc-big'))||tx(td[1]),status:st2.toUpperCase(),sub,pill:tx(td[3])};}
   const c2=td[2].cloneNode(true);qa(c2,'.cc-pts,.cc-why').forEach(x=>x.remove());
   const sc1=tx(q(td[1],'.cc-sc'))||tx(td[1]),b=bandOf(num(sc1));
   return {tone:rowTone(tr)||b[1],name:tx(td[0]),score:sc1,fill:(q(td[1],'.bar-fill')||{style:{}}).style.width||'0%',status:tx(q(td[1],'.cc-b'))||b[0].toUpperCase(),found:ih(c2),
           pts:qa(td[2],'.cc-pt').map(p=>({k:['full','part','zero','off'].find(k=>p.classList.contains(k))||'',h:ih(p)})),why:ih(q(td[2],'.cc-why')),pill:tx(td[3])}})},
 ai:{eyebrow:tx(q(ai,'.hero-eyebrow')),title:ih(q(ai,'.hero-title')),sub:ih(q(ai,'.hero-sub')),facts:facts(ai),icon:tx(abl&&abl.children[0]),label:tx(abl&&abl.children[1]),
     sub2:tx(abl&&abl.children[2]),gapsTitle:tx(q(ab,'.score-banner-context .score-label')),bullets:bullets(ai),how:card(q(ai,':scope>.finding-card')),
     tableTitle:tx(at&&at.previousElementSibling),head:qa(at,'thead th').map(tx),
     rows:qa(at,'tbody tr').map(tr=>{const td=tr.children,nm=tx(q(td[0],'strong'))||tx(td[0]),stt=noEmoji(tx(td[2]));return {total:tr.classList.contains('cc-total')||/^OVERALL/i.test(nm),tone:rowTone(tr)||sigTone(stt),name:nm,desc:tx(q(td[0],'div')),
       tag:tx(td[1]),tagTone:/green/.test(td[1].innerHTML)?'green':'amber',status:stt.toUpperCase(),fix:tx(td[3])}}),
     groups:groups(ai),close:{title:tx(q(ai,':scope>.mids-box .mids-title')),body:ih(q(ai,':scope>.mids-box .mids-body'))}},
 findings:{groups:groups(fi)},
 opportunities:{title:tx(q(op,'.section-title')),head:qa(ot,'thead th').map(tx),
  rows:qa(ot,'tbody tr').map(tr=>{const td=tr.children,tag=q(td[2],'.roi-tag');return {name:tx(td[0]),impact:tx(td[1]),action:tag?tx(tag.lastElementChild):tx(td[2]),pill:tx(td[3]),fin:!tag}})},
 solution:{name:tx(q(so,'.solution-name')),tagline:tx(q(so,'.solution-tagline')),para:ih(q(so,'.solution-body>p')),features:qa(so,'ul.feature-list li').map(ih),
  mids:{title:tx(q(so,'.mids-title')),body:ih(q(so,'.mids-body'))},
  managed:{headline:tx(q(so,'.managed-headline')),chips:qa(so,'.managed-box>div:not([class])>span').map(tx),pitTitle:tx(q(so,'.managed-pitfall-title')),
           pits:qa(so,'.pitfall-list li').map(ih),footer:ih(q(so,'.managed-footer'))}},
 why:{title:tx(wst[0]),note:ih(q(wy,':scope>p')),stats:qa(wy,'.snap-card').map(c=>({num:tx(q(c,'.snap-num')),lbl:tx(q(c,'.snap-lbl'))})),title2:tx(wst[1]),
      cards:qa(wy,':scope>.finding-card').map(card),roi:roi(q(wy,'.roi-banner'))},
 investment:{title:tx(q(inv,'.section-title')),head:qa(it,'thead th').map(tx),rows:qa(it,'tbody tr').map(tr=>[...tr.children].map(ih)),
             incTitle:tx(inc&&inc.previousElementSibling),included:qa(inc,'li').map(ih),roi:roi(q(inv,'.roi-banner'))}
};}"""


def esc(s):
    return H.escape(s or "", quote=True)


def strip(h):
    return H.unescape(re.sub(r"<[^>]+>", "", h or "")).strip()


def num_attrs(s):
    """Count-up attributes for a plain number such as 5.8, 72%, +62.4% or 60+; nothing for words."""
    m = re.fullmatch(r"([+\-]?)(\d+(?:\.\d+)?)(%|\+)?", (s or "").strip())
    if not m:
        return ""
    dec = len(m.group(2).split(".")[1]) if "." in m.group(2) else 0
    return f' data-count="{m.group(2)}" data-dec="{dec}" data-pre="{m.group(1)}" data-suf="{m.group(3) or ""}" data-final="{esc(s.strip())}"'


def ekg(color, cls="lr-ekg"):
    beat = "h70l7-5 7 5h10l6 9 9-34 9 44 7-19h12l9-8 9 8h85"
    return (f'<svg class="{cls}" viewBox="0 0 1200 46" preserveAspectRatio="xMidYMid slice" aria-hidden="true" style="--ek:{color}">'
            f'<path pathLength="1" d="M0 26{beat * 5}"/></svg>')


def gauge(score):
    v = max(0.0, min(10.0, float(score)))
    def pt(val, r):
        a = math.radians(180 - 18 * val); return 120 + r * math.cos(a), 120 - r * math.sin(a)
    def arc(a, b, r=96):
        (x0, y0), (x1, y1) = pt(a, r), pt(b, r); return f"M{x0:.1f} {y0:.1f}A{r} {r} 0 0 1 {x1:.1f} {y1:.1f}"
    bands = [(0, 5, HEX["red"]), (5, 7, HEX["org"]), (7, 9, HEX["yel"]), (9, 10, HEX["grn"])]
    paths = "".join(f'<path d="{arc(a + (.07 if a else 0), b - (.07 if b < 10 else 0))}" stroke="{c}" stroke-width="16" fill="none"/>' for a, b, c in bands)
    ticks = "".join(f'<text x="{pt(t, 117)[0]:.1f}" y="{pt(t, 117)[1] + 3:.1f}" text-anchor="middle">{t}</text>' for t in (0, 5, 7, 9, 10))
    return (f'<div class="lr-gauge"><svg viewBox="-16 -6 272 140" role="img" aria-label="{esc(score)} out of 10">'
            f'<path d="{arc(0, 10)}" stroke="rgba(255,255,255,.08)" stroke-width="24" fill="none"/>{paths}{ticks}'
            f'<g class="lr-needle" style="--a:{v * 18 - 90:.1f}deg"><path d="M120 120L115.5 120L120 38L124.5 120Z" fill="#fff"/></g>'
            f'<circle cx="120" cy="120" r="9" fill="#fff"/><circle cx="120" cy="120" r="4" fill="#0f172a"/></svg></div>')


def facts_html(facts, light=False):
    cells = "".join(f'<div class="hero-fact lr-fact lr-rv" style="--d:{i * .08:.2f}s"><div class="hero-fact-num {f["tone"]}"{num_attrs(f["num"])}>{esc(f["num"])}</div>'
                    f'<div class="hero-fact-lbl">{esc(f["lbl"])}</div></div>' for i, f in enumerate(facts))
    return f'<div class="lr-factwrap{" lr-light" if light else ""}">{proof_popup.HINT}<div class="lr-facts">{cells}</div></div>'


def bullets_html(items):
    return '<ul class="lr-bul">' + "".join(f"<li>{b}</li>" for b in items) + "</ul>" if items else ""


def pill(text, logo="", green=False):
    if not text:
        return ""
    img = f'<img src="{esc(logo)}" alt="">' if logo else ""
    return f'<span class="lr-pill{" green" if green else ""}">{img}{esc(text)}</span>'


def card_html(c, d=0.0, clamp=True):
    tag = f' <span class="lr-tag {c["tagTone"]}">{esc(c["tag"])}</span>' if c["tag"] else ""
    pl = f'<div>{pill(c["pill"])}</div>' if c["pill"] else ""
    return (f'<article class="lr-card k-{c["kind"]} lr-rv"{" data-clamp" if clamp else ""} style="--d:{d:.2f}s"><header><span class="ic">{esc(c["icon"])}</span>'
            f'<span class="tt">{c["title"]}{tag}</span></header><div class="bd">{c["body"]}</div>{pl}<span class="more" aria-hidden="true"></span></article>')


def roi_html(r):
    if not r:
        return ""
    sub = re.sub(r"(Results in 90 days\.)(\s*\1)+", r"\1", r["sub"])   # the built page repeats this sentence
    return (f'<div class="lr-cta lr-rv"><div class="ce">{esc(r["eyebrow"])}</div><div class="ca">{esc(r["amount"])}</div><div class="cs">{sub}</div>'
            f'<a class="lr-btn" href="{esc(r["href"])}" target="_blank" rel="noopener">{esc(r["cta"])}</a></div>')


# ---------------------------------------------------------------- chapters
def ch_summary(D, X):
    s = D["summary"]
    tot = next((r for r in D["scorecard"]["rows"] if r.get("total")), {"tone": "red"})
    col = {"red": "#ff5c69", "org": "#fb923c", "yel": "#facc15", "grn": "#4ade80"}.get(tot["tone"], "#ff5c69")
    live = f'<span class="lr-live">{esc(X["live"])}</span>' if X.get("live") else ""
    scale = "".join(f'<span><i style="background:{HEX[t]}"></i>{esc(x)}</span>' for t, x in zip(("red", "org", "yel", "grn"), D["scorecard"]["legend"]))
    return (f'<div class="lr-eyebrow lr-rv">{esc(s["eyebrow"])}{live}</div>'
            f'<div class="lr-hero"><div class="lr-rv"><h1 class="lr-h1">{s["title"]}</h1><p class="lr-lead">{s["sub"]}</p></div>'
            f'<div class="lr-gcard lr-rv" style="--sc:{col};--d:.15s">{gauge(s["score"])}'
            f'<div class="lr-score"><span class="lr-score-n"{num_attrs(s["score"])}>{esc(s["score"])}</span><span class="lr-score-d">{esc(s["denom"])}</span></div>'
            f'<div class="lr-score-l">{esc(s["label"])}</div><div class="lr-scale">{scale}</div>{bullets_html(s["bullets"])}</div></div>'
            f'{facts_html(s["facts"])}')


def row_html(r, logo, i, opened):
    pts = "".join(f'<span class="cc-pt {p["k"]}">{p["h"]}</span>' for p in r["pts"])
    return (f'<div class="lr-row t-{r["tone"]} lr-rv{" open" if opened else ""}" data-k="{r["tone"]}" style="--d:{i * .06:.2f}s">'
            f'<button type="button" class="lr-row-h" aria-expanded="{"true" if opened else "false"}"><span class="lr-row-n">{esc(r["name"])}</span>'
            f'<span class="lr-bar"><i style="--w:{esc(r["fill"])}"></i></span><span class="lr-row-s">{esc(r["score"])}</span>'
            f'<span class="lr-chip">{esc(r["status"])}</span><span class="lr-chev" aria-hidden="true"></span></button>'
            f'<div class="lr-row-d"><div><div class="lr-row-di"><div>{r["found"]}</div><div class="lr-pts">{pts}</div><div class="lr-why">{r["why"]}</div>{pill(r["pill"], logo)}</div></div></div></div>')


def ch_scorecard(D, X):
    s = D["scorecard"]; rows = [r for r in s["rows"] if not r.get("total")]; tot = next((r for r in s["rows"] if r.get("total")), None)
    low = min(range(len(rows)), key=lambda i: float(rows[i]["score"].split("/")[0])) if rows else -1
    cnt = lambda t: sum(1 for r in rows if r["tone"] == t)
    chips = f'<button type="button" class="active" data-f="">All <em>{len(rows)}</em></button>' + "".join(
        f'<button type="button" class="t-{t}" data-f="{t}"{"" if cnt(t) else " disabled"}><i></i>{esc(x)} <em>{cnt(t)}</em></button>' for t, x in zip(("red", "org", "yel", "grn"), s["legend"]))
    body = "".join(row_html(r, D["pillLogo"], i, i == low) for i, r in enumerate(rows))
    total = (f'<div class="lr-total t-{tot["tone"]} lr-rv"><div><div class="lr-total-n">{esc(tot["name"])}</div><div class="lr-total-s">{esc(tot["score"])}</div></div>'
             f'<div class="lr-total-t"><span class="lr-chip">{esc(tot["status"])}</span>{tot["sub"]}</div>{pill(tot["pill"], green=True)}</div>') if tot else ""
    head = esc(s["head"][2]) if len(s["head"]) > 2 else ""
    return (f'<h2 class="lr-h2 lr-rv">{esc(s["title"])}</h2><p class="lr-small lr-rv">{s["intro"]}</p>'
            f'<div class="lr-filter lr-rv" data-target="#lr-sc">{chips}</div>'
            f'<div class="lr-tools lr-rv"><div class="lr-dlbl" style="margin:0">{head}</div>'
            f'<button type="button" class="lr-linkbtn" data-expand="#lr-sc" data-more="Open all" data-less="Close all">Open all</button></div>'
            f'<div class="lr-rows" id="lr-sc">{body}</div>{total}')


def ch_ai(D, X):
    a = D["ai"]; rows = [r for r in a["rows"] if not r["total"]]; tot = next((r for r in a["rows"] if r["total"]), None)
    tone = tot["tone"] if tot else "red"; dark = {"red": "#ff5c69", "org": "#fb923c", "yel": "#facc15", "grn": "#4ade80"}.get(tone, "#ff5c69")
    tags = []
    for r in rows:
        if r["tag"] and r["tag"] not in tags:
            tags.append(r["tag"])
    slug = lambda t: re.sub(r"[^a-z]+", "-", t.lower()).strip("-")
    chips = '<button type="button" class="active" data-f="">All <em>' + str(len(rows)) + "</em></button>" + "".join(
        f'<button type="button" data-f="{slug(t)}">{esc(t)} <em>{sum(1 for r in rows if r["tag"] == t)}</em></button>' for t in tags)
    fixh = esc(a["head"][3]) if len(a["head"]) > 3 else ""
    body = "".join(
        f'<div class="lr-row sig t-{r["tone"]} lr-rv" data-k="{slug(r["tag"])}" style="--d:{i * .05:.2f}s"><button type="button" class="lr-row-h" aria-expanded="false">'
        f'<span class="lr-row-n">{esc(r["name"])}</span><span class="lr-tag {r["tagTone"]}">{esc(r["tag"])}</span><span class="lr-chip">{esc(r["status"])}</span>'
        f'<span class="lr-chev" aria-hidden="true"></span></button><div class="lr-row-d"><div><div class="lr-row-di"><div>{esc(r["desc"])}</div>'
        f'<div style="margin-top:10px"><span class="lr-dlbl" style="display:inline;margin-right:8px">{fixh}</span>{pill(r["fix"])}</div></div></div></div></div>'
        for i, r in enumerate(rows))
    total = (f'<div class="lr-total t-{tot["tone"]} lr-rv"><div class="lr-total-n">{esc(tot["name"])}</div><div class="lr-total-t"><span class="lr-chip">{esc(tot["status"])}</span></div>'
             f'{pill(tot["fix"], green=True)}</div>') if tot else ""
    groups = "".join(f'<h3 class="lr-h3 lr-rv">{esc(g["title"])}</h3><div class="lr-cards">' + "".join(card_html(c, i * .08) for i, c in enumerate(g["cards"])) + "</div>" for g in a["groups"])
    how = card_html(a["how"], clamp=False) if a["how"] else ""
    close = f'<div class="lr-mids blue lr-rv"><div class="mt">{esc(a["close"]["title"])}</div><div class="mb">{a["close"]["body"]}</div></div>' if a["close"]["title"] else ""
    return (f'<div class="lr-eyebrow lr-rv">{esc(a["eyebrow"])}</div>'
            f'<div class="lr-hero"><div class="lr-rv"><h2 class="lr-h2">{a["title"]}</h2><p class="lr-lead">{a["sub"]}</p></div>'
            f'<div class="lr-gcard lr-navy lr-rv" style="--sc:{dark};--d:.15s"><div class="lr-aistat"><span>{esc(a["icon"])}</span><span class="lb">{esc(a["label"])}</span>'
            f'<span class="sb">{esc(a["sub2"])}</span></div><div class="lr-dlbl">{esc(a["gapsTitle"])}</div>{bullets_html(a["bullets"])}</div></div>'
            f'{facts_html(a["facts"], light=True)}<div class="lr-cards one" style="margin-top:22px">{how}</div>'
            f'<h3 class="lr-h3 lr-rv">{esc(a["tableTitle"])}</h3><div class="lr-filter lr-rv" data-target="#lr-ai">{chips}</div>'
            f'<div class="lr-rows" id="lr-ai">{body}</div>{total}{groups}{close}')


def both_views(ev):
    """The 'Both views' rule as a picture: what the website schema describes next to what Google lists."""
    if not ev:
        return ""
    L = ev.get("listings") or {}; n = (ev.get("schema") or {}).get("department_entities")
    if n not in (0, 3):
        return ""   # the evidence does not say which departments the schema describes
    on = {"Sales": bool(L.get("sales")), "Service": bool(L.get("service") or L.get("combined")), "Parts": bool(L.get("parts") or L.get("combined"))}
    cell = lambda ok, yes: f'<div class="lr-vcell{"" if ok else " miss"}">{"&#10003; " + yes if ok else "&#10005; Missing"}</div>'
    return ('<div class="lr-views lr-rv"><div class="lr-dlbl">Both views</div><div class="lr-views-g"><div></div>' + "".join(f'<div class="hd">{d}</div>' for d in on)
            + '<div class="rl">Website schema</div>' + "".join(cell(n == 3, "In schema") for _ in on)
            + '<div class="rl">Google Business Profile listing</div>' + "".join(cell(v, "Listed") for v in on.values()) + "</div></div>")


def ch_findings(D, X):
    gs = D["findings"]["groups"]; total = sum(len(g["cards"]) for g in gs)
    chips = f'<button type="button" class="active" data-f="">All <em>{total}</em></button>' + "".join(
        f'<button type="button" data-f="g{i}">{esc(g["title"])} <em>{len(g["cards"])}</em></button>' for i, g in enumerate(gs))
    body = "".join(f'<div class="lr-fgroup" data-k="g{i}"><h3 class="lr-h3 lr-rv">{esc(g["title"])}</h3><div class="lr-cards">'
                   + "".join(card_html(c, j * .07) for j, c in enumerate(g["cards"])) + "</div></div>" for i, g in enumerate(gs))
    return (f'<h2 class="lr-h2 lr-rv">{esc(X["label"])}</h2>{both_views(X.get("evidence"))}'
            f'<div class="lr-filter lr-rv" data-target="#lr-fi">{chips}</div><div id="lr-fi">{body}</div>')


def ch_opportunities(D, X):
    o = D["opportunities"]; h = o["head"] + [""] * 4
    def kind(r):
        return "fin k-fin" if r["fin"] else "k-crit" if "Critical" in r["impact"] else "k-maj" if "Major" in r["impact"] else "k-opp"
    rows = "".join(
        f'<div class="lr-opp {kind(r)} lr-rv"><div class="lr-opp-a"><span class="lr-imp">{esc(r["impact"])}</span><div class="nm"><strong>{esc(r["name"])}</strong></div></div>'
        f'<div class="lr-opp-ar" aria-hidden="true"><i></i></div><div class="lr-opp-b"><span>{"<strong>" + esc(r["action"]) + "</strong>" if r["fin"] else esc(r["action"])}</span>'
        f'{pill(r["pill"], D["pillLogo"], green=r["fin"])}</div></div>' for r in o["rows"])
    return (f'<h2 class="lr-h2 lr-rv">{esc(o["title"])}</h2><div class="lr-opphead lr-rv"><span>{esc(h[0])} · {esc(h[1])}</span><span></span><span>{esc(h[2])}</span></div>{rows}')


def ch_solution(D, X):
    s = D["solution"]; prof, posts, rest = {}, {}, []
    for f in s["features"]:
        t = strip(f)
        m = re.match(r"^(Sales|Service|Parts) Profile(?: \(([^)]+)\))? — (.+)$", t); n = re.match(r"^Up to (\d+) (Sales|Service|Parts) Posts", t)
        if m: prof[m.group(1)] = (m.group(2) or "", m.group(3))
        elif n: posts[n.group(2)] = (n.group(1), t)
        else: rest.append(f)
    pack = ""
    if set(prof) == set(posts) == {"Sales", "Service", "Parts"}:
        pack = '<div class="lr-pack">' + "".join(
            f'<div class="lr-pack-c lr-rv" style="--d:{i * .12:.2f}s"><div class="pn">{d} Profile{"<em>" + esc(prof[d][0]) + "</em>" if prof[d][0] else ""}</div><div class="pd">{esc(prof[d][1])}</div>'
            f'<div class="pc"{num_attrs(posts[d][0])}>{posts[d][0]}</div><div class="pl">{esc(posts[d][1])}</div></div>' for i, d in enumerate(("Sales", "Service", "Parts"))) + "</div>"
    else:
        rest = s["features"]
    hub = ""
    omni = next((f for f in rest if "Omni-Social" in strip(f)), None); plats = [p for p in PLATFORMS if p in strip(s["para"])]
    if omni and len(plats) >= 3:
        rest = [f for f in rest if f is not omni]
        hub = (f'<div class="lr-hub lr-rv"><div class="lr-hub-t">{omni}</div><div class="lr-hub-src">GBP post</div><div class="lr-hub-wire" aria-hidden="true"><i></i></div>'
               '<div class="lr-hub-out">' + "".join(f'<span style="--i:{i}">{p}</span>' for i, p in enumerate(plats)) + "</div></div>")
    m = s["managed"]
    managed = (f'<div class="lr-managed lr-rv"><div class="mh">{esc(m["headline"])}</div><div class="lr-mchips">' + "".join(f"<span>{esc(c)}</span>" for c in m["chips"]) + "</div>"
               f'<h3 class="lr-h3" style="margin-top:20px">{esc(m["pitTitle"])}</h3><ul class="lr-pits lr-rv">' + "".join(f"<li>{p}</li>" for p in m["pits"]) + "</ul>"
               f'<div class="lr-foot">{m["footer"]}</div></div>') if m["headline"] else ""
    mids = f'<div class="lr-mids lr-rv"><div class="mt">{esc(s["mids"]["title"])}</div><div class="mb">{s["mids"]["body"]}</div></div>' if s["mids"]["title"] else ""
    return (f'<h2 class="lr-h2 lr-rv">{esc(s["name"])}</h2><div class="lr-tagline lr-rv">{esc(s["tagline"])}</div><p class="lr-lead lr-rv">{s["para"]}</p>{pack}{hub}'
            f'<div class="lr-box lr-rv"><ul class="lr-checks" style="margin-top:0">' + "".join(f"<li>{f}</li>" for f in rest) + f"</ul></div>{mids}{managed}")


def ch_why(D, X):
    w = D["why"]
    stats = "".join(f'<div class="lr-stat lr-rv" style="--d:{i * .08:.2f}s"><div class="sn"{num_attrs(s["num"])}>{esc(s["num"])}</div><div class="sl">{esc(s["lbl"])}</div></div>' for i, s in enumerate(w["stats"]))
    cards = "".join(card_html(c, i * .08, clamp=False) for i, c in enumerate(w["cards"]))
    return (f'<h2 class="lr-h2 lr-rv">{esc(w["title"])}</h2><div class="lr-note lr-rv">{w["note"]}</div><div class="lr-stats">{stats}</div>'
            f'<h3 class="lr-h3 lr-rv" style="margin-top:38px">{esc(w["title2"])}</h3><div class="lr-cards one">{cards}</div>{roi_html(w["roi"])}')


def steps_html(kb):
    """Next steps, quoted from the knowledge base; left out if any sentence is no longer in it."""
    if not kb:
        return ""
    answers = " ".join(e.get("answer", "") for e in kb.get("entries", []))
    for _, _, must in STEPS:
        for frag in must:
            if frag not in answers:
                print("note: Next steps left out; the knowledge base no longer says:", frag)
                return ""
    tabs = "".join(f'<button type="button" role="tab"><i>{i + 1}</i>{esc(lbl)}</button>' for i, (lbl, _, _) in enumerate(STEPS))
    panels = "".join(f'<div class="lr-steps-p" role="tabpanel">{esc(text)}</div>' for _, text, _ in STEPS)
    return f'<h3 class="lr-h3 lr-rv">Next steps</h3><div class="lr-steps lr-rv"><div class="lr-steps-t" role="tablist">{tabs}</div>{panels}</div>'


def ch_investment(D, X):
    v = D["investment"]
    head = "".join(f"<th>{esc(h)}</th>" for h in v["head"])
    rows = "".join('<tr' + (' class="tot"' if strip(r[0]).startswith("Total") else "") + ">" + "".join(
        f'<td data-label="{esc(v["head"][i]) if i < len(v["head"]) else ""}">{c}</td>' for i, c in enumerate(r)) + "</tr>" for r in v["rows"])
    inc = (f'<div class="lr-box lr-rv"><div style="font-size:.9rem;font-weight:800;color:#111827;margin-bottom:12px">{esc(v["incTitle"])}</div>'
           '<ul class="lr-checks green" style="margin-top:0">' + "".join(f"<li>{f}</li>" for f in v["included"]) + "</ul></div>") if v["included"] else ""
    steps = steps_html(X.get("kb")) if "MiDS" in json.dumps(D["investment"]) else ""
    return (f'<h2 class="lr-h2 lr-rv">{esc(v["title"])}</h2><div class="lr-rv"><table class="lr-table"><thead><tr>{head}</tr></thead><tbody>{rows}</tbody></table></div>'
            f'{inc}{steps}{roi_html(v["roi"])}<div class="lr-end" aria-hidden="true">{ekg("#16a34a")}</div>')


CHAPTERS = {"summary": ch_summary, "scorecard": ch_scorecard, "aivisibility": ch_ai, "findings": ch_findings, "opportunities": ch_opportunities,
            "solution": ch_solution, "whyact": ch_why, "investment": ch_investment}


def living_dhap(src_html, D, X, proof_block):
    tabs = [t for t in D["tabs"] if t["id"] in CHAPTERS]; n = len(tabs)
    nav = "".join(f'<button type="button" data-goto="{t["id"]}"><i>{i + 1:02d}</i>{esc(t["t"])}</button>' for i, t in enumerate(tabs))
    secs = []
    for i, t in enumerate(tabs):
        X["label"] = t["t"]; inner = CHAPTERS[t["id"]](D, X)
        mark = "" if t["id"] in ("summary", "aivisibility") else f'<div class="lr-eyebrow lr-rv"><b>{i + 1:02d}</b> / {n:02d} · {esc(t["t"])}</div>'
        tail = ekg("#e82b39") if t["id"] == "summary" else ""
        secs.append(f'<section class="lr-ch {BANDS.get(t["id"], "")}" id="{t["id"]}" style="--c:{COLORS[t["id"]]}"><div class="lr-in"><div class="lr-node" aria-hidden="true">{i + 1:02d}</div>'
                    f'{mark}{inner}{tail}</div></section>')
    metas = "".join(re.findall(r"<meta[^>]+>", src_html[:src_html.index("</head>")]))
    head = src_html[:src_html.index("</head>")]
    clarity = re.search(r"<!-- Microsoft Clarity.*?</script>", head, re.S)
    clarity = clarity.group(0) if clarity else ""
    jess = ""
    if "JESSICA" in src_html:
        a = src_html.index("<!-- ===== JESSICA"); jess = src_html[a:src_html.rindex("</body>")]
        jess = re.sub(r"<!-- PROOF POPUPS START.*?<!-- PROOF POPUPS END -->\n?", "", jess, flags=re.S)   # the popup block is placed once, below
    css = (HERE / "living.css").read_text(encoding="utf-8"); js = (HERE / "living.js").read_text(encoding="utf-8")
    return (f'<!DOCTYPE html>\n<html lang="en">\n<head>\n{metas}\n<title>{esc(D["title"])}</title>\n<style>\n{css}</style>\n{clarity}\n</head>\n<body>\n'
            f'<header class="lr-top"><div class="lr-top-in"><img src="{esc(D["logo"])}" class="lr-logo" alt="CLIKdata"/><nav class="lr-nav" aria-label="Report chapters">{nav}</nav></div>'
            f'<div class="lr-progwrap"><div class="lr-prog"></div></div></header>\n'
            f'<main class="lr-main"><div class="lr-spine" aria-hidden="true"><i></i><b></b></div>\n' + "\n".join(secs) + "\n</main>\n"
            f"{proof_block}<script>\n{js}</script>\n{jess}</body>\n</html>\n")


def living_alert(src_html, proof_block):
    """Same Alert, same words: the three screens stacked into one scroll, the breadcrumb following the reader."""
    h = src_html
    css = (HERE / "alert.css").read_text(encoding="utf-8"); js = (HERE / "alert.js").read_text(encoding="utf-8")
    crumbs = [strip(c) for c in re.findall(r'<button[^>]*class="crumb[^"]*"[^>]*>(.*?)</button>', h, re.S)]
    a = h.index("var screens=[document.getElementById('s1')"); s0 = h.rindex("<script>", 0, a); s1 = h.index("</script>", a) + len("</script>")
    h = h[:s0] + f"<script>\n{js}</script>" + h[s1:]
    # the step buttons are gone: the line that sat above each one stays as plain text, at the button's type size
    h, folded = re.subn(r'(<div class="step-teaser">.*?</div>)\s*<a[^>]*class="step-btn"[^>]*>.*?</a>', r"\1", h, flags=re.S)
    if folded != 2:
        raise ValueError(f"expected 2 step buttons with a line above them, found {folded}")
    h = re.sub(r'\s*<button[^>]*class="step-back"[^>]*>.*?</button>', "", h, flags=re.S)   # no back links: the breadcrumb is the way around
    for n in (2, 3):
        label = crumbs[n - 1] if len(crumbs) >= n else ""
        mark = f'<div class="screen" id="s{n}">'
        if mark not in h:
            raise ValueError(f"Alert screen {n} not found")
        h = h.replace(mark, f'<div class="lv-link" aria-hidden="true">{ekg("#4ade80", "lv-line")}<span>{esc(label)}</span></div>\n{mark}', 1)
    nav = h.index('<nav class="crumbs"')
    h = h[:nav] + f'<div class="lv-ekg" aria-hidden="true">{ekg("#4ade80", "lv-line")}</div>\n' + h[nav:]
    h = h.replace("</head>", f"<style>\n{css}</style>\n</head>", 1)
    return proof_popup.add_to_page(h, "alert", proof_block) if proof_block else h


def extract(path):
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        b = p.chromium.launch(); pg = b.new_page()
        pg.route("**/*", lambda r: r.abort() if r.request.url.startswith("http") else r.continue_())
        pg.goto(pathlib.Path(path).resolve().as_uri()); data = pg.evaluate(EXTRACT); b.close()
    return data


LIVING_MARK = "<!-- LIVING REPORT v17 -->"
BLOCK_RE = re.compile(r"<!-- PROOF POPUPS START.*?<!-- PROOF POPUPS END -->\n?", re.S)


def convert(dhap_path, alert_path=None, evidence=None, proof_block=None):
    """Convert the built pages in place. Returns the paths converted."""
    dhap_path = pathlib.Path(dhap_path); done = []
    dhap_html = dhap_path.read_text(encoding="utf-8")
    alert_html = pathlib.Path(alert_path).read_text(encoding="utf-8") if alert_path else ""
    kbf = REPO / "knowledge-base/jessica-kb-qa.json"
    live = re.search(r'class="live-badge"[^>]*>(.*?)</span>', alert_html, re.S)
    X = {"evidence": json.loads(pathlib.Path(evidence).read_text(encoding="utf-8")) if evidence else None,
         "kb": json.loads(kbf.read_text(encoding="utf-8")) if kbf.exists() else None,
         "live": strip(live.group(1)).lstrip("●").strip() if live else ""}
    if LIVING_MARK not in dhap_html:
        m = BLOCK_RE.search(dhap_html); block = proof_block if proof_block is not None else (m.group(0) if m else "")
        D = extract(dhap_path)
        dhap_path.write_text(living_dhap(dhap_html, D, X, block).replace("<body>", "<body>\n" + LIVING_MARK, 1), encoding="utf-8"); done.append(str(dhap_path))
    if alert_path and LIVING_MARK not in alert_html:
        m = BLOCK_RE.search(alert_html); block = proof_block if proof_block is not None else (m.group(0) if m else "")
        pathlib.Path(alert_path).write_text(living_alert(alert_html, block).replace("<body>", "<body>\n" + LIVING_MARK, 1), encoding="utf-8"); done.append(str(alert_path))
    return done


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("dhap"); ap.add_argument("alert", nargs="?", default="-")
    ap.add_argument("--evidence"); ap.add_argument("--proof-spec"); ap.add_argument("--proof-images")
    a = ap.parse_args(); block = None
    if a.proof_spec and a.proof_images:
        spec = json.loads(pathlib.Path(a.proof_spec).read_text(encoding="utf-8")); block = proof_popup.block(spec["keys"], a.proof_images, spec.get("rules"))
    done = convert(a.dhap, None if a.alert == "-" else a.alert, a.evidence, block)
    print("Living Report:", ", ".join(done) if done else "already in the Living design, nothing to do")


if __name__ == "__main__":
    main()

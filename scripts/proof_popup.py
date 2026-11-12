#!/usr/bin/env python3
"""Evidence popups (RULE K): builds the CSS + script block that makes every tile and card of a DHAP or Digital Health Alert
open its evidence in a side panel (v16.8): hovering only tints the stat and shows a pointing-hand cursor; a click or tap
slides a single-column panel in from the right over a 50% black shade; it scrolls on its own, and closing it (X, Esc,
or a click on the shade) returns the reader to exactly where they were.

Usage:
  python3 scripts/proof_popup.py spec.json images_dir > block.html      # then insert the block before </body>
spec.json: {"keys": {"phones": {"t": "title", "n": "note with date + method", "i": [["image_name", "caption"]], "c": "optional code/text excerpt"}},
            "rules": [["phones", "regex on the card title / label"]]}      # "rules" optional: DEFAULT_RULES is used when omitted
images_dir/<image_name>.jpg are cropped audit screenshots (about 480 px wide; blur names, crop out account details).
Scope (RULE K): only the hero-fact numbers (DHAP Summary and the top of AI Visibility), Alert KPI tiles and Alert stat cards - never the bullets under the score, the Key Gaps, or any card. Never the Findings, Why Act Now or lower AI Visibility cards.
Elements are matched by the text of `.kpi-lbl`, or the element text for hero facts, callout bullets and stat cards;
first matching rule wins. Run scripts/check_proof_popups.py on the built page: every non-exempt card must resolve to a key."""
import base64, json, pathlib, sys

DEFAULT_RULES = [
 ["duplicates", "duplicate"],
 ["dormant", "dormant|posts on service|service (&|and) parts listings? (have|show)|service (&|and) parts (listings )?have no"],
 ["listings", "listings exist"],
 ["replies", "reviews\\s*answered|replies_of_10|no owner repl|unanswered reviews|0 of the 10 newest"],
 ["site_reviews", "not shown on (the )?website|aren.t shown on the website|invisible on the website|reviews not shown"],
 ["sameas", "link in\\s*sameas|sameas_links|sameas has no google|sameas lists"],
 ["areaserved", "areaserved"],
 ["phones", "phone numbers"],
 ["rating", "google rating|large, active review base"],
 ["facebook", "facebook rating"],
 ["logo", "no logo"],
 ["posts", "steady sales posting|posts are all|sales posts in|10 sales posts|learn more"],
 ["schema_dept", "parts entity|parts department schema|department entities|website schema foundation|schema foundation"],
 ["aigaps", "ai_vis_gaps|ai search visibility$"],
]

def block(keys_spec, images_dir, rules=None):
    images_dir = pathlib.Path(images_dir); imgs = {}; kd = {}
    for k, d in keys_spec.items():
        o = {"t": d["t"], "n": d["n"]}
        if d.get("i"):
            o["i"] = []
            for n, c in d["i"]:
                if n not in imgs:
                    imgs[n] = "data:image/jpeg;base64," + base64.b64encode((images_dir / f"{n}.jpg").read_bytes()).decode()
                o["i"].append([n, c])
        if d.get("c"): o["c"] = d["c"]
        kd[k] = o
    rules = [r for r in (rules or DEFAULT_RULES) if r[0] in kd]
    css = """<style>
.has-proof{cursor:pointer;transition:box-shadow .15s ease;}
.has-proof:hover,.has-proof.pp-active{box-shadow:inset 0 0 0 9999px rgba(148,163,184,.16);}
.has-proof:focus{outline:none;}
.has-proof:focus-visible{outline:2px solid #3b82f6;outline-offset:2px;}
.proof-hint{display:block;max-width:760px;margin:16px auto 6px;padding:11px 16px;background:#fef9c3;border:2px solid #f59e0b;border-left:6px solid #d97706;border-radius:10px;color:#78350f;font-size:1rem;font-weight:800;line-height:1.4;text-align:center;font-style:normal;box-shadow:0 2px 8px rgba(217,119,6,.25);}
@media(max-width:680px){.proof-hint{font-size:.92rem;padding:10px 12px;}}
#proof-shade{position:fixed;inset:0;background:rgba(0,0,0,.5);z-index:2147483646;opacity:0;visibility:hidden;transition:opacity .25s ease,visibility 0s linear .25s;}
#proof-shade.open{opacity:1;visibility:visible;transition:opacity .25s ease;}
#proof-pop{position:fixed;top:0;right:0;bottom:0;width:min(520px,100vw);z-index:2147483647;background:#fff;color:#111827;box-shadow:-12px 0 40px rgba(0,0,0,.35);overflow-y:auto;overscroll-behavior:contain;-webkit-overflow-scrolling:touch;font-family:inherit;text-align:left;transform:translateX(100%);visibility:hidden;transition:transform .28s ease,visibility 0s linear .28s;}
#proof-pop.open{transform:none;visibility:visible;transition:transform .28s ease;}
#proof-pop .pp-head{position:sticky;top:0;z-index:1;display:flex;align-items:center;justify-content:space-between;gap:12px;background:#0f172a;color:#fff;padding:12px 16px;}
#proof-pop .pp-k{font-size:.72rem;font-weight:800;letter-spacing:.08em;text-transform:uppercase;color:#fbbf24;}
#proof-pop .pp-x{background:none;border:none;font-size:1.7rem;color:#e2e8f0;cursor:pointer;line-height:1;padding:0 4px;}
#proof-pop .pp-x:hover{color:#fff;}
#proof-pop .pp-body{padding:18px 20px 28px;}
#proof-pop .pp-t{font-weight:800;font-size:1.08rem;line-height:1.35;margin:0 0 8px;}
#proof-pop .pp-n{font-size:.86rem;color:#374151;line-height:1.55;margin-bottom:16px;}
#proof-pop .pp-i{display:flex;flex-direction:column;gap:18px;}
#proof-pop figure{margin:0;width:100%;}
#proof-pop img{width:100%;height:auto;display:block;background:#f8fafc;border:1px solid #e5e7eb;border-radius:8px;}
#proof-pop figcaption{font-size:.78rem;color:#4b5563;margin-top:6px;line-height:1.45;}
#proof-pop pre{background:#0f172a;color:#bbf7d0;border-radius:8px;padding:12px;font-size:.76rem;line-height:1.5;overflow:auto;white-space:pre-wrap;word-break:break-word;margin:0 0 16px;}
@media(max-width:680px){#proof-pop{width:92vw;}#proof-pop .pp-body{padding:16px 16px 28px;}}
@media(prefers-reduced-motion:reduce){#proof-shade,#proof-pop,#proof-shade.open,#proof-pop.open{transition:none;}}
</style>
<div id="proof-shade" aria-hidden="true"></div>
<div id="proof-pop" role="dialog" aria-modal="true" aria-label="Audit evidence" aria-hidden="true"><div class="pp-head"><span class="pp-k">Audit evidence</span><button type="button" class="pp-x" aria-label="Close">&times;</button></div><div class="pp-body"></div></div>
"""
    js = """<script>
(function(){
var IMG=%s, DATA=%s, RULES=%s;
var SEL='.hero-fact,.kpi-tile,.t-stat';
var pop=document.getElementById('proof-pop'), shade=document.getElementById('proof-shade'), body=pop.querySelector('.pp-body');
var de=document.documentElement, openEl=null, sx=0, sy=0, ovH='', ovB='';
function esc(s){return s.replace(/&/g,'&amp;').replace(/</g,'&lt;');}
function fill(k){var d=DATA[k], h='<div class="pp-t">'+d.t+'</div><div class="pp-n">'+d.n+'</div>';
  if(d.c){h+='<pre>'+esc(d.c)+'</pre>';}
  if(d.i){h+='<div class="pp-i">'+d.i.map(function(x){return '<figure><img alt="" src="'+IMG[x[0]]+'"><figcaption>'+x[1]+'</figcaption></figure>';}).join('')+'</div>';}
  body.innerHTML=h;}
function open(el,k){
  if(openEl){openEl.classList.remove('pp-active');}
  else{sx=window.pageXOffset; sy=window.pageYOffset; ovH=de.style.overflow; ovB=document.body.style.overflow; de.style.overflow='hidden'; document.body.style.overflow='hidden';}
  openEl=el; el.classList.add('pp-active'); fill(k); pop.scrollTop=0;
  shade.classList.add('open'); pop.classList.add('open'); pop.setAttribute('aria-hidden','false');
  try{pop.querySelector('.pp-x').focus({preventScroll:true});}catch(e){}}
function close(){
  if(!openEl) return;
  var el=openEl; openEl=null; el.classList.remove('pp-active');
  shade.classList.remove('open'); pop.classList.remove('open'); pop.setAttribute('aria-hidden','true');
  de.style.overflow=ovH; document.body.style.overflow=ovB; window.scrollTo(sx,sy);
  try{el.focus({preventScroll:true});}catch(e){}}
function nobr(n){var c=n.cloneNode(true);[].forEach.call(c.querySelectorAll('br'),function(b){b.replaceWith(' ');});return c.textContent;}
function label(el){var lb=el.querySelector('.kpi-lbl,.finding-title'); var s=nobr(lb||el); return (s||'').replace(/\\s+/g,' ').trim();}
function tag(){
  [].forEach.call(document.querySelectorAll(SEL),function(el){
    var t=label(el), key=null;
    RULES.some(function(r){if(new RegExp(r[1],'i').test(t)){key=r[0];return true;}});
    if(!key) return;
    el.classList.add('has-proof'); el.setAttribute('tabindex','0'); el.setAttribute('role','button'); el.setAttribute('data-proof',key);
    el.setAttribute('aria-haspopup','dialog');
    el.addEventListener('click',function(e){ e.preventDefault(); e.stopPropagation(); open(el,key); });
    el.addEventListener('keydown',function(e){ if(e.key==='Enter'||e.key===' '){ e.preventDefault(); open(el,key); } });
  });}
pop.querySelector('.pp-x').addEventListener('click',close);
shade.addEventListener('click',close);
document.addEventListener('keydown',function(e){ if(e.key==='Escape') close(); });
tag();
})();
</script>
""" % (json.dumps(imgs), json.dumps(kd), json.dumps(rules))
    return "<!-- PROOF POPUPS START (RULE K) -->\n" + css + js + "<!-- PROOF POPUPS END -->\n"


def block_from_uris(keys_spec, image_uris, rules=None):
    """Same block as block(), but images arrive as ready data URIs: {"name": "data:image/jpeg;base64,..."}."""
    import tempfile, pathlib as _p
    with tempfile.TemporaryDirectory() as d:
        for n, u in (image_uris or {}).items():
            if not str(u).startswith("data:image/"):
                raise ValueError(f"image {n!r} must be a data:image URI")
            (_p.Path(d) / f"{n}.jpg").write_bytes(base64.b64decode(str(u).split(",", 1)[1]))
        return block(keys_spec, d, rules)


HINT = '<div class="proof-hint">CLICK or tap any stat to see the audit proof behind it.</div>'

def add_to_page(html, kind, popup_block):
    """Insert the popup block before </body> and the prominent hint lines. kind: 'dhap' (hints above the Summary and AI Visibility score banners)
    or 'alert' (hints above the screen 2 tiles and the screen 3 stat cards). Replaces an earlier block and hints, so it can be run twice."""
    if "<!-- PROOF POPUPS START" in html:
        i = html.index("<!-- PROOF POPUPS START"); j = html.index("<!-- PROOF POPUPS END -->") + len("<!-- PROOF POPUPS END -->\n")
        html = html[:i] + html[j:]
    import re as _re
    html = _re.sub(r'<div class="proof-hint">.*?</div>', '', html, flags=_re.S)
    if kind == "dhap":
        spots = [m.start() for m in _re.finditer(r'<div class="score-banner">', html)][:2]
        if len(spots) != 2: raise ValueError("expected 2 score banners (Summary and AI Visibility)")
        for i in reversed(spots): html = html[:i] + HINT + "\n    " + html[i:]
    else:
        for marker in ('<div class="impact-stats">', '<div class="kpi-grid">'):
            i = html.index(marker); html = html[:i] + HINT + "\n  " + html[i:]
    if html.count("</body>") != 1: raise ValueError("expected exactly one </body>")
    return html.replace("</body>", popup_block.rstrip("\n") + "\n</body>", 1)

if __name__ == "__main__":
    args = sys.argv[1:]
    pages = []
    if "--insert" in args:
        k = args.index("--insert"); pages = args[k + 1:]; args = args[:k]
    spec = json.load(open(args[0])); blk = block(spec["keys"], args[1], spec.get("rules"))
    if not pages:
        sys.stdout.write(blk)
    for pg in pages:
        t = pathlib.Path(pg); kind = "alert" if ("health" in t.name or "hotsheet" in t.name) else "dhap"
        t.write_text(add_to_page(t.read_text(encoding="utf-8"), kind, blk), encoding="utf-8"); print("popups + hints added:", t.name)

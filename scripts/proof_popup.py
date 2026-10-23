#!/usr/bin/env python3
"""Evidence popups (RULE K): builds the CSS + script block that makes every tile and card of a DHAP or Digital Health Alert
open an in-page evidence popup on hover (preview) or click/tap (pinned, enlarged).

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
.has-proof{cursor:help;transition:box-shadow .15s;}
.has-proof:hover,.has-proof:focus{box-shadow:0 0 0 2px #3b82f6;outline:none;border-radius:6px;}
.proof-hint{display:block;max-width:760px;margin:16px auto 6px;padding:11px 16px;background:#fef9c3;border:2px solid #f59e0b;border-left:6px solid #d97706;border-radius:10px;color:#78350f;font-size:1rem;font-weight:800;line-height:1.4;text-align:center;font-style:normal;box-shadow:0 2px 8px rgba(217,119,6,.25);}
@media(max-width:680px){.proof-hint{font-size:.92rem;padding:10px 12px;}}
#proof-pop{pointer-events:none;display:none;position:fixed;z-index:2147483647;background:#fff;color:#111827;border:1px solid #cbd5e1;border-radius:12px;box-shadow:0 18px 50px rgba(0,0,0,.35);padding:14px 16px 12px;width:min(640px,94vw);max-height:84vh;overflow:auto;font-family:inherit;text-align:left;}
#proof-pop.pinned{pointer-events:auto;}
#proof-pop.pinned figure{flex-basis:280px;}
#proof-pop.pinned img{max-height:430px;}
#proof-pop .pp-t{font-weight:800;font-size:.98rem;margin:0 26px 4px 0;}
#proof-pop .pp-n{font-size:.78rem;color:#374151;line-height:1.5;margin-bottom:10px;}
#proof-pop .pp-i{display:flex;flex-wrap:wrap;gap:12px;}
#proof-pop figure{margin:0;flex:1 1 185px;max-width:100%;}
#proof-pop img{width:100%;height:auto;max-height:210px;object-fit:contain;background:#f8fafc;border:1px solid #e5e7eb;border-radius:6px;display:block;}
#proof-pop figcaption{font-size:.7rem;color:#6b7280;margin-top:3px;line-height:1.4;}
#proof-pop pre{background:#0f172a;color:#bbf7d0;border-radius:8px;padding:12px;font-size:.74rem;line-height:1.5;overflow:auto;white-space:pre-wrap;word-break:break-word;margin:0 0 10px;}
#proof-pop .pp-x{position:absolute;top:6px;right:10px;background:none;border:none;font-size:1.4rem;color:#6b7280;cursor:pointer;line-height:1;}
@media(max-width:680px){#proof-pop{left:3vw!important;right:3vw;top:auto!important;bottom:12px;width:auto;max-height:78vh;}}
</style>
<div id="proof-pop" role="dialog" aria-label="Audit evidence"><button type="button" class="pp-x" aria-label="Close">&times;</button><div class="pp-body"></div></div>
"""
    js = """<script>
(function(){
var IMG=%s, DATA=%s, RULES=%s;
var SEL='.hero-fact,.kpi-tile,.t-stat';
var pop=document.getElementById('proof-pop'), body=pop.querySelector('.pp-body'), cur=null, pinned=false, timer=null;
function esc(s){return s.replace(/&/g,'&amp;').replace(/</g,'&lt;');}
function fill(k){var d=DATA[k], h='<div class="pp-t">'+d.t+'</div><div class="pp-n">'+d.n+'</div>';
  if(d.c){h+='<pre>'+esc(d.c)+'</pre>';}
  if(d.i){h+='<div class="pp-i">'+d.i.map(function(x){return '<figure><img alt="" src="'+IMG[x[0]]+'"><figcaption>'+x[1]+'</figcaption></figure>';}).join('')+'</div>';}
  body.innerHTML=h;}
function place(el){if(window.innerWidth<=680){pop.style.left='';pop.style.top='';return;}
  var r=el.getBoundingClientRect(), w=Math.min(640,window.innerWidth*0.94), left=Math.max(8,Math.min(r.left+r.width/2-w/2,window.innerWidth-w-8));
  pop.style.left=left+'px'; var below=r.bottom+10; pop.style.top=below+'px';
  var ph=pop.offsetHeight; if(below+ph>window.innerHeight-8){var up=r.top-ph-10; pop.style.top=Math.max(8,up>8?up:window.innerHeight-ph-8)+'px';}}
function show(el,k){clearTimeout(timer); if(cur!==k){fill(k);} cur=k; pop.style.display='block'; place(el);}
function hide(){pop.style.display='none'; pop.classList.remove('pinned'); cur=null; pinned=false;}
function later(){clearTimeout(timer); if(!pinned) timer=setTimeout(hide,60);}
function nobr(n){var c=n.cloneNode(true);[].forEach.call(c.querySelectorAll('br'),function(b){b.replaceWith(' ');});return c.textContent;}
function label(el){var lb=el.querySelector('.kpi-lbl,.finding-title'); var s=nobr(lb||el); return (s||'').replace(/\\s+/g,' ').trim();}
function tag(){
  [].forEach.call(document.querySelectorAll(SEL),function(el){
    var t=label(el), key=null;
    RULES.some(function(r){if(new RegExp(r[1],'i').test(t)){key=r[0];return true;}});
    if(!key) return;
    el.classList.add('has-proof'); el.setAttribute('tabindex','0'); el.setAttribute('data-proof',key);
    el.addEventListener('mouseenter',function(){ if(!pinned) show(el,key); });
    el.addEventListener('mouseleave',later);
    el.addEventListener('mousemove',function(){ if(!pinned && pop.style.display!=='block') show(el,key); });
    el.addEventListener('focus',function(){ show(el,key); });
    el.addEventListener('click',function(e){ e.stopPropagation(); if(pinned&&cur===key){hide();} else {pinned=true; pop.classList.add('pinned'); show(el,key);} });
  });}
pop.querySelector('.pp-x').addEventListener('click',hide);
pop.addEventListener('click',function(e){e.stopPropagation();});
document.addEventListener('click',hide);
document.addEventListener('keydown',function(e){if(e.key==='Escape')hide();});
window.addEventListener('scroll',function(){ if(!pinned) hide(); },true);
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


HINT = '<div class="proof-hint">HOVER over any stat to see the audit screenshot behind it. Click or tap to enlarge.</div>'

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

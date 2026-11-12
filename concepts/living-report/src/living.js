(function(){
var d=document,root=d.documentElement,W=window;root.classList.add('lr-js');
var reduce=W.matchMedia&&W.matchMedia('(prefers-reduced-motion: reduce)').matches;
function all(s,r){return [].slice.call((r||d).querySelectorAll(s));}
/* count-ups */
function count(scope){all('[data-count]',scope).concat(scope.matches&&scope.matches('[data-count]')?[scope]:[]).forEach(function(el){
  if(el._c)return;el._c=1;var to=parseFloat(el.getAttribute('data-count')),dec=+el.getAttribute('data-dec')||0,pre=el.getAttribute('data-pre')||'',suf=el.getAttribute('data-suf')||'',fin=el.getAttribute('data-final'),t0=null;
  if(reduce||!to){el.textContent=fin;return;}
  function step(ts){if(t0===null)t0=ts;var p=Math.min((ts-t0)/1500,1),e=1-Math.pow(1-p,3);el.textContent=pre+(to*e).toFixed(dec)+suf;if(p<1){W.requestAnimationFrame(step);}else{el.textContent=fin;}}
  el.textContent=pre+(0).toFixed(dec)+suf;W.requestAnimationFrame(step);});}
/* reveal on scroll */
var rv=all('.lr-rv');
function show(el){el.classList.add('in');count(el);seq(el);}
if(reduce||!('IntersectionObserver' in W)){rv.forEach(show);}
else{var io=new IntersectionObserver(function(es){es.forEach(function(x){if(x.isIntersecting){show(x.target);io.unobserve(x.target);}});},{threshold:.15,rootMargin:'0px 0px -6% 0px'});rv.forEach(function(e){io.observe(e);});}
/* pitfalls tick off one by one */
function seq(el){if(!el.classList.contains('lr-pits'))return;all('li',el).forEach(function(li,i){setTimeout(function(){li.classList.add('on');},reduce?0:500+i*260);});}
/* progress, spine and chapter spy */
var main=d.querySelector('.lr-main'),chs=all('.lr-ch'),nav=d.querySelector('.lr-nav'),nb=all('.lr-nav button'),prog=d.querySelector('.lr-prog'),spine=d.querySelector('.lr-spine'),cur=-1,tick=false;
function grad(){if(!spine||!main)return;var h=main.offsetHeight||1,st=chs.map(function(c){var col=getComputedStyle(c).getPropertyValue('--c').trim()||'#e82b39';return col+' '+(((c.offsetTop+76)/h)*100).toFixed(2)+'%';});
  spine.style.setProperty('--grad','linear-gradient(180deg,'+st.join(',')+')');}
function upd(){tick=false;if(!main)return;var vh=W.innerHeight,r=main.getBoundingClientRect(),p=Math.max(0,Math.min(1,(vh*.5-r.top)/r.height));
  if(spine)spine.style.setProperty('--p',(p*100).toFixed(2)+'%');
  var sp=Math.max(0,Math.min(1,W.pageYOffset/Math.max(1,root.scrollHeight-vh)));if(prog)prog.style.transform='scaleX('+sp.toFixed(4)+')';
  var a=0;chs.forEach(function(c,i){var on=c.getBoundingClientRect().top<vh*.5;c.classList.toggle('on',on);if(on)a=i;});
  if(a!==cur){cur=a;nb.forEach(function(b,i){b.classList.toggle('active',i===a);b.classList.toggle('done',i<a);});
    if(spine)spine.style.setProperty('--tip',getComputedStyle(chs[a]).getPropertyValue('--c').trim());
    var n=nb[a];if(n&&nav&&nav.scrollWidth>nav.clientWidth){var left=(n.getBoundingClientRect().left-nav.getBoundingClientRect().left+nav.scrollLeft)-(nav.clientWidth-n.offsetWidth)/2;try{nav.scrollTo({left:left,behavior:reduce?'auto':'smooth'});}catch(e){nav.scrollLeft=left;}}}}
function ask(){if(!tick){tick=true;W.requestAnimationFrame(upd);}}
W.addEventListener('scroll',ask,{passive:true});W.addEventListener('resize',function(){grad();ask();});W.addEventListener('load',function(){grad();ask();});grad();upd();
function go(id){var t=d.getElementById(id);if(t)t.scrollIntoView({behavior:reduce?'auto':'smooth',block:'start'});}
d.addEventListener('click',function(e){var g=e.target.closest?e.target.closest('[data-goto]'):null;if(g){e.preventDefault();go(g.getAttribute('data-goto'));}});
/* expandable rows */
function setRow(r,open){r.classList.toggle('open',open);var h=r.querySelector('.lr-row-h');if(h)h.setAttribute('aria-expanded',open?'true':'false');}
all('.lr-row-h').forEach(function(h){h.addEventListener('click',function(){var r=h.parentNode;setRow(r,!r.classList.contains('open'));});});
all('[data-expand]').forEach(function(b){b.addEventListener('click',function(){var rows=all('.lr-row',d.querySelector(b.getAttribute('data-expand'))),open=!rows.every(function(r){return r.classList.contains('open');});
  rows.forEach(function(r){setRow(r,open);});b.textContent=open?b.getAttribute('data-less'):b.getAttribute('data-more');});});
/* filters: the legend is the control */
all('.lr-filter').forEach(function(f){var box=d.querySelector(f.getAttribute('data-target')),bs=all('button',f);
  bs.forEach(function(b){b.addEventListener('click',function(){var k=b.getAttribute('data-f');
    if(k&&b.classList.contains('active')){k='';}
    bs.forEach(function(x){x.classList.toggle('active',x.getAttribute('data-f')===k);});
    all('[data-k]',box).forEach(function(it){it.classList.toggle('hide',!!k&&it.getAttribute('data-k')!==k);});
    all('.lr-rv',box).forEach(show);});});});
/* long cards open on click */
function clampAll(){all('.lr-card[data-clamp]').forEach(function(c){if(c.classList.contains('open'))return;var b=c.querySelector('.bd');if(!b)return;c.classList.add('clamp');
  if(b.scrollHeight<=b.clientHeight+2){c.classList.remove('clamp');c.removeAttribute('tabindex');c.removeAttribute('role');}else{c.setAttribute('tabindex','0');c.setAttribute('role','button');c.setAttribute('aria-expanded','false');}});}
clampAll();W.addEventListener('load',clampAll);
function tog(c){if(!c.classList.contains('clamp'))return;var o=!c.classList.contains('open');c.classList.toggle('open',o);c.setAttribute('aria-expanded',o?'true':'false');}
all('.lr-card[data-clamp]').forEach(function(c){c.addEventListener('click',function(e){if(e.target.closest&&e.target.closest('a'))return;tog(c);});
  c.addEventListener('keydown',function(e){if(e.key==='Enter'||e.key===' '){e.preventDefault();tog(c);}});});
/* next steps */
all('.lr-steps').forEach(function(s){var bs=all('.lr-steps-t button',s),ps=all('.lr-steps-p',s);
  function set(n){bs.forEach(function(b,i){b.classList.toggle('active',i===n);b.classList.toggle('done',i<n);b.setAttribute('aria-selected',i===n?'true':'false');});ps.forEach(function(p,i){p.classList.toggle('active',i===n);});}
  bs.forEach(function(b,i){b.addEventListener('click',function(){set(i);});});set(0);});
})();

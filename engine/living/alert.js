(function(){
var d=document,W=window,root=d.documentElement;root.classList.add('lv-js');
var reduce=W.matchMedia&&W.matchMedia('(prefers-reduced-motion: reduce)').matches;
function all(s,r){return [].slice.call((r||d).querySelectorAll(s));}
var screens=[1,2,3].map(function(n){return d.getElementById('s'+n);}),crumbs=all('.crumb'),lbl=d.getElementById('crumbStep'),reached=1,cur=0,tick=false;
function paint(n){crumbs.forEach(function(c,i){var k=i+1;c.classList.toggle('active',k===n);c.classList.toggle('done',k<=reached&&k!==n);c.disabled=false;});if(lbl)lbl.textContent='STEP '+n+' OF 3';}
function upd(){tick=false;var vh=W.innerHeight,n=1;screens.forEach(function(s,i){if(s&&s.getBoundingClientRect().top<vh*.55)n=i+1;});
  var grew=n>reached;if(grew)reached=n;if(n!==cur||grew){cur=n;paint(n);}}
function go(n){var s=screens[n-1];if(!s)return;if(n>reached)reached=n;s.scrollIntoView({behavior:reduce?'auto':'smooth',block:'start'});}
d.addEventListener('click',function(e){var t=e.target.closest?e.target:null;if(!t)return;
  var c=t.closest('.crumb');if(c){e.preventDefault();var k=crumbs.indexOf(c)+1;if(k)go(k);return;}
  var g=t.closest('[data-go]');if(!g)return;e.preventDefault();var n=parseInt(g.getAttribute('data-go'),10);go(n);});
W.addEventListener('scroll',function(){if(!tick){tick=true;W.requestAnimationFrame(upd);}},{passive:true});W.addEventListener('resize',upd);upd();
/* numbers count up and alarms fire as each part scrolls into view */
function count(el,dec){if(el._c)return;el._c=1;var m=/^(\d+(?:\.\d+)?)(%?)$/.exec(el.textContent.trim());if(!m||reduce||!parseFloat(m[1]))return;
  var to=parseFloat(m[1]),suf=m[2],fin=el.textContent,t0=null;dec=dec||(m[1].indexOf('.')>-1?m[1].split('.')[1].length:0);
  function step(ts){if(t0===null)t0=ts;var p=Math.min((ts-t0)/1500,1),e=1-Math.pow(1-p,3);el.textContent=(to*e).toFixed(dec)+suf;if(p<1){W.requestAnimationFrame(step);}else{el.textContent=fin;}}
  el.textContent=(0).toFixed(dec)+suf;W.requestAnimationFrame(step);}
var rv=all('.score-row,.term-card,.kpi-tile,.impact-box,.cta-card');
all('.kpi-grid').forEach(function(g){all('.kpi-tile',g).forEach(function(t,i){t.style.setProperty('--d',(i*.16)+'s');});});
function show(el){el.classList.add('in');all('.score-fill',el).forEach(function(f){f.classList.add('go');});all('.score-big,.kpi-val',el).forEach(function(v){count(v);});}
rv.forEach(function(el){el.classList.add('lv-rv');});
if(reduce||!('IntersectionObserver' in W)){rv.forEach(show);}
else{var io=new IntersectionObserver(function(es){es.forEach(function(x){if(x.isIntersecting){show(x.target);io.unobserve(x.target);}});},{threshold:.2});rv.forEach(function(e){io.observe(e);});}
})();

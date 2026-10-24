// DHAP GBP — website schema collector. Paste the whole file into one javascript_tool call on the dealer's
// HOMEPAGE (same origin), then call:  await dhapSchema()            -> finds key pages from the nav and audits them
//                                  or await dhapSchema({home:'/', about:'/contactus', service:'/service', parts:'/parts', directions:'/hours'})
// It returns ONE short JSON string with the evidence fields the rubric needs (schema rows 7 and 8) plus
// short notes. It only READS pages (same-origin fetch with the browser's own cookies). No clicks, no edits.
// Output avoids ? = & characters (some tools block them).
async function dhapSchema(paths) {
  const opts = Object.assign({}, paths && (paths.rendered !== undefined || paths.wait) ? paths : {}); if (paths) { delete paths.rendered; delete paths.wait; }
  const KEYS = ['home', 'about', 'service', 'parts', 'directions'];
  const clean = s => String(s == null ? '' : s).replace(/[?=&]/g, '~');
  const host = location.hostname.replace(/^www\./, '');
  // ---- 1. find the five key pages from the site's own links
  function findPages() {
    const links = [...document.querySelectorAll('a[href]')].map(a => {
      let u; try { u = new URL(a.getAttribute('href'), location.href); } catch (e) { return null; }
      if (u.hostname.replace(/^www\./, '') !== host) return null;
      return { text: (a.textContent || '').trim().toLowerCase(), path: u.pathname.replace(/\/+$/, '') || '/' };
    }).filter(Boolean);
    const PROMO = /special|promo|coupon|offer|schedul|appoint|financ|inventory|search/i;
    const pick = (re, avoid) => {
      const okp = l => l.path !== '/' && !PROMO.test(l.path) && !(avoid && avoid.test(l.path));
      const hit = links.find(l => re.test(l.path) && okp(l)) || links.find(l => re.test(l.text) && okp(l));
      return hit ? hit.path : null;
    };
    return {
      home: '/',
      about: pick(/about/i) || pick(/contact/i),
      service: pick(/service[-_]?(department|center|centre)?(\.aspx|\.htm|$)|\/service$/i) || pick(/service/i, /parts/i),
      parts: pick(/parts[-_]?(department|center|centre)?|orderparts/i) || pick(/parts/i),
      directions: pick(/direction|hours|map/i) || pick(/directions|hours/i),
    };
  }
  const P = Object.assign(findPages(), paths || {});
  // ---- 2. parse helpers
  const typesOf = o => [].concat(o && o['@type'] || []).map(String);
  const isBiz = o => typesOf(o).some(t => /AutoDealer|AutomotiveBusiness|AutoRepair|AutoPartsStore|AutoBodyShop|LocalBusiness|Store|Organization/.test(t));
  const ctxOk = c => [].concat(c || []).some(x => typeof x === 'string' ? /^https?:\/\/schema\.org\/?$/.test(x) : (x && typeof x === 'object'));
  const classify = u => /google\.[a-z.]+\/maps|maps\.google|goo\.gl\/maps|maps\.app\.goo|g\.page|[?&]cid=/i.test(u) ? 'G'
      : /facebook\./i.test(u) ? 'FB' : /instagram\./i.test(u) ? 'IG' : /yelp\./i.test(u) ? 'YELP' : /youtube\./i.test(u) ? 'YT'
      : /(twitter|x)\.com/i.test(u) ? 'X' : /linkedin\./i.test(u) ? 'LI' : /tiktok\./i.test(u) ? 'TT' : 'OTHER';
  const digits = t => String(t || '').replace(/\D/g, '').replace(/^1(?=\d{10}$)/, '');
  async function getDoc(path) {
    if (!path) return null;
    try {
      const r = await fetch(path, { credentials: 'include' });
      if (!r.ok) return { status: r.status };
      return new DOMParser().parseFromString(await r.text(), 'text/html');
    } catch (e) { return (path === '/' || path === location.pathname) ? document : { status: 'ERR' }; }
  }
  function blocksOf(doc) {
    const out = { blocks: 0, parseErr: 0, badCtx: 0, ents: [], hasAgg: false, faq: false };
    const byId = {};
    [...doc.querySelectorAll('script[type="application/ld+json"]')].forEach(s => {
      out.blocks++;
      let j; try { j = JSON.parse(s.textContent); } catch (e) { out.parseErr++; return; }
      const tops = Array.isArray(j) ? j : [j];
      tops.forEach(t => {
        if (!t || typeof t !== 'object') return;
        if (!ctxOk(t['@context'])) out.badCtx++;
        if (/"aggregateRating"|"review"\s*:/.test(JSON.stringify(t))) out.hasAgg = true;
        const items = t['@graph'] ? t['@graph'] : [t];
        const walk = (o, depth) => {
          if (Array.isArray(o)) return o.forEach(x => walk(x, depth));
          if (!o || typeof o !== 'object') return;
          if (o['@id']) byId[o['@id']] = Object.assign(byId[o['@id']] || {}, o);
          if (typesOf(o).includes('FAQPage')) out.faq = true;
          if (isBiz(o) && depth <= 2) out.ents.push(o);
          Object.keys(o).forEach(k => { if (k !== 'department') walk(o[k], depth + 1); });
          if (o.department) [].concat(o.department).forEach(d => walk(d, depth + 1));
        };
        items.forEach(i => walk(i, 0));
      });
    });
    // resolve {"@id":...} references
    const res = o => (o && o['@id'] && Object.keys(o).length === 1 && byId[o['@id']]) ? byId[o['@id']] : o;
    out.ents = out.ents.map(res); out.byId = byId; out.res = res;
    return out;
  }
  // rendered reading (v15 JavaScript check): load the page in a hidden same-origin frame and read it after its scripts ran
  async function getRendered(path, wait) {
    if (!path) return null;
    if (path === location.pathname && document.readyState === 'complete') return document;
    return await new Promise(resolve => {
      const f = document.createElement('iframe'); f.style.cssText = 'position:fixed;left:-9999px;width:1200px;height:900px;';
      let done = false; const end = v => { if (done) return; done = true; resolve(v); setTimeout(() => f.remove(), 50); };
      f.onload = () => setTimeout(() => { try { const d = f.contentDocument; end(!d || !d.body ? { status: 'BLOCKED' } : !/html/i.test(d.contentType || '') ? { status: 'NOT RENDERED' } : d); } catch (e) { end({ status: 'BLOCKED' }); } }, wait);
      setTimeout(() => end({ status: 'TIMEOUT' }), wait + 8000);
      f.src = path; document.body.appendChild(f);
    });
  }
  const rawDocs = {};
  // ---- 3. audit each page (once on the raw pages, once after JavaScript)
  async function audit(get, keep) {
  const pages = {}; let main = null, mainBlocks = null, homeTypes = [];
  const roleOf = d => { const t = typesOf(d).join(' ') + ' ' + (d.name || ''); return /parts/i.test(t) ? 'parts' : /repair|service/i.test(t) ? 'service' : /dealer|sales/i.test(t) ? 'sales' : 'other'; };
  const source = {};
  for (const k of KEYS) {
    if (k !== 'home' && main && (!P[k] || P[k] === '/') && (k === 'service' || k === 'parts')) {
      const d = [].concat(main.department || []).map(mainBlocks.res).find(x => x && roleOf(x) === k && x.url);
      if (d) { try { const u = new URL(String(d.url), location.href); let mh = ''; try { mh = new URL(String(main.url)).hostname.replace(/^www\./, ''); } catch (e) {} if ([host, mh].includes(u.hostname.replace(/^www\./, '')) && u.pathname !== '/') { P[k] = u.pathname; source[k] = 'schema'; } } catch (e) {} }
    }
    if (k !== 'home' && P[k] === '/') P[k] = null;
    const doc = await get(P[k]);
    if (keep && doc && !doc.status) keep[k] = doc;
    if (!doc || doc.status) { pages[k] = { path: clean(P[k]), status: doc ? doc.status : 'NOT FOUND' }; continue; }
    const b = blocksOf(doc);
    pages[k] = { path: clean(P[k]), blocks: b.blocks, parseErr: b.parseErr, badCtx: b.badCtx, agg: b.hasAgg, faq: b.faq,
      areaServed: b.ents.some(e => e.areaServed), map: b.ents.some(e => e.hasMap || e.map || e.maps) };
    if (k === 'home') {
      mainBlocks = b; homeTypes = b.ents.map(e => typesOf(e).join('/'));
      // main entity = the top-level business entity with the most fields that carries a department list, else the richest one
      const tops = b.ents.filter(e => !b.ents.some(p => p !== e && [].concat(p.department || []).map(b.res).includes(e)));
      main = tops.sort((x, y) => (y.department ? 100 : 0) + Object.keys(y).length - (x.department ? 100 : 0) - Object.keys(x).length)[0] || null;
    }
  }
  // ---- 4. turn the homepage main entity into rubric fields
  const ev = {}; const notes = [];
  const withLd = KEYS.filter(k => pages[k] && pages[k].blocks > 0).length;
  ev.pages_with_jsonld = withLd;
  ev.parses_cleanly = KEYS.every(k => !pages[k] || !pages[k].blocks || (pages[k].parseErr === 0 && pages[k].badCtx === 0));
  if (!main) {
    Object.assign(ev, { business_type_ok: false, department_entities: 0, dept_own_page_address: 0, dept_own_phone: 0, core_fields: 0,
      logo_or_image: false, sameas_google: false, sameas_other: false, hasmap_or_map: false, services_or_offers: false });
    notes.push('no business entity on the homepage');
  } else {
    const r = mainBlocks.res;
    const mt = typesOf(main);
    ev.business_type_ok = mt.some(t => /AutoDealer|AutomotiveBusiness/.test(t));
    const depts = [].concat(main.department || []).map(r).filter(Boolean);
    const role = roleOf;
    const roles = {}; depts.forEach(d => { const k = role(d); if (k !== 'other' && !roles[k]) roles[k] = d; });
    ev.department_entities = Object.keys(roles).length;
    const mainUrl = String(main.url || '').replace(/\/+$/, ''), mainTel = digits(main.telephone);
    const deptList = ['sales', 'service', 'parts'];
    ev.dept_own_page_address = deptList.filter(k => roles[k] && roles[k].url && String(roles[k].url).replace(/\/+$/, '') !== mainUrl).length;
    ev.dept_own_phone = deptList.filter(k => roles[k] && digits(roles[k].telephone) && digits(roles[k].telephone) !== mainTel).length;
    const addr = r(main.address) || {}; const geo = r(main.geo) || {};
    const core = { name: !!main.name, address: !!(addr.streetAddress || typeof main.address === 'string'), telephone: !!main.telephone,
      url: !!main.url && !/google\.[a-z.]+\/url/.test(String(main.url)), hours: !!(main.openingHoursSpecification || main.openingHours),
      geo: !!(geo.latitude || geo['@id']) };
    ev.core_fields = Object.values(core).filter(Boolean).length;
    ev.logo_or_image = !!(main.logo || main.image);
    const same = [].concat(main.sameAs || []).map(String); const cls = same.map(classify);
    ev.sameas_google = cls.includes('G'); ev.sameas_other = cls.some(c => c !== 'G');
    ev.hasmap_or_map = !!(main.hasMap || main.map || main.maps);
    ev.services_or_offers = !!(main.makesOffer || main.hasOfferCatalog);
    ev._detail = {
      main_type: mt.join('/'), main_tel: clean(main.telephone), sameAs: cls.join(','),
      areaServed: [].concat(main.areaServed || []).map(a => clean(typeof a === 'string' ? a : (r(a) || {}).name)).join('/'),
      depts: deptList.map(k => roles[k] ? `${k}:${typesOf(roles[k]).join('/')}|tel ${clean(roles[k].telephone)}|url ${clean(String(roles[k].url || '-').replace(/^https?:\/\/(www\.)?[^/]+/, ''))}|sameAs ${roles[k].sameAs ? 'Y' : '-'}|map ${(roles[k].hasMap || roles[k].map) ? 'Y' : '-'}` : `${k}:none`),
      missing_core: Object.keys(core).filter(k => !core[k]).join(',') || 'none',
      home_types: homeTypes.join(',')
    };
    if (pages.home && pages.home.agg) notes.push('RISK: aggregateRating/review markup present (flag to director, never a selling point)');
  }
  KEYS.forEach(k => { if (pages[k] && pages[k].status === 'NOT FOUND') notes.push(`${k} page not found from the menu or schema: give its path by hand`); });
  KEYS.forEach(k => { const p = pages[k]; if (p && p.parseErr) notes.push(`${k}: ${p.parseErr} block(s) fail to parse`); if (p && p.badCtx) notes.push(`${k}: ${p.badCtx} block(s) with a non-schema.org @context`); });
  // compact page summary: path:blocks b/parse errors e/bad context c[/faq][/area][/map]
  const pg = KEYS.map(k => { const p = pages[k]; return (source[k] ? '(from schema) ' : '') + (p.status ? `${k} ${p.path}:${p.status}` : `${k} ${p.path}:${p.blocks}b/${p.parseErr}e/${p.badCtx}c${p.faq ? '/faq' : ''}${p.areaServed ? '/area' : ''}${p.map ? '/map' : ''}${p.agg ? '/AGG' : ''}`); });
  return { ev, pg, notes, main, pages, area: main && main.areaServed !== undefined ? main.areaServed : null };
  }
  const R = await audit(getDoc, rawDocs);
  const failed = {};
  const G = opts.rendered === false ? null : await audit(async p => { const d = await getRendered(p, opts.wait || 3500); if (d && d.status) { failed[p] = d.status; return rawDocs[Object.keys(rawDocs).find(k => P[k] === p)] || d; } return d; });
  // ---- 5. what only appears after JavaScript (ChatGPT, Claude and Perplexity do not see it; Google does)
  const js_only = [];
  if (G) {
    Object.keys(R.ev).filter(k => k !== '_detail').forEach(k => { if (JSON.stringify(R.ev[k]) !== JSON.stringify(G.ev[k])) js_only.push(`${k}: raw ${JSON.stringify(R.ev[k])} / after JavaScript ${JSON.stringify(G.ev[k])}`); });
    KEYS.forEach(k => { const a = R.pages[k], b = G.pages[k]; if (a && b && !a.status && !b.status && b.blocks !== a.blocks) js_only.push(`${k}: ${a.blocks} JSON-LD block(s) raw, ${b.blocks} after JavaScript`); if (failed[P[k]]) R.notes.push(`${k}: the after-JavaScript reading failed (${failed[P[k]]}); its raw reading stands in, so no difference is claimed. Open that page in this tab and run dhapSchema again (it then reads the open page directly)`); });
  }
  // ---- 6. readable text of the raw pages: the sentences JEV judges (serving towns, delivery, reviews shown)
  const txt = {}; const sent = { serving: [], delivery: [], reviews: [] };
  const RX = { serving: /\b(serv(e|es|ing)|drivers (from|in|throughout|across|near)|customers (from|in|throughout|across)|shoppers (from|in)|residents of|areas? we serve|near)\b/i,
               delivery: /\b(deliver\w*|pick[- ]?up|valet|mobile (service|mechanic|repair)|ship(s|ping|ped)?)\b/i,
               reviews: /\b(reviews?|testimonials?|rated|stars?)\b/i };
  KEYS.forEach(k => {
    const d = rawDocs[k]; if (!d || !d.body) return;
    const c = d.body.cloneNode(true); c.querySelectorAll('script,style,noscript,template,svg').forEach(x => x.remove());
    // keep block boundaries: a detached page has no layout, so textContent would glue "Directions" + "Proudly serving..."
    c.querySelectorAll('p,div,li,ul,ol,h1,h2,h3,h4,h5,h6,br,tr,td,th,section,article,header,footer,nav,a,button,span,label,option,dt,dd,blockquote,figcaption').forEach(x => x.after(d.createTextNode('\n')));
    const lines = (c.textContent || '').split(/\n+/).map(x => x.replace(/\s+/g, ' ').trim()).filter(Boolean);
    const t = lines.join(' \n '); txt[k] = t;
    lines.flatMap(l => l.split(/(?<=[.!?])\s+(?=[A-Z0-9"“])|(?<=[a-z0-9][.!?])(?=[A-Z][a-z])/)).forEach(x => { x = x.trim().slice(0, 300); for (const n of Object.keys(sent)) if (RX[n].test(x) && sent[n].length < 25 && !sent[n].some(y => y.s === x)) sent[n].push({ page: k, s: x }); });
  });
  window.__dhapText = Object.values(txt).join(' \n ');
  const out = { rendered_failed: Object.keys(failed).length, evidence_schema: R.ev, evidence_schema_rendered: G ? G.ev : null, js_only, pages: R.pg, pages_rendered: G ? G.pg : null,
                area_served_raw: R.area, sentences: sent, notes: R.notes };
  return JSON.stringify(out).replace(/[?=&]/g, '~');
}

// after dhapSchema(): which of these place names appear in the raw readable text of the 5 key pages (rule 4, code_on_page)
function dhapFind(names) {
  const fold = s => String(s).normalize('NFKD').replace(/[\u0300-\u036f]/g, '').toLowerCase().replace(/\bsaint\b/g, 'st').replace(/\bmount\b/g, 'mt').replace(/\bfort\b/g, 'ft').replace(/[.]/g, '').replace(/-/g, ' ').replace(/\s+/g, ' ').trim();
  const t = ' ' + fold(window.__dhapText || '') + ' ';
  return JSON.stringify(names.filter(n => new RegExp('(?<![a-z0-9])' + fold(n).replace(/[.*+?^${}()|[\]\\]/g, '\\$&') + '(?![a-z0-9])').test(t)));
}

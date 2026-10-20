// DHAP GBP — website schema collector. Paste the whole file into one javascript_tool call on the dealer's
// HOMEPAGE (same origin), then call:  await dhapSchema()            -> finds key pages from the nav and audits them
//                                  or await dhapSchema({home:'/', about:'/contactus', service:'/service', parts:'/parts', directions:'/hours'})
// It returns ONE short JSON string with the evidence fields the rubric needs (schema rows 7 and 8) plus
// short notes. It only READS pages (same-origin fetch with the browser's own cookies). No clicks, no edits.
// Output avoids ? = & characters (some tools block them).
async function dhapSchema(paths) {
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
  // ---- 3. audit each page
  const pages = {}; let main = null, mainBlocks = null, homeTypes = [];
  const roleOf = d => { const t = typesOf(d).join(' ') + ' ' + (d.name || ''); return /parts/i.test(t) ? 'parts' : /repair|service/i.test(t) ? 'service' : /dealer|sales/i.test(t) ? 'sales' : 'other'; };
  const source = {};
  for (const k of KEYS) {
    if (k !== 'home' && main && (!P[k] || P[k] === '/') && (k === 'service' || k === 'parts')) {
      const d = [].concat(main.department || []).map(mainBlocks.res).find(x => x && roleOf(x) === k && x.url);
      if (d) { try { const u = new URL(String(d.url), location.href); let mh = ''; try { mh = new URL(String(main.url)).hostname.replace(/^www\./, ''); } catch (e) {} if ([host, mh].includes(u.hostname.replace(/^www\./, '')) && u.pathname !== '/') { P[k] = u.pathname; source[k] = 'schema'; } } catch (e) {} }
    }
    if (k !== 'home' && P[k] === '/') P[k] = null;
    const doc = await getDoc(P[k]);
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
      logo_or_image: false, sameas_google: false, sameas_other: false, areaserved: false, hasmap_or_map: false, services_or_offers: false });
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
    ev.areaserved = !!main.areaServed; ev.hasmap_or_map = !!(main.hasMap || main.map || main.maps);
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
  return JSON.stringify({ evidence_schema: ev, pages: pg, notes }).replace(/[?=&]/g, '~');
}

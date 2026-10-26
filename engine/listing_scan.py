#!/usr/bin/env python3
"""DHAP GBP engine — search the listing sites that allow it, signed out, and save DRAFT readings (rule 8, v15.2).

For every site in listing_sites.json with method "headless": open its search, find the dealer's result (by phone, else
by the match words), open the listing when the result does not show the phone, copy the name, address and phone it
shows, and save a screenshot. A complete reading (name, phone, and a street with
a ZIP, all in the dealer's result) is accepted as is, with its screenshot as proof. An incomplete one is saved with
"draft": true — the run fills the missing part from the screenshot and removes "draft" (the evidence check refuses
drafts). A site that refuses the browser or times out is "blocked" and skipped: one try per site, never retried.
Usage: python3 listing_scan.py --name "James Mitsubishi Greece" --match "James Mitsubishi" --city Greece --st NY --zip 14626
                               --phone 585-563-2029 --out DIR        -> DIR/listing_scan.json + DIR/proof/*.png
Needs Playwright's Chromium (the DHAP venv)."""
import argparse, asyncio, datetime, json, pathlib, re, sys, urllib.parse
from playwright.async_api import async_playwright

ENG = pathlib.Path(__file__).resolve().parent
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36"
PHONE = re.compile(r"\(?\b\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4}\b")
STREET = re.compile(r"\b\d{2,6}\s+(?:[NSEW]\.?\s+|North\s+|South\s+|East\s+|West\s+)?[A-Za-z0-9.' -]{2,40}?\b(?:Road|Rd|Street|St|Avenue|Ave|Drive|Dr|Boulevard|Blvd|Highway|Hwy|Parkway|Pkwy|Lane|Ln|Way|Pike|Route|Rte|Court|Ct|Place|Pl|Circle|Cir|Trail|Trl|Turnpike|Tpke|Expressway|Expy|Freeway|Fwy)\b\.?(?:,?\s*(?:Ste|Suite|Unit|#)\s*[\w-]+)?(?:,\s*[A-Za-z .'-]+,?\s+(?:[A-Z]{2}|[A-Z][a-z]+(?: [A-Z][a-z]+)?)\.?,?\s+\d{5}(?:-\d{4})?)?", re.I)
BLOCKED = re.compile(r"(?i)just a moment|performing security verification|access denied|press & hold|are you a robot|captcha")

def digits(t): return re.sub(r"\D", "", t or "").removeprefix("1")[-10:]

def parse(block, match, phone):
    """name, address, phone from one result's text (newlines kept)."""
    lines = [l.strip() for l in block.splitlines() if l.strip()]
    flat = ", ".join(lines)
    nm = next((l for l in lines if match.lower() in l.lower() and not re.search(r"(?i)results? for|search|^top \d+", l)), "")
    if not nm:   # the listing's name may differ from the match words (a legal name): first line that is not a phone, address or heading
        nm = next((l for l in lines if not PHONE.search(l) and not STREET.search(l) and not re.search(r"(?i)results? for|^top \d+|search|directions|website", l) and len(l) > 3), "")
    nm = re.sub(r"^\s*\d+\.\s*", "", nm)                      # "1. James Mitsubishi Greece" -> the name
    ph = [p for p in PHONE.findall(flat)]
    ph = next((p for p in ph if digits(p) == digits(phone)), ph[0] if ph else "")
    ad = STREET.search(flat); ad = re.sub(r"\s*,\s*,", ",", ad.group(0)).strip(" ,") if ad else ""
    return nm[:120], ad[:160], ph

JS_BLOCK = """([match, ph]) => {
  const want = (t) => t && (t.toLowerCase().includes(match.toLowerCase()) || t.replace(/\\D/g,'').includes(ph));
  const bad = (t) => /results? for|search results|showing results|^\\s*top \\d+ best/i.test(t);
  const links = [...document.querySelectorAll('a[href]')].filter(e => want(e.innerText||'') && !bad(e.innerText||'') && (e.innerText||'').length < 200);
  const rest = [...document.querySelectorAll('body *')].filter(e => e.children.length < 40 && want(e.innerText||'') && !bad(e.innerText||'') && (e.innerText||'').length < 900);
  rest.sort((a,b) => (a.innerText||'').length - (b.innerText||'').length);
  const els = links.concat(rest);
  for (const e of els) {            // smallest element with the name, then grow to the result card (has a phone or an address)
    let c = e;
    for (let i = 0; i < 6 && c.parentElement; i++) {
      const t = c.innerText || '';
      if (/\\d{3}\\D{0,3}\\d{3}\\D?\\d{4}/.test(t) && /\\d{2,6} \\w/.test(t)) break;
      if ((c.parentElement.innerText||'').length > 900) break;
      c = c.parentElement;
    }
    c.setAttribute('data-dhap', '1');
    const a = c.querySelector('a[href]') || (c.closest('a[href]'));
    const link = [...c.querySelectorAll('a[href]')].find(x => (x.innerText||'').toLowerCase().includes(match.toLowerCase())) || a;
    return {text: c.innerText, href: link ? link.href : null};
  }
  return null;
}"""

async def one(b, site, a, out_dir, sem):   # one try per site: a site that can't be read is recorded and skipped, never retried
    url = site["url"].format(**{k: urllib.parse.quote_plus(v) for k, v in vars(a).items() if isinstance(v, str)})
    r = {"directory": site["id"], "when": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"), "url": url, "draft": True}
    async with sem:
        ctx = await b.new_context(user_agent=UA, viewport={"width": 1280, "height": 1000}); pg = await ctx.new_page()
        try:
            resp = await pg.goto(url, timeout=35000, wait_until="domcontentloaded"); await pg.wait_for_timeout(4000)
            body = await pg.evaluate("document.body ? document.body.innerText : ''")
            if (resp and resp.status in (401, 403, 429)) or BLOCKED.search(body[:600]):
                r.update(status="blocked", reason=f"refused the automated browser (HTTP {resp.status if resp else '?'}) — skipped"); r.pop("draft"); return r
            hit = await pg.evaluate(JS_BLOCK, [a.match, digits(a.phone)])
            if not hit:
                r.update(status="not_found", searched=f"{site['name']} search: {a.match} / {a.city}, {a.st} / {a.phone}"); r.pop("draft"); return r
            nm, ad, ph = parse(hit["text"], a.match, a.phone)
            el = await pg.query_selector("[data-dhap='1']")
            if (not ph or not ad) and hit.get("href") and hit["href"].startswith("http"):   # open the listing for the missing parts
                await pg.goto(hit["href"], timeout=35000, wait_until="domcontentloaded"); await pg.wait_for_timeout(3500)
                page = await pg.evaluate("document.body ? document.body.innerText : ''")
                n2, a2, p2 = parse(page[:6000], a.match, a.phone); r["url"] = pg.url
                nm, ad, ph = nm or n2, ad or a2, ph or p2; el = None
            shot = out_dir / f"{site['id']}.png"
            if el: await el.screenshot(path=str(shot))
            else: await pg.screenshot(path=str(shot), full_page=False)
            r.update(status="found", name=nm, address=ad, phone=ph, proof=str(shot.relative_to(out_dir.parent)), block=hit["text"][:600])
            if nm and ph and re.search(r"\d{5}", ad): r.pop("draft")   # complete reading (name, phone, street with ZIP): accepted; the screenshot stays as proof
        except Exception as e:
            r.update(status="blocked", reason=f"page error: {str(e)[:120]} — skipped"); r.pop("draft", None)
        finally:
            await ctx.close()
    return r

async def main():
    ap = argparse.ArgumentParser(); [ap.add_argument("--" + k, required=True) for k in ("name", "city", "st", "zip", "phone", "out")]
    ap.add_argument("--match", help="words that identify the dealer in results (default: the first two words of --name)")
    a = ap.parse_args(); a.match = a.match or " ".join(a.name.split()[:2])
    out = pathlib.Path(a.out); proof = out / "proof"; proof.mkdir(parents=True, exist_ok=True)
    sites = [x for x in json.loads((ENG / "listing_sites.json").read_text())["sites"] if x["method"] == "headless"]
    async with async_playwright() as p:
        b = await p.chromium.launch(); sem = asyncio.Semaphore(6)
        R = await asyncio.gather(*(one(b, x, a, proof, sem) for x in sites)); await b.close()
    (out / "listing_scan.json").write_text(json.dumps(R, indent=1, ensure_ascii=False))
    for r in R: print(f"{r['directory']:18} {r['status']:9} {r.get('phone', ''):16} {r.get('address', '')[:55]:55} {r.get('name', r.get('reason', r.get('searched', '')))[:60]}")
    print(f"saved {out / 'listing_scan.json'} — only readings marked draft need a look at their screenshot; then read the Chrome sites")

if __name__ == "__main__": asyncio.run(main())

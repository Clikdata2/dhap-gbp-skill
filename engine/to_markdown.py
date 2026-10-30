#!/usr/bin/env python3
"""DHAP GBP engine — Markdown copy of a built page (v16.5, decided by Travis Oct 29 2026).

Every DHAP and Digital Health Alert is delivered as HTML plus a Markdown copy with the same name (.md), so each dealer
run delivers seven files. The page is opened in headless Chromium (Playwright) so the count-up numbers show their final
values, every DHAP tab is read in order, and the text is written as Markdown: the page's title and section titles as
headings, card titles in bold, tables as Markdown tables. What the reader cannot see on the page stays out: the
evidence popups (their figures are in the audit-evidence record), the Live Support widget, images and anything
blurred behind the Alert's lock.

Usage: python3 to_markdown.py PAGE.html [PAGE2.html ...]   -> writes PAGE.md next to each page and prints the paths
"""
import pathlib, re, sys

WAIT_MS = 4500   # the count-ups finish in about 3 s

JS = r"""
() => { window.__md = (root) => {
  const H1 = ['hero-title', 'header-title'];
  const H3 = ['section-title', 'section-lbl', 'solution-name', 'managed-pitfall-title', 'cta-headline', 'go-title',
              'alert-lbl', 'term-title', 'roi-amount'];
  const BOLD = ['finding-title', 'bf-title', 'kpi-lbl', 't-cap', 't-head', 'hero-fact-lbl', 'snap-lbl', 'score-label',
                'hero-eyebrow', 'solution-tagline', 'id-name', 'lock-text', 'go-urgent'];
  const SKIP = el => el.matches('script,style,noscript,svg,img,video,iframe,button.tab-btn,nav,[class*="pp-"],.proof-hint,[class*="jw-"],[aria-hidden="true"],.step-cta-wrap,[class*="crumb"],.screen:not(.md-on)');
  const has = (el, list) => list.some(c => el.classList && el.classList.contains(c));
  const INLINE = new Set(['SPAN','B','STRONG','EM','I','A','BR','CODE','SMALL','SUP','SUB','U','MARK','ABBR']);
  const hidden = el => { const s = getComputedStyle(el); return s.display === 'none' || s.visibility === 'hidden' || /blur/.test(s.filter); };
  const clean = t => t.replace(/\u00a0/g, ' ').replace(/[ \t]+/g, ' ').replace(/ *\n */g, ' ').trim();
  const inline = el => {
    if (el.nodeType === 3) return el.textContent;
    if (el.nodeType !== 1 || SKIP(el) || hidden(el)) return '';
    if (el.tagName === 'BR') return ' ';
    let t = [...el.childNodes].map(inline).join('');
    if (!/^inline$/.test(getComputedStyle(el).display) && t.trim()) t = ' ' + t + ' ';   // a label in its own box keeps its spacing
    if (/^(B|STRONG)$/.test(el.tagName) && clean(t)) t = '**' + clean(t) + '**';
    if (el.tagName === 'CODE' && clean(t)) t = '`' + clean(t) + '`';
    return t;
  };
  const cell = el => clean([...el.childNodes].map(n => n.nodeType === 1 && !INLINE.has(n.tagName) ? ' ' + block(n).join(' ').replace(/\n/g, ' ') + ' ' : inline(n)).join('')).replace(/\|/g, '\\|').replace(/^[#>-]+\s*/, '');
  const table = t => {
    const rows = [...t.querySelectorAll('tr')].filter(r => !hidden(r)).map(r => [...r.children].filter(c => !hidden(c)).map(cell));
    if (!rows.length) return [];
    const n = Math.max(...rows.map(r => r.length));
    const pad = r => r.concat(Array(n - r.length).fill(''));
    const head = pad(rows[0]);
    return ['', '| ' + head.join(' | ') + ' |', '|' + head.map(() => '---').join('|') + '|', ...rows.slice(1).map(r => '| ' + pad(r).join(' | ') + ' |'), ''];
  };
  function block(el) {
    if (el.nodeType === 3) { const t = clean(el.textContent); return t ? [t] : []; }
    if (el.nodeType !== 1 || SKIP(el) || hidden(el)) return [];
    if (el.tagName === 'TABLE') return table(el);
    const kids = [...el.childNodes];
    const leaf = kids.every(n => n.nodeType === 3 || (n.nodeType === 1 && (INLINE.has(n.tagName) || SKIP(n))));
    if (leaf) {
      const t = clean(inline(el)); if (!t) return [];
      if (has(el, H1)) return ['', '# ' + t, ''];
      if (has(el, H3)) return ['', '### ' + t.replace(/\*\*/g, ''), ''];
      if (has(el, BOLD)) return ['**' + t.replace(/\*\*/g, '') + '**'];
      if (el.tagName === 'LI') return ['- ' + t];
      if (/^H[1-6]$/.test(el.tagName)) return ['', '#'.repeat(Math.min(+el.tagName[1] + 1, 6)) + ' ' + t, ''];
      return [t];
    }
    let out = [];
    // a mixed block: runs of inline nodes become one line, block children recurse
    let run = '';
    const flush = () => { const t = clean(run); if (t) out.push(el.tagName === 'LI' ? '- ' + t : t); run = ''; };
    for (const n of kids) {
      if (n.nodeType === 3 || (n.nodeType === 1 && INLINE.has(n.tagName))) run += inline(n);
      else { flush(); out = out.concat(block(n)); }
    }
    flush();
    if (/^(DIV|SECTION|ARTICLE|P|UL|OL|HEADER|FOOTER|MAIN)$/.test(el.tagName) && out.length) out = ['', ...out, ''];
    return out;
  }
  // the Alert's stat cards: write each card's final value the way the page's own finish() does (no half-run count-up)
  document.querySelectorAll('.t-stat').forEach(c => {
    const n = +c.getAttribute('data-target'), v = c.querySelector('.t-val'), st = c.querySelector('.t-status');
    if (v) v.textContent = (c.getAttribute('data-comma') === '1' ? n.toLocaleString('en-US') : String(n)) + (c.getAttribute('data-suffix') || '');
    if (st) st.innerHTML = '&gt; Status: <b>' + (c.getAttribute('data-status') || 'Critical') + '</b>';
  });
  if (root) return [...document.querySelector(root).childNodes].flatMap(block);
  // every DHAP tab, in order, as a section
  const panels = [...document.querySelectorAll('.tab-panel')];
  const names = [...document.querySelectorAll('.tab-btn, [class*="tab"] button, nav button')].map(b => clean(b.innerText)).filter(Boolean);
  let lines = [];
  if (panels.length) {
    panels.forEach((p, i) => { p.style.display = 'block'; p.classList.add('active'); lines.push('', '## ' + (names[i] || p.id), ''); lines = lines.concat([...p.childNodes].flatMap(block)); });
    // after the panels (footer)
    const last = panels[panels.length - 1].parentElement;
    let after = false;
    for (const k of last.children) { if (k === panels[panels.length - 1]) { after = true; continue; } if (after) lines = lines.concat(block(k)); }
  } else lines = [...document.body.childNodes].flatMap(block);
  return lines;
}; return true; }
"""


def to_md(page, browser):
    pg = browser.new_page(viewport={"width": 1280, "height": 900})
    pg.goto(page.resolve().as_uri()); pg.wait_for_timeout(WAIT_MS)
    pg.evaluate(JS)
    screens = pg.eval_on_selector_all(".screen[id]", "els => els.map(e => e.id)")
    title = None
    if screens:   # the Alert: click through its screens like a reader so each screen's count-ups finish
        # the header above the screens, read once: each block before the first screen is wrapped so __md can read it
        n = pg.evaluate("""() => { const first = document.querySelector('.screen'); const keep = [];
            const walk = el => { for (const k of el.children) { if (k === first) return true; if (k.contains(first)) { if (walk(k)) return true; } else keep.push(k); } return false; };
            walk(document.body);
            keep.forEach((k, i) => { const w = document.createElement('div'); w.id = 'md-head-' + i; k.parentNode.insertBefore(w, k); w.appendChild(k); });
            return keep.length; }""")
        lines = [x for i in range(n) for x in pg.evaluate("id => window.__md('#' + id)", f"md-head-{i}")]
        for i, sid in enumerate(screens):
            if i:
                pg.evaluate("n => { const b = document.querySelector('[data-go=\"' + n + '\"]'); if (b) b.click(); }", i + 1)
                pg.wait_for_timeout(WAIT_MS)
            pg.evaluate("id => document.getElementById(id).classList.add('md-on')", sid)
            lines += ["", f"## Screen {i + 1} of {len(screens)}", ""] + pg.evaluate("id => window.__md('#' + id)", sid)
    else:
        lines = pg.evaluate("() => window.__md()")
    title = pg.title()
    pg.close()
    text = "\n".join(lines)
    if title: text = f"# {title}\n\n" + re.sub(r"(?m)^# ", "### ", text)   # one page title; titles inside the tabs become sections
    text = re.sub(r"\n{3,}", "\n\n", text).strip() + "\n"
    text = re.sub(r"(?m)^(\*\*[^*\n]+\*\*)\n\n(?=\S)", r"\1\n", text)      # a bold label sits on the line above its value
    head = f"<!-- Markdown copy of {page.name} (DHAP GBP engine to_markdown.py). The HTML is the designed page; this copy holds the same text. -->\n\n"
    return head + text


def main(paths):
    from playwright.sync_api import sync_playwright
    out = []
    with sync_playwright() as p:
        b = p.chromium.launch()
        for s in paths:
            page = pathlib.Path(s)
            md = page.with_suffix(".md")
            md.write_text(to_md(page, b), encoding="utf-8"); out.append(str(md))
        b.close()
    for o in out: print(o)
    return out


if __name__ == "__main__":
    if len(sys.argv) < 2: print(__doc__); sys.exit(2)
    main(sys.argv[1:])

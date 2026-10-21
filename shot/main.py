"""DHAP proof service — evidence for RULE K popups when the run has no browser of its own (Ask AI).

A Google Cloud Run service with a hidden, signed-out Chromium. Same team codes as the key service (secret DHAP_TEAM_CODES);
every route except /health needs the code in the X-DHAP-Code header.

Routes
  GET  /health
  GET  /screenshot?url=<page>&preset=<preset>
       -> {"status": "ok"|"blocked"|"error", "image": "data:image/jpeg;base64,...", "final_url", "title",
           "text": "<first 1,500 visible characters>", "captured_at": "<UTC time>", "blocked_reason"}
       presets: full (default) · gmaps_panel (Google Maps listing, left panel)
                · apple_panel (Apple Maps place card)
       "blocked" means the site refused a signed-out browser (robot check, login wall, access denied). Use a data proof instead.
  GET  /schema?url=<page>   -> every JSON-LD block on the page, parsed (plain fetch first, then the browser)
  POST /popup               -> body {"keys": {...}, "images": {"name": "data:image/..."}, "rules": [[key, regex], ...]}
                               returns the RULE K popup block (CSS + script) to insert before </body>
Read-only: it never signs in, never clicks claim/edit/review/post buttons, and refuses private or internal addresses.
"""
import base64, datetime, ipaddress, json, os, re, socket, urllib.parse, urllib.request
import functions_framework
from proof_popup import block_from_uris

VIEW = {"width": 1280, "height": 900}
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36"
BLOCK_WORDS = ["unusual traffic", "not a robot", "captcha", "access denied", "you have been blocked", "verify you are human",
               "are you a human", "before you continue to google"]
CROPS = {"gmaps_panel": (72, 0, 480, 900), "apple_panel": (170, 0, 520, 900)}


def _codes():
    try:
        return {str(k): str(v) for k, v in json.loads(os.environ.get("DHAP_TEAM_CODES") or "{}").items()}
    except ValueError:
        return {}


def _who(code):
    import hmac
    found = None
    for name, c in _codes().items():
        if code and hmac.compare_digest(code.encode(), c.encode()):
            found = name
    return found


def _reply(obj, status=200):
    return (json.dumps(obj), status, {"Content-Type": "application/json", "Cache-Control": "no-store"})


def _public_url(url):
    """Only http(s) pages on public internet addresses (blocks the cloud metadata server and private networks)."""
    p = urllib.parse.urlparse(url)
    if p.scheme not in ("http", "https") or not p.hostname:
        return False
    try:
        for info in socket.getaddrinfo(p.hostname, None):
            ip = ipaddress.ip_address(info[4][0])
            if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast:
                return False
    except OSError:
        return False
    return True


def _now():
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


def _jpeg_data_uri(png_bytes, crop=None, width=480):
    from PIL import Image
    import io
    im = Image.open(io.BytesIO(png_bytes)).convert("RGB")
    if crop:
        im = im.crop(crop)
    if im.width > width:
        im = im.resize((width, int(im.height * width / im.width)))
    buf = io.BytesIO()
    im.save(buf, "JPEG", quality=72, optimize=True)
    return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()


def _screenshot(url, preset):
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        b = p.chromium.launch(args=["--no-sandbox"])
        ctx = b.new_context(viewport=VIEW, locale="en-US", user_agent=UA)
        pg = ctx.new_page()
        pg.goto(url, timeout=45000, wait_until="domcontentloaded")
        pg.wait_for_timeout(5000)
        if "facebook.com" in pg.url:
            pg.keyboard.press("Escape")          # closes the "log in" box; never signs in
            pg.wait_for_timeout(1000)
        text = pg.evaluate("document.body ? document.body.innerText : ''")
        final, title = pg.url, pg.title()
        png = pg.screenshot()
        b.close()
    low = text.lower()
    hit = next((w for w in BLOCK_WORDS if w in low), None)
    if hit or len(text.strip()) < 40:
        return {"status": "blocked", "blocked_reason": hit or "empty page", "final_url": final, "title": title, "captured_at": _now()}
    return {"status": "ok", "image": _jpeg_data_uri(png, CROPS.get(preset)), "final_url": final, "title": title,
            "text": re.sub(r"\n{3,}", "\n\n", text)[:1500], "captured_at": _now()}


def _jsonld_from_html(html):
    blocks = re.findall(r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>', html, flags=re.S | re.I)
    out = []
    for b in blocks:
        try:
            out.append(json.loads(b.strip()))
        except ValueError:
            out.append({"_parse_error": b.strip()[:300]})
    return out


def _schema(url):
    method, html = "plain fetch", ""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=20) as r:
            html = r.read().decode(errors="replace")
    except Exception:
        html = ""
    if not html or "access denied" in html.lower()[:2000]:
        from playwright.sync_api import sync_playwright
        method = "browser"
        with sync_playwright() as p:
            b = p.chromium.launch(args=["--no-sandbox"])
            pg = b.new_context(user_agent=UA).new_page()
            pg.goto(url, timeout=45000, wait_until="domcontentloaded")
            pg.wait_for_timeout(4000)
            html = pg.content()
            b.close()
        if "access denied" in html.lower()[:3000]:
            return {"status": "blocked", "method": method, "captured_at": _now()}
    return {"status": "ok", "method": method, "blocks": _jsonld_from_html(html), "captured_at": _now()}


@functions_framework.http
def app(request):
    path = request.path.strip("/")
    if path == "health":
        return _reply({"ok": True, "team_codes": len(_codes())})
    who = _who((request.headers.get("X-DHAP-Code") or "").strip())
    if not who:
        return _reply({"error": "missing or wrong team code"}, 401)
    print(json.dumps({"who": who, "route": path}))
    if path in ("screenshot", "schema"):
        url = request.args.get("url", "")
        if not _public_url(url):
            return _reply({"error": "url must be a public http(s) page"}, 400)
        try:
            if path == "screenshot":
                preset = request.args.get("preset", "full")
                if preset not in ("full",) + tuple(CROPS):
                    return _reply({"error": "unknown preset"}, 400)
                return _reply(_screenshot(url, preset))
            return _reply(_schema(url))
        except Exception as e:
            return _reply({"status": "error", "error": f"{type(e).__name__}: {str(e)[:200]}"}, 502)
    if path == "popup" and request.method == "POST":
        try:
            d = request.get_json(force=True)
            return (block_from_uris(d["keys"], d.get("images") or {}, d.get("rules")), 200, {"Content-Type": "text/html; charset=utf-8"})
        except Exception as e:
            return _reply({"error": f"bad popup spec: {type(e).__name__}: {str(e)[:200]}"}, 400)
    return _reply({"error": "unknown route"}, 404)

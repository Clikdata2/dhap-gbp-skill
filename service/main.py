"""DHAP key service — holds the Google Places and TypeSafe (JEV) API keys so no employee machine or Ask AI needs them.

Runs as one Google Cloud Run function. Every request must carry a team code (header X-DHAP-Code, or ?code= on /lookup).
Codes live in the secret DHAP_TEAM_CODES as JSON {"name": "code", ...}; remove a name to cut that person off.

Routes
  GET  /health                         -> {"ok": true}  (no code needed; shows which keys are loaded)
  POST /places/v1/places:searchText    -> forwarded to Google Places (New) with the key added
  GET  /places/v1/places/<id>          -> forwarded to Google Places (New) with the key added
  POST /jev                            -> forwarded to TypeSafe System One (JEV) with the key added
  GET  /lookup?q=<dealer, street, city, state>&code=<team code>
                                       -> one simple answer for Ask AI / GHL: name, address, phone, website,
                                          rating, review count, hours, Maps link
Keys never leave this service. Nothing is stored. Each call is logged with the team member's name, never the code.
"""
import hmac, json, os, re, urllib.error, urllib.parse, urllib.request
import functions_framework

PLACES = "https://places.googleapis.com/v1"
JEV_URL = "https://api.typesafe.ai/v1/systemone"
JEV_MODELS = {"jev-1.14.0"}
DETAIL_FIELDS = ("id,displayName,formattedAddress,nationalPhoneNumber,websiteUri,rating,userRatingCount,businessStatus,"
                 "googleMapsUri,regularOpeningHours.weekdayDescriptions")
PLACE_ID = re.compile(r"^[A-Za-z0-9_-]{10,300}$")
MAX_BODY = 200_000


def _key(name):
    v = (os.environ.get(name) or "").strip()
    return "" if v.lower() in ("", "none") else v


def _codes():
    try:
        d = json.loads(os.environ.get("DHAP_TEAM_CODES") or "{}")
        return {str(k): str(v) for k, v in d.items() if str(v).strip()}
    except ValueError:
        return {}


def _who(code):
    """Return the team member's name for a valid code, else None (constant-time compare)."""
    found = None
    for name, c in _codes().items():
        if code and hmac.compare_digest(code.encode(), c.encode()):
            found = name
    return found


def _reply(obj, status=200):
    return (json.dumps(obj), status, {"Content-Type": "application/json", "Cache-Control": "no-store"})


def _forward(url, headers, body=None, method="GET", timeout=20):
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.read().decode(), r.status
    except urllib.error.HTTPError as e:
        return e.read().decode(errors="replace")[:2000], e.code


def _places(path, method, body, mask):
    key = _key("GOOGLE_PLACES_API_KEY")
    if not key:
        return _reply({"error": "Places key not set on the service"}, 503)
    if method == "POST" and path == "places:searchText":
        return _forward(f"{PLACES}/places:searchText",
                        {"X-Goog-Api-Key": key, "X-Goog-FieldMask": mask or "places.id", "Content-Type": "application/json"},
                        body, "POST") + ({"Content-Type": "application/json"},)
    if method == "GET" and path.startswith("places/") and PLACE_ID.match(path[7:]):
        return _forward(f"{PLACES}/{path}", {"X-Goog-Api-Key": key, "X-Goog-FieldMask": mask or "id"}) + ({"Content-Type": "application/json"},)
    return _reply({"error": "only places:searchText (POST) and places/<id> (GET) are allowed"}, 404)


def _jev(body):
    key = _key("TYPESAFE_API_KEY")
    if not key:
        return _reply({"error": "JEV key not set on the service"}, 503)
    try:
        d = json.loads(body or b"{}")
    except ValueError:
        return _reply({"error": "body must be JSON"}, 400)
    if d.get("model") not in JEV_MODELS:
        return _reply({"error": "model not allowed"}, 400)
    return _forward(JEV_URL, {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}, json.dumps(d).encode(), "POST") + (
        {"Content-Type": "application/json"},)


def _lookup(q):
    key = _key("GOOGLE_PLACES_API_KEY")
    if not key:
        return _reply({"status": "skipped", "reason": "Places key not set on the service"}, 503)
    if not q.strip():
        return _reply({"status": "skipped", "reason": "add ?q=dealer name, street, city, state"}, 400)
    txt, code = _forward(f"{PLACES}/places:searchText",
                         {"X-Goog-Api-Key": key, "X-Goog-FieldMask": "places.id", "Content-Type": "application/json"},
                         json.dumps({"textQuery": q, "pageSize": 3}).encode(), "POST")
    if code != 200:
        return _reply({"status": "skipped", "reason": f"search failed (HTTP {code})"}, 502)
    ids = [p.get("id") for p in (json.loads(txt).get("places") or []) if p.get("id")]
    if not ids:
        return _reply({"status": "skipped", "reason": "no listing found for that search"})
    txt, code = _forward(f"{PLACES}/places/{urllib.parse.quote(ids[0])}", {"X-Goog-Api-Key": key, "X-Goog-FieldMask": DETAIL_FIELDS})
    if code != 200:
        return _reply({"status": "skipped", "reason": f"details failed (HTTP {code})"}, 502)
    d = json.loads(txt)
    return _reply({"status": "ok", "query": q, "other_matches": len(ids) - 1, "place": {
        "name": (d.get("displayName") or {}).get("text"), "address": d.get("formattedAddress"), "phone": d.get("nationalPhoneNumber"),
        "website": d.get("websiteUri"), "rating": d.get("rating"), "review_count": d.get("userRatingCount"),
        "business_status": d.get("businessStatus"), "maps_url": d.get("googleMapsUri"),
        "hours": (d.get("regularOpeningHours") or {}).get("weekdayDescriptions") or []}})


@functions_framework.http
def app(request):
    path = request.path.strip("/")
    if path == "health":
        return _reply({"ok": True, "places_key": bool(_key("GOOGLE_PLACES_API_KEY")), "jev_key": bool(_key("TYPESAFE_API_KEY")),
                       "team_codes": len(_codes())})
    code = request.headers.get("X-DHAP-Code") or (request.args.get("code") if path == "lookup" else None) or ""
    who = _who(code.strip())
    if not who:
        return _reply({"error": "missing or wrong team code"}, 401)
    body = request.get_data(cache=False)
    if body and len(body) > MAX_BODY:
        return _reply({"error": "request too large"}, 413)
    print(json.dumps({"who": who, "route": path.split("/")[0], "method": request.method}))
    if path == "lookup":
        return _lookup(request.args.get("q", ""))
    if path.startswith("places/v1/"):
        return _places(path[len("places/v1/"):], request.method, body, request.headers.get("X-Goog-FieldMask", ""))
    if path == "jev" and request.method == "POST":
        return _jev(body)
    return _reply({"error": "unknown route"}, 404)

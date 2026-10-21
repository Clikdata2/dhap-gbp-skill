#!/usr/bin/env python3
"""DHAP GBP engine — optional Google Places cross-check of the Maps collector.

Looks up the listing in Google's Places API (New) and compares it with what the Maps collector read in Chrome:
name, rating, review count, phone, street address and website. Any difference is listed for a person to look at
(a misread page, a listing that changed, or the wrong listing). Places never changes a score or the evidence.
It also returns the weekly hours Google shows, which the collector does not read, for the hours checks.
Places cannot see posts, photo dates, newest-first reviews or owner replies, so the Chrome step is still needed.

Cost: finding the listing uses the free "IDs only" search; reading it is one Place Details Enterprise call
(the first 1,000 a month are free, then $0.02 each).
Key: either the team key service (DHAP_SERVICE_URL + DHAP_TEAM_CODE in the environment; see service/) or, as a
fallback, GOOGLE_PLACES_API_KEY on this machine. Never put either in the repository. With neither, no network, a bad
reply or a timeout, it returns status "skipped" with the reason, and the audit goes on.
Usage: python3 places.py "Dealer name, street, city, state" [maps.json]   (maps.json = the collector's answer)
"""
import json, os, re, sys, urllib.error, urllib.parse, urllib.request

BASE = "https://places.googleapis.com/v1"
FIELDS = ("id,displayName,formattedAddress,nationalPhoneNumber,websiteUri,rating,userRatingCount,businessStatus,"
          "googleMapsUri,regularOpeningHours.weekdayDescriptions")
PRICE_DETAILS = 0.02   # US$ per Place Details Enterprise call after the monthly free calls

def _service():
    """(base URL, team code) for the team key service, or (None, None) when it is not set up on this machine."""
    url, code = os.environ.get("DHAP_SERVICE_URL", "").rstrip("/"), os.environ.get("DHAP_TEAM_CODE", "")
    return (url + "/places/v1", code) if url and code else (None, None)

def _call(url, key, timeout, body=None, mask="id"):
    auth = {"X-DHAP-Code": key[5:]} if key.startswith("team:") else {"X-Goog-Api-Key": key}
    req = urllib.request.Request(url, data=json.dumps(body).encode() if body is not None else None,
                                 headers={**auth, "X-Goog-FieldMask": mask, "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode())

def _words(s): return set(re.findall(r"[a-z0-9]+", str(s or "").lower())) - {"the", "of", "and", "inc", "llc"}
def _digits(s): d = re.sub(r"\D", "", str(s or "")); return d[-10:] if len(d) >= 10 else d
def _domain(s):
    s = str(s or "").strip().lower()
    host = urllib.parse.urlparse(s if "//" in s else "//" + s).hostname or ""
    return host[4:] if host.startswith("www.") else host
def _street(s):
    m = re.match(r"\s*(\d+)\s+([A-Za-z0-9 .]+?)(?:,|$)", str(s or ""))
    if not m: return ""
    st = m.group(2).lower().replace(".", "")
    for a, b in ((" west ", " w "), (" east ", " e "), (" north ", " n "), (" south ", " s "), (" road", " rd"), (" drive", " dr"),
                 (" street", " st"), (" avenue", " ave"), (" pike", " pike"), (" boulevard", " blvd"), (" highway", " hwy")):
        st = (" " + st + " ").replace(a, b).strip()
    return m.group(1) + " " + re.sub(r"\s+", " ", st)
def _zip(s): m = re.search(r"\b(\d{5})(?:-\d{4})?\b(?!.*\b\d{5}\b)", str(s or "")); return m.group(1) if m else ""

def lookup(query, key=None, timeout=15, base=None):
    """Find the listing (free IDs-only search), then read it (one Enterprise call)."""
    if key is None and base is None:
        s_base, s_code = _service()
        if s_base: base, key = s_base, "team:" + s_code
    base = base or BASE
    key = key if key is not None else os.environ.get("GOOGLE_PLACES_API_KEY", "")
    out = {"status": "skipped", "query": query, "calls": 0, "cost_usd": 0.0}
    if not str(query or "").strip(): out["reason"] = "no search text"; return out
    if not key: out["reason"] = "GOOGLE_PLACES_API_KEY not set (and no team key service: DHAP_SERVICE_URL + DHAP_TEAM_CODE)"; return out
    try:
        found = _call(base + "/places:searchText", key, timeout, {"textQuery": query, "pageSize": 3}, "places.id")
        ids = [p.get("id") for p in (found.get("places") or []) if isinstance(p, dict) and p.get("id")]
        if not ids: out["reason"] = "no listing found for that search"; return out
        out["other_matches"] = len(ids) - 1
        d = _call(base + "/places/" + urllib.parse.quote(ids[0]), key, timeout, None, FIELDS)
        out["calls"] = 1; out["cost_usd"] = PRICE_DETAILS
    except urllib.error.HTTPError as e: out["reason"] = f"HTTP {e.code}"; return out
    except Exception as e: out["reason"] = f"{type(e).__name__}: {str(e)[:120]}"; return out
    if not isinstance(d, dict) or not d.get("id"): out["reason"] = "reply had no listing"; return out
    out["status"] = "ok"
    out["place"] = {"id": d.get("id"), "name": (d.get("displayName") or {}).get("text"), "address": d.get("formattedAddress"),
                    "phone": d.get("nationalPhoneNumber"), "website": d.get("websiteUri"), "rating": d.get("rating"),
                    "review_count": d.get("userRatingCount"), "status": d.get("businessStatus"), "maps_url": d.get("googleMapsUri"),
                    "hours": (d.get("regularOpeningHours") or {}).get("weekdayDescriptions") or []}
    return out

def cross_check(maps, place):
    """maps: the Maps collector's answer; place: lookup()["place"]. Returns (rows, review list)."""
    rows, review = [], []
    def row(field, a, b, same, note=""):
        rows.append({"field": field, "maps": a, "places": b, "match": same})
        if not same: review.append(f"{field}: Chrome read {a!r}, Places says {b!r}" + (f" ({note})" if note else ""))
    nm, np_ = _words(maps.get("name")), _words(place.get("name"))
    row("name", maps.get("name"), place.get("name"), bool(nm) and (nm <= np_ or np_ <= nm), "possibly a different listing")
    row("rating", maps.get("rating"), place.get("rating"), maps.get("rating") == place.get("rating"))
    mc, pc = maps.get("n_reviews", maps.get("review_count")), place.get("review_count")
    row("review count", mc, pc, mc == pc, "Places can lag Maps by a day; re-check if the gap is small")
    row("phone", maps.get("phone"), place.get("phone"), _digits(maps.get("phone")) == _digits(place.get("phone")) != "")
    ma, pa = maps.get("addr", maps.get("address")), place.get("address")
    row("street address", ma, pa, _street(ma) == _street(pa) != "" and _zip(ma) == _zip(pa))
    mw, pw = maps.get("web", maps.get("website")), place.get("website")
    row("website", mw, pw, _domain(mw) == _domain(pw) != "")
    if place.get("status") not in (None, "OPERATIONAL"): review.append(f"Google lists the business as {place.get('status')}")
    return rows, review

def run(query, maps=None, **kw):
    r = lookup(query, **kw)
    if r["status"] == "ok" and maps:
        # other_matches is kept for the record only: nearby department listings match the search too, and the
        # name check above already catches a wrong listing
        r["compare"], r["review"] = cross_check(maps, r["place"]); r["agree"] = not r["review"]
    return r

if __name__ == "__main__":
    m = json.load(open(sys.argv[2])) if len(sys.argv) > 2 else None
    print(json.dumps(run(sys.argv[1], m), indent=1, ensure_ascii=False))

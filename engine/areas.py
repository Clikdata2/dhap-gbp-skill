#!/usr/bin/env python3
"""DHAP GBP engine — areaServed, both directions (rule 4, v15; tested Oct 22 2026 on 4 live dealers + attacks).

1. Places in the code: areaServed on the block that describes the whole dealership, raw page only, naming anything
   smaller than a country (states, counties, towns, ZIPs, local areas). "US", "Nationwide" and radius-only earn nothing.
2. Places the pages say the dealer serves: names after serving words ("proudly serving", "drivers from", "customers in"...)
   in the readable text of the 5 key pages, raw page only. JEV first decides whether each sentence is a serving sentence
   (decide.py, kind "serving"); this file pulls the names out and Google Places confirms each is a real town, county or
   ZIP within 200 km of the dealer.
3. points = 2 x (places in the code that also appear in the page text) / (all places named in either).
Usage: python3 areas.py towns "sentence"   -> the place names the rule pulls out of one sentence
"""
import json, math, os, re, sys, unicodedata, urllib.request

TOO_BIG = {"us", "u.s.", "usa", "u.s.a.", "united states", "united states of america", "america", "north america",
           "nationwide", "national", "worldwide", "world", "global", "international", "canada", "mexico"}
SERVE = re.compile(r"\b(proudly serv(?:e|es|ing)|serv(?:e|es|ing)|drivers (?:from|in|throughout|across|near)|customers (?:from|in|throughout|across)|shoppers (?:from|in)|residents of|areas? we serve|service areas?|near)\b", re.I)
FILLER = re.compile(r"^(?:and|or|the|greater|wider|surrounding|all of the|all of|throughout|across|nearby|entire|whole|of)\b\s*", re.I)
REGION_WORDS = re.compile(r"^\s*(?:suburbs?|area|areas|region|metro|community|communities)\b", re.I)
STATE_CODES = set("AL AK AZ AR CA CO CT DE FL GA HI ID IL IN IA KS KY LA ME MD MA MI MN MS MO MT NE NV NH NJ NM NY NC ND OH OK OR PA RI SC SD TN TX UT VT VA WA WV WI WY DC".split())
NAME = re.compile(r"\d{5}(?![\d-])|(?:(?:St|Mt|Ft|Ste)\.\s+)?[A-Z][A-Za-z'\-]+(?:\s+(?:(?:St|Mt|Ft)\.\s+)?[A-Z][A-Za-z'\-]+)*")
OK_TYPES = {"locality", "administrative_area_level_1", "administrative_area_level_2", "administrative_area_level_3",
            "postal_code", "sublocality", "sublocality_level_1", "neighborhood", "colloquial_area"}

def fold(s):
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode().lower()
    s = re.sub(r"\bsaint\b", "st", s); s = re.sub(r"\bmount\b", "mt", s); s = re.sub(r"\bfort\b", "ft", s)
    return re.sub(r"\s+", " ", s.replace(".", "").replace("-", " ")).strip()

def schema_places(area_served):
    """Place names in one areaServed value (string, list, Place objects, URLs). Country-size or bigger and radii are dropped."""
    v = area_served
    if isinstance(v, list): return [p for x in v for p in schema_places(x)]
    if isinstance(v, dict):
        if v.get("@type") in ("GeoCircle", "GeoShape", "Country", "Continent"): return []
        return schema_places(v.get("name")) if isinstance(v.get("name"), str) else []
    if isinstance(v, str):
        if v.startswith("http"): v = v.rstrip("/").split("/")[-1].replace("_", " ").split(",")[0]   # wiki link: "Des_Plaines,_Illinois" -> "Des Plaines"
        out = []
        for p in re.split(r"[;]|,(?!\s*(?:%s)\b)" % "|".join(STATE_CODES), v):
            p = p.strip()
            p = re.sub(r",\s*(?:%s)$" % "|".join(STATE_CODES), "", p).strip()       # "Greece, NY" -> "Greece"
            if p and fold(p) not in TOO_BIG: out.append(p)
        return out
    return []

def towns(sentence):
    """Names the rule pulls out after a serving word (only for sentences JEV or the rule decided are serving sentences)."""
    out = []
    for m in SERVE.finditer(sentence):
        rest = sentence[m.end():]
        lead = re.match(r"^((?:\s*[a-z][a-z'\-]*){0,5})\s*(?=[A-Z]|\d{5})", rest)
        if not lead: continue
        rest = rest[lead.end():]
        for piece in re.split(r",|;|\band\b|\bor\b|&", rest):
            p = piece.strip()
            while True:
                q = FILLER.sub("", p)
                if q == p: break
                p = q
            if not p: continue
            if not (p[0].isupper() or re.match(r"\d{5}(?![\d-])", p)): break
            n = NAME.match(p)
            if not n: break
            name, after = n.group(0), p[n.end():]
            if name in STATE_CODES: continue
            if REGION_WORDS.match(after): break
            out.append(name)
            if after.strip(): break
    return out

def serving_rule(sentence):
    """The rule's answer to 'is this a serving sentence': a serving word followed by at least one place name."""
    return bool(towns(sentence))

def _km(a, b, c, d):
    r = math.radians; x = math.sin(r(c - a) / 2) ** 2 + math.cos(r(a)) * math.cos(r(c)) * math.sin(r(d - b) / 2) ** 2
    return 6371 * 2 * math.asin(math.sqrt(x))

def confirm(name, state, lat, lng, search=None):
    """Google Places: a real town, county, state or ZIP, spelled the way Google spells it, within 200 km. -> (name or None, why)"""
    if search is None:
        url, code = os.environ.get("DHAP_SERVICE_URL", "").rstrip("/"), os.environ.get("DHAP_TEAM_CODE", "")
        if not (url and code): return None, "not checked (no team key service)"
        def search(q):
            body = {"textQuery": q, "pageSize": 1, "locationBias": {"circle": {"center": {"latitude": lat, "longitude": lng}, "radius": 50000}}}
            req = urllib.request.Request(url + "/places/v1/places:searchText", data=json.dumps(body).encode(),
                  headers={"X-DHAP-Code": code, "X-Goog-FieldMask": "places.displayName,places.types,places.location", "Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=20) as r: return (json.loads(r.read().decode()).get("places") or [None])[0]
    p = search(f"{name}, {state}")
    if not p: return None, "Google can't find it"
    if not set(p.get("types", [])) & OK_TYPES: return None, "not a town, county, state or ZIP"
    g = p["displayName"]["text"]
    if fold(g).replace(" county", "") != fold(name).replace(" county", ""): return None, f"Google spells it {g}"
    d = _km(lat, lng, p["location"]["latitude"], p["location"]["longitude"])
    if d > 200 and "administrative_area_level_1" not in p.get("types", []): return None, f"{d:.0f} km away, likely a different place"
    return g, "ok"

def score(code_places, page_places, code_on_page):
    """code_places: places in the dealership's areaServed (raw). page_places: confirmed places the pages say it serves.
    code_on_page: the code places that also appear anywhere in the readable page text. -> (points 0..2, details)"""
    universe = {}
    for t in list(code_places) + list(page_places): universe.setdefault(fold(t), t)
    good = {fold(t) for t in code_on_page} & {fold(t) for t in code_places}
    pts = round(2 * len(good) / len(universe), 3) if universe else 0.0
    return pts, {"in_both": sorted(universe[k] for k in good),
                 "code_not_page": sorted(universe[fold(t)] for t in code_places if fold(t) not in good),
                 "page_not_code": sorted(universe[fold(t)] for t in page_places if fold(t) not in {fold(c) for c in code_places})}

if __name__ == "__main__":
    if sys.argv[1:2] == ["towns"]: print(towns(sys.argv[2]))

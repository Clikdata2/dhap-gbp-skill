#!/usr/bin/env python3
"""DHAP GBP engine — NAP on every listing site that matters, from saved readings (rule 8, v15.2; audits dated on or after Oct 25 2026).

The sites are in engine/listing_sites.json, in two groups that are scored separately:
  network  the directories CLIKsearch syndicates to (its 60+ list), checked where a public lookup exists
  ai       the sites AI tools, search engines and car shoppers read (Bing, Apple Maps, Yelp, Facebook, the brand locator,
           CarGurus, Autotrader, KBB, Cars.com, DealerRater, Edmunds, TrueCar, CARFAX, BBB, Yellow Pages, Foursquare...),
           plus every site the AI answer check saw an AI tool cite for this dealer ("cited:<domain>")
A site in both groups counts in both. Each site's name, address and phone are saved word for word (with the page
address, time and a screenshot), and the engine decides whether it agrees with the website. Nobody types a yes/no.
  authority  the dealership's WEBSITE is the reference for every comparison (Travis, Oct 25 2026). Department to
           department: a listing's phone is compared with the website's number for the same department (dept: sales, the
           default, service or parts).
  phone    the digits match (country code ignored). Toll-free numbers (800, 833, 844, 855, 866, 877, 888) are not local:
           a toll-free number is never compared with a local one, either way, and never counts against the dealer
           ("not compared"). A department with no local number on the website is noted for the rep brief.
  local    the main rule: every business number should be LOCAL. A toll-free Sales, Service or Parts number on the
           website (header or schema) or on the Google listing is flagged (local_flags): toll-free on both; toll-free on
           the website while Google is local; local on the website while Google is toll-free. Flags are findings, not
           points. A listing site that shows a toll-free number is marked "toll-free (should be local)".
  address  the street number and street name match, ignoring abbreviations (Rd/Road), N/S/E/W and suite numbers;
           then the ZIP matches, or, when the site shows no ZIP, the city matches the website's or a postal name
           recorded in nap.postal_cities (for example Rochester for Greece, NY 14626)
  name     the names match after dropping punctuation, "the", "inc", "llc", the city and the state, or one contains the
           other without adding a department word (Parts, Service...); otherwise the run's JEV decision
           ("same_business", saved as name_same) is used; with neither, the rule's no stands and the site is listed for a person
  points   each group: 2 x (listings that agree) / (listings found); a group with no listing found earns 0. A site with
           no listing ("not_found") is reported, not scored; a site that refused even the signed-in Chrome is "blocked".
Usage: python3 directories.py evidence.json   -> each site's result and the group points (JSON)
"""
import json, pathlib, re, sys

START = "2026-10-25"
REGISTRY = json.loads((pathlib.Path(__file__).resolve().parent / "listing_sites.json").read_text())
SITES = {x["id"]: x for x in REGISTRY["sites"]}
CHECKED = [x["id"] for x in REGISTRY["sites"] if x["method"] in ("headless", "chrome", "site_search")]   # every run records each of these
def groups(site_id):
    if site_id.startswith("cited:"): return {"ai"}
    g = SITES[site_id]["group"]; return {"network", "ai"} if g == "both" else {g}
def label(site_id): return site_id[6:] if site_id.startswith("cited:") else SITES[site_id]["name"]
ABBR = {"street": "st", "road": "rd", "avenue": "ave", "av": "ave", "drive": "dr", "boulevard": "blvd", "highway": "hwy", "parkway": "pkwy",
        "lane": "ln", "court": "ct", "place": "pl", "circle": "cir", "turnpike": "tpke", "expressway": "expy", "freeway": "fwy", "route": "rte",
        "terrace": "ter", "trail": "trl", "square": "sq", "plaza": "plz", "center": "ctr", "mount": "mt", "saint": "st"}
DIRECTIONS = {"n", "s", "e", "w", "ne", "nw", "se", "sw", "north", "south", "east", "west", "northeast", "northwest", "southeast", "southwest"}
TYPES = set(ABBR.values())
UNIT = re.compile(r"(?:\b(?:ste|suite|unit|apt|bldg|building)\b\.?|#)\s*[\w-]*", re.I)
DROP = {"the", "inc", "llc", "co", "corp", "ltd", "of", "and", "&"}
DEPT_WORDS = {"parts", "service", "collision", "body", "express", "quick", "lube"}   # a name that adds one of these is a department, not the dealer

def applies(ev): return str(ev.get("audit_date", "")) >= START
TOLL_FREE = {"800", "833", "844", "855", "866", "877", "888"}
DEPTS = ("sales", "service", "parts")
def toll_free(p): d = digits(p); return len(d) == 10 and d[:3] in TOLL_FREE
def site_phone(site, dept):
    """The website's number for that department (the authority)."""
    return (site.get("phones") or {}).get(dept) or (site["phone"] if dept == "sales" else None)
def phone_check(shown, site, dept="sales"):
    """True / False, or None when it can't be measured: either side toll-free, or no local number on the website for that department."""
    ref = site_phone(site, dept)
    if not shown or not ref or toll_free(shown) or toll_free(ref): return None
    return digits(shown) == digits(ref)
def local_flags(ev):
    """The always-local rule (Travis, Oct 25 2026): toll-free numbers on the website or the Google listing, per department, Sales first."""
    N = ev.get("nap") or {}; site = N.get("site") or {}; g = N.get("google_phones") or {}; out = []
    for d in DEPTS:
        w, gp, D_ = site_phone(site, d) if site else None, g.get(d), d.title()
        if w and toll_free(w) and gp and toll_free(gp): out.append({"dept": d, "case": "both", "website": w, "google": gp, "text": f"The website and the Google listing both use a toll-free {D_} number ({w}). It should be a local number."})
        elif w and toll_free(w) and gp: out.append({"dept": d, "case": "website", "website": w, "google": gp, "text": f"Google shows a local {D_} number ({gp}), but the website shows only a toll-free one ({w}). The website should show the local number."})
        elif w and toll_free(w): out.append({"dept": d, "case": "website", "website": w, "google": gp, "text": f"The website shows only a toll-free {D_} number ({w}). It should be a local number."})
        elif gp and toll_free(gp): out.append({"dept": d, "case": "google", "website": w, "google": gp, "text": f"The website shows a local {D_} number ({w}), but the Google listing shows a toll-free one ({gp}). Google should show the local number." if w else f"The Google listing shows a toll-free {D_} number ({gp}). It should be a local number."})
    sch = [p for p in site.get("schema_phones") or [] if p]
    if sch and all(toll_free(p) for p in sch): out.append({"dept": "sales", "case": "schema", "website": ", ".join(sch), "google": None, "text": f"The website's business schema lists only toll-free numbers ({', '.join(sch)}). The main number in the schema should be local."})
    return out

def notes(ev):
    """Rep-brief notes: the always-local flags, then departments with no number on the website (Sales first)."""
    site = (ev.get("nap") or {}).get("site") or {}; out = [f["text"] for f in local_flags(ev)]
    for d in DEPTS:
        if site and not site_phone(site, d): out.append(f"The website shows no {d.title()} number, so {d.title()} listings are not phone-compared.")
    return out
def digits(t): return re.sub(r"\D", "", str(t or "")).removeprefix("1")[-10:]
def words(t): return re.sub(r"[^a-z0-9#& ]+", " ", str(t or "").casefold().replace("&amp;", "&")).split()

def street(addr):
    """('3800', 'ridge') from '3800 West Ridge Road, Greece, NY 14626': number + core name, abbreviations and directions dropped."""
    first = UNIT.sub(" ", str(addr or "").split(",")[0])
    w = [ABBR.get(x, x) for x in words(first)]
    if not w or not w[0][0].isdigit(): return None, None
    core = [x for x in w[1:] if x not in DIRECTIONS and x not in TYPES]
    return w[0], "".join(core)

def zip5(addr):
    m = re.findall(r"\b(\d{5})(?:-\d{4})?\b", str(addr or "").split(",", 1)[-1])
    return m[-1] if m else None

def city(addr):
    parts = [p.strip() for p in str(addr or "").split(",")]
    return "".join(words(parts[1])) if len(parts) >= 3 else None

def same_address(site, reading, postal):
    if street(site) != street(reading) or street(site)[0] is None: return False
    zs, zr = zip5(site), zip5(reading)
    if zs and zr: return zs == zr
    c = city(reading)
    return c is not None and (c == city(site) or c in {"".join(words(p)) for p in postal})

def same_name(site, reading, place=()):
    strip = lambda t: [x for x in words(t) if x not in DROP and x not in place]
    a, b = " ".join(strip(site)), " ".join(strip(reading))
    if not (a and b): return False
    if a == b: return True
    short, long_ = sorted((a, b), key=len)
    return f" {short} " in f" {long_} " and not (set(long_.split()) - set(short.split())) & DEPT_WORDS

def check(ev):
    """Problems with nap.site / nap.directories (rule 8). Empty list = OK, or the audit predates rule 8."""
    if not applies(ev): return []
    N = ev.get("nap") or {}; P = []
    st = N.get("site")
    if not (isinstance(st, dict) and all(str(st.get(k, "")).strip() for k in ("name", "address", "phone"))):
        P.append("nap.site: the website's name, address and phone, word for word (rule 8)")
    elif not (isinstance(st.get("phones"), dict) and set(st["phones"]) == set(DEPTS) and all(v is None or str(v).strip() for v in st["phones"].values())):
        P.append("nap.site.phones: the website's sales, service and parts numbers word for word (null when the website shows none) — the website is the authority")
    if isinstance(st, dict) and not isinstance(st.get("schema_phones"), list): P.append("nap.site.schema_phones: every telephone in the website's raw business schema (empty list when none) — the always-local check")
    gp = N.get("google_phones")
    if not (isinstance(gp, dict) and set(gp) == set(DEPTS) and all(v is None or str(v).strip() for v in gp.values())):
        P.append("nap.google_phones: the phone on the Google listing for sales (main listing), service and parts, word for word (null when there is no listing) — the always-local check")
    if "directories_agree" in N and "_directory_results" not in N: P.append("nap.directories_agree: not typed from v15.2 — the engine decides it from nap.directories (rule 8)")
    D = N.get("directories")
    if not isinstance(D, list): return P + ["nap.directories: one saved reading per listing site in engine/listing_sites.json (rule 8)"]
    got = [d.get("directory") for d in D if isinstance(d, dict)]
    for k in CHECKED:
        if k not in got: P.append(f"nap.directories: {k} ({SITES[k]['name']}) not recorded — found, not_found or blocked")
    for k in got:
        if got.count(k) > 1: P.append(f"nap.directories: {k} recorded {got.count(k)} times"); break
    for d in D:
        if not isinstance(d, dict): P.append("nap.directories: each reading must be an object"); continue
        k = str(d.get("directory")); p = f"nap.directories[{k}]"
        if d.get("draft"): P.append(p + ": still a draft from listing_scan.py — check it against its screenshot, correct it, then remove \"draft\"")
        if k not in SITES and not re.match(r"^cited:[a-z0-9.-]+\.[a-z]{2,}$", k): P.append(p + ": unknown site (use an id from engine/listing_sites.json, or cited:<domain> for a site an AI tool cited)"); continue
        if not re.match(r"^\d{4}-\d{2}-\d{2}", str(d.get("when", ""))): P.append(p + ".when: YYYY-MM-DD (and time) it was read")
        stt = d.get("status")
        if stt in ("not_found", "blocked"):
            if not str(d.get("searched" if stt == "not_found" else "reason", "")).strip(): P.append(p + (".searched: what was searched to find no listing" if stt == "not_found" else ".reason: what blocked it, even in the signed-in Chrome"))
            continue
        if stt != "found": P.append(p + ".status: found | not_found | blocked"); continue
        for f in ("name", "address", "phone", "url", "proof"):
            if not str(d.get(f, "")).strip(): P.append(f"{p}.{f}: {'the screenshot file' if f == 'proof' else 'the page that was read' if f == 'url' else 'word for word as the site shows it'}")
        if d.get("dept", "sales") not in DEPTS: P.append(p + ".dept: sales (default), service or parts — which website number this listing is compared with")
        if "name_same" in d and not isinstance(d["name_same"], bool): P.append(p + ".name_same: true/false from the JEV decision (same_business)")
    pc = N.get("postal_cities", [])
    if not (isinstance(pc, list) and all(isinstance(x, str) for x in pc)): P.append("nap.postal_cities: list of postal city names for the dealer's address (empty when none)")
    return P

def results(ev):
    """Each site: found or not, agrees or not, and why."""
    N = ev["nap"]; st = N["site"]; postal = N.get("postal_cities", [])
    place = set(words(city(st["address"]) or "")) | {x for x in words(str(st["address"]).split(",")[-1]) if not x.isdigit()}
    out = []
    for d in N["directories"]:
        k = d["directory"]; r = {"directory": k, "label": label(k), "groups": sorted(groups(k)), "status": d["status"]}
        if d["status"] != "found":
            r.update(agree=None, why="no listing found" if d["status"] == "not_found" else "blocked: " + d.get("reason", "")); out.append(r); continue
        nm_rule = same_name(st["name"], d["name"], place)
        nm = nm_rule or d.get("name_same") is True
        ad = same_address(st["address"], d["address"], postal); ph = phone_check(d["phone"], st, d.get("dept", "sales"))
        why = [w for w, ok in (("name", nm), ("address", ad), ("phone", ph is not False)) if not ok]
        r.update(agree=nm and ad and ph is not False, why="matches" if not why else "differs: " + ", ".join(why), shows={x: d[x] for x in ("name", "address", "phone")}, url=d["url"],
                 dept=d.get("dept", "sales"), phone_compared=ph is not None)
        if ph is None: r["why"] += " (phone not compared: toll-free or no local website number)"
        if toll_free(d["phone"]): r["toll_free"] = True
        if not nm_rule and "name_same" not in d: r["review"] = f"name {d['name']!r} vs {st['name']!r}: send to JEV (same_business) or a person"
        out.append(r)
    return out

def points(R):
    """{'network': (points out of 2, agree, found), 'ai': (...)}"""
    out = {}
    for g in ("network", "ai"):
        found = [r for r in R if g in r["groups"] and r["status"] == "found"]; ok = sum(1 for r in found if r["agree"])
        out[g] = (2 * ok / len(found) if found else 0.0, ok, len(found))
    return out

def resolve(ev):
    """Fill nap.directories_agree (the order the rubric uses) from the saved readings. Before rule 8: leave it as typed."""
    N = ev.get("nap")
    if not applies(ev) or not isinstance(N, dict) or check(ev): return ev
    R = results(ev); N["_directory_results"] = R; N["_directory_points"] = points(R)
    N["directories_agree"] = [r["agree"] for r in R if r["status"] == "found"]   # kept for older readers; v15.2 scores _directory_points
    return ev

if __name__ == "__main__":
    if len(sys.argv) != 2: print(__doc__); sys.exit(2)
    ev = json.load(open(sys.argv[1])); p = check(ev)
    if p: sys.exit("DIRECTORIES INCOMPLETE:\n  - " + "\n  - ".join(p))
    R = results(ev); print(json.dumps({"sites": R, "points": points(R), "local_flags": local_flags(ev), "rep_brief_notes": notes(ev)}, indent=2, ensure_ascii=False))

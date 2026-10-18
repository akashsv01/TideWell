"""Nearby maternity care. Free public data, no API keys.

- Doctors, midwives and hospitals: the CMS NPI Registry (npiregistry.cms.hhs.gov/api, v2.1), the
  official US list of licensed providers. Searched by taxonomy ("Obstetrics & Gynecology", "Midwife",
  "General Acute Care Hospital") and ZIP prefix; each result's practice ("LOCATION") address and phone.
- Distances: provider addresses geocoded with the US Census geocoder
  (geocoding.geo.census.gov/geocoder/locations/onelineaddress, benchmark Public_AR_Current).
- Patient location: browser coordinates or a ZIP code (Nominatim/OpenStreetMap geocoding; reverse
  geocoding turns coordinates into the ZIP the NPI search needs).
- OpenStreetMap Overpass adds hospitals tagged emergency=yes when it answers quickly; it is often
  slow or down, so it gets a short timeout and the NPI results stand on their own.
Results are cached (24 h for searches, longer for geocodes) and sorted by distance. Listings can be out
of date, so the UI always says "call ahead".
"""
import json
import logging
import math
import re
import time
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeout
from typing import Optional

log = logging.getLogger("tidewell.care")

UA = "Tidewell/0.1 (hackathon postpartum care companion; contact: team@tidewell.example)"
NPI = "https://npiregistry.cms.hhs.gov/api/"
CENSUS = "https://geocoding.geo.census.gov/geocoder/locations/onelineaddress"
OVERPASS = "https://overpass-api.de/api/interpreter"
NOMINATIM = "https://nominatim.openstreetmap.org"
_cache: dict[tuple, tuple[float, object]] = {}
TTL = 24 * 3600
GEO_TTL = 30 * 24 * 3600
MAX_KM = 40
_pool = ThreadPoolExecutor(max_workers=8)

# NPI taxonomy search term -> our kind
NPI_SEARCHES = {"obgyn": "Obstetrics & Gynecology", "midwife": "Midwife", "hospital": "General Acute Care Hospital"}
# The provider's primary taxonomy must match too (the search also matches secondary taxonomies).
PRIMARY_MATCH = {"obgyn": ("obstetric", "gynecolog"), "midwife": ("midwife",), "hospital": ("hospital",)}
_HOSPITAL_NAME = re.compile(r"hospital|hosptial|medical|health|center|centre", re.I)
OSM_WAIT_S = 4  # how long a lookup waits for Overpass before going ahead with NPI alone
KIND_LABEL = {"emergency": "Hospital with emergency room", "hospital": "Hospital",
              "obgyn": "OB-GYN", "midwife": "Midwife or birth centre"}
_NOT_MATERNITY = ("rehab", "veteran", " va ", "psychiatr", "behavioral", "children", "pediatric",
                  "paediatric", "hospice", "nursing home", "long term", "long-term", "specialized care",
                  "billing", "anesthesia", "radiology", "pathology", "laborator", "respiratory", "attn",
                  "business office", "surgery center", "dialysis")


def _get_json(url: str, data: Optional[bytes] = None, timeout: float = 20):
    req = urllib.request.Request(url, data=data, headers={"User-Agent": UA, "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())


def _cached(key: tuple, fn, ttl: float = TTL):
    hit = _cache.get(key)
    if hit and time.time() - hit[0] < ttl:
        return hit[1]
    val = fn()
    _cache[key] = (time.time(), val)
    return val


def _km(lat1, lon1, lat2, lon2) -> float:
    p = math.pi / 180
    a = 0.5 - math.cos((lat2 - lat1) * p) / 2 + math.cos(lat1 * p) * math.cos(lat2 * p) * (1 - math.cos((lon2 - lon1) * p)) / 2
    return 12742 * math.asin(math.sqrt(a))


def _title(s: str) -> str:
    """NPI data is all caps. Title-case it, keeping abbreviations (LLC, CNM, NW) and unit numbers."""
    s = re.sub(r",(?=\S)", ", ", s or "")
    small = {"of", "and", "the", "at", "for", "in"}
    out = []
    for i, w in enumerate(s.split()):
        core = re.sub(r"[^A-Za-z]", "", w)
        if any(ch.isdigit() for ch in w) or (core and not re.search(r"[AEIOUYaeiouy]", core)):
            out.append(w.upper())  # 7TH, U8A, LLC, CNM, NW, MD
        elif i and w.lower() in small:
            out.append(w.lower())
        else:
            out.append("-".join(x.capitalize() for x in w.split("-")))
    return " ".join(out)


def _not_maternity(name: str) -> bool:
    return any(w in f" {name.lower()} " for w in _NOT_MATERNITY)


# --- Patient location -------------------------------------------------------------------------------
def geocode(postal_code: str, country: str = "us") -> Optional[tuple[float, float, str]]:
    """(lat, lon, display name) for a postal code, or None."""
    q = urllib.parse.urlencode({"postalcode": postal_code, "country": country, "format": "json", "limit": 1})

    def run():
        res = _get_json(f"{NOMINATIM}/search?{q}")
        return (float(res[0]["lat"]), float(res[0]["lon"]), res[0].get("display_name", postal_code)) if res else None

    try:
        return _cached(("geo", postal_code.strip().lower(), country), run, GEO_TTL)
    except Exception as e:  # noqa: BLE001
        log.warning("geocode failed: %s", e)
        return None


def zip_for(lat: float, lon: float) -> Optional[str]:
    """US ZIP code at a point (Nominatim reverse geocoding), or None."""
    q = urllib.parse.urlencode({"lat": lat, "lon": lon, "format": "json", "zoom": 16, "addressdetails": 1})

    def run():
        pc = (_get_json(f"{NOMINATIM}/reverse?{q}", timeout=10).get("address") or {}).get("postcode", "")
        return pc[:5] if pc[:5].isdigit() else None

    try:
        return _cached(("rev", round(lat, 3), round(lon, 3)), run, GEO_TTL)
    except Exception as e:  # noqa: BLE001
        log.warning("reverse geocode failed: %s", e)
        return None


# --- NPI Registry ----------------------------------------------------------------------------------
def _npi(kind: str, zip_prefix: str) -> list[dict]:
    params = {"version": "2.1", "taxonomy_description": NPI_SEARCHES[kind], "postal_code": f"{zip_prefix}*", "limit": 200}
    if kind == "hospital":
        params["enumeration_type"] = "NPI-2"  # organisations only
    q = urllib.parse.urlencode(params)
    return _cached(("npi", kind, zip_prefix), lambda: _get_json(f"{NPI}?{q}", timeout=12).get("results", []))


def _npi_place(r: dict, kind: str) -> Optional[dict]:
    loc = next((a for a in r.get("addresses", []) if a.get("address_purpose") == "LOCATION"), None)
    b = r.get("basic", {})
    if not loc or loc.get("country_code") != "US" or b.get("status", "A") != "A":
        return None
    primary = next((t.get("desc", "") for t in r.get("taxonomies", []) if t.get("primary")), "").lower()
    if not any(w in primary for w in PRIMARY_MATCH[kind]):
        return None
    if r.get("enumeration_type") == "NPI-2":
        name = _title(b.get("organization_name", ""))
    else:
        name = " ".join(x for x in [_title(b.get("first_name", "")), _title(b.get("last_name", ""))] if x)
        cred = (b.get("credential") or "").replace(".", "").strip().upper()
        name = f"Dr. {name}" if cred.upper().startswith(("MD", "DO")) else name
        name = f"{name}, {cred}" if cred else name
    if not name or _not_maternity(name):
        return None
    if kind == "hospital" and not _HOSPITAL_NAME.search(name):
        return None  # skips practices and universities registered under a hospital taxonomy
    zip5 = (loc.get("postal_code") or "")[:5]
    if re.search(r"attn|business office|billing", (loc.get("address_1", "") + " " + loc.get("address_2", "")), re.I):
        return None  # an admin office, not where patients go
    street = _title(" ".join(x for x in [loc.get("address_1"), loc.get("address_2")] if x))
    return {
        "name": name, "kind": kind, "kind_label": KIND_LABEL[kind], "source": "npi", "npi": r.get("number"),
        "address": f"{street}, {_title(loc.get('city', ''))}, {loc.get('state', '')} {zip5}".strip(", "),
        "_geo_address": f"{loc.get('address_1', '')}, {loc.get('city', '')}, {loc.get('state', '')} {zip5}",
        "_zip": zip5, "_org": r.get("enumeration_type") == "NPI-2", "phone": loc.get("telephone_number"), "website": None,
    }


def _census_point(address: str) -> Optional[tuple[float, float]]:
    q = urllib.parse.urlencode({"address": address, "benchmark": "Public_AR_Current", "format": "json"})

    def run():
        m = _get_json(f"{CENSUS}?{q}", timeout=10)["result"]["addressMatches"]
        return (m[0]["coordinates"]["y"], m[0]["coordinates"]["x"]) if m else None

    try:
        return _cached(("census", address.lower()), run, GEO_TTL)
    except Exception as e:  # noqa: BLE001
        log.info("census geocode failed for one address: %s", e)
        return None


def _npi_nearby(lat: float, lon: float, zip5: str, per_kind: int = 14) -> list[dict]:
    """NPI providers near a ZIP: search the ZIP's area (4- then 3-digit prefix), pick the candidates
    whose ZIP is closest, geocode those, and keep the ones within MAX_KM."""
    jobs = {(k, p): _pool.submit(_npi, k, p) for k in NPI_SEARCHES for p in (zip5[:4], zip5[:3])}
    candidates: list[dict] = []
    seen: set = set()  # one listing per practice address: a clinic, not each clinician in it
    for kind in NPI_SEARCHES:
        rows = []
        for prefix in (zip5[:4], zip5[:3]):
            try:
                results = jobs[(kind, prefix)].result()
            except Exception as e:  # noqa: BLE001
                log.warning("NPI search failed (%s %s): %s", kind, prefix, e)
                continue
            # organisations first, so a practice is listed by its own name rather than one clinician's
            for p in sorted(filter(None, (_npi_place(r, kind) for r in results)), key=lambda p: not p["_org"]):
                key = " ".join(p["_geo_address"].lower().split()[:2]) + p["_zip"]  # house number + street
                if key not in seen:
                    seen.add(key)
                    rows.append(p)
        rows.sort(key=lambda p: (p["_zip"] != zip5, abs(int(p["_zip"] or 0) - int(zip5))))
        candidates += rows[:per_kind]
    points = list(_pool.map(lambda p: _census_point(p["_geo_address"]), candidates))
    out = []
    for p, pt in zip(candidates, points):
        if not pt:
            continue
        d = _km(lat, lon, *pt)
        if d > MAX_KM:
            continue
        p = {k: v for k, v in p.items() if not k.startswith("_")}
        out.append({**p, "lat": pt[0], "lon": pt[1], "distance_km": round(d, 1),
                    "directions_url": f"https://www.google.com/maps/dir/?api=1&destination={pt[0]},{pt[1]}"})
    return out


# --- OpenStreetMap (secondary: emergency-room tags) -------------------------------------------------
def _osm_hospitals(lat: float, lon: float, radius_km: float) -> list[dict]:
    r = int(radius_km * 1000)
    query = f"""[out:json][timeout:8];
(
  nwr(around:{r},{lat},{lon})["amenity"="hospital"];
  nwr(around:{r},{lat},{lon})["healthcare"~"^(midwife|birthing_center|birthing_centre)$"];
);
out center tags 40;"""

    def run():
        data = _get_json(OVERPASS, data=urllib.parse.urlencode({"data": query}).encode(), timeout=9)
        out = []
        for el in data.get("elements", []):
            t = el.get("tags", {})
            name = t.get("name")
            plat = el.get("lat") or el.get("center", {}).get("lat")
            plon = el.get("lon") or el.get("center", {}).get("lon")
            if not name or plat is None or plon is None or _not_maternity(name):
                continue
            kind = ("midwife" if t.get("healthcare") in ("midwife", "birthing_center", "birthing_centre")
                    else "emergency" if t.get("emergency") == "yes" else "hospital")
            addr = " ".join(x for x in [t.get("addr:housenumber"), t.get("addr:street")] if x)
            out.append({
                "name": name, "kind": kind, "kind_label": KIND_LABEL[kind], "source": "osm",
                "address": ", ".join(x for x in [addr, t.get("addr:city")] if x) or None,
                "phone": t.get("phone") or t.get("contact:phone"), "website": t.get("website") or t.get("contact:website"),
                "lat": plat, "lon": plon, "distance_km": round(_km(lat, lon, plat, plon), 1),
                "directions_url": f"https://www.google.com/maps/dir/?api=1&destination={plat},{plon}",
            })
        return out

    try:
        return _cached(("osm", round(lat, 2), round(lon, 2), radius_km), run)
    except Exception as e:  # noqa: BLE001
        log.info("overpass unavailable (%s); using NPI results only", e)
        return []


def _merge(npi: list[dict], osm: list[dict]) -> list[dict]:
    """NPI first; OSM adds places NPI lacks and marks NPI hospitals that OSM tags as having an ER."""
    out = list(npi)
    for o in osm:
        twin = next((p for p in out if p["kind"] in ("hospital", "emergency") and _km(p["lat"], p["lon"], o["lat"], o["lon"]) < 0.4), None)
        if twin:
            if o["kind"] == "emergency":
                twin.update(kind="emergency", kind_label=KIND_LABEL["emergency"])
            twin["website"] = twin.get("website") or o.get("website")
        elif not any(o["name"].lower() == p["name"].lower() for p in out):
            out.append(o)
    return out


def nearby(lat: float, lon: float, postal_code: Optional[str] = None, radius_km: float = 25,
           limit: int = 15) -> list[dict]:
    """Closest maternity care, nearest first: a mix of OB-GYNs, midwives and hospitals. [] on failure."""
    zip5 = (postal_code or "").strip()[:5]
    if not zip5.isdigit():
        zip5 = zip_for(lat, lon) or ""

    def run():
        osm = _pool.submit(_osm_hospitals, lat, lon, radius_km)
        try:
            npi = _npi_nearby(lat, lon, zip5) if zip5 else []
        except Exception as e:  # noqa: BLE001
            log.warning("NPI lookup failed: %s", e)
            npi = []
        try:
            extra = osm.result(timeout=OSM_WAIT_S)
        except FutureTimeout:
            extra = []  # still finishing in the background; its own cache serves the next lookup
        places = _merge(npi, extra)
        places.sort(key=lambda x: x["distance_km"])
        if not places:
            raise RuntimeError("no care sources answered")  # don't cache an empty answer
        return places

    try:
        places = _cached(("near", round(lat, 2), round(lon, 2), zip5, radius_km), run)
    except Exception as e:  # noqa: BLE001
        log.warning("nearby care lookup failed: %s", e)
        return []
    # Keep a useful mix in the top results: the 5 nearest of each kind, then by distance.
    by_kind: dict[str, int] = {}
    picked = []
    for p in places:
        group = "hospital" if p["kind"] == "emergency" else p["kind"]
        if by_kind.get(group, 0) < 5:
            by_kind[group] = by_kind.get(group, 0) + 1
            picked.append(p)
    return picked[:limit]


def best_for_visit(places: list[dict]) -> list[dict]:
    """Where to book a postpartum check: OB-GYN/midwife first, then hospitals; 3 options."""
    rank = {"obgyn": 0, "midwife": 1, "hospital": 2, "emergency": 3}
    return sorted(places, key=lambda p: (rank[p["kind"]], p["distance_km"]))[:3]


def nearest_er(places: list[dict]) -> Optional[dict]:
    ers = [p for p in places if p["kind"] == "emergency"] or [p for p in places if p["kind"] == "hospital"]
    return ers[0] if ers else None

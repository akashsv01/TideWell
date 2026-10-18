"""Nearby maternity care from OpenStreetMap (free, no API key).

- Geocoding a ZIP/postal code: Nominatim (OSM). Browser geolocation is used when the patient allows it.
- Places: Overpass API, within a radius: hospitals (ER if tagged emergency=yes), OB-GYN clinics/doctors
  (healthcare:speciality gynaecology/obstetrics), midwives and birth centres.
Results are cached for 24 h per rounded location to respect the public servers' usage policies, and
sorted by distance. Data is community-maintained: always "call ahead" (shown in the UI).
"""
import json
import logging
import math
import time
import urllib.parse
import urllib.request
from typing import Optional

log = logging.getLogger("tidewell.care")

UA = "Tidewell/0.1 (hackathon postpartum care companion; contact: team@tidewell.example)"
OVERPASS = "https://overpass-api.de/api/interpreter"
NOMINATIM = "https://nominatim.openstreetmap.org/search"
_cache: dict[tuple, tuple[float, object]] = {}
TTL = 24 * 3600


def _get_json(url: str, data: Optional[bytes] = None, timeout: int = 25):
    req = urllib.request.Request(url, data=data, headers={"User-Agent": UA, "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())


def _cached(key: tuple, fn):
    hit = _cache.get(key)
    if hit and time.time() - hit[0] < TTL:
        return hit[1]
    val = fn()
    _cache[key] = (time.time(), val)
    return val


def geocode(postal_code: str, country: str = "us") -> Optional[tuple[float, float, str]]:
    """(lat, lon, display name) for a postal code, or None."""
    q = urllib.parse.urlencode({"postalcode": postal_code, "country": country, "format": "json", "limit": 1})

    def run():
        res = _get_json(f"{NOMINATIM}?{q}")
        return (float(res[0]["lat"]), float(res[0]["lon"]), res[0].get("display_name", postal_code)) if res else None

    try:
        return _cached(("geo", postal_code.strip().lower(), country), run)
    except Exception as e:  # noqa: BLE001
        log.warning("geocode failed: %s", e)
        return None


def _km(lat1, lon1, lat2, lon2) -> float:
    p = math.pi / 180
    a = 0.5 - math.cos((lat2 - lat1) * p) / 2 + math.cos(lat1 * p) * math.cos(lat2 * p) * (1 - math.cos((lon2 - lon1) * p)) / 2
    return 12742 * math.asin(math.sqrt(a))


_NOT_MATERNITY = ("rehab", "veteran", " va ", "psychiatr", "behavioral", "children", "pediatric",
                  "paediatric", "hospice", "nursing home", "long term", "long-term", "specialized care")


def _kind(t: dict) -> Optional[str]:
    if any(w in f" {(t.get('name') or '').lower()} " for w in _NOT_MATERNITY):
        return None
    spec = (t.get("healthcare:speciality") or "").lower()
    if t.get("amenity") == "hospital" or t.get("healthcare") == "hospital":
        return "emergency" if t.get("emergency") == "yes" else "hospital"
    if "obstetric" in spec or "gynaecolog" in spec or "gynecolog" in spec:
        return "obgyn"
    if t.get("healthcare") in ("midwife", "birthing_center", "birthing_centre"):
        return "midwife"
    return None


KIND_LABEL = {"emergency": "Hospital with emergency room", "hospital": "Hospital",
              "obgyn": "OB-GYN clinic", "midwife": "Midwife or birth centre"}


def nearby(lat: float, lon: float, radius_km: float = 25, limit: int = 12) -> list[dict]:
    """Closest maternity-relevant places, nearest first. [] if the lookup fails."""
    r = int(radius_km * 1000)
    query = f"""[out:json][timeout:20];
(
  nwr(around:{r},{lat},{lon})["amenity"="hospital"];
  nwr(around:{r},{lat},{lon})["healthcare"="hospital"];
  nwr(around:{r},{lat},{lon})["healthcare"~"^(midwife|birthing_center|birthing_centre)$"];
  nwr(around:{r},{lat},{lon})["healthcare:speciality"~"gynaecology|obstetrics|gynecology",i];
);
out center tags 80;"""

    def run():
        data = _get_json(OVERPASS, data=urllib.parse.urlencode({"data": query}).encode(), timeout=30)
        out, seen = [], set()
        for el in data.get("elements", []):
            t = el.get("tags", {})
            kind, name = _kind(t), t.get("name")
            if not kind or not name or name in seen:
                continue
            seen.add(name)
            plat = el.get("lat") or el.get("center", {}).get("lat")
            plon = el.get("lon") or el.get("center", {}).get("lon")
            if plat is None or plon is None:
                continue
            addr = " ".join(x for x in [t.get("addr:housenumber"), t.get("addr:street")] if x)
            city = t.get("addr:city")
            out.append({
                "name": name, "kind": kind, "kind_label": KIND_LABEL[kind],
                "address": ", ".join(x for x in [addr, city] if x) or None,
                "phone": t.get("phone") or t.get("contact:phone"),
                "website": t.get("website") or t.get("contact:website"),
                "lat": plat, "lon": plon, "distance_km": round(_km(lat, lon, plat, plon), 1),
                "directions_url": f"https://www.google.com/maps/dir/?api=1&destination={plat},{plon}",
            })
        out.sort(key=lambda x: x["distance_km"])
        return out

    try:
        return _cached(("near", round(lat, 2), round(lon, 2), radius_km), run)[:limit]
    except Exception as e:  # noqa: BLE001
        log.warning("overpass failed: %s", e)
        return []


def best_for_visit(places: list[dict]) -> list[dict]:
    """Where to book a postpartum check: OB-GYN/midwife first, then hospitals; 3 options."""
    rank = {"obgyn": 0, "midwife": 1, "hospital": 2, "emergency": 3}
    return sorted(places, key=lambda p: (rank[p["kind"]], p["distance_km"]))[:3]


def nearest_er(places: list[dict]) -> Optional[dict]:
    ers = [p for p in places if p["kind"] == "emergency"] or [p for p in places if p["kind"] == "hospital"]
    return ers[0] if ers else None

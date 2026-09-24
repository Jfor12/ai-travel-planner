"""
Checks the places a guide mentions against OpenStreetMap (Nominatim), so map
pins come from a geocoder instead of coordinates the language model guessed.

Nominatim's usage policy: at most one request per second, an identifying
User-Agent, and cache results. Guides are cached, so this runs rarely.
"""

import json
import math
import os
import threading
import time
from urllib.parse import urlencode
from urllib.request import Request, urlopen

GEOCODER_URL = os.getenv("GEOCODER_URL", "https://nominatim.openstreetmap.org/search")
USER_AGENT = "ai-travel-planner/1.1 (+https://github.com/Jfor12/ai-travel-planner)"
MAX_DISTANCE_KM = 60  # a place further than this from the destination is a wrong match

_lock = threading.Lock()
_last_request = 0.0
_cache = {}


class GeocoderUnavailable(Exception):
    pass


def _fetch(query):
    """One Nominatim lookup, spaced at least a second from the previous one."""
    global _last_request
    with _lock:
        wait = 1.0 - (time.monotonic() - _last_request)
        if wait > 0:
            time.sleep(wait)
        url = f"{GEOCODER_URL}?{urlencode({'q': query, 'format': 'jsonv2', 'limit': 1})}"
        request = Request(url, headers={"User-Agent": USER_AGENT, "Accept-Language": "en"})
        try:
            with urlopen(request, timeout=8) as response:
                return json.load(response)
        except Exception as error:
            raise GeocoderUnavailable(str(error)) from error
        finally:
            _last_request = time.monotonic()


def geocode(query):
    """(lat, lon) for a place, None if the geocoder has no match.
    Raises GeocoderUnavailable if the service can't be reached."""
    key = query.strip().lower()
    if key not in _cache:
        results = _fetch(query)
        _cache[key] = (float(results[0]["lat"]), float(results[0]["lon"])) if results else None
    return _cache[key]


def distance_km(a, b):
    lat1, lon1, lat2, lon2 = map(math.radians, (*a, *b))
    h = math.sin((lat2 - lat1) / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin((lon2 - lon1) / 2) ** 2
    return 6371 * 2 * math.asin(math.sqrt(h))


def verify_locations(destination, locations):
    """Replace model-guessed coordinates with geocoded ones.

    Places the geocoder can't find, or finds far from the destination, are
    dropped: no pin is better than a wrong one. If the geocoder is down, the
    original coordinates are kept so the map still works.
    """
    if not locations:
        return locations
    try:
        centre = geocode(destination)
        verified = []
        for loc in locations:
            point = geocode(f"{loc['name']}, {destination}")
            if point and (centre is None or distance_km(centre, point) <= MAX_DISTANCE_KM):
                verified.append({"name": loc["name"], "lat": round(point[0], 5), "lon": round(point[1], 5)})
        return verified
    except GeocoderUnavailable:
        return locations

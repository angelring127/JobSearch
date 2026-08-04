import logging
import os
from typing import Optional, Tuple

import httpx

logger = logging.getLogger(__name__)


def geocode_location(
    location_text: Optional[str],
    region_hint: Optional[str] = None,
    allow_region_fallback: bool = True,
) -> Tuple[Optional[float], Optional[float], float]:
    if not location_text or not location_text.strip():
        if region_hint and allow_region_fallback:
            return get_region_center(region_hint)
        return None, None, 0.3

    query = location_text.strip()
    if region_hint and region_hint.lower() not in query.lower():
        query = "%s, %s, Canada" % (query, region_hint)
    elif not any(province in query for province in ["BC", "AB", "ON", "QC", "MB", "SK", "NB", "NS", "PE", "NL", "YT", "NT", "NU", "Canada"]):
        query = "%s, Canada" % query

    nominatim_url = os.getenv("NOMINATIM_URL", "https://nominatim.openstreetmap.org")
    params = {
        "q": query,
        "format": "json",
        "limit": 1,
        "addressdetails": 1,
        "countrycodes": "ca",
        "accept-language": "en",
    }
    headers = {"User-Agent": "JobMap/1.0 (contact@jobmap.ca)"}

    try:
        response = httpx.get("%s/search" % nominatim_url, params=params, headers=headers, timeout=10.0)
        if response.status_code == 200:
            data = response.json()
            if data:
                result = data[0]
                importance = result.get("importance", 0)
                if importance > 0.7:
                    confidence = 0.9
                elif importance > 0.5:
                    confidence = 0.8
                elif importance > 0.3:
                    confidence = 0.7
                else:
                    confidence = 0.6
                return float(result["lat"]), float(result["lon"]), confidence

        logger.warning("Geocoding returned no results for '%s'", location_text)
    except Exception as exc:
        logger.warning("Geocoding failed for '%s': %s", location_text, exc)

    if region_hint and allow_region_fallback:
        return get_region_center(region_hint)
    return None, None, 0.3


def get_region_center(region_hint: str) -> Tuple[Optional[float], Optional[float], float]:
    region_centers = {
        "Vancouver": (49.2827, -123.1207),
        "Victoria": (48.4284, -123.3656),
        "Toronto": (43.6532, -79.3832),
        "Whistler": (50.1163, -122.9574),
        "Burnaby": (49.2488, -122.9805),
        "Surrey": (49.1913, -122.8490),
        "Richmond": (49.1666, -123.1364),
        "Kelowna": (49.8880, -119.4960),
        "Banff": (51.1784, -115.5708),
        "Canmore": (51.0888, -115.3581),
        "Calgary": (51.0447, -114.0719),
        "Edmonton": (53.5461, -113.4938),
        "Vernon": (50.2670, -119.2724),
        "Nelson": (49.4995, -117.2855),
        "Revelstoke": (50.9971, -118.1953),
        "Jasper": (52.8737, -118.0814),
        "Halifax": (44.6488, -63.5752),
        "Montreal": (45.5017, -73.5673),
        "Winnipeg": (49.8951, -97.1384),
        "Yellowknife": (62.4540, -114.3718),
    }

    region_hint_lower = region_hint.lower()
    for city, center in region_centers.items():
        if city.lower() in region_hint_lower:
            lat, lng = center
            return lat, lng, 0.5

    logger.warning("Unknown region_hint '%s'; no fallback coordinates available", region_hint)
    return None, None, 0.3

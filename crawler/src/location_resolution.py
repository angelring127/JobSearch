import re
from typing import Any, Dict, Optional, Tuple

from geocoding import geocode_location


PRECISE_LOCATION_KINDS = {"street_address", "business_or_landmark"}

# These addresses were verified against the named business's public location
# page (or a current public business listing where no official location page is
# available). They are deliberately narrow aliases, not fuzzy employer guesses.
VERIFIED_BUSINESS_LOCATIONS = (
    {
        "aliases": ("k well integrative wellness clinic",),
        "required_any": ("downtown", "다운타운"),
        "address": "889 W Pender St, Vancouver, BC",
        "region_hint": "Vancouver",
        "evidence_url": "https://k-acuwellness.com/about/downtown",
    },
    {
        "aliases": ("akihana sushi",),
        "address": "1205 Davie Street, Vancouver, BC V6E 1N4",
        "region_hint": "Vancouver",
        "evidence_url": "https://www.ubereats.com/ca/store/akihana-sushi-1205-davie-street/yoUGF_g5VpeMa1W2nU776w",
    },
    {
        "aliases": ("vanmak", "vanmak bistro", "밴막"),
        "required_any": ("downtown", "다운타운", "stadium chinatown"),
        "address": "82 Keefer Pl, Vancouver, BC V6B 6C1",
        "region_hint": "Vancouver",
        "evidence_url": "https://www.vanmak.ca/",
    },
    {
        "aliases": ("ninnin ramen", "nin nin ramen"),
        "address": "660 Abbott Street, Vancouver, BC V6B 0E1",
        "region_hint": "Vancouver",
        "evidence_url": "https://www.ubereats.com/ca/store/nin-nin-ramen-house-660-abbott-st/qVeBDvhxUxS5XpawWupT2A",
    },
)


def apply_verified_business_location(job_data: Dict[str, Any]) -> Dict[str, Any]:
    resolved = dict(job_data)
    haystack = _normalized_business_text(
        "%s %s" % (resolved.get("title") or "", resolved.get("location_text") or "")
    )
    for location in VERIFIED_BUSINESS_LOCATIONS:
        if not any(_contains_normalized_phrase(haystack, alias) for alias in location["aliases"]):
            continue
        required_any = location.get("required_any") or ()
        if required_any and not any(
            _contains_normalized_phrase(haystack, context) for context in required_any
        ):
            continue
        resolved["location_text"] = location["address"]
        resolved["region_hint"] = location["region_hint"]
        resolved["location_kind"] = "street_address"
        resolved["location_evidence_url"] = location["evidence_url"]
        return resolved
    return resolved


def resolve_map_location(
    job_data: Dict[str, Any],
    default_region: Optional[str] = None,
) -> Tuple[Dict[str, Any], Optional[float], Optional[float], float]:
    resolved = apply_verified_business_location(job_data)
    location_kind = str(resolved.get("location_kind") or "")

    # A city or neighborhood label is useful list context, but it is not an
    # exact workplace. Publishing its centroid makes unrelated jobs look as if
    # they share one employer address.
    if location_kind and location_kind not in PRECISE_LOCATION_KINDS:
        return resolved, None, None, 0.3

    location_text = resolved.get("location_text")
    if not location_text and location_kind:
        return resolved, None, None, 0.3

    # Legacy adapters without an explicit policy keep their old behavior until
    # they are migrated. Current adapters always provide location_kind.
    allow_region_fallback = not bool(location_kind)
    lat, lng, confidence = geocode_location(
        location_text or resolved.get("region_hint") or default_region,
        resolved.get("region_hint") or default_region,
        allow_region_fallback=allow_region_fallback,
    )
    return resolved, lat, lng, confidence


def has_street_address(value: Any) -> bool:
    normalized = " ".join(str(value or "").split())
    return bool(
        re.search(
            r"(?:^|,\s*)#?\d+[A-Za-z]?(?:\s*-\s*\d+[A-Za-z]?)?\s+[A-Za-z0-9]",
            normalized,
        )
    )


def _normalized_business_text(value: str) -> str:
    return " ".join(re.sub(r"[^\w]+", " ", value.casefold()).split())


def _contains_normalized_phrase(haystack: str, phrase: str) -> bool:
    return bool(re.search(r"(?:^|\s)%s(?:\s|$)" % re.escape(phrase), haystack))

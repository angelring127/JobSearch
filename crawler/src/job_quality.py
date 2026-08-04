import json
import logging
import os
import re
from typing import Any, Dict, Optional, Protocol, Tuple

import httpx


logger = logging.getLogger(__name__)

MAP_LOCATION_KINDS = {"street_address", "business_or_landmark", "neighborhood"}

JOB_INTENT_PATTERN = re.compile(
    r"구인|채용|모집|직원|스탭|스태프|구합니다|찾습니다|함께\s*일|"
    r"\bstaff\b|\bhiring\b|\brecruit(?:ing|ment)?\b",
    re.IGNORECASE,
)

NON_JOB_TITLE_PATTERNS = [
    re.compile(r"튜터|과외|레슨|수업\s*(?:제공|해드)", re.IGNORECASE),
    re.compile(r"자기소개서|이력서\s*(?:첨삭|작성)|취업\s*컨설팅", re.IGNORECASE),
    re.compile(r"프로모션|\bpromotion\b|최저가|가입\s*상담|신규\s*개통", re.IGNORECASE),
]

NEIGHBORHOOD_HINTS = [
    (re.compile(r"로히드|lougheed", re.IGNORECASE), "Lougheed Town Centre, Burnaby, BC", "Burnaby"),
    (re.compile(r"메트로타운|metrotown", re.IGNORECASE), "Metropolis at Metrotown, Burnaby, BC", "Burnaby"),
    (re.compile(r"버퀴틀람|burquitlam", re.IGNORECASE), "Burquitlam Station, Coquitlam, BC", "Coquitlam"),
    (re.compile(r"코퀴틀람\s*센터|coquitlam\s+centre", re.IGNORECASE), "Coquitlam Centre, Coquitlam, BC", "Coquitlam"),
    (re.compile(r"길포드|guildford", re.IGNORECASE), "Guildford Town Centre, Surrey, BC", "Surrey"),
    (re.compile(r"랍슨|robson", re.IGNORECASE), "Robson Street, Vancouver, BC", "Vancouver"),
    (re.compile(r"다운타운|downtown", re.IGNORECASE), "Downtown Vancouver, Vancouver, BC", "Vancouver"),
]

REGION_ALIASES = [
    ("new westminster", "New Westminster"),
    ("north vancouver", "North Vancouver"),
    ("west vancouver", "West Vancouver"),
    ("port coquitlam", "Port Coquitlam"),
    ("coquitlam", "Coquitlam"),
    ("campbell river", "Campbell River"),
    ("burnaby", "Burnaby"),
    ("richmond", "Richmond"),
    ("surrey", "Surrey"),
    ("langley", "Langley"),
    ("vancouver", "Vancouver"),
    ("toronto", "Toronto"),
]


class JobAnalyzer(Protocol):
    def analyze(self, title: str, content: str) -> Optional[Dict[str, Any]]:
        ...


class CodexBridgeJobAnalyzer:
    def __init__(self, base_url: str, api_key: str, model: Optional[str] = None, timeout: float = 60.0):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.timeout = timeout

    @classmethod
    def from_env(cls) -> Optional["CodexBridgeJobAnalyzer"]:
        base_url = os.getenv("CODEX_BRIDGE_BASE_URL", "").strip()
        api_key = os.getenv("CODEX_BRIDGE_API_KEY", "").strip()
        if not base_url or not api_key:
            return None
        try:
            timeout = float(os.getenv("CODEX_BRIDGE_TIMEOUT_SECONDS", "60"))
        except ValueError:
            timeout = 60.0
        return cls(base_url, api_key, os.getenv("CODEX_BRIDGE_MODEL") or None, timeout)

    def analyze(self, title: str, content: str) -> Optional[Dict[str, Any]]:
        prompt = (
            "You classify one Korean Canadian community-board post for a job-location map.\n"
            "Return ONLY one JSON object, without markdown:\n"
            '{"is_job_posting": boolean, "location_kind": "street_address"|'
            '"business_or_landmark"|"neighborhood"|"city_only"|"none", '
            '"location_query": string|null, "region_hint": string|null, "reason": string}\n'
            "A product/service advertisement, tutor offering lessons, resume service, or general promotion "
            "is not a job posting. A real employer recruiting workers can be a job posting. "
            "Only use location evidence present in the supplied title/content. Never invent an address. "
            "A broad city alone is city_only and is not precise enough for a map marker. "
            "A named neighborhood may be normalized to an English Canadian map query.\n"
            "TITLE:\n%s\nCONTENT:\n%s" % (title[:500], content[:6000])
        )
        payload: Dict[str, Any] = {"input": prompt}
        if self.model:
            payload["model"] = self.model

        try:
            response = httpx.post(
                "%s/v1/responses" % self.base_url,
                headers={
                    "Authorization": "Bearer %s" % self.api_key,
                    "Content-Type": "application/json",
                },
                json=payload,
                timeout=self.timeout,
            )
            response.raise_for_status()
            output_text = response.json().get("output_text") or ""
            return _parse_json_object(output_text)
        except Exception as exc:
            logger.warning("Codex Bridge job analysis failed: %s", exc)
            return None


def curate_ourvancouver_job(
    job: Dict[str, Any],
    analyzer: Optional[JobAnalyzer] = None,
) -> Optional[Dict[str, Any]]:
    curated = dict(job)
    content = str(curated.pop("_content", "") or "")
    title = str(curated.get("title") or "")
    combined = "%s %s" % (title, content)
    has_job_intent = bool(JOB_INTENT_PATTERN.search("%s %s" % (title, content[:500])))

    if not has_job_intent and any(pattern.search(title) for pattern in NON_JOB_TITLE_PATTERNS):
        return None

    grounded = _grounded_location(curated, combined)
    if has_job_intent and grounded and grounded[2] == "street_address":
        return _apply_location(curated, *grounded)

    analyzer = analyzer or CodexBridgeJobAnalyzer.from_env()
    analysis = analyzer.analyze(title, content) if analyzer else None
    if not analysis:
        return _apply_location(curated, *grounded) if has_job_intent and grounded else None
    if analysis.get("is_job_posting") is not True:
        return None

    location_kind = str(analysis.get("location_kind") or "")
    location_query = analysis.get("location_query")
    if location_kind not in MAP_LOCATION_KINDS or not isinstance(location_query, str):
        return _apply_location(curated, *grounded) if has_job_intent and grounded else None

    location_query = " ".join(location_query.split())[:200]
    if location_kind == "business_or_landmark":
        location_query = " ".join(
            re.sub(r"\bdowntown\b", " ", location_query, flags=re.IGNORECASE).split()
        )
    if not location_query or ";" in location_query:
        return None
    if location_kind == "street_address" and not _street_address_is_grounded(location_query, combined):
        return None

    normalized = _neighborhood_location("%s %s" % (combined, location_query))
    location_fallback_text = None
    if normalized:
        region_hint = normalized[1]
        if location_kind == "neighborhood":
            location_query = normalized[0]
        elif location_kind == "business_or_landmark":
            location_fallback_text = normalized[0]
    else:
        region_hint = (
            _canonical_region(location_query)
            or _canonical_region(str(analysis.get("region_hint") or ""))
            or str(curated.get("region_hint") or "")
            or "Vancouver"
        )

    result = _apply_location(curated, location_query, region_hint, location_kind)
    if location_fallback_text:
        result["location_fallback_text"] = location_fallback_text
    return result


def _grounded_location(job: Dict[str, Any], combined: str) -> Optional[Tuple[str, str, str]]:
    location_text = str(job.get("location_text") or "").strip()
    if location_text and re.search(r"\d", location_text):
        region_hint = str(job.get("region_hint") or "") or _canonical_region(combined) or "Vancouver"
        return location_text, region_hint, "street_address"

    neighborhood = _neighborhood_location(combined)
    if neighborhood:
        return neighborhood[0], neighborhood[1], "neighborhood"
    return None


def _neighborhood_location(value: str) -> Optional[Tuple[str, str]]:
    for pattern, query, region in NEIGHBORHOOD_HINTS:
        if pattern.search(value):
            return query, region
    return None


def _apply_location(job: Dict[str, Any], query: str, region_hint: str, location_kind: str) -> Dict[str, Any]:
    job["location_text"] = _normalize_location_query(query)
    job["region_hint"] = region_hint
    job["location_kind"] = location_kind
    return job


def _normalize_location_query(value: str) -> str:
    normalized = " ".join(value.replace("–", "-").replace("—", "-").split())
    normalized = re.sub(r"^#?\d+\s*-\s*(?=\d+\s)", "", normalized)
    normalized = re.sub(r",?\s+Vancouver\s+UBC\b", ", Vancouver, BC", normalized, flags=re.IGNORECASE)
    return normalized.strip(" ,")


def _canonical_region(value: str) -> Optional[str]:
    normalized = value.lower()
    for alias, region in REGION_ALIASES:
        if alias in normalized:
            return region
    return None


def _street_address_is_grounded(query: str, source_text: str) -> bool:
    query_numbers = set(re.findall(r"\d+", query))
    source_numbers = set(re.findall(r"\d+", source_text))
    return bool(query_numbers and query_numbers <= source_numbers)


def _parse_json_object(value: str) -> Optional[Dict[str, Any]]:
    text = value.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
        text = re.sub(r"\s*```$", "", text)
    start = text.find("{")
    end = text.rfind("}")
    if start < 0 or end < start:
        return None
    try:
        parsed = json.loads(text[start : end + 1])
    except json.JSONDecodeError:
        return None
    return parsed if isinstance(parsed, dict) else None

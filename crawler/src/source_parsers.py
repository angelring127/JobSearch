import re
from datetime import datetime
from typing import Dict, List, Optional

from bs4 import BeautifulSoup

from crawler import extract_address, extract_location_hints, parse_category, parse_wage


def _clean_text(value: str) -> str:
    return " ".join((value or "").split())


def _unique_ids(values: List[int], last_seen_id: int) -> List[int]:
    return sorted({value for value in values if value > last_seen_id}, reverse=True)


def _posted_at(value: str, patterns: List[str]) -> Optional[str]:
    for pattern in patterns:
        match = re.search(pattern, value)
        if not match:
            continue
        normalized = match.group(1).replace("/", "-")
        try:
            return datetime.strptime(normalized, "%Y-%m-%d").isoformat()
        except ValueError:
            continue
    return None


def _posted_datetime(value: str, patterns: List[tuple[str, str]]) -> Optional[str]:
    for pattern, date_format in patterns:
        match = re.search(pattern, value)
        if not match:
            continue
        try:
            return datetime.strptime(match.group(1), date_format).isoformat()
        except ValueError:
            continue
    return None


def _canonical_region(value: str, default: str) -> str:
    normalized = (value or "").lower()
    aliases = [
        ("포트코퀴틀람", "Port Coquitlam"),
        ("port coquitlam", "Port Coquitlam"),
        ("뉴웨스트민스터", "New Westminster"),
        ("new westminster", "New Westminster"),
        ("웨스트밴쿠버", "West Vancouver"),
        ("west vancouver", "West Vancouver"),
        ("노스밴쿠버", "North Vancouver"),
        ("north vancouver", "North Vancouver"),
        ("메이플릿지", "Maple Ridge"),
        ("maple ridge", "Maple Ridge"),
        ("아보츠포드", "Abbotsford"),
        ("abbotsford", "Abbotsford"),
        ("캠벨리버", "Campbell River"),
        ("campbell river", "Campbell River"),
        ("코퀴틀람", "Coquitlam"),
        ("coquitlam", "Coquitlam"),
        ("리치몬드", "Richmond"),
        ("richmond", "Richmond"),
        ("화이트록", "White Rock"),
        ("white rock", "White Rock"),
        ("밴쿠버", "Vancouver"),
        ("vancouver area", "Vancouver"),
        ("vancouver", "Vancouver"),
        ("빅토리아", "Victoria"),
        ("victoria", "Victoria"),
        ("버나비", "Burnaby"),
        ("burnaby", "Burnaby"),
        ("써리", "Surrey"),
        ("surrey", "Surrey"),
        ("랭리", "Langley"),
        ("langley", "Langley"),
        ("델타", "Delta"),
        ("delta", "Delta"),
        ("토론토", "Toronto"),
        ("toronto", "Toronto"),
        ("오타와", "Ottawa"),
        ("ottawa", "Ottawa"),
        ("캘거리", "Calgary"),
        ("calgary", "Calgary"),
        ("에드먼턴", "Edmonton"),
        ("edmonton", "Edmonton"),
        ("몬트리올", "Montreal"),
        ("montreal", "Montreal"),
        ("위니펙", "Winnipeg"),
        ("winnipeg", "Winnipeg"),
        ("핼리팩스", "Halifax"),
        ("halifax", "Halifax"),
        ("켈로나", "Kelowna"),
        ("kelowna", "Kelowna"),
    ]
    for alias, canonical in aliases:
        if alias in normalized:
            return canonical
    return extract_location_hints(value) or default


def _location_text(content: str, region_hint: str) -> Optional[str]:
    address = extract_address(content)
    if address and re.search(r"\d", address):
        return address

    street_match = re.search(
        r"\b\d+[A-Za-z]?(?:\s+[A-Za-z0-9#.'-]+){1,8}\s+"
        r"(?:Street|St|Avenue|Ave|Road|Rd|Drive|Dr|Boulevard|Blvd|Way|Lane|Ln)\b"
        r"(?:\s*,\s*[A-Za-z .]+){0,2}",
        content,
        re.IGNORECASE,
    )
    return _clean_text(street_match.group(0)).rstrip(" ,") if street_match else None


def _strip_address_unit(value: str) -> str:
    without_named_unit = re.sub(
        r"^(?:Suite|Unit)\s*#?[A-Za-z0-9-]+\s+(?=\d)",
        "",
        _clean_text(value),
        flags=re.IGNORECASE,
    )
    without_unit_range = re.sub(r"^\d+-(?=\d+\s)", "", without_named_unit)
    return re.sub(
        r",?\s+(?:Suite|Unit)\s*#?[A-Za-z0-9-]+(?=\s*,|$)",
        "",
        without_unit_range,
        flags=re.IGNORECASE,
    )


def extract_ourvancouver_ids(html: str, last_seen_id: int) -> List[int]:
    ids = [int(value) for value in re.findall(r"\bdataid\s*:\s*(\d+)", html)]
    return _unique_ids(ids, last_seen_id)


def parse_ourvancouver_posted_at(html: str) -> Optional[str]:
    return _posted_datetime(
        html,
        [(r"PLAIN_REGDT\s*:\s*['\"](\d{14})['\"]", "%Y%m%d%H%M%S")],
    )


def parse_ourvancouver_job(html: str, source_url: str, item_id: int) -> Optional[Dict]:
    soup = BeautifulSoup(html, "lxml")
    title_node = soup.select_one("h3.tit_subject, .bbs_read_tit .article_title")
    content_node = soup.select_one(".tx-content-container")
    title = _clean_text(title_node.get_text(" ", strip=True) if title_node else "")
    content = _clean_text(content_node.get_text(" ", strip=True) if content_node else "")
    if not title or not content:
        return None

    combined = "%s %s" % (title, content)
    region_hint = _canonical_region(combined, "")
    location_text = _location_text(content, region_hint)
    wage_min, wage_max = parse_wage(combined)

    return {
        "msgid": item_id,
        "source_url": source_url,
        "title": title,
        "wage_min": wage_min,
        "wage_max": wage_max,
        "category": parse_category(title, content),
        "region_hint": region_hint,
        "location_text": location_text,
        "location_kind": "street_address" if location_text else "none",
        "posted_at": parse_ourvancouver_posted_at(html),
        "_content": content,
    }


def extract_jinzaicanada_ids(html: str, last_seen_id: int) -> List[int]:
    soup = BeautifulSoup(html, "lxml")
    ids = []
    for link in soup.select("a.job-list__item[href]"):
        match = re.search(r"/job/(\d+)(?:[/?#]|$)", link.get("href", ""))
        if match:
            ids.append(int(match.group(1)))
    return _unique_ids(ids, last_seen_id)


def parse_jinzaicanada_job(html: str, source_url: str, item_id: int) -> Optional[Dict]:
    soup = BeautifulSoup(html, "lxml")
    detail = soup.select_one("main.job-detail")
    title_node = soup.select_one("main.job-detail h1.entry-title")
    title = _clean_text(title_node.get_text(" ", strip=True) if title_node else "")
    if not detail or not title:
        return None

    fields: Dict[str, str] = {}
    for row in detail.select("tr"):
        cells = row.find_all(["th", "td"], recursive=False)
        if len(cells) >= 2:
            fields[_clean_text(cells[0].get_text(" ", strip=True))] = _clean_text(
                cells[1].get_text(" ", strip=True)
            )

    content = _clean_text(detail.get_text(" ", strip=True))
    location_text = _strip_address_unit(fields.get("本社所在地") or fields.get("エリア") or "")
    region_hint = _canonical_region(location_text, "") or _canonical_region(
        fields.get("エリア", ""), "Vancouver"
    )
    wage_text = "%s %s" % (fields.get("時給", ""), content)
    wage_min, wage_max = parse_wage(wage_text)
    published_node = soup.select_one('meta[property="article:published_time"]')
    published_value = published_node.get("content", "") if published_node else ""
    posted_at = _posted_datetime(
        published_value,
        [(r"^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})$", "%Y-%m-%d %H:%M:%S")],
    ) or _posted_at(content, [r"掲載日\s*:\s*(\d{4}/\d{2}/\d{2})"])

    return {
        "msgid": item_id,
        "source_url": source_url,
        "title": title,
        "wage_min": wage_min,
        "wage_max": wage_max,
        "category": parse_category(title, "%s %s" % (fields.get("ポジション", ""), content)),
        "region_hint": region_hint,
        "location_text": location_text or region_hint,
        "posted_at": posted_at,
    }


def extract_vanchosun_ids(html: str, last_seen_id: int) -> List[int]:
    soup = BeautifulSoup(html, "lxml")
    ids = []
    for row in soup.select("tr.marketListTr.job_findworker"):
        link = row.find("a", href=True)
        if not link:
            continue
        match = re.search(r"[?&]bdId=(\d+)", link.get("href", ""))
        if match:
            ids.append(int(match.group(1)))
    return _unique_ids(ids, last_seen_id)


def parse_vanchosun_job(html: str, source_url: str, item_id: int) -> Optional[Dict]:
    soup = BeautifulSoup(html, "lxml")
    detail = soup.select_one("#cf_middle")
    title_node = detail.select_one("font b") if detail else None
    content_node = detail.select_one("#div_overflow") if detail else None
    title = _clean_text(title_node.get_text(" ", strip=True) if title_node else "")
    content = _clean_text(content_node.get_text(" ", strip=True) if content_node else "")
    if not detail or not title or not content:
        return None

    fields: Dict[str, str] = {}
    for label in detail.select("td.board_section_frame1"):
        value = label.find_next_sibling("td")
        if value:
            fields[_clean_text(label.get_text(" ", strip=True))] = _clean_text(
                value.get_text(" ", strip=True)
            )

    detail_text = _clean_text(detail.get_text(" ", strip=True))
    region_hint = _canonical_region("%s %s" % (fields.get("근무지역", ""), content), "Vancouver")
    location_text = _location_text(content, region_hint)
    wage_min, wage_max = parse_wage("%s %s" % (fields.get("희망임금", ""), content))

    return {
        "msgid": item_id,
        "source_url": source_url,
        "title": title,
        "wage_min": wage_min,
        "wage_max": wage_max,
        "category": parse_category(title, "%s %s" % (fields.get("모집분야", ""), content)),
        "region_hint": region_hint,
        "location_text": location_text,
        "posted_at": _posted_at(detail_text, [r"등록일\s*:\s*(\d{4}-\d{2}-\d{2})"]),
    }

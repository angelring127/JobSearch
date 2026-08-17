from abc import ABC, abstractmethod
from datetime import date, datetime, timedelta
import html as html_lib
import re
import time
from typing import Any, Callable, Dict, List, Optional
from zoneinfo import ZoneInfo

import httpx

from crawler import crawl_bbs_listing, crawl_job_post
from job_quality import (
    CodexBridgeJobAnalyzer,
    JOB_INTENT_PATTERN,
    NON_JOB_TITLE_PATTERNS,
    curate_ourvancouver_job,
)
from source_parsers import (
    extract_jinzaicanada_ids,
    extract_sinojobs_ids,
    extract_vanchosun_ids,
    parse_jinzaicanada_job,
    parse_casmo_listing_job,
    parse_ourvancouver_job,
    parse_ourvancouver_posted_at,
    parse_sinojobs_job,
    parse_vanchosun_job,
)


PUBLIC_SOURCE_REQUEST_INTERVAL = 1.0
SINOJOBS_REQUEST_INTERVAL = 20.0
OURVANCOUVER_LISTING_REQUEST_INTERVAL = 0.2
OURVANCOUVER_RETENTION_DAYS = 14
OURVANCOUVER_MAX_LISTING_PAGES = 200
CASMO_LISTING_REQUEST_INTERVAL = 0.2
CASMO_MAX_LISTING_PAGES = 20

ITEM_AVAILABILITY_ACTIVE = "active"
ITEM_AVAILABILITY_REMOVED = "removed"
ITEM_AVAILABILITY_UNKNOWN = "unknown"


class CrawlerAdapter(ABC):
    source_key: str
    display_name: str
    refresh_current_listing = False
    scan_recent_window = False
    verify_missing_items = False

    @abstractmethod
    def get_regions(self, db_client: Any) -> List[Dict[str, Any]]:
        raise NotImplementedError

    @abstractmethod
    def get_new_item_ids(self, region: Dict[str, Any], last_seen_id: int, client: httpx.Client) -> List[int]:
        raise NotImplementedError

    @abstractmethod
    def fetch_item(self, item_id: int, region: Dict[str, Any], client: httpx.Client) -> Optional[Dict[str, Any]]:
        raise NotImplementedError

    def fetch_posted_at(self, item_id: int, region: Dict[str, Any], client: httpx.Client) -> Optional[str]:
        job = self.fetch_item(item_id, region, client)
        return str(job["posted_at"]) if job and job.get("posted_at") else None

    def check_item_availability(
        self,
        item_id: int,
        region: Dict[str, Any],
        client: httpx.Client,
    ) -> str:
        del item_id, region, client
        return ITEM_AVAILABILITY_UNKNOWN


def _fetch_public_html(client: httpx.Client, url: str) -> str:
    response = client.get(url)
    response.raise_for_status()
    if not response.text.strip():
        raise RuntimeError("Empty response from %s" % url)
    return response.text


class JPCanadaAdapter(CrawlerAdapter):
    source_key = "jpcanada"
    display_name = "JPCanada"
    base_url = "https://bbs.jpcanada.com"

    def get_regions(self, db_client: Any) -> List[Dict[str, Any]]:
        return db_client.get_regions()

    def get_new_item_ids(self, region: Dict[str, Any], last_seen_id: int, client: httpx.Client) -> List[int]:
        return crawl_bbs_listing(region["listing_url"], last_seen_id, client)

    def fetch_item(self, item_id: int, region: Dict[str, Any], client: httpx.Client) -> Optional[Dict[str, Any]]:
        return crawl_job_post(item_id, self.base_url, int(region["bbs"]), client)


class OurVancouverAdapter(CrawlerAdapter):
    source_key = "ourvancouver"
    display_name = "우벤유"
    scan_recent_window = True
    verify_missing_items = True
    listing_url = "https://m.cafe.daum.net/ourvancouver/1xBD?"
    listing_api_url = "https://m.cafe.daum.net/api/v1/common-articles"
    detail_url = "https://m.cafe.daum.net/ourvancouver/1xBD/{item_id}"
    detail_fetch_url = "https://cafe.daum.net/_c21_/bbs_read?grpid=hPc&fldid=1xBD&datanum={item_id}"

    def __init__(
        self,
        today_provider: Optional[Callable[[], date]] = None,
        max_listing_pages: int = OURVANCOUVER_MAX_LISTING_PAGES,
        listing_request_interval: float = OURVANCOUVER_LISTING_REQUEST_INTERVAL,
    ):
        self.today_provider = today_provider or (
            lambda: datetime.now(ZoneInfo("Asia/Seoul")).date()
        )
        self.max_listing_pages = max(1, max_listing_pages)
        self.listing_request_interval = max(0.0, listing_request_interval)

    def get_regions(self, db_client: Any) -> List[Dict[str, Any]]:
        return [{"city": "Vancouver", "bbs": 1, "listing_url": self.listing_url}]

    def get_new_item_ids(self, region: Dict[str, Any], last_seen_id: int, client: httpx.Client) -> List[int]:
        del last_seen_id  # Seen-item tracking, not the old page-1 cursor, filters backlog work.
        cutoff = self.today_provider() - timedelta(days=OURVANCOUVER_RETENTION_DAYS)
        html = _fetch_public_html(client, region["listing_url"])
        articles = _parse_ourvancouver_listing_articles(html)
        if not articles:
            raise RuntimeError("Our Vancouver listing did not contain article metadata")

        recent_ids: List[int] = []
        expired_page_streak = 0
        page = 1
        while True:
            recent_ids.extend(
                article["dataid"]
                for article in articles
                if _ourvancouver_article_is_recent(article, cutoff)
            )

            if _ourvancouver_page_is_expired(articles, cutoff):
                expired_page_streak += 1
            else:
                expired_page_streak = 0

            if expired_page_streak >= 2:
                break
            if page >= self.max_listing_pages:
                raise RuntimeError(
                    "Our Vancouver listing page ceiling reached before the 14-day boundary"
                )

            after_depth = str(articles[-1].get("bbsDepth") or "").strip()
            if not after_depth:
                raise RuntimeError("Our Vancouver listing pagination depth is missing")

            page += 1
            response = client.get(
                self.listing_api_url,
                params={
                    "grpid": "hPc",
                    "fldid": "1xBD",
                    "targetPage": page,
                    "afterBbsDepth": after_depth,
                    "pageSize": 20,
                },
                headers={"Referer": region["listing_url"], "Accept": "application/json"},
            )
            response.raise_for_status()
            payload = response.json()
            raw_articles = payload.get("articles") if isinstance(payload, dict) else None
            if not isinstance(raw_articles, list):
                raise RuntimeError("Our Vancouver listing API returned malformed articles")
            if not raw_articles:
                break
            articles = _normalize_ourvancouver_api_articles(raw_articles)
            if self.listing_request_interval:
                time.sleep(self.listing_request_interval)

        return list(dict.fromkeys(recent_ids))

    def fetch_item(self, item_id: int, region: Dict[str, Any], client: httpx.Client) -> Optional[Dict[str, Any]]:
        url = self.detail_url.format(item_id=item_id)
        # The desktop read response contains the same title/content plus the
        # source publication timestamp. One request avoids doubling the public
        # source traffic for every high-volume backlog item.
        html = _fetch_public_html(client, self.detail_fetch_url.format(item_id=item_id))
        time.sleep(PUBLIC_SOURCE_REQUEST_INTERVAL)
        job = parse_ourvancouver_job(html, url, item_id)
        return curate_ourvancouver_job(job) if job else None

    def fetch_posted_at(self, item_id: int, region: Dict[str, Any], client: httpx.Client) -> Optional[str]:
        html = _fetch_public_html(client, self.detail_fetch_url.format(item_id=item_id))
        time.sleep(PUBLIC_SOURCE_REQUEST_INTERVAL)
        return parse_ourvancouver_posted_at(html)

    def check_item_availability(
        self,
        item_id: int,
        region: Dict[str, Any],
        client: httpx.Client,
    ) -> str:
        del region
        try:
            response = client.get(self.detail_fetch_url.format(item_id=item_id))
            if response.status_code in {404, 410}:
                return ITEM_AVAILABILITY_REMOVED
            if response.status_code != 200:
                return ITEM_AVAILABILITY_UNKNOWN

            html = response.text.strip()
            if not html:
                return ITEM_AVAILABILITY_UNKNOWN
            if any(
                marker in html
                for marker in (
                    "존재하지 않는 게시물입니다",
                    "삭제된 게시물입니다",
                    "삭제되었거나 존재하지 않는 게시물",
                )
            ):
                return ITEM_AVAILABILITY_REMOVED
            return ITEM_AVAILABILITY_ACTIVE
        except httpx.HTTPError:
            return ITEM_AVAILABILITY_UNKNOWN
        finally:
            time.sleep(PUBLIC_SOURCE_REQUEST_INTERVAL)


class _PrecomputedJobAnalyzer:
    def __init__(self, analysis: Dict[str, Any]):
        self.analysis = analysis

    def analyze(self, title: str, content: str) -> Dict[str, Any]:
        del title, content
        return self.analysis


class CasmoAdapter(CrawlerAdapter):
    source_key = "casmo"
    display_name = "캐스모"
    scan_recent_window = True
    listing_url = "https://m.cafe.daum.net/skc67/8cBB?"
    listing_api_url = "https://m.cafe.daum.net/api/v1/common-articles"
    detail_url = "https://m.cafe.daum.net/skc67/8cBB/{item_id}"

    def __init__(
        self,
        now_provider: Optional[Callable[[], datetime]] = None,
        max_listing_pages: int = CASMO_MAX_LISTING_PAGES,
        listing_request_interval: float = CASMO_LISTING_REQUEST_INTERVAL,
        sleeper: Callable[[float], None] = time.sleep,
        analyzer: Optional[Any] = None,
    ):
        self.now_provider = now_provider or (
            lambda: datetime.now(ZoneInfo("Asia/Seoul")).replace(tzinfo=None)
        )
        self.max_listing_pages = max(1, max_listing_pages)
        self.listing_request_interval = max(CASMO_LISTING_REQUEST_INTERVAL, listing_request_interval)
        self.sleeper = sleeper
        self.analyzer = analyzer if analyzer is not None else CodexBridgeJobAnalyzer.from_env()
        self._articles: Dict[int, Dict[str, Any]] = {}
        self._analysis_unavailable = False

    def get_regions(self, db_client: Any) -> List[Dict[str, Any]]:
        del db_client
        return [{"city": "Canada", "bbs": 1, "listing_url": self.listing_url}]

    def get_new_item_ids(self, region: Dict[str, Any], last_seen_id: int, client: httpx.Client) -> List[int]:
        del last_seen_id
        self._articles = {}
        self._analysis_unavailable = False
        after_depth = ""

        for page in range(1, self.max_listing_pages + 1):
            params = {
                "grpid": "7rX",
                "fldid": "8cBB",
                "targetPage": page,
                "pageSize": 20,
            }
            if after_depth:
                params["afterBbsDepth"] = after_depth

            try:
                response = client.get(
                    self.listing_api_url,
                    params=params,
                    headers={"Referer": region["listing_url"], "Accept": "application/json"},
                )
                response.raise_for_status()
                payload = response.json()
            finally:
                self.sleeper(self.listing_request_interval)

            raw_articles = payload.get("articles") if isinstance(payload, dict) else None
            if not isinstance(raw_articles, list):
                raise RuntimeError("Casmo listing API returned malformed articles")
            if not raw_articles:
                break

            articles = _normalize_casmo_api_articles(raw_articles)
            after_depth = str(articles[-1]["bbsDepth"])
            for article in articles:
                if _casmo_article_is_eligible(article):
                    self._articles[int(article["dataid"])] = article

        return list(self._articles)

    def fetch_item(self, item_id: int, region: Dict[str, Any], client: httpx.Client) -> Optional[Dict[str, Any]]:
        del region, client
        article = self._articles.get(item_id)
        if not article:
            raise RuntimeError("Casmo listing metadata is unavailable for item %s" % item_id)

        source_url = self.detail_url.format(item_id=item_id)
        job = parse_casmo_listing_job(article, source_url, item_id, now=self.now_provider())
        if not job:
            return None

        if job.get("location_kind") == "street_address":
            return curate_ourvancouver_job(job)

        if self._analysis_unavailable or self.analyzer is None:
            raise RuntimeError("Casmo title analysis is unavailable; leaving item retryable")

        title = str(job.get("title") or "")
        analysis = self.analyzer.analyze(title, title)
        if not analysis:
            self._analysis_unavailable = True
            raise RuntimeError("Casmo title analysis failed; leaving item retryable")
        if not _casmo_analysis_is_valid(analysis, job):
            self._analysis_unavailable = True
            raise RuntimeError("Casmo title analysis was invalid; leaving item retryable")

        return curate_ourvancouver_job(job, analyzer=_PrecomputedJobAnalyzer(analysis))


def _normalize_casmo_api_articles(raw_articles: List[Any]) -> List[Dict[str, Any]]:
    articles: List[Dict[str, Any]] = []
    for raw in raw_articles:
        if not isinstance(raw, dict):
            raise RuntimeError("Casmo listing API returned a malformed article")
        try:
            item_id = int(raw["dataid"])
        except (KeyError, TypeError, ValueError) as exc:
            raise RuntimeError("Casmo listing API article ID is missing") from exc
        depth = str(raw.get("bbsDepth") or "").strip()
        title = html_lib.unescape(str(raw.get("title") or "")).strip()
        if not depth or not title:
            raise RuntimeError("Casmo listing API article metadata is incomplete")
        articles.append(
            {
                "dataid": item_id,
                "title": title,
                "articleElapsedTime": str(raw.get("articleElapsedTime") or "").strip(),
                "bbsDepth": depth,
                "headCont": str(raw.get("headCont") or "").strip(),
            }
        )
    return articles


def _casmo_article_is_eligible(article: Dict[str, Any]) -> bool:
    title = str(article.get("title") or "").strip()
    head = str(article.get("headCont") or "").strip()
    if not title or head == "구직" or "구직" in title:
        return False
    if re.search(r"일자리\s*(?:를\s*)?(?:찾|구하)|취업\s*(?:자리\s*)?(?:찾|원하)", title):
        return False
    if not JOB_INTENT_PATTERN.search(title):
        return False
    if any(pattern.search(title) for pattern in NON_JOB_TITLE_PATTERNS):
        return False
    if re.search(r"자원\s*봉사|volunteer", title, re.IGNORECASE):
        return False
    if re.search(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}", title):
        return False
    if re.search(r"(?:\+?1[\s.-]?)?\(?\d{3}\)?[\s.-]\d{3}[\s.-]\d{4}", title):
        return False
    return True


def _casmo_analysis_is_valid(analysis: Any, job: Dict[str, Any]) -> bool:
    if not isinstance(analysis, dict) or not isinstance(analysis.get("is_job_posting"), bool):
        return False
    if analysis["is_job_posting"] is False:
        return True

    location_kind = str(analysis.get("location_kind") or "")
    if location_kind in {"city_only", "none"}:
        return True
    if location_kind not in {"street_address", "business_or_landmark", "neighborhood"}:
        return False

    location_query = str(analysis.get("location_query") or "").strip()
    title = str(job.get("title") or "")
    region_hint = str(job.get("region_hint") or "").strip()
    analysis_region = str(analysis.get("region_hint") or "")
    if not location_query or not region_hint:
        return False
    analyzed_location = ("%s %s" % (location_query, analysis_region)).casefold()
    if region_hint.casefold() not in analyzed_location:
        return False

    if location_kind == "street_address":
        query_numbers = set(re.findall(r"\d+", location_query))
        title_numbers = set(re.findall(r"\d+", title))
        return bool(query_numbers and query_numbers <= title_numbers)

    ignored_tokens = {
        "canada",
        "ontario",
        "on",
        "british",
        "columbia",
        "bc",
        "alberta",
        "ab",
        "restaurant",
        "store",
        "location",
    }
    ignored_tokens.update(re.findall(r"[a-z0-9가-힣]+", region_hint.casefold()))
    query_tokens = {
        token
        for token in re.findall(r"[a-z0-9가-힣]+", location_query.casefold())
        if len(token) >= 2 and token not in ignored_tokens
    }
    title_tokens = set(re.findall(r"[a-z0-9가-힣]+", title.casefold()))
    return bool(query_tokens & title_tokens)


def _parse_ourvancouver_listing_articles(html: str) -> List[Dict[str, Any]]:
    matches = list(re.finditer(r"\bdataid\s*:\s*(\d+)", html))
    articles: List[Dict[str, Any]] = []
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(html)
        block = html[match.start():end]
        elapsed = re.search(r"\barticleElapsedTime\s*:\s*['\"]([^'\"]+)['\"]", block)
        depth = re.search(r"\bbbsDepth\s*:\s*['\"]([^'\"]+)['\"]", block)
        if not elapsed or not depth:
            raise RuntimeError("Our Vancouver listing article metadata is incomplete")
        articles.append(
            {
                "dataid": int(match.group(1)),
                "articleElapsedTime": elapsed.group(1),
                "bbsDepth": depth.group(1),
            }
        )
    return articles


def _normalize_ourvancouver_api_articles(raw_articles: List[Any]) -> List[Dict[str, Any]]:
    articles: List[Dict[str, Any]] = []
    for raw in raw_articles:
        if not isinstance(raw, dict):
            raise RuntimeError("Our Vancouver listing API returned a malformed article")
        try:
            item_id = int(raw["dataid"])
        except (KeyError, TypeError, ValueError) as exc:
            raise RuntimeError("Our Vancouver listing API article ID is missing") from exc
        depth = str(raw.get("bbsDepth") or "").strip()
        if not depth:
            raise RuntimeError("Our Vancouver listing API pagination depth is missing")
        articles.append(
            {
                "dataid": item_id,
                "articleElapsedTime": str(raw.get("articleElapsedTime") or "").strip(),
                "bbsDepth": depth,
            }
        )
    return articles


def _ourvancouver_listing_date(value: str) -> Optional[date]:
    if not re.fullmatch(r"\d{2}\.\d{2}\.\d{2}", value.strip()):
        return None
    try:
        return datetime.strptime(value.strip(), "%y.%m.%d").date()
    except ValueError:
        return None


def _ourvancouver_article_is_recent(article: Dict[str, Any], cutoff: date) -> bool:
    posted_date = _ourvancouver_listing_date(str(article.get("articleElapsedTime") or ""))
    return posted_date is None or posted_date >= cutoff


def _ourvancouver_page_is_expired(articles: List[Dict[str, Any]], cutoff: date) -> bool:
    dates = [
        _ourvancouver_listing_date(str(article.get("articleElapsedTime") or ""))
        for article in articles
    ]
    return bool(dates) and all(posted_date is not None and posted_date < cutoff for posted_date in dates)


class JinzaiCanadaAdapter(CrawlerAdapter):
    source_key = "jinzaicanada"
    display_name = "인재 캐나다"
    listing_url = "https://jinzaicanada.com/job/list"
    detail_url = "https://jinzaicanada.com/job/{item_id}"

    def get_regions(self, db_client: Any) -> List[Dict[str, Any]]:
        return [{"city": "Canada", "bbs": 1, "listing_url": self.listing_url}]

    def get_new_item_ids(self, region: Dict[str, Any], last_seen_id: int, client: httpx.Client) -> List[int]:
        return extract_jinzaicanada_ids(_fetch_public_html(client, region["listing_url"]), last_seen_id)

    def fetch_item(self, item_id: int, region: Dict[str, Any], client: httpx.Client) -> Optional[Dict[str, Any]]:
        url = self.detail_url.format(item_id=item_id)
        html = _fetch_public_html(client, url)
        time.sleep(PUBLIC_SOURCE_REQUEST_INTERVAL)
        return parse_jinzaicanada_job(html, url, item_id)


class VanchosunAdapter(CrawlerAdapter):
    source_key = "vanchosun"
    display_name = "밴조선"
    refresh_current_listing = True
    listing_url = "https://www.vanchosun.com/market/main/frame.php?main=job"
    detail_url = "https://www.vanchosun.com/market/main/frame.php?main=job&bdId={item_id}"

    def get_regions(self, db_client: Any) -> List[Dict[str, Any]]:
        return [{"city": "Vancouver", "bbs": 1, "listing_url": self.listing_url}]

    def get_new_item_ids(self, region: Dict[str, Any], last_seen_id: int, client: httpx.Client) -> List[int]:
        # Vanchosun bumps older posts back to the top of the live listing, so its
        # numeric post ID is not a reliable freshness cursor. Refresh the current
        # top rows and let the source URL upsert keep the operation idempotent.
        return extract_vanchosun_ids(_fetch_public_html(client, region["listing_url"]), 0)

    def fetch_item(self, item_id: int, region: Dict[str, Any], client: httpx.Client) -> Optional[Dict[str, Any]]:
        url = self.detail_url.format(item_id=item_id)
        html = _fetch_public_html(client, url)
        time.sleep(PUBLIC_SOURCE_REQUEST_INTERVAL)
        return parse_vanchosun_job(html, url, item_id)


class SinojobsAdapter(CrawlerAdapter):
    source_key = "sinojobs"
    display_name = "Sinojobs Canada"
    scan_recent_window = True
    feed_url = "https://en.sinojobs.ca/feed/?post_type=job_listing"
    detail_url = "https://en.sinojobs.ca/?post_type=job_listing&p={item_id}"

    def __init__(
        self,
        today_provider: Optional[Callable[[], date]] = None,
        request_interval: float = SINOJOBS_REQUEST_INTERVAL,
        sleeper: Callable[[float], None] = time.sleep,
    ):
        self.today_provider = today_provider or (
            lambda: datetime.now(ZoneInfo("America/Toronto")).date()
        )
        self.request_interval = max(SINOJOBS_REQUEST_INTERVAL, request_interval)
        self.sleeper = sleeper

    def get_regions(self, db_client: Any) -> List[Dict[str, Any]]:
        del db_client
        return [{"city": "Canada", "bbs": 1, "listing_url": self.feed_url}]

    def get_new_item_ids(self, region: Dict[str, Any], last_seen_id: int, client: httpx.Client) -> List[int]:
        del last_seen_id  # Recent-window seen-item tracking retries failures without skipping IDs.
        html = self._fetch_with_crawl_delay(client, region["listing_url"])
        return extract_sinojobs_ids(html, 0, today=self.today_provider())

    def fetch_item(self, item_id: int, region: Dict[str, Any], client: httpx.Client) -> Optional[Dict[str, Any]]:
        del region
        url = self.detail_url.format(item_id=item_id)
        html = self._fetch_with_crawl_delay(client, url)
        return parse_sinojobs_job(html, url, item_id, today=self.today_provider())

    def _fetch_with_crawl_delay(self, client: httpx.Client, url: str) -> str:
        try:
            return _fetch_public_html(client, url)
        finally:
            # Sinojobs publishes Crawl-Delay: 20. Waiting after successful and
            # failed responses protects retries and RSS-to-detail transitions.
            self.sleeper(self.request_interval)


def get_adapter_registry() -> Dict[str, CrawlerAdapter]:
    adapters = [
        JPCanadaAdapter(),
        OurVancouverAdapter(),
        CasmoAdapter(),
        JinzaiCanadaAdapter(),
        VanchosunAdapter(),
        SinojobsAdapter(),
    ]
    return {adapter.source_key: adapter for adapter in adapters}

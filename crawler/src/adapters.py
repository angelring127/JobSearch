from abc import ABC, abstractmethod
import time
from typing import Any, Dict, List, Optional

import httpx

from crawler import crawl_bbs_listing, crawl_job_post
from job_quality import curate_ourvancouver_job
from source_parsers import (
    extract_jinzaicanada_ids,
    extract_ourvancouver_ids,
    extract_vanchosun_ids,
    parse_jinzaicanada_job,
    parse_ourvancouver_job,
    parse_ourvancouver_posted_at,
    parse_vanchosun_job,
)


PUBLIC_SOURCE_REQUEST_INTERVAL = 1.0


class CrawlerAdapter(ABC):
    source_key: str
    display_name: str

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
    listing_url = "https://m.cafe.daum.net/ourvancouver/1xBD?"
    detail_url = "https://m.cafe.daum.net/ourvancouver/1xBD/{item_id}"
    detail_fetch_url = "https://cafe.daum.net/_c21_/bbs_read?grpid=hPc&fldid=1xBD&datanum={item_id}"

    def get_regions(self, db_client: Any) -> List[Dict[str, Any]]:
        return [{"city": "Vancouver", "bbs": 1, "listing_url": self.listing_url}]

    def get_new_item_ids(self, region: Dict[str, Any], last_seen_id: int, client: httpx.Client) -> List[int]:
        return extract_ourvancouver_ids(_fetch_public_html(client, region["listing_url"]), last_seen_id)

    def fetch_item(self, item_id: int, region: Dict[str, Any], client: httpx.Client) -> Optional[Dict[str, Any]]:
        url = self.detail_url.format(item_id=item_id)
        html = _fetch_public_html(client, url)
        time.sleep(PUBLIC_SOURCE_REQUEST_INTERVAL)
        posted_at = self.fetch_posted_at(item_id, region, client)
        job = parse_ourvancouver_job(html, url, item_id)
        if job:
            job["posted_at"] = posted_at
        return curate_ourvancouver_job(job) if job else None

    def fetch_posted_at(self, item_id: int, region: Dict[str, Any], client: httpx.Client) -> Optional[str]:
        html = _fetch_public_html(client, self.detail_fetch_url.format(item_id=item_id))
        time.sleep(PUBLIC_SOURCE_REQUEST_INTERVAL)
        return parse_ourvancouver_posted_at(html)


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
    listing_url = "https://www.vanchosun.com/market/main/frame.php?main=job"
    detail_url = "https://www.vanchosun.com/market/main/frame.php?main=job&bdId={item_id}"

    def get_regions(self, db_client: Any) -> List[Dict[str, Any]]:
        return [{"city": "Vancouver", "bbs": 1, "listing_url": self.listing_url}]

    def get_new_item_ids(self, region: Dict[str, Any], last_seen_id: int, client: httpx.Client) -> List[int]:
        return extract_vanchosun_ids(_fetch_public_html(client, region["listing_url"]), last_seen_id)

    def fetch_item(self, item_id: int, region: Dict[str, Any], client: httpx.Client) -> Optional[Dict[str, Any]]:
        url = self.detail_url.format(item_id=item_id)
        html = _fetch_public_html(client, url)
        time.sleep(PUBLIC_SOURCE_REQUEST_INTERVAL)
        return parse_vanchosun_job(html, url, item_id)


def get_adapter_registry() -> Dict[str, CrawlerAdapter]:
    adapters = [
        JPCanadaAdapter(),
        OurVancouverAdapter(),
        JinzaiCanadaAdapter(),
        VanchosunAdapter(),
    ]
    return {adapter.source_key: adapter for adapter in adapters}

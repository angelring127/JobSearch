"""
データベースクライアント（API経由）
regions と crawl_log 情報をバックエンド経由で取得/更新
"""
import logging
from typing import List, Dict, Optional

import httpx

logger = logging.getLogger(__name__)


class DbClient:
    """バックエンドAPIを利用してDB情報を取得するクライアント"""

    def __init__(self, base_url: str, api_key: Optional[str] = None):
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.client = httpx.Client(timeout=30.0)

    def _auth_headers(self) -> Dict[str, str]:
        headers: Dict[str, str] = {}
        if self.api_key:
            headers['X-API-Key'] = self.api_key
        return headers

    def get_regions(self) -> List[Dict]:
        """バックエンドAPIから地域情報を取得"""
        endpoint = f"{self.base_url}/internal/regions"
        try:
            response = self.client.get(endpoint, headers=self._auth_headers())
            response.raise_for_status()
            payload = response.json()

            if payload.get('success') and isinstance(payload.get('data'), list):
                regions: List[Dict] = payload['data']

                # listing_url 도메인을 최신 형식으로 정규화
                for region in regions:
                    listing_url = region.get('listing_url', '')
                    if listing_url.startswith('https://jpcanada.com'):
                        region['listing_url'] = listing_url.replace('https://jpcanada.com', 'https://bbs.jpcanada.com', 1)
                logger.info("Loaded %d regions from API", len(regions))
                return regions

            logger.warning("Unexpected response from regions API: %s", payload)
        except Exception as exc:
            logger.error("Failed to fetch regions from API %s: %s", endpoint, exc)

        return []

    def get_last_msgid(self, bbs_id: int) -> int:
        """crawl_log 정보를 가져오기 (추후 API 구현 예정)"""
        # TODO: /internal/crawl-log API 구현 후 연동
        return 0

    def update_last_msgid(self, bbs_id: int, msgid: int) -> bool:
        """crawl_log 갱신 (추후 API 구현 예정)"""
        # TODO: /internal/crawl-log API 구현 후 연동
        logger.info("Updated last_msgid for BBS %s: %s (stub)", bbs_id, msgid)
        return True

    def close(self):
        self.client.close()

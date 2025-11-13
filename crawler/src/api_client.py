"""
バックエンドAPIクライアント
"""
import logging
import httpx
from typing import Optional, Dict
from datetime import datetime

logger = logging.getLogger(__name__)


class ApiClient:
    """バックエンドAPIクライアント"""
    
    def __init__(self, base_url: str, api_key: str):
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.client = httpx.Client(
            headers={
                'X-API-Key': api_key,
                'Content-Type': 'application/json',
            },
            timeout=30.0
        )
    
    def ingest_job(self, job_data: Dict) -> bool:
        """
        ジョブデータをバックエンドに送信
        """
        try:
            response = self.client.post(
                f"{self.base_url}/internal/ingest",
                json=job_data
            )
            
            if response.status_code == 200:
                result = response.json()
                if result.get('success'):
                    created = result.get('data', {}).get('created', False)
                    logger.info(
                        f"Job ingested successfully: {job_data.get('source_url')} "
                        f"(created: {created})"
                    )
                    return True
                else:
                    error = result.get('error', {})
                    logger.warning(
                        f"Failed to ingest job: {error.get('message', 'Unknown error')}"
                    )
            else:
                logger.error(
                    f"API error {response.status_code}: {response.text}"
                )
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to send job data to API: {e}")
            return False
    
    def close(self):
        """クライアントを閉じる"""
        self.client.close()


"""
JobMap 크롤러 메인 엔트리 포인트
"""
import os
import time
import logging
from dotenv import load_dotenv
from crawler import (
    crawl_bbs_listing,
    crawl_job_post,
    REQUEST_INTERVAL,
    USER_AGENT
)
from api_client import ApiClient
from db_client import DbClient
import httpx

load_dotenv()

# ロギング設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def main():
    """メイン関数"""
    logger.info("JobMap Crawler started")
    
    # 環境変数取得
    api_base_url = os.getenv('API_BASE_URL', 'http://localhost:8000')
    api_key = os.getenv('API_KEY', '')
    
    if not api_key:
        logger.error("API_KEY environment variable is not set")
        return
    
    # クライアント初期化
    db_client = DbClient(api_base_url, api_key)
    api_client = ApiClient(api_base_url, api_key)
    
    # HTTPクライアント初期化
    http_client = httpx.Client(
        headers={'User-Agent': USER_AGENT},
        timeout=30.0,
        follow_redirects=True
    )
    
    try:
        # リージョンリスト取得
        regions = db_client.get_regions()
        
        if not regions:
            logger.warning("No regions found")
            return
        
        # 各リージョンを処理
        for region in regions:
            city = region['city']
            bbs_id = region['bbs']
            listing_url = region['listing_url']
            
            logger.info(f"Processing region: {city} (BBS ID: {bbs_id})")
            
            try:
                # 最後に処理したmsgidを取得
                last_msgid = db_client.get_last_msgid(bbs_id)
                logger.info(f"Last processed msgid for {city}: {last_msgid}")
                
                # BBSリストページをクロール
                new_msgids = crawl_bbs_listing(listing_url, last_msgid, http_client)
                
                if not new_msgids:
                    logger.info(f"No new posts found for {city}")
                    continue
                
                # リクエスト間隔を確保
                time.sleep(REQUEST_INTERVAL)
                
                # 各投稿を処理
                max_msgid = last_msgid
                success_count = 0
                fail_count = 0
                
                for msgid in new_msgids:
                    try:
                        # ジョブ投稿をクロール
                        # listing_urlからbase URLを抽出（例: https://bbs.jpcanada.com）
                        if 'listing.php' in listing_url:
                            base_url = listing_url.split('listing.php')[0].rstrip('/')
                        else:
                            base_url = listing_url.rsplit('/', 1)[0]
                        
                        job_data = crawl_job_post(
                            msgid,
                            base_url,
                            bbs_id,
                            http_client
                        )
                        
                        if job_data:
                            # バックエンドAPIに送信
                            if api_client.ingest_job(job_data):
                                success_count += 1
                                max_msgid = max(max_msgid, msgid)
                            else:
                                fail_count += 1
                        else:
                            fail_count += 1
                            logger.warning(f"Failed to parse job post {msgid}")
                        
                    except Exception as e:
                        logger.error(f"Error processing msgid {msgid}: {e}")
                        fail_count += 1
                    
                    # リクエスト間隔を確保
                    time.sleep(REQUEST_INTERVAL)
                
                # 最後に処理したmsgidを更新
                if max_msgid > last_msgid:
                    db_client.update_last_msgid(bbs_id, max_msgid)
                
                logger.info(
                    f"Completed {city}: "
                    f"{success_count} succeeded, {fail_count} failed, "
                    f"max_msgid: {max_msgid}"
                )
                
            except Exception as e:
                logger.error(f"Error processing region {city}: {e}")
                continue
            
            # リージョン間の間隔
            time.sleep(REQUEST_INTERVAL * 2)
        
        logger.info("JobMap Crawler completed")
        
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
    finally:
        # クライアントを閉じる
        http_client.close()
        api_client.close()
        db_client.close()


if __name__ == "__main__":
    main()



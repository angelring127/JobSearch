import logging
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx
from dotenv import load_dotenv
from fastapi import Body, FastAPI, Header, HTTPException

SRC_DIR = Path(__file__).resolve().parent / "src"
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SRC_DIR))

load_dotenv(PROJECT_ROOT / ".env.local")
load_dotenv(Path(__file__).resolve().parent / ".env")

from adapters import get_adapter_registry  # noqa: E402
from crawler import USER_AGENT  # noqa: E402
from db_direct import DirectDbClient  # noqa: E402
from geocoding import geocode_location  # noqa: E402
from posted_date import backfill_missing_posted_dates  # noqa: E402
from title_translation import backfill_missing_title_translations  # noqa: E402

logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger(__name__)

DEFAULT_MAX_POSTS_PER_REGION = 3
DEFAULT_OURVANCOUVER_MAX_POSTS_PER_REGION = 100
DEFAULT_JOB_RETENTION_DAYS = 14
ADAPTERS = get_adapter_registry()

app = FastAPI(title="JobMap Crawler")


@app.get("/crawler/health", include_in_schema=False)
@app.get("/health")
def health() -> Dict[str, str]:
    return {"status": "ok", "service": "crawler"}


@app.get("/crawler/cron/crawl", include_in_schema=False)
@app.get("/cron/crawl")
def cron_crawl(authorization: str = Header(default="")) -> Dict[str, Any]:
    _require_crawler_auth(authorization)
    return run_enabled_sources(trigger_type="cron")


@app.post("/crawler/admin/run", include_in_schema=False)
@app.post("/admin/run")
def admin_run(
    payload: Optional[Dict[str, Any]] = Body(default=None),
    authorization: str = Header(default=""),
) -> Dict[str, Any]:
    _require_crawler_auth(authorization)

    source_key = (payload or {}).get("source_key") or "jpcanada"
    max_posts = int(
        (payload or {}).get("max_posts_per_region")
        or os.getenv("CRAWLER_MAX_POSTS_PER_REGION", str(DEFAULT_MAX_POSTS_PER_REGION))
    )
    return run_source_crawl(source_key=source_key, max_posts_per_region=max_posts, trigger_type="manual")


def run_enabled_sources(
    max_posts_per_region: Optional[int] = None,
    trigger_type: str = "cron",
) -> Dict[str, Any]:
    db = DirectDbClient()
    sources = db.get_enabled_sources()
    results = []
    for source in sources:
        results.append(
            run_source_crawl(
                source_key=source["source_key"],
                max_posts_per_region=(
                    max_posts_per_region
                    if max_posts_per_region is not None
                    else _scheduled_source_limit(source["source_key"])
                ),
                trigger_type=trigger_type,
                db=db,
            )
        )

    status = _aggregate_status(results)
    posted_date_backfill = backfill_missing_posted_dates(db, ADAPTERS, USER_AGENT)
    try:
        retention = {
            "status": "ok",
            **db.delete_expired_jobs(retention_days=DEFAULT_JOB_RETENTION_DAYS),
        }
    except Exception as exc:
        logger.exception("Failed to delete expired jobs")
        retention = {
            "status": "failed",
            "retention_days": DEFAULT_JOB_RETENTION_DAYS,
            "error": str(exc)[:300],
        }
        status = "partial" if results else "failed"

    title_translation = backfill_missing_title_translations(db)
    try:
        # Reconcile after translation so same-run cross-language titles can be
        # compared without waiting for the next scheduled crawl.
        dedupe = {
            "status": "ok",
            **db.reconcile_duplicate_jobs(),
        }
    except Exception as exc:
        logger.exception("Failed to reconcile duplicate jobs")
        dedupe = {"status": "failed", "error": str(exc)[:300]}
        status = "partial" if results else "failed"

    return {
        "status": status,
        "sources": results,
        "processed": sum(item.get("processed", 0) for item in results),
        "created": sum(item.get("created", 0) for item in results),
        "updated": sum(item.get("updated", 0) for item in results),
        "skipped": sum(item.get("skipped", 0) for item in results),
        "failed": sum(item.get("failed", 0) for item in results),
        "dedupe": dedupe,
        "posted_date_backfill": posted_date_backfill,
        "retention": retention,
        "title_translation": title_translation,
    }


def run_crawl(max_posts_per_region: int = DEFAULT_MAX_POSTS_PER_REGION) -> Dict[str, Any]:
    return run_source_crawl("jpcanada", max_posts_per_region=max_posts_per_region, trigger_type="manual")


def run_source_crawl(
    source_key: str,
    max_posts_per_region: int = DEFAULT_MAX_POSTS_PER_REGION,
    trigger_type: str = "cron",
    db: Optional[DirectDbClient] = None,
) -> Dict[str, Any]:
    started_at = time.time()
    db = db or DirectDbClient()
    run_id = db.create_crawl_run(source_key, trigger_type)
    source = db.get_source(source_key)
    adapter = ADAPTERS.get(source_key)
    summary = {
        "run_id": run_id,
        "source_key": source_key,
        "status": "ok",
        "trigger_type": trigger_type,
        "regions": 0,
        "processed": 0,
        "created": 0,
        "updated": 0,
        "skipped": 0,
        "failed": 0,
        "failures": [],
    }

    try:
        if not source:
            summary["status"] = "failed"
            _record_failure(summary, {"city": None, "bbs": None}, None, "Unknown crawler source")
            return summary

        if not source.get("enabled"):
            summary["status"] = "skipped"
            summary["skipped"] = 1
            return summary

        if not adapter:
            summary["status"] = "failed"
            _record_failure(summary, {"city": None, "bbs": None}, None, "No crawler adapter registered for source")
            return summary

        regions = adapter.get_regions(db)
        summary["regions"] = len(regions)

        with httpx.Client(headers={"User-Agent": USER_AGENT}, timeout=30.0, follow_redirects=True) as client:
            for region in regions:
                bbs = int(region["bbs"])
                last_msgid = db.get_last_msgid(source_key, bbs)
                max_seen_msgid = last_msgid

                try:
                    msgids = adapter.get_new_item_ids(region, last_msgid, client)
                except Exception as exc:
                    _record_failure(summary, region, None, str(exc))
                    continue

                unique_msgids = list(dict.fromkeys(msgids))
                if getattr(adapter, "scan_recent_window", False) is True:
                    seen_msgids = db.get_seen_item_ids(source_key, bbs, unique_msgids)
                    unseen_msgids = [msgid for msgid in unique_msgids if msgid not in seen_msgids]
                    # This source scans the entire recent window on every run.
                    # Prefer the newest unseen current posts, then fill remaining
                    # capacity from the newest unseen backlog below the cursor.
                    new_msgids = sorted(
                        (msgid for msgid in unseen_msgids if msgid > last_msgid),
                        reverse=True,
                    )
                    backlog_msgids = sorted(
                        (msgid for msgid in unseen_msgids if msgid <= last_msgid),
                        reverse=True,
                    )
                    selected_msgids = (new_msgids + backlog_msgids)[:max_posts_per_region]
                elif adapter.refresh_current_listing:
                    # Refresh-style boards can bump an older post ID back to the
                    # top. Preserve listing order so the current public rows win.
                    selected_msgids = unique_msgids[:max_posts_per_region]
                else:
                    # Process the oldest pending IDs first so advancing the
                    # high-water mark never skips a normal monotonic source.
                    selected_msgids = sorted(unique_msgids)[:max_posts_per_region]

                for msgid in selected_msgids:
                    max_seen_msgid = max(max_seen_msgid, msgid)
                    try:
                        job_data = adapter.fetch_item(msgid, region, client)
                        if not job_data:
                            if getattr(adapter, "scan_recent_window", False) is True:
                                db.mark_crawl_item_seen(source_key, bbs, msgid, "skipped")
                            summary["skipped"] += 1
                            continue

                        has_explicit_location_policy = "location_kind" in job_data
                        location_text = job_data.get("location_text")
                        if not location_text and not has_explicit_location_policy:
                            location_text = job_data.get("region_hint") or region["city"]
                        lat, lng, confidence = geocode_location(
                            location_text,
                            job_data.get("region_hint") or region["city"],
                            allow_region_fallback=not has_explicit_location_policy,
                        )
                        if (lat is None or lng is None) and job_data.get("location_fallback_text"):
                            lat, lng, confidence = geocode_location(
                                job_data["location_fallback_text"],
                                job_data.get("region_hint") or region["city"],
                                allow_region_fallback=False,
                            )
                        result = db.upsert_job(source_key, job_data, lat, lng, confidence)
                        if getattr(adapter, "scan_recent_window", False) is True:
                            db.mark_crawl_item_seen(source_key, bbs, msgid, "stored")

                        summary["processed"] += 1
                        if result["created"]:
                            summary["created"] += 1
                        else:
                            summary["updated"] += 1
                    except Exception as exc:
                        _record_failure(summary, region, msgid, str(exc))

                if max_seen_msgid > last_msgid:
                    db.update_last_msgid(source_key, bbs, max_seen_msgid)

        if summary["failed"] > 0 and summary["processed"] == 0:
            summary["status"] = "failed"
        elif summary["failed"] > 0:
            summary["status"] = "partial"
        return summary
    except Exception as exc:
        summary["status"] = "failed"
        _record_failure(summary, {"city": None, "bbs": None}, None, str(exc))
        return summary
    finally:
        summary["duration_sec"] = round(time.time() - started_at, 3)
        db.record_crawl_failures(run_id, source_key, summary["failures"])
        db.finish_crawl_run(run_id, source_key, summary)


def _record_failure(summary: Dict[str, Any], region: Dict[str, Any], msgid: Any, message: str) -> None:
    summary["failed"] += 1
    if len(summary["failures"]) < 10:
        summary["failures"].append(
            {
                "bbs": region.get("bbs"),
                "city": region.get("city"),
                "msgid": msgid,
                "message": message[:300],
            }
        )


def _scheduled_source_limit(source_key: str) -> int:
    global_limit = int(
        os.getenv("CRAWLER_MAX_POSTS_PER_REGION", str(DEFAULT_MAX_POSTS_PER_REGION))
    )
    if source_key == "ourvancouver":
        return max(
            1,
            int(
                os.getenv(
                    "OURVANCOUVER_MAX_POSTS_PER_REGION",
                    str(DEFAULT_OURVANCOUVER_MAX_POSTS_PER_REGION),
                )
            ),
        )
    return max(1, global_limit)


def _require_crawler_auth(authorization: str) -> None:
    expected = "Bearer %s" % os.getenv("CRON_SECRET", "dev-cron-secret")
    if authorization != expected:
        raise HTTPException(status_code=401, detail="Invalid crawler authorization")


def _aggregate_status(results: List[Dict[str, Any]]) -> str:
    if not results:
        return "skipped"
    statuses = [item.get("status") for item in results]
    if any(status == "failed" for status in statuses):
        return "failed" if all(status == "failed" for status in statuses) else "partial"
    if any(status == "partial" for status in statuses):
        return "partial"
    if all(status == "skipped" for status in statuses):
        return "skipped"
    return "ok"

import logging
from typing import Any, Dict, Optional
from urllib.parse import parse_qs, urlparse

import httpx


logger = logging.getLogger(__name__)


def backfill_missing_posted_dates(
    db: Any,
    adapters: Dict[str, Any],
    user_agent: str,
    limit: int = 20,
    client: Optional[httpx.Client] = None,
) -> Dict[str, Any]:
    try:
        sources = db.get_job_sources_missing_posted_at(limit=limit)
    except Exception as exc:
        logger.warning("Posted-date backfill query failed: %s", exc)
        return {"status": "failed", "requested": 0, "updated": 0, "failed": 0, "error": str(exc)[:300]}

    if not sources:
        return {"status": "ok", "requested": 0, "updated": 0, "failed": 0}

    owns_client = client is None
    http_client = client or httpx.Client(
        headers={"User-Agent": user_agent},
        timeout=30.0,
        follow_redirects=True,
    )
    updated = 0
    failed = 0
    try:
        for source in sources:
            adapter = adapters.get(source.get("source_key"))
            if not adapter:
                failed += 1
                continue

            try:
                posted_at = adapter.fetch_posted_at(
                    int(source["msgid"]),
                    _region_for_source(source),
                    http_client,
                )
                if not posted_at:
                    failed += 1
                    continue
                db.update_job_source_posted_at(int(source["id"]), str(posted_at))
                updated += 1
            except Exception as exc:
                failed += 1
                logger.warning(
                    "Posted-date backfill failed for %s:%s: %s",
                    source.get("source_key"),
                    source.get("msgid"),
                    exc,
                )
    finally:
        if owns_client:
            http_client.close()

    return {
        "status": "ok" if failed == 0 else "partial",
        "requested": len(sources),
        "updated": updated,
        "failed": failed,
    }


def _region_for_source(source: Dict[str, Any]) -> Dict[str, Any]:
    query = parse_qs(urlparse(str(source.get("source_url") or "")).query)
    bbs_values = query.get("bbs") or [0]
    try:
        bbs = int(bbs_values[0])
    except (TypeError, ValueError):
        bbs = 0
    return {
        "city": source.get("region_hint") or "Canada",
        "bbs": bbs,
        "listing_url": "",
    }

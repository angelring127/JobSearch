import os
import re
from difflib import SequenceMatcher
from math import asin, cos, radians, sin, sqrt
from typing import Any, Dict, List, Optional, Set
from urllib.parse import urlparse

import psycopg2
from psycopg2.extras import Json, RealDictCursor


AUTO_MERGE_THRESHOLD = 0.92
DUPLICATE_CANDIDATE_THRESHOLD = 0.7


class DirectDbClient:
    def __init__(self, database_url: Optional[str] = None):
        self.database_url = database_url or os.getenv("DATABASE_URL")
        if not self.database_url:
            raise RuntimeError("DATABASE_URL is not configured")

    def _connect(self):
        return psycopg2.connect(self.database_url, cursor_factory=RealDictCursor)

    def get_regions(self) -> List[Dict[str, Any]]:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT city, bbs, listing_url
                    FROM regions
                    ORDER BY id ASC
                    """
                )
                return [dict(row) for row in cur.fetchall()]

    def get_source(self, source_key: str) -> Optional[Dict[str, Any]]:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT source_key, display_name, adapter_key, enabled, last_status,
                           last_run_at, last_success_at, last_error
                    FROM crawler_sources
                    WHERE source_key = %s
                    """,
                    (source_key,),
                )
                row = cur.fetchone()
                return dict(row) if row else None

    def get_enabled_sources(self) -> List[Dict[str, Any]]:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT source_key, display_name, adapter_key, enabled
                    FROM crawler_sources
                    WHERE enabled = TRUE
                    ORDER BY display_name ASC
                    """
                )
                return [dict(row) for row in cur.fetchall()]

    def create_crawl_run(self, source_key: str, trigger_type: str) -> int:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO crawl_runs (source_key, trigger_type, status)
                    VALUES (%s, %s, 'running')
                    RETURNING id
                    """,
                    (source_key, trigger_type),
                )
                row = cur.fetchone()
                return int(row["id"])

    def finish_crawl_run(self, run_id: int, source_key: str, summary: Dict[str, Any]) -> None:
        failures = summary.get("failures") or []
        first_error = failures[0].get("message") if failures else None
        duration_ms = int(float(summary.get("duration_sec") or 0) * 1000)
        status = summary.get("status") or "failed"

        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE crawl_runs
                    SET status = %(status)s,
                        finished_at = NOW(),
                        duration_ms = %(duration_ms)s,
                        regions = %(regions)s,
                        processed = %(processed)s,
                        created = %(created)s,
                        updated = %(updated)s,
                        skipped = %(skipped)s,
                        failed = %(failed)s,
                        error_message = %(error_message)s,
                        summary = %(summary)s
                    WHERE id = %(run_id)s
                    """,
                    {
                        "run_id": run_id,
                        "status": status,
                        "duration_ms": duration_ms,
                        "regions": summary.get("regions") or 0,
                        "processed": summary.get("processed") or 0,
                        "created": summary.get("created") or 0,
                        "updated": summary.get("updated") or 0,
                        "skipped": summary.get("skipped") or 0,
                        "failed": summary.get("failed") or 0,
                        "error_message": first_error,
                        "summary": Json(summary),
                    },
                )
                cur.execute(
                    """
                    UPDATE crawler_sources
                    SET last_status = %(status)s,
                        last_run_at = NOW(),
                        last_success_at = CASE
                          WHEN %(status)s IN ('ok', 'partial') THEN NOW()
                          ELSE last_success_at
                        END,
                        last_error = CASE
                          WHEN %(status)s IN ('ok', 'skipped') THEN NULL
                          ELSE %(error_message)s
                        END,
                        updated_at = NOW()
                    WHERE source_key = %(source_key)s
                    """,
                    {
                        "source_key": source_key,
                        "status": status,
                        "error_message": first_error,
                    },
                )

    def record_crawl_failures(self, run_id: int, source_key: str, failures: List[Dict[str, Any]]) -> None:
        if not failures:
            return

        with self._connect() as conn:
            with conn.cursor() as cur:
                for failure in failures[:10]:
                    cur.execute(
                        """
                        INSERT INTO crawl_failures (
                          run_id, source_key, bbs, city, msgid, source_url, error_message
                        )
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                        """,
                        (
                            run_id,
                            source_key,
                            failure.get("bbs"),
                            failure.get("city"),
                            failure.get("msgid"),
                            failure.get("source_url"),
                            failure.get("message") or "Unknown crawler failure",
                        ),
                    )

    def delete_expired_jobs(self, retention_days: int = 14) -> Dict[str, int]:
        if retention_days < 1:
            raise ValueError("retention_days must be at least 1")

        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    DELETE FROM job_sources
                    WHERE COALESCE(posted_at, created_at) < NOW() - make_interval(days => %s)
                    RETURNING job_id
                    """,
                    (retention_days,),
                )
                deleted_rows = cur.fetchall()
                affected_job_ids = sorted(
                    {int(row["job_id"]) for row in deleted_rows if row.get("job_id") is not None}
                )

                cur.execute(
                    """
                    DELETE FROM jobs j
                    WHERE NOT EXISTS (
                        SELECT 1 FROM job_sources js WHERE js.job_id = j.id
                      )
                      AND (
                        j.id = ANY(%s)
                        OR j.created_at < NOW() - make_interval(days => %s)
                      )
                    RETURNING j.id
                    """,
                    (affected_job_ids, retention_days),
                )
                deleted_jobs = len(cur.fetchall())

                reconciled_jobs = 0
                if affected_job_ids:
                    cur.execute(
                        """
                        WITH source_counts AS (
                          SELECT job_id, COUNT(*)::INTEGER AS source_count
                          FROM job_sources
                          WHERE job_id = ANY(%s)
                          GROUP BY job_id
                        ),
                        new_primary AS (
                          SELECT DISTINCT ON (js.job_id)
                            js.job_id,
                            js.id AS source_id,
                            js.title,
                            js.region_hint,
                            js.wage_min,
                            js.wage_max,
                            js.lat,
                            js.lng,
                            js.geom,
                            js.category,
                            js.confidence
                          FROM job_sources js
                          WHERE js.job_id = ANY(%s)
                          ORDER BY
                            js.job_id,
                            COALESCE(js.posted_at, js.created_at) DESC,
                            js.id DESC
                        )
                        UPDATE jobs j
                        SET primary_source_id = np.source_id,
                            title = np.title,
                            region_hint = np.region_hint,
                            wage_min = np.wage_min,
                            wage_max = np.wage_max,
                            lat = np.lat,
                            lng = np.lng,
                            geom = np.geom,
                            category = np.category,
                            confidence = np.confidence,
                            source_count = sc.source_count,
                            updated_at = NOW()
                        FROM new_primary np
                        JOIN source_counts sc ON sc.job_id = np.job_id
                        WHERE j.id = np.job_id
                        RETURNING j.id
                        """,
                        (affected_job_ids, affected_job_ids),
                    )
                    reconciled_jobs = len(cur.fetchall())

                return {
                    "retention_days": retention_days,
                    "deleted_sources": len(deleted_rows),
                    "deleted_jobs": deleted_jobs,
                    "reconciled_jobs": reconciled_jobs,
                }

    def delete_source_job(self, source_key: str, external_id: str) -> Dict[str, int]:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    DELETE FROM job_sources
                    WHERE source_key = %s AND external_id = %s
                    RETURNING job_id
                    """,
                    (source_key, external_id),
                )
                deleted = cur.fetchone()
                if not deleted:
                    return {"deleted_sources": 0, "deleted_jobs": 0, "reconciled_jobs": 0}

                job_id = int(deleted["job_id"]) if deleted.get("job_id") is not None else None
                if job_id is None:
                    return {"deleted_sources": 1, "deleted_jobs": 0, "reconciled_jobs": 0}

                cur.execute(
                    """
                    SELECT id, title, region_hint, wage_min, wage_max, lat, lng, geom,
                           category, confidence
                    FROM job_sources
                    WHERE job_id = %s
                    ORDER BY COALESCE(posted_at, created_at) DESC, id DESC
                    LIMIT 1
                    """,
                    (job_id,),
                )
                replacement = cur.fetchone()
                if not replacement:
                    cur.execute("DELETE FROM jobs WHERE id = %s", (job_id,))
                    return {"deleted_sources": 1, "deleted_jobs": 1, "reconciled_jobs": 0}

                cur.execute(
                    """
                    UPDATE jobs
                    SET primary_source_id = %(source_id)s,
                        title = %(title)s,
                        title_translations = '{}'::jsonb,
                        region_hint = %(region_hint)s,
                        wage_min = %(wage_min)s,
                        wage_max = %(wage_max)s,
                        lat = %(lat)s,
                        lng = %(lng)s,
                        geom = %(geom)s,
                        category = %(category)s,
                        confidence = %(confidence)s,
                        source_count = (SELECT COUNT(*) FROM job_sources WHERE job_id = %(job_id)s),
                        updated_at = NOW()
                    WHERE id = %(job_id)s
                    """,
                    dict(replacement, source_id=replacement["id"], job_id=job_id),
                )
                return {"deleted_sources": 1, "deleted_jobs": 0, "reconciled_jobs": 1}

    def get_last_msgid(self, source_key: str, bbs: int) -> int:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT last_seen_msgid
                    FROM crawl_log
                    WHERE source_key = %s AND bbs = %s
                    """,
                    (source_key, bbs),
                )
                row = cur.fetchone()
                return int(row["last_seen_msgid"] or 0) if row else 0

    def update_last_msgid(self, source_key: str, bbs: int, last_seen_msgid: int) -> None:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO crawl_log (source_key, bbs, last_seen_msgid, updated_at)
                    VALUES (%s, %s, %s, NOW())
                    ON CONFLICT (source_key, bbs)
                    DO UPDATE SET
                      last_seen_msgid = GREATEST(crawl_log.last_seen_msgid, EXCLUDED.last_seen_msgid),
                      updated_at = NOW()
                    """,
                    (source_key, bbs, last_seen_msgid),
                )

    def upsert_job(
        self,
        source_key: str,
        job_data: Dict[str, Any],
        lat: Optional[float],
        lng: Optional[float],
        confidence: float,
    ) -> Dict[str, Any]:
        external_id = str(job_data.get("msgid") or _external_id_from_url(job_data["source_url"]))
        params = {
            "source_key": source_key,
            "external_id": external_id,
            "msgid": job_data.get("msgid") or 0,
            "source_url": job_data["source_url"],
            "region_hint": job_data.get("region_hint"),
            "title": job_data.get("title"),
            "title_translations": Json(job_data.get("title_translations") or {}),
            "wage_min": job_data.get("wage_min"),
            "wage_max": job_data.get("wage_max"),
            "lat": lat,
            "lng": lng,
            "category": job_data.get("category"),
            "confidence": confidence,
            "posted_at": job_data.get("posted_at"),
        }

        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT id FROM job_sources WHERE source_url = %(source_url)s", params)
                existing = cur.fetchone()
                if existing:
                    cur.execute(
                        """
                        UPDATE job_sources
                        SET source_key = %(source_key)s,
                            external_id = %(external_id)s,
                            msgid = %(msgid)s,
                            region_hint = %(region_hint)s,
                            title = %(title)s,
                            wage_min = %(wage_min)s,
                            wage_max = %(wage_max)s,
                            lat = %(lat)s,
                            lng = %(lng)s,
                            geom = CASE
                              WHEN %(lat)s IS NOT NULL AND %(lng)s IS NOT NULL
                                THEN ST_SetSRID(ST_MakePoint(%(lng)s, %(lat)s), 4326)::geography
                              ELSE NULL
                            END,
                            category = %(category)s,
                            confidence = %(confidence)s,
                            posted_at = %(posted_at)s,
                            updated_at = NOW()
                        WHERE id = %(id)s
                        RETURNING id
                        """,
                        dict(params, id=existing["id"]),
                    )
                    row = cur.fetchone()
                    source_id = int(row["id"])
                    job_id = self._attach_representative_job(cur, source_id, source_key, params)
                    return {"id": source_id, "job_id": job_id, "created": False}

                cur.execute(
                    """
                    INSERT INTO job_sources (
                      source_key, external_id, msgid, source_url, region_hint, title,
                      wage_min, wage_max, lat, lng, geom, category, confidence, posted_at
                    )
                    VALUES (
                      %(source_key)s, %(external_id)s, %(msgid)s, %(source_url)s, %(region_hint)s, %(title)s,
                      %(wage_min)s, %(wage_max)s, %(lat)s, %(lng)s,
                      CASE
                        WHEN %(lat)s IS NOT NULL AND %(lng)s IS NOT NULL
                          THEN ST_SetSRID(ST_MakePoint(%(lng)s, %(lat)s), 4326)::geography
                        ELSE NULL
                      END,
                      %(category)s, %(confidence)s, %(posted_at)s
                    )
                    RETURNING id
                    """,
                    params,
                )
                row = cur.fetchone()
                source_id = int(row["id"])
                job_id = self._attach_representative_job(cur, source_id, source_key, params)
                return {"id": source_id, "job_id": job_id, "created": True}

    def _attach_representative_job(
        self,
        cur: Any,
        source_id: int,
        source_key: str,
        params: Dict[str, Any],
    ) -> int:
        cur.execute("SELECT job_id FROM job_sources WHERE id = %s", (source_id,))
        row = cur.fetchone()
        existing_job_id = int(row["job_id"]) if row and row["job_id"] else None

        if existing_job_id:
            self._update_representative_job(cur, existing_job_id, source_id, params)
            self._refresh_source_count(cur, existing_job_id)
            return existing_job_id

        duplicate = self._find_duplicate_job(cur, source_id, params)
        if duplicate and duplicate["score"] >= AUTO_MERGE_THRESHOLD:
            job_id = int(duplicate["job_id"])
            cur.execute("UPDATE job_sources SET job_id = %s WHERE id = %s", (job_id, source_id))
            self._refresh_source_count(cur, job_id)
            cur.execute(
                """
                INSERT INTO job_merge_history (job_id, source_job_id, action, reason)
                VALUES (%s, %s, 'auto_merge', %s)
                """,
                (job_id, source_id, Json(duplicate["reason"])),
            )
            return job_id

        job_id = self._create_representative_job(cur, source_id, params)
        if duplicate and duplicate["score"] >= DUPLICATE_CANDIDATE_THRESHOLD:
            cur.execute(
                """
                INSERT INTO duplicate_candidates (source_job_id, candidate_job_id, score, reason)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (source_job_id, candidate_job_id)
                DO UPDATE SET
                  score = EXCLUDED.score,
                  reason = EXCLUDED.reason
                WHERE duplicate_candidates.status = 'pending'
                """,
                (source_id, duplicate["job_id"], duplicate["score"], Json(duplicate["reason"])),
            )
        return job_id

    def reconcile_duplicate_jobs(self, limit: int = 500) -> Dict[str, int]:
        bounded_limit = max(2, min(limit, 2000))
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT
                      j.id::INTEGER AS id,
                      j.title,
                      j.title_translations,
                      j.region_hint,
                      j.wage_min,
                      j.wage_max,
                      j.lat,
                      j.lng,
                      j.category,
                      j.source_count::INTEGER AS source_count,
                      ps.source_key AS primary_source_key,
                      ps.posted_at
                    FROM jobs j
                    LEFT JOIN job_sources ps ON ps.id = j.primary_source_id
                    WHERE j.hidden = FALSE
                      AND j.title IS NOT NULL
                      AND j.region_hint IS NOT NULL
                    ORDER BY j.updated_at DESC, j.id DESC
                    LIMIT %s
                    """,
                    (bounded_limit,),
                )
                rows = [dict(row) for row in cur.fetchall()]
                matches = _select_auto_merge_pairs(rows)
                moved_sources = 0
                merged_jobs = 0
                for match in matches:
                    moved = self._merge_representative_jobs(
                        cur,
                        keep_job_id=match["keep_job_id"],
                        remove_job_id=match["remove_job_id"],
                        reason=match["reason"],
                    )
                    if moved >= 0:
                        moved_sources += moved
                        merged_jobs += 1

                return {
                    "checked_jobs": len(rows),
                    "candidate_pairs": len(matches),
                    "merged_jobs": merged_jobs,
                    "moved_sources": moved_sources,
                }

    def _merge_representative_jobs(
        self,
        cur: Any,
        keep_job_id: int,
        remove_job_id: int,
        reason: Dict[str, Any],
    ) -> int:
        cur.execute(
            "SELECT id::INTEGER AS id FROM jobs WHERE id IN (%s, %s) ORDER BY id",
            (keep_job_id, remove_job_id),
        )
        if len(cur.fetchall()) != 2:
            return -1

        cur.execute(
            "SELECT id::INTEGER AS id FROM job_sources WHERE job_id = %s ORDER BY id",
            (remove_job_id,),
        )
        moved_source_ids = [int(row["id"]) for row in cur.fetchall()]

        cur.execute(
            "DELETE FROM duplicate_candidates WHERE candidate_job_id = %s",
            (remove_job_id,),
        )
        if moved_source_ids:
            history_reason = dict(reason, previous_job_id=remove_job_id)
            cur.execute(
                "DELETE FROM duplicate_candidates WHERE source_job_id = ANY(%s)",
                (moved_source_ids,),
            )
            cur.execute(
                "UPDATE job_sources SET job_id = %s, updated_at = NOW() WHERE id = ANY(%s)",
                (keep_job_id, moved_source_ids),
            )
            for source_id in moved_source_ids:
                cur.execute(
                    """
                    INSERT INTO job_merge_history (
                      job_id, source_job_id, action, previous_job_id, reason
                    )
                    VALUES (%s, %s, 'auto_merge', %s, %s)
                    """,
                    (keep_job_id, source_id, remove_job_id, Json(history_reason)),
                )

        # A representative can already own merge history from earlier source
        # consolidations. Move that audit trail before deleting the empty job.
        cur.execute(
            "UPDATE job_merge_history SET job_id = %s WHERE job_id = %s",
            (keep_job_id, remove_job_id),
        )
        cur.execute("DELETE FROM jobs WHERE id = %s", (remove_job_id,))
        self._refresh_source_count(cur, keep_job_id)
        return len(moved_source_ids)

    def _create_representative_job(self, cur: Any, source_id: int, params: Dict[str, Any]) -> int:
        cur.execute(
            """
            INSERT INTO jobs (
              primary_source_id, title, title_translations, region_hint, wage_min, wage_max,
              lat, lng, geom, category, confidence, source_count
            )
            VALUES (
              %(source_id)s, %(title)s, %(title_translations)s, %(region_hint)s, %(wage_min)s, %(wage_max)s,
              %(lat)s, %(lng)s,
              CASE
                WHEN %(lat)s IS NOT NULL AND %(lng)s IS NOT NULL
                  THEN ST_SetSRID(ST_MakePoint(%(lng)s, %(lat)s), 4326)::geography
                ELSE NULL
              END,
              %(category)s, %(confidence)s, 1
            )
            RETURNING id
            """,
            dict(params, source_id=source_id),
        )
        row = cur.fetchone()
        job_id = int(row["id"])
        cur.execute("UPDATE job_sources SET job_id = %s WHERE id = %s", (job_id, source_id))
        return job_id

    def _update_representative_job(self, cur: Any, job_id: int, source_id: int, params: Dict[str, Any]) -> None:
        cur.execute(
            """
            UPDATE jobs
            SET title = %(title)s,
                title_translations = CASE
                  WHEN title IS DISTINCT FROM %(title)s THEN '{}'::jsonb
                  WHEN %(title_translations)s::jsonb = '{}'::jsonb THEN title_translations
                  ELSE %(title_translations)s::jsonb
                END,
                region_hint = %(region_hint)s,
                wage_min = %(wage_min)s,
                wage_max = %(wage_max)s,
                lat = %(lat)s,
                lng = %(lng)s,
                geom = CASE
                  WHEN %(lat)s IS NOT NULL AND %(lng)s IS NOT NULL
                    THEN ST_SetSRID(ST_MakePoint(%(lng)s, %(lat)s), 4326)::geography
                  ELSE NULL
                END,
                category = %(category)s,
                confidence = %(confidence)s,
                primary_source_id = COALESCE(primary_source_id, %(source_id)s),
                updated_at = NOW()
            WHERE id = %(job_id)s
              AND (primary_source_id IS NULL OR primary_source_id = %(source_id)s)
            """,
            dict(params, job_id=job_id, source_id=source_id),
        )

    def get_jobs_missing_title_translations(self, limit: int = 20) -> List[Dict[str, Any]]:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id::INTEGER AS id, title
                    FROM jobs
                    WHERE title IS NOT NULL
                      AND title <> ''
                      AND NOT (title_translations ?& ARRAY['ko', 'en', 'ja', 'zh'])
                    ORDER BY updated_at DESC, id DESC
                    LIMIT %s
                    """,
                    (max(1, min(limit, 50)),),
                )
                return [dict(row) for row in cur.fetchall()]

    def update_job_title_translations(self, job_id: int, translations: Dict[str, str]) -> None:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE jobs
                    SET title_translations = %s,
                        updated_at = NOW()
                    WHERE id = %s
                    """,
                    (Json(translations), job_id),
                )

    def get_job_sources_missing_posted_at(self, limit: int = 20) -> List[Dict[str, Any]]:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT
                      id::INTEGER AS id,
                      source_key,
                      msgid::INTEGER AS msgid,
                      source_url,
                      region_hint
                    FROM job_sources
                    WHERE posted_at IS NULL
                    ORDER BY created_at DESC, id DESC
                    LIMIT %s
                    """,
                    (max(1, min(limit, 50)),),
                )
                return [dict(row) for row in cur.fetchall()]

    def update_job_source_posted_at(self, source_id: int, posted_at: str) -> None:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE job_sources
                    SET posted_at = %s,
                        updated_at = NOW()
                    WHERE id = %s
                      AND posted_at IS NULL
                    """,
                    (posted_at, source_id),
                )

    def _refresh_source_count(self, cur: Any, job_id: int) -> None:
        cur.execute(
            """
            UPDATE jobs
            SET source_count = (
              SELECT COUNT(*) FROM job_sources WHERE job_id = %s
            ),
            updated_at = NOW()
            WHERE id = %s
            """,
            (job_id, job_id),
        )

    def _find_duplicate_job(
        self,
        cur: Any,
        source_id: int,
        params: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        if not params.get("title") or not params.get("region_hint"):
            return None

        cur.execute(
            """
            SELECT
              j.id,
              j.title,
              j.title_translations,
              j.region_hint,
              j.wage_min,
              j.wage_max,
              j.lat,
              j.lng,
              j.category,
              ps.source_key AS primary_source_key,
              ps.posted_at
            FROM jobs j
            LEFT JOIN job_sources ps ON ps.id = j.primary_source_id
            WHERE j.hidden = FALSE
              AND j.region_hint IS NOT NULL
              AND LOWER(j.region_hint) = LOWER(%s)
              AND j.id NOT IN (
                SELECT COALESCE(job_id, -1) FROM job_sources WHERE id = %s
              )
            ORDER BY j.updated_at DESC
            LIMIT 50
            """,
            (params.get("region_hint"), source_id),
        )

        best = None
        for row in cur.fetchall():
            score, reason = _duplicate_score(params, row)
            if not best or score > best["score"]:
                best = {"job_id": int(row["id"]), "score": score, "reason": reason}
        return best


def _external_id_from_url(source_url: str) -> str:
    parsed = urlparse(source_url)
    return parsed.query or source_url


_DUPLICATE_TITLE_STOPWORDS = {
    "구인", "구합니다", "구함", "모집", "모집합니다", "채용", "직원", "스탭", "스태프",
    "함께", "일하실", "분", "풀타임", "파트타임",
    "hiring", "hire", "job", "jobs", "recruiting", "staff", "wanted", "fulltime", "parttime",
    "募集", "募集中", "求人", "急募", "スタッフ", "採用",
    "招聘", "招募", "员工", "全职", "兼职",
}


def _title_tokens(value: Optional[str]) -> List[str]:
    if not value:
        return []
    normalized = value.casefold().replace("＆", "&")
    tokens = re.findall(r"[^\W_]+", normalized, flags=re.UNICODE)
    return [token for token in tokens if len(token) > 1 and token not in _DUPLICATE_TITLE_STOPWORDS]


def _tokenize(value: Optional[str]) -> Set[str]:
    return set(_title_tokens(value))


def _title_similarity(left: Optional[str], right: Optional[str]) -> float:
    left_sequence = _title_tokens(left)
    right_sequence = _title_tokens(right)
    if not left_sequence or not right_sequence:
        return 0.0
    left_tokens = set(left_sequence)
    right_tokens = set(right_sequence)
    left_normalized = " ".join(left_sequence)
    right_normalized = " ".join(right_sequence)
    if left_normalized == right_normalized:
        return 1.0
    jaccard = len(left_tokens & right_tokens) / len(left_tokens | right_tokens)
    sequence = SequenceMatcher(None, left_normalized, right_normalized).ratio()
    return max(jaccard, sequence)


def _title_candidates(record: Dict[str, Any]) -> List[str]:
    candidates = [str(record.get("title") or "").strip()]
    translations = record.get("title_translations")
    if isinstance(translations, dict):
        candidates.extend(str(value).strip() for value in translations.values())
    return list(dict.fromkeys(value for value in candidates if value))


def _best_title_similarity(source: Dict[str, Any], candidate: Dict[str, Any]) -> tuple:
    best_similarity = 0.0
    best_token_count = 0
    for left in _title_candidates(source):
        for right in _title_candidates(candidate):
            similarity = _title_similarity(left, right)
            token_count = min(len(_tokenize(left)), len(_tokenize(right)))
            if similarity > best_similarity or (
                similarity == best_similarity and token_count > best_token_count
            ):
                best_similarity = similarity
                best_token_count = token_count
    return best_similarity, best_token_count


def _location_similarity(source: Dict[str, Any], candidate: Dict[str, Any]) -> float:
    coordinates = [source.get("lat"), source.get("lng"), candidate.get("lat"), candidate.get("lng")]
    if all(value is not None for value in coordinates):
        source_lat, source_lng, candidate_lat, candidate_lng = [float(value) for value in coordinates]
        radius_km = 6371.0
        lat_delta = radians(candidate_lat - source_lat)
        lng_delta = radians(candidate_lng - source_lng)
        haversine = (
            sin(lat_delta / 2) ** 2
            + cos(radians(source_lat)) * cos(radians(candidate_lat)) * sin(lng_delta / 2) ** 2
        )
        distance_km = 2 * radius_km * asin(sqrt(haversine))
        if distance_km <= 0.1:
            return 1.0
        if distance_km <= 0.3:
            return 0.9
        if distance_km <= 1.0:
            return 0.65
        return 0.0
    return 0.4


def _wage_similarity(
    left_min: Optional[int],
    left_max: Optional[int],
    right_min: Optional[int],
    right_max: Optional[int],
) -> float:
    if not left_min or not right_min:
        return 0.5
    left_high = left_max or left_min
    right_high = right_max or right_min
    overlaps = max(left_min, right_min) <= min(left_high, right_high)
    if overlaps:
        return 1.0
    gap = min(abs(left_min - right_high), abs(right_min - left_high))
    return 0.6 if gap <= 2 else 0.0


def _duplicate_score(source: Dict[str, Any], candidate: Dict[str, Any]) -> tuple:
    title, title_token_count = _best_title_similarity(source, candidate)
    location = _location_similarity(source, candidate)
    wage = _wage_similarity(
        source.get("wage_min"),
        source.get("wage_max"),
        candidate.get("wage_min"),
        candidate.get("wage_max"),
    )
    category = 1.0 if source.get("category") and source.get("category") == candidate.get("category") else 0.5
    score = (title * 0.65) + (location * 0.2) + (wage * 0.1) + (category * 0.05)
    if title >= 0.98 and title_token_count >= 3 and location >= 0.65:
        score = max(score, 0.93)
    if title_token_count < 3:
        score = min(score, 0.89)
    score = round(score, 4)
    return score, {
        "title_similarity": round(title, 4),
        "title_token_count": title_token_count,
        "region_match": True,
        "location_similarity": location,
        "wage_similarity": wage,
        "category_match": source.get("category") == candidate.get("category"),
    }


def _select_auto_merge_pairs(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    matches: List[Dict[str, Any]] = []
    removed_job_ids = set()
    for index, left in enumerate(rows):
        left_id = int(left["id"])
        if left_id in removed_job_ids:
            continue
        for right in rows[index + 1 :]:
            right_id = int(right["id"])
            if right_id in removed_job_ids:
                continue
            if str(left.get("region_hint") or "").casefold() != str(right.get("region_hint") or "").casefold():
                continue
            score, reason = _duplicate_score(left, right)
            if score < AUTO_MERGE_THRESHOLD:
                continue

            keep, remove = sorted(
                (left, right),
                key=lambda row: (-int(row.get("source_count") or 1), int(row["id"])),
            )
            removed_job_ids.add(int(remove["id"]))
            reason = dict(reason, score=score, reconciliation=True)
            matches.append(
                {
                    "keep_job_id": int(keep["id"]),
                    "remove_job_id": int(remove["id"]),
                    "score": score,
                    "reason": reason,
                }
            )
            if int(remove["id"]) == left_id:
                break
    return matches

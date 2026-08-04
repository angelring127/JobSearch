import os
import unittest
from unittest.mock import Mock, patch

from fastapi.testclient import TestClient

import api


class CrawlerRouteTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(api.app)

    def test_health(self):
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok", "service": "crawler"})

    def test_cron_rejects_invalid_authorization(self):
        with patch.dict(os.environ, {"CRON_SECRET": "test-secret"}):
            response = self.client.get(
                "/cron/crawl",
                headers={"Authorization": "Bearer wrong-secret"},
            )
        self.assertEqual(response.status_code, 401)

    def test_cron_accepts_valid_authorization(self):
        summary = {
            "status": "ok",
            "sources": [],
            "processed": 0,
            "created": 0,
            "updated": 0,
            "skipped": 0,
            "failed": 0,
        }
        with (
            patch.dict(os.environ, {"CRON_SECRET": "test-secret"}),
            patch.object(api, "run_enabled_sources", return_value=summary) as run_enabled,
        ):
            response = self.client.get(
                "/cron/crawl",
                headers={"Authorization": "Bearer test-secret"},
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), summary)
        run_enabled.assert_called_once()

    def test_admin_run_forwards_selected_source(self):
        summary = {"status": "ok", "source_key": "vanchosun"}
        with (
            patch.dict(os.environ, {"CRON_SECRET": "test-secret"}),
            patch.object(api, "run_source_crawl", return_value=summary) as run_source,
        ):
            response = self.client.post(
                "/admin/run",
                headers={"Authorization": "Bearer test-secret"},
                json={"source_key": "vanchosun", "max_posts_per_region": 2},
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), summary)
        run_source.assert_called_once_with(
            source_key="vanchosun",
            max_posts_per_region=2,
            trigger_type="manual",
        )

    def test_scheduled_source_limit_uses_ourvancouver_override(self):
        with patch.dict(
            os.environ,
            {
                "CRAWLER_MAX_POSTS_PER_REGION": "4",
                "OURVANCOUVER_MAX_POSTS_PER_REGION": "80",
            },
        ):
            self.assertEqual(api._scheduled_source_limit("ourvancouver"), 80)
            self.assertEqual(api._scheduled_source_limit("vanchosun"), 4)

    def test_refresh_source_preserves_current_listing_order(self):
        db = Mock()
        db.create_crawl_run.return_value = 41
        db.get_source.return_value = {"source_key": "refresh", "enabled": True}
        db.get_last_msgid.return_value = 100
        db.upsert_job.return_value = {"created": True}

        adapter = Mock()
        adapter.refresh_current_listing = True
        adapter.get_regions.return_value = [
            {"city": "Vancouver", "bbs": 1, "listing_url": "https://example.test/jobs"}
        ]
        adapter.get_new_item_ids.return_value = [90, 110, 90]
        adapter.fetch_item.side_effect = lambda item_id, region, client: {
            "msgid": item_id,
            "source_url": "https://example.test/jobs/%s" % item_id,
            "title": "Restaurant role %s" % item_id,
            "region_hint": "Vancouver",
            "location_text": "100 Main St",
            "location_kind": "street_address",
        }

        with (
            patch.dict(api.ADAPTERS, {"refresh": adapter}),
            patch.object(api, "geocode_location", return_value=(49.28, -123.12, 0.8)),
        ):
            summary = api.run_source_crawl("refresh", max_posts_per_region=2, db=db)

        self.assertEqual(summary["processed"], 2)
        self.assertEqual(
            [call.args[0] for call in adapter.fetch_item.call_args_list],
            [90, 110],
        )

    def test_recent_window_source_prioritizes_new_then_unseen_backlog(self):
        db = Mock()
        db.create_crawl_run.return_value = 42
        db.get_source.return_value = {"source_key": "recent", "enabled": True}
        db.get_last_msgid.return_value = 110
        db.get_seen_item_ids.return_value = {115}
        db.upsert_job.return_value = {"created": True}

        adapter = Mock()
        adapter.scan_recent_window = True
        adapter.refresh_current_listing = False
        adapter.get_regions.return_value = [
            {"city": "Vancouver", "bbs": 1, "listing_url": "https://example.test/jobs"}
        ]
        adapter.get_new_item_ids.return_value = [105, 120, 100, 115, 120]
        adapter.fetch_item.side_effect = [
            {
                "msgid": 120,
                "source_url": "https://example.test/jobs/120",
                "title": "New restaurant role",
                "region_hint": "Vancouver",
                "location_text": "100 Main St",
                "location_kind": "street_address",
            },
            None,
        ]

        with (
            patch.dict(api.ADAPTERS, {"recent": adapter}),
            patch.object(api, "geocode_location", return_value=(49.28, -123.12, 0.8)),
        ):
            summary = api.run_source_crawl("recent", max_posts_per_region=2, db=db)

        self.assertEqual([call.args[0] for call in adapter.fetch_item.call_args_list], [120, 105])
        db.get_seen_item_ids.assert_called_once_with("recent", 1, [105, 120, 100, 115])
        self.assertEqual(
            [call.args for call in db.mark_crawl_item_seen.call_args_list],
            [("recent", 1, 120, "stored"), ("recent", 1, 105, "skipped")],
        )
        db.update_last_msgid.assert_called_once_with("recent", 1, 120)
        self.assertEqual(summary["processed"], 1)
        self.assertEqual(summary["skipped"], 1)

    def test_recent_window_failure_is_not_marked_seen(self):
        db = Mock()
        db.create_crawl_run.return_value = 43
        db.get_source.return_value = {"source_key": "recent", "enabled": True}
        db.get_last_msgid.return_value = 110
        db.get_seen_item_ids.return_value = set()

        adapter = Mock()
        adapter.scan_recent_window = True
        adapter.refresh_current_listing = False
        adapter.get_regions.return_value = [
            {"city": "Vancouver", "bbs": 1, "listing_url": "https://example.test/jobs"}
        ]
        adapter.get_new_item_ids.return_value = [120]
        adapter.fetch_item.side_effect = RuntimeError("temporary detail failure")

        with patch.dict(api.ADAPTERS, {"recent": adapter}):
            summary = api.run_source_crawl("recent", max_posts_per_region=1, db=db)

        db.mark_crawl_item_seen.assert_not_called()
        self.assertEqual(summary["failed"], 1)

    def test_enabled_sources_runs_retention_cleanup_once(self):
        db = Mock()
        db.get_enabled_sources.return_value = []
        db.reconcile_duplicate_jobs.return_value = {
            "checked_jobs": 0,
            "candidate_pairs": 0,
            "merged_jobs": 0,
            "moved_sources": 0,
        }
        db.delete_expired_jobs.return_value = {
            "retention_days": 14,
            "deleted_sources": 3,
            "deleted_jobs": 2,
            "reconciled_jobs": 1,
        }

        with (
            patch.object(api, "DirectDbClient", return_value=db),
            patch.object(
                api,
                "backfill_missing_title_translations",
                return_value={"status": "skipped", "reason": "test"},
            ),
            patch.object(
                api,
                "backfill_missing_posted_dates",
                return_value={"status": "ok", "requested": 0, "updated": 0, "failed": 0},
            ),
        ):
            summary = api.run_enabled_sources()

        self.assertEqual(summary["status"], "skipped")
        self.assertEqual(summary["retention"]["status"], "ok")
        self.assertEqual(summary["retention"]["deleted_sources"], 3)
        self.assertEqual(summary["dedupe"]["status"], "ok")
        db.reconcile_duplicate_jobs.assert_called_once_with()
        db.delete_expired_jobs.assert_called_once_with(retention_days=14)

    def test_enabled_sources_translates_before_duplicate_reconciliation(self):
        events = []
        db = Mock()
        db.get_enabled_sources.return_value = []
        db.delete_expired_jobs.return_value = {
            "retention_days": 14,
            "deleted_sources": 0,
            "deleted_jobs": 0,
            "reconciled_jobs": 0,
        }
        db.reconcile_duplicate_jobs.side_effect = lambda: events.append("dedupe") or {
            "checked_jobs": 0,
            "candidate_pairs": 0,
            "merged_jobs": 0,
            "moved_sources": 0,
        }

        with (
            patch.object(api, "DirectDbClient", return_value=db),
            patch.object(
                api,
                "backfill_missing_title_translations",
                side_effect=lambda client: events.append("translate") or {"status": "ok"},
            ),
            patch.object(
                api,
                "backfill_missing_posted_dates",
                return_value={"status": "ok", "requested": 0, "updated": 0, "failed": 0},
            ),
        ):
            api.run_enabled_sources()

        self.assertEqual(events, ["translate", "dedupe"])

    def test_enabled_sources_reports_retention_failure(self):
        db = Mock()
        db.get_enabled_sources.return_value = []
        db.reconcile_duplicate_jobs.return_value = {
            "checked_jobs": 0,
            "candidate_pairs": 0,
            "merged_jobs": 0,
            "moved_sources": 0,
        }
        db.delete_expired_jobs.side_effect = RuntimeError("cleanup failed")

        with (
            patch.object(api, "DirectDbClient", return_value=db),
            patch.object(
                api,
                "backfill_missing_title_translations",
                return_value={"status": "skipped", "reason": "test"},
            ),
            patch.object(
                api,
                "backfill_missing_posted_dates",
                return_value={"status": "ok", "requested": 0, "updated": 0, "failed": 0},
            ),
            self.assertLogs(api.logger, level="ERROR"),
        ):
            summary = api.run_enabled_sources()

        self.assertEqual(summary["status"], "failed")
        self.assertEqual(summary["retention"]["status"], "failed")
        self.assertEqual(summary["retention"]["retention_days"], 14)


if __name__ == "__main__":
    unittest.main()

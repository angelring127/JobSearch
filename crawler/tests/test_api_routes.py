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

    def test_enabled_sources_runs_retention_cleanup_once(self):
        db = Mock()
        db.get_enabled_sources.return_value = []
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
        db.delete_expired_jobs.assert_called_once_with(retention_days=14)

    def test_enabled_sources_reports_retention_failure(self):
        db = Mock()
        db.get_enabled_sources.return_value = []
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

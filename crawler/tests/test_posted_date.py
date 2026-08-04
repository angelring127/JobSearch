import unittest
from unittest.mock import Mock

from posted_date import backfill_missing_posted_dates


class PostedDateBackfillTests(unittest.TestCase):
    def test_backfill_updates_actual_source_dates(self):
        db = Mock()
        db.get_job_sources_missing_posted_at.return_value = [
            {
                "id": 7,
                "source_key": "ourvancouver",
                "msgid": 405999,
                "source_url": "https://m.cafe.daum.net/ourvancouver/1xBD/405999",
                "region_hint": "Vancouver",
            }
        ]
        adapter = Mock()
        adapter.fetch_posted_at.return_value = "2026-08-04T05:35:07"

        summary = backfill_missing_posted_dates(
            db,
            {"ourvancouver": adapter},
            "test-agent",
            client=Mock(),
        )

        self.assertEqual(summary, {"status": "ok", "requested": 1, "updated": 1, "failed": 0})
        db.update_job_source_posted_at.assert_called_once_with(7, "2026-08-04T05:35:07")

    def test_backfill_does_not_substitute_collection_time(self):
        db = Mock()
        db.get_job_sources_missing_posted_at.return_value = [
            {
                "id": 8,
                "source_key": "jinzaicanada",
                "msgid": 3233,
                "source_url": "https://jinzaicanada.com/job/3233",
                "region_hint": "Vancouver",
            }
        ]
        adapter = Mock()
        adapter.fetch_posted_at.return_value = None

        summary = backfill_missing_posted_dates(
            db,
            {"jinzaicanada": adapter},
            "test-agent",
            client=Mock(),
        )

        self.assertEqual(summary, {"status": "partial", "requested": 1, "updated": 0, "failed": 1})
        db.update_job_source_posted_at.assert_not_called()


if __name__ == "__main__":
    unittest.main()

import fcntl
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from run_scheduled import exit_code_for_result, run_once


class ScheduledRunnerTests(unittest.TestCase):
    def _environment(self):
        return patch.dict(
            os.environ,
            {
                "DATABASE_URL": "postgresql://example.invalid/jobmap",
                "CODEX_BRIDGE_BASE_URL": "http://127.0.0.1:9999",
                "CODEX_BRIDGE_API_KEY": "test-key",
            },
        )

    def test_runs_enabled_sources_with_cron_trigger(self):
        runner = Mock(return_value={"status": "ok", "title_translation": {"status": "ok"}})
        with tempfile.TemporaryDirectory() as directory, self._environment():
            result = run_once(runner=runner, lock_path=Path(directory) / "crawl.lock")

        self.assertEqual(result["status"], "ok")
        runner.assert_called_once_with(trigger_type="cron")

    def test_skips_when_another_process_owns_the_lock(self):
        runner = Mock()
        with tempfile.TemporaryDirectory() as directory, self._environment():
            lock_path = Path(directory) / "crawl.lock"
            with lock_path.open("a+", encoding="utf-8") as lock_file:
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                result = run_once(runner=runner, lock_path=lock_path)

        self.assertEqual(result, {"status": "skipped", "reason": "already_running"})
        runner.assert_not_called()

    def test_rejects_missing_production_environment(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(RuntimeError, "DATABASE_URL"):
                run_once(runner=Mock(), lock_path=Path(directory) / "crawl.lock")

    def test_marks_partial_title_translation_as_failed_run(self):
        self.assertEqual(
            exit_code_for_result({"status": "ok", "title_translation": {"status": "partial"}}),
            1,
        )
        self.assertEqual(
            exit_code_for_result({"status": "partial", "title_translation": {"status": "ok"}}),
            0,
        )


if __name__ == "__main__":
    unittest.main()

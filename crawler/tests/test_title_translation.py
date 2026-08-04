import unittest
from unittest.mock import Mock, patch

from title_translation import backfill_missing_title_translations, parse_translation_response


class TitleTranslationTests(unittest.TestCase):
    def test_parses_complete_translation_and_normalizes_whitespace(self):
        source_jobs = [{"id": 7, "title": "주방 직원 모집"}]
        result = parse_translation_response(
            '{"translations":[{"id":7,"ko":"주방 직원 모집","en":"Hiring kitchen staff",'
            '"ja":"キッチン スタッフ募集","zh":"招聘厨房员工"}]}',
            source_jobs,
        )

        self.assertEqual(result[7]["en"], "Hiring kitchen staff")
        self.assertEqual(result[7]["ja"], "キッチン スタッフ募集")

    def test_rejects_partial_or_unknown_translation_items(self):
        source_jobs = [{"id": 7, "title": "Kitchen staff"}]
        result = parse_translation_response(
            '{"translations":['
            '{"id":7,"ko":"주방 직원","en":"Kitchen staff","ja":"キッチンスタッフ"},'
            '{"id":99,"ko":"가짜","en":"Fake","ja":"偽","zh":"假"}]}' ,
            source_jobs,
        )

        self.assertEqual(result, {})

    def test_backfill_updates_only_complete_results(self):
        db = Mock()
        db.get_jobs_missing_title_translations.return_value = [
            {"id": 1, "title": "Server wanted"},
            {"id": 2, "title": "Cook wanted"},
        ]
        translator = Mock()
        translator.translate_batch.return_value = {
            1: {"ko": "서버 모집", "en": "Server wanted", "ja": "サーバー募集", "zh": "招聘服务员"},
        }

        summary = backfill_missing_title_translations(db, translator=translator, limit=20)

        self.assertEqual(summary, {"status": "partial", "requested": 2, "translated": 1, "failed": 1})
        db.update_job_title_translations.assert_called_once_with(
            1,
            {"ko": "서버 모집", "en": "Server wanted", "ja": "サーバー募集", "zh": "招聘服务员"},
        )

    def test_backfill_skips_without_configured_translator(self):
        db = Mock()
        with patch.dict(
            "os.environ",
            {"CODEX_BRIDGE_BASE_URL": "", "CODEX_BRIDGE_API_KEY": ""},
        ):
            summary = backfill_missing_title_translations(db, translator=None)
        self.assertEqual(summary["status"], "skipped")
        db.get_jobs_missing_title_translations.assert_not_called()


if __name__ == "__main__":
    unittest.main()

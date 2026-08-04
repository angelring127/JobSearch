import unittest

from db_direct import AUTO_MERGE_THRESHOLD, _duplicate_score, _select_auto_merge_pairs, _title_similarity


def job(job_id, title, *, source_count=1, role_category="restaurant", lat=49.28, lng=-123.12):
    return {
        "id": job_id,
        "title": title,
        "region_hint": "Vancouver",
        "wage_min": 18,
        "wage_max": 20,
        "lat": lat,
        "lng": lng,
        "category": role_category,
        "source_count": source_count,
        "title_translations": {},
    }


class DuplicateScoringTests(unittest.TestCase):
    def test_unicode_korean_titles_participate_in_similarity(self):
        similarity = _title_similarity(
            "로히드 홍대불족 서버 구인",
            "로히드 홍대불족 서버 모집",
        )
        self.assertGreaterEqual(similarity, 0.95)

    def test_exact_substantive_title_at_same_location_auto_merges(self):
        score, reason = _duplicate_score(
            job(1, "Sushi Box 롤맨 풀타임 모집"),
            job(2, "Sushi Box 롤맨 구인"),
        )
        self.assertGreaterEqual(score, AUTO_MERGE_THRESHOLD)
        self.assertGreaterEqual(reason["title_token_count"], 2)

    def test_generic_one_token_title_never_auto_merges(self):
        score, _ = _duplicate_score(job(1, "서버 구인"), job(2, "서버 모집"))
        self.assertLess(score, AUTO_MERGE_THRESHOLD)

    def test_generic_two_token_title_never_auto_merges(self):
        score, _ = _duplicate_score(job(1, "Restaurant Server"), job(2, "Restaurant Server"))
        self.assertLess(score, AUTO_MERGE_THRESHOLD)

    def test_missing_coordinates_do_not_auto_merge_on_title_alone(self):
        left = job(1, "Hibiki Ramen Server")
        right = job(2, "Hibiki Ramen Server")
        left["lat"] = left["lng"] = None
        right["lat"] = right["lng"] = None
        score, _ = _duplicate_score(left, right)
        self.assertLess(score, AUTO_MERGE_THRESHOLD)

    def test_different_roles_at_same_business_remain_separate(self):
        score, _ = _duplicate_score(
            job(1, "로히드 홍대불족 서버 구인"),
            job(2, "로히드 홍대불족 디시워셔 구인"),
        )
        self.assertLess(score, AUTO_MERGE_THRESHOLD)

    def test_reconciliation_prefers_existing_multi_source_representative(self):
        rows = [
            job(20, "Hibiki Ramen Yakitori Bar", source_count=1),
            job(10, "Hibiki Ramen Yakitori Bar", source_count=2),
        ]
        matches = _select_auto_merge_pairs(rows)
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0]["keep_job_id"], 10)
        self.assertEqual(matches[0]["remove_job_id"], 20)

    def test_translated_titles_enable_cross_language_duplicate_match(self):
        japanese = job(1, "響ラーメンでサーバー募集")
        japanese["title_translations"] = {"en": "Hibiki Ramen hiring servers"}
        korean = job(2, "히비키 라멘 서버 구인")
        korean["title_translations"] = {"en": "Hibiki Ramen hiring servers"}
        score, _ = _duplicate_score(japanese, korean)
        self.assertGreaterEqual(score, AUTO_MERGE_THRESHOLD)


if __name__ == "__main__":
    unittest.main()

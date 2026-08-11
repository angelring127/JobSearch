import unittest
from unittest.mock import Mock

from job_quality import curate_ourvancouver_job


def job(item_id, title, content, location_text=None, region_hint=""):
    return {
        "msgid": item_id,
        "source_url": "https://m.cafe.daum.net/ourvancouver/1xBD/%s" % item_id,
        "title": title,
        "region_hint": region_hint,
        "location_text": location_text,
        "location_kind": "street_address" if location_text else "none",
        "_content": content,
    }


class JobQualityTests(unittest.TestCase):
    def test_rejects_product_promotion_without_calling_ai(self):
        analyzer = Mock()
        result = curate_ourvancouver_job(
            job(405996, "ROGERS (SHAW) Internet/TV/Mobile Special Promotion", "신규 개통 할인"),
            analyzer,
        )
        self.assertIsNone(result)
        analyzer.analyze.assert_not_called()

    def test_rejects_tutor_service_without_calling_ai(self):
        analyzer = Mock()
        result = curate_ourvancouver_job(
            job(405991, "기초 영어회화, 시험영어 튜터 해드립니다", "영어 수업을 제공합니다"),
            analyzer,
        )
        self.assertIsNone(result)
        analyzer.analyze.assert_not_called()

    def test_rejects_locationless_job_after_ai_review(self):
        analyzer = Mock()
        analyzer.analyze.return_value = {
            "is_job_posting": True,
            "location_kind": "none",
            "location_query": None,
            "region_hint": None,
        }
        result = curate_ourvancouver_job(
            job(405997, "서버와 주방보조 구인 합니다", "이메일로 이력서를 보내주세요"),
            analyzer,
        )
        self.assertIsNone(result)

    def test_rejects_city_only_job_after_ai_review(self):
        analyzer = Mock()
        analyzer.analyze.return_value = {
            "is_job_posting": True,
            "location_kind": "city_only",
            "location_query": "Vancouver",
            "region_hint": "Vancouver",
        }
        result = curate_ourvancouver_job(
            job(405994, "밴쿠버 지사 직원 채용", "게임 프레젠터를 모집합니다"),
            analyzer,
        )
        self.assertIsNone(result)

    def test_uses_lougheed_title_as_grounded_neighborhood(self):
        analyzer = Mock()
        analyzer.analyze.return_value = {
            "is_job_posting": True,
            "location_kind": "business_or_landmark",
            "location_query": "Hongdae Buljok Lougheed",
            "region_hint": "Burnaby",
        }
        result = curate_ourvancouver_job(
            job(405992, "로히드홍대불족 디쉬 구인합니다", "주방보조와 디시워셔 모집"),
            analyzer,
        )
        self.assertIsNotNone(result)
        self.assertEqual(result["location_text"], "Hongdae Buljok Lougheed")
        self.assertNotIn("location_fallback_text", result)
        self.assertEqual(result["region_hint"], "Burnaby")
        self.assertEqual(result["location_kind"], "business_or_landmark")

    def test_accepts_grounded_ai_business_location(self):
        analyzer = Mock()
        analyzer.analyze.return_value = {
            "is_job_posting": True,
            "location_kind": "business_or_landmark",
            "location_query": "Example Sushi Metrotown",
            "region_hint": "Burnaby",
        }
        result = curate_ourvancouver_job(
            job(1, "스시 직원 모집", "Example Sushi 메트로타운 지점"),
            analyzer,
        )
        self.assertIsNotNone(result)
        self.assertEqual(result["location_text"], "Example Sushi Metrotown")
        self.assertNotIn("location_fallback_text", result)
        self.assertEqual(result["region_hint"], "Burnaby")

    def test_prefers_hongdae_pocha_business_over_robson_street_center(self):
        analyzer = Mock()
        analyzer.analyze.return_value = {
            "is_job_posting": True,
            "location_kind": "business_or_landmark",
            "location_query": "Hongdae Pocha Robson downtown",
            "region_hint": "Downtown Robson",
        }
        result = curate_ourvancouver_job(
            job(405995, "다운타운 랍슨 홍대포차에서 주방직원 모집", "홍대포차 팀원 모집"),
            analyzer,
        )
        self.assertIsNotNone(result)
        self.assertEqual(result["location_text"], "Hongdae Pocha Robson")
        self.assertNotIn("location_fallback_text", result)
        self.assertEqual(result["region_hint"], "Vancouver")

    def test_ai_neighborhood_is_not_overridden_by_downtown_title(self):
        analyzer = Mock()
        analyzer.analyze.return_value = {
            "is_job_posting": True,
            "location_kind": "neighborhood",
            "location_query": "Lonsdale, North Vancouver, BC",
            "region_hint": "North Vancouver",
        }
        result = curate_ourvancouver_job(
            job(
                405984,
                "노스밴 포케바 라인서버, 키친헬퍼 구인합니다.",
                "위치: 노스밴 론즈데일 다운타운",
            ),
            analyzer,
        )
        self.assertIsNotNone(result)
        self.assertEqual(result["location_text"], "Lonsdale, North Vancouver, BC")
        self.assertEqual(result["region_hint"], "North Vancouver")
        self.assertEqual(result["location_kind"], "neighborhood")

    def test_rejects_multiple_locations_for_one_map_marker(self):
        analyzer = Mock()
        analyzer.analyze.return_value = {
            "is_job_posting": True,
            "location_kind": "street_address",
            "location_query": "4635 Kingsway; 6611 Kingsway",
            "region_hint": "Burnaby",
        }
        result = curate_ourvancouver_job(
            job(405981, "두 지점 서버 구합니다", "4635 Kingsway 또는 6611 Kingsway에서 모집"),
            analyzer,
        )
        self.assertIsNone(result)

    def test_normalizes_address_unit_and_vancouver_landmark_suffix(self):
        analyzer = Mock()
        analyzer.analyze.return_value = {
            "is_job_posting": True,
            "location_kind": "street_address",
            "location_query": "#210 - 150 Esplanade W North Vancouver, BC V7M 1A3",
            "region_hint": "North Vancouver",
        }
        result = curate_ourvancouver_job(
            job(405983, "레스토랑 오픈 멤버 모집", "근무지 #210 - 150 Esplanade W North Vancouver, BC V7M 1A3"),
            analyzer,
        )
        self.assertIsNotNone(result)
        self.assertEqual(result["location_text"], "150 Esplanade W North Vancouver, BC V7M 1A3")


if __name__ == "__main__":
    unittest.main()

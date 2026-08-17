import unittest
from datetime import datetime
from unittest.mock import Mock

import httpx

from adapters import (
    CASMO_LISTING_REQUEST_INTERVAL,
    CasmoAdapter,
    _casmo_article_is_eligible,
)


def article(item_id, title, *, elapsed="5분 전", depth=None, head="구인"):
    return {
        "dataid": item_id,
        "title": title,
        "articleElapsedTime": elapsed,
        "bbsDepth": depth or "depth-%s" % item_id,
        "headCont": head,
    }


class CasmoAdapterTests(unittest.TestCase):
    def test_public_listing_is_bounded_and_filters_unsafe_titles(self):
        requested_paths = []
        requested_pages = []
        sleeper = Mock()
        pages = {
            1: [
                article(637174, "Hay Sushi 노스욕 1호점 서버 구인"),
                article(637173, "노스욕 일자리 구합니다", head="구직"),
                article(637172, "토론토 자원봉사자 모집"),
                article(637171, "토론토 스탭 모집 416-555-1212"),
                article(637170, "이민 상담 서비스"),
            ],
            2: [article(637169, "5310 Yonge St, North York, ON 주방 직원 모집")],
        }

        def handler(request):
            requested_paths.append(request.url.path)
            self.assertEqual(request.url.path, "/api/v1/common-articles")
            page = int(request.url.params["targetPage"])
            requested_pages.append(page)
            self.assertEqual(request.url.params["grpid"], "7rX")
            self.assertEqual(request.url.params["fldid"], "8cBB")
            self.assertEqual(request.url.params["pageSize"], "20")
            if page == 1:
                self.assertNotIn("afterBbsDepth", request.url.params)
            else:
                self.assertEqual(request.url.params["afterBbsDepth"], "depth-637170")
            return httpx.Response(200, json={"articles": pages[page]})

        adapter = CasmoAdapter(max_listing_pages=2, sleeper=sleeper)
        region = adapter.get_regions(None)[0]
        with httpx.Client(transport=httpx.MockTransport(handler)) as client:
            item_ids = adapter.get_new_item_ids(region, last_seen_id=999999, client=client)

        self.assertEqual(item_ids, [637174, 637169])
        self.assertEqual(requested_pages, [1, 2])
        self.assertEqual(requested_paths, ["/api/v1/common-articles"] * 2)
        self.assertEqual(
            sleeper.call_args_list,
            [
                unittest.mock.call(CASMO_LISTING_REQUEST_INTERVAL),
                unittest.mock.call(CASMO_LISTING_REQUEST_INTERVAL),
            ],
        )

    def test_fetch_uses_cached_title_only_and_never_requests_detail(self):
        analyzer = Mock()
        analyzer.analyze.return_value = {
            "is_job_posting": True,
            "location_kind": "business_or_landmark",
            "location_query": "Hay Sushi, North York, ON",
            "region_hint": "North York",
            "reason": "Business and city are present in the title",
        }
        adapter = CasmoAdapter(
            now_provider=lambda: datetime(2026, 8, 17, 12, 0, 0),
            analyzer=analyzer,
            sleeper=Mock(),
        )
        adapter._articles = {
            637174: article(637174, "Hay Sushi 노스욕 1호점 서버 구인", elapsed="5분 전")
        }

        def fail_on_request(request):
            self.fail("Casmo fetch_item must not request member-only detail: %s" % request.url)

        with httpx.Client(transport=httpx.MockTransport(fail_on_request)) as client:
            job = adapter.fetch_item(637174, adapter.get_regions(None)[0], client)

        self.assertEqual(job["source_url"], "https://m.cafe.daum.net/skc67/8cBB/637174")
        self.assertEqual(job["region_hint"], "North York")
        self.assertEqual(job["location_text"], "Hay Sushi, North York, ON")
        self.assertEqual(job["location_kind"], "business_or_landmark")
        self.assertEqual(job["posted_at"], "2026-08-17T11:55:00")
        analyzer.analyze.assert_called_once_with(job["title"], job["title"])

    def test_grounded_street_address_bypasses_title_analyzer(self):
        analyzer = Mock()
        adapter = CasmoAdapter(analyzer=analyzer, sleeper=Mock())
        adapter._articles = {
            637169: article(637169, "5310 Yonge St, North York, ON 주방 직원 모집")
        }

        job = adapter.fetch_item(637169, adapter.get_regions(None)[0], Mock())

        self.assertEqual(job["location_kind"], "street_address")
        self.assertIn("5310 Yonge St", job["location_text"])
        analyzer.analyze.assert_not_called()

    def test_missing_or_failed_title_analysis_remains_retryable(self):
        adapters = [
            CasmoAdapter(analyzer=None, sleeper=Mock()),
            CasmoAdapter(analyzer=Mock(analyze=Mock(return_value=None)), sleeper=Mock()),
        ]
        for adapter in adapters:
            adapter.analyzer = adapter.analyzer if adapter is adapters[1] else None
            adapter._articles = {
                637174: article(637174, "Hay Sushi 노스욕 1호점 서버 구인")
            }
            with self.subTest(analyzer=adapter.analyzer):
                with self.assertRaisesRegex(RuntimeError, "retryable"):
                    adapter.fetch_item(637174, adapter.get_regions(None)[0], Mock())

    def test_invalid_or_ungrounded_title_analysis_remains_retryable(self):
        invalid_results = [
            {"location_kind": "business_or_landmark", "location_query": "Hay Sushi"},
            {
                "is_job_posting": True,
                "location_kind": "business_or_landmark",
                "location_query": "Invented Cafe, North York, ON",
                "region_hint": "North York",
            },
        ]
        for analysis in invalid_results:
            analyzer = Mock()
            analyzer.analyze.return_value = analysis
            adapter = CasmoAdapter(analyzer=analyzer, sleeper=Mock())
            adapter._articles = {
                637174: article(637174, "Hay Sushi 노스욕 1호점 서버 구인")
            }
            with self.subTest(analysis=analysis):
                with self.assertRaisesRegex(RuntimeError, "retryable"):
                    adapter.fetch_item(637174, adapter.get_regions(None)[0], Mock())

    def test_new_listing_scan_resets_transient_analysis_outage(self):
        analyzer = Mock()
        analyzer.analyze.side_effect = [
            None,
            {
                "is_job_posting": True,
                "location_kind": "business_or_landmark",
                "location_query": "Hay Sushi, North York, ON",
                "region_hint": "North York",
            },
        ]
        adapter = CasmoAdapter(analyzer=analyzer, max_listing_pages=1, sleeper=Mock())
        region = adapter.get_regions(None)[0]

        def handler(request):
            return httpx.Response(
                200,
                json={"articles": [article(637174, "Hay Sushi 노스욕 1호점 서버 구인")]},
            )

        with httpx.Client(transport=httpx.MockTransport(handler)) as client:
            adapter.get_new_item_ids(region, 0, client)
            with self.assertRaisesRegex(RuntimeError, "retryable"):
                adapter.fetch_item(637174, region, client)
            adapter.get_new_item_ids(region, 0, client)
            job = adapter.fetch_item(637174, region, client)

        self.assertEqual(job["location_text"], "Hay Sushi, North York, ON")
        self.assertEqual(analyzer.analyze.call_count, 2)

    def test_cityless_title_is_rejected_before_analysis(self):
        analyzer = Mock()
        adapter = CasmoAdapter(analyzer=analyzer, sleeper=Mock())
        adapter._articles = {637160: article(637160, "Sushi House 서버 구인")}

        self.assertIsNone(adapter.fetch_item(637160, adapter.get_regions(None)[0], Mock()))
        analyzer.analyze.assert_not_called()

    def test_malformed_page_fails_closed_and_still_observes_delay(self):
        sleeper = Mock()
        adapter = CasmoAdapter(max_listing_pages=1, sleeper=sleeper)

        def handler(request):
            return httpx.Response(200, json={"articles": "not-a-list"})

        with httpx.Client(transport=httpx.MockTransport(handler)) as client:
            with self.assertRaisesRegex(RuntimeError, "malformed articles"):
                adapter.get_new_item_ids(adapter.get_regions(None)[0], 0, client)

        sleeper.assert_called_once_with(CASMO_LISTING_REQUEST_INTERVAL)

    def test_eligibility_rejects_job_seeker_volunteer_and_contact_titles(self):
        rejected = [
            article(1, "[구직] 토론토 주방 직원 일자리 찾습니다"),
            article(2, "토론토 자원 봉사자 모집"),
            article(3, "토론토 서버 구인 test@example.com"),
            article(4, "토론토 서버 구인 647.555.1212"),
            article(5, "토론토 주방 직원 일자리 찾습니다", head=""),
            article(6, "토론토 이력서 작성 서비스 스탭 모집", head=""),
        ]
        self.assertTrue(all(not _casmo_article_is_eligible(item) for item in rejected))


if __name__ == "__main__":
    unittest.main()

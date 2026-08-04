import unittest
from datetime import date

import httpx
from unittest.mock import patch

from adapters import OurVancouverAdapter


def _listing_article(item_id, elapsed, depth):
    return """
    {
      dataid: %s,
      articleElapsedTime: '%s',
      bbsDepth: '%s'
    }
    """ % (item_id, elapsed, depth)


class OurVancouverPaginationTests(unittest.TestCase):
    def test_detail_fetch_uses_single_dated_desktop_response(self):
        requested_paths = []
        detail = """
        <script>CAFEAPP.ui = { PLAIN_REGDT: '20260803112233' };</script>
        <div class="bbs_read_tit"><span class="article_title">버나비 식당 주방 직원 모집</span></div>
        <div class="tx-content-container">1234 Kingsway, Burnaby, BC에서 직원을 모집합니다.</div>
        """

        def handler(request):
            requested_paths.append(request.url.path)
            return httpx.Response(200, text=detail)

        adapter = OurVancouverAdapter(today_provider=lambda: date(2026, 8, 3))
        region = {"city": "Vancouver", "bbs": 1, "listing_url": adapter.listing_url}
        with (
            httpx.Client(transport=httpx.MockTransport(handler)) as client,
            patch("adapters.time.sleep"),
        ):
            job = adapter.fetch_item(406024, region, client)

        self.assertIsNotNone(job)
        self.assertEqual(job["posted_at"], "2026-08-03T11:22:33")
        self.assertEqual(requested_paths, ["/_c21_/bbs_read"])

    def test_scans_recent_window_below_checkpoint_and_stops_after_expired_pages(self):
        first_page = "var articles = [%s, %s];" % (
            _listing_article(105, "3분 전", "depth-105"),
            _listing_article(104, "26.08.03", "depth-104"),
        )
        requested_pages = []

        def handler(request):
            if request.url.path == "/ourvancouver/1xBD":
                return httpx.Response(200, text=first_page)

            self.assertEqual(request.url.path, "/api/v1/common-articles")
            page = int(request.url.params["targetPage"])
            requested_pages.append(page)
            self.assertEqual(request.url.params["grpid"], "hPc")
            self.assertEqual(request.url.params["fldid"], "1xBD")
            self.assertEqual(request.url.params["pageSize"], "20")

            pages = {
                2: [
                    {"dataid": 103, "articleElapsedTime": "26.07.25", "bbsDepth": "depth-103"},
                    {"dataid": 102, "articleElapsedTime": "26.07.24", "bbsDepth": "depth-102"},
                    {"dataid": 104, "articleElapsedTime": "26.08.03", "bbsDepth": "duplicate"},
                ],
                3: [
                    {"dataid": 101, "articleElapsedTime": "26.07.19", "bbsDepth": "depth-101"},
                ],
                4: [
                    {"dataid": 100, "articleElapsedTime": "26.07.18", "bbsDepth": "depth-100"},
                ],
            }
            return httpx.Response(200, json={"articles": pages[page]})

        adapter = OurVancouverAdapter(today_provider=lambda: date(2026, 8, 3))
        region = {"city": "Vancouver", "bbs": 1, "listing_url": adapter.listing_url}
        with httpx.Client(transport=httpx.MockTransport(handler)) as client:
            result = adapter.get_new_item_ids(region, last_seen_id=103, client=client)

        self.assertEqual(result, [105, 104, 103, 102])
        self.assertEqual(requested_pages, [2, 3, 4])

    def test_raises_when_recent_window_exceeds_page_ceiling(self):
        first_page = "var articles = [%s];" % _listing_article(105, "26.08.03", "depth-105")

        def handler(request):
            if request.url.path == "/ourvancouver/1xBD":
                return httpx.Response(200, text=first_page)
            return httpx.Response(
                200,
                json={
                    "articles": [
                        {"dataid": 104, "articleElapsedTime": "26.08.03", "bbsDepth": "depth-104"}
                    ]
                },
            )

        adapter = OurVancouverAdapter(
            today_provider=lambda: date(2026, 8, 3),
            max_listing_pages=2,
        )
        region = {"city": "Vancouver", "bbs": 1, "listing_url": adapter.listing_url}
        with httpx.Client(transport=httpx.MockTransport(handler)) as client:
            with self.assertRaisesRegex(RuntimeError, "page ceiling"):
                adapter.get_new_item_ids(region, last_seen_id=0, client=client)

    def test_raises_for_partial_first_page_metadata(self):
        malformed = """
        var articles = [
          { dataid: 105, articleElapsedTime: '26.08.03' },
          { dataid: 104, articleElapsedTime: '26.08.03', bbsDepth: 'depth-104' }
        ];
        """

        adapter = OurVancouverAdapter(today_provider=lambda: date(2026, 8, 3))
        region = {"city": "Vancouver", "bbs": 1, "listing_url": adapter.listing_url}

        def handler(request):
            return httpx.Response(200, text=malformed)

        with httpx.Client(transport=httpx.MockTransport(handler)) as client:
            with self.assertRaisesRegex(RuntimeError, "article metadata"):
                adapter.get_new_item_ids(region, last_seen_id=0, client=client)


if __name__ == "__main__":
    unittest.main()

import unittest

from adapters import get_adapter_registry
from crawler import parse_category
from source_parsers import (
    extract_jinzaicanada_ids,
    extract_ourvancouver_ids,
    extract_vanchosun_ids,
    parse_jinzaicanada_job,
    parse_ourvancouver_job,
    parse_vanchosun_job,
)


class SourceParserTests(unittest.TestCase):
    def test_registry_contains_all_public_sources(self):
        self.assertEqual(
            set(get_adapter_registry()),
            {"jpcanada", "ourvancouver", "jinzaicanada", "vanchosun"},
        )

    def test_ourvancouver_listing_and_detail(self):
        listing = "dataid: 405974, dataid: 405973, dataid: 405974,"
        self.assertEqual(extract_ourvancouver_ids(listing, 405973), [405974])

        detail = """
        <script>CAFEAPP.ui = { PLAIN_REGDT: '20260802143509' };</script>
        <article><div class="bbs_read_tit"><span class="article_title">버나비 식당 주방 직원 모집</span></div>
        <div class="tx-content-container">근무지 Burnaby, BC. 시급 $22.00</div></article>
        """
        job = parse_ourvancouver_job(detail, "https://example.test/405974", 405974)
        self.assertIsNotNone(job)
        self.assertEqual(job["region_hint"], "Burnaby")
        self.assertEqual(job["wage_min"], 22)
        self.assertEqual(job["category"], "restaurant")
        self.assertEqual(job["posted_at"], "2026-08-02T14:35:09")

    def test_jinzaicanada_listing_and_detail(self):
        listing = """
        <a class="job-list__item" href="/job/3378">Newest</a>
        <a class="job-list__item" href="/job/3377">Older</a>
        """
        self.assertEqual(extract_jinzaicanada_ids(listing, 3377), [3378])

        detail = """
        <meta property="article:published_time" content="2026-08-01 08:30:15" />
        <main class="job-detail">
          <h1 class="entry-title">Kitchen staff</h1>
          <div>掲載日: 2026/08/02</div>
          <table>
            <tr><th>エリア</th><td>Vancouver Area, BC</td></tr>
            <tr><th>本社所在地</th><td>210-406 6th St, New Westminster, BC, Suite 600</td></tr>
            <tr><th>ポジション</th><td>Restaurant / Food</td></tr>
            <tr><th>時給</th><td>$18.25</td></tr>
          </table>
        </main>
        """
        job = parse_jinzaicanada_job(detail, "https://example.test/job/3378", 3378)
        self.assertIsNotNone(job)
        self.assertEqual(job["region_hint"], "New Westminster")
        self.assertEqual(job["location_text"], "406 6th St, New Westminster, BC")
        self.assertEqual(job["posted_at"], "2026-08-01T08:30:15")

    def test_vanchosun_filters_job_rows_and_parses_detail(self):
        listing = """
        <table>
          <tr class="marketListTr job_findworker"><td><a href="frame.php?main=job&amp;bdId=89001">구인</a></td></tr>
          <tr class="marketListTr job_premium"><td><a href="frame.php?main=job&amp;bdId=99999">광고</a></td></tr>
        </table>
        """
        self.assertEqual(extract_vanchosun_ids(listing, 0), [89001])

        detail = """
        <div id="cf_middle">
          <font><b>랭리 레스토랑 서버 구인</b></font>
          <div>등록일 : 2026-08-02</div>
          <table><tr>
            <td class="board_section_frame1">희망임금</td><td class="board_section_frame2">시급 $18.25</td>
            <td class="board_section_frame1">근무지역</td><td class="board_section_frame2">랭리</td>
          </tr></table>
          <div id="div_overflow">19933 88th Avenue, Langley, BC 주방 직원 모집</div>
        </div>
        """
        job = parse_vanchosun_job(detail, "https://example.test/?bdId=89001", 89001)
        self.assertIsNotNone(job)
        self.assertEqual(job["region_hint"], "Langley")
        self.assertIn("19933 88th Avenue", job["location_text"])
        self.assertEqual(job["category"], "restaurant")
        self.assertEqual(job["posted_at"], "2026-08-02T00:00:00")

    def test_multilingual_categories(self):
        self.assertEqual(parse_category("주방 직원", ""), "restaurant")
        self.assertEqual(parse_category("물류 배송 담당자", ""), "warehouse")


if __name__ == "__main__":
    unittest.main()

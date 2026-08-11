import unittest

from crawler import parse_job_post


def post_html(item_id: int, title: str, content: str) -> str:
    return """
    <div>
      <span>No.%s</span>
      <h2>%s</h2>
      <p>%s</p>
    </div>
    """ % (item_id, title, content)


class JPCanadaLocationKindTests(unittest.TestCase):
    def test_city_only_post_does_not_claim_a_precise_location(self):
        job = parse_job_post(
            post_html(
                1001,
                "Staff hiring now",
                "We are hiring experienced staff in Vancouver for a full-time role with flexible shifts.",
            ),
            "https://example.test/topics.php?msgid=1001",
            1001,
        )
        self.assertEqual(job["location_text"], "Vancouver, BC")
        self.assertEqual(job["location_kind"], "city_only")

    def test_named_business_post_uses_business_location_kind(self):
        job = parse_job_post(
            post_html(
                1002,
                "Example Sushi staff hiring",
                "Example Sushi is hiring experienced kitchen staff in Vancouver for weekday and weekend shifts.",
            ),
            "https://example.test/topics.php?msgid=1002",
            1002,
        )
        self.assertEqual(job["location_kind"], "business_or_landmark")
        self.assertIn("Example Sushi", job["location_text"])

    def test_numbered_street_post_uses_street_address_kind(self):
        job = parse_job_post(
            post_html(
                1003,
                "Kitchen staff hiring",
                "We are hiring kitchen staff at 1234 Main Street, Vancouver, BC for regular full-time shifts.",
            ),
            "https://example.test/topics.php?msgid=1003",
            1003,
        )
        self.assertEqual(job["location_kind"], "street_address")
        self.assertIn("1234 Main Street", job["location_text"])


if __name__ == "__main__":
    unittest.main()

import unittest
from unittest.mock import Mock, patch

from geocoding import geocode_location, get_region_center


class GeocodingTests(unittest.TestCase):
    def test_precise_location_does_not_fall_back_to_city_center(self):
        response = Mock(status_code=200)
        response.json.return_value = []
        with patch("geocoding.httpx.get", return_value=response):
            result = geocode_location(
                "Unknown Business, Cambie St, Vancouver",
                "Vancouver",
                allow_region_fallback=False,
            )
        self.assertEqual(result, (None, None, 0.3))

    def test_unknown_region_has_no_vancouver_default(self):
        self.assertEqual(get_region_center("Campbell River"), (None, None, 0.3))


if __name__ == "__main__":
    unittest.main()

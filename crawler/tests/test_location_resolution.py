import unittest
from unittest.mock import patch

from location_resolution import (
    apply_verified_business_location,
    has_street_address,
    resolve_map_location,
)


class LocationResolutionTests(unittest.TestCase):
    def test_street_address_requires_a_leading_street_number(self):
        self.assertTrue(has_street_address("1205 Davie Street, Vancouver, BC"))
        self.assertTrue(has_street_address("Restaurant, 82 Keefer Pl, Vancouver, BC"))
        self.assertFalse(has_street_address("Mississauga, Ontario L5B 4N4, Canada"))

    def test_verified_business_catalog_promotes_named_business_to_address(self):
        result = apply_verified_business_location(
            {
                "title": "[다운타운 K-Well Integrative Wellness Clinic] 리셉셔니스트 모집",
                "location_text": "K-Well Integrative Wellness Clinic",
                "region_hint": "Vancouver",
                "location_kind": "business_or_landmark",
            }
        )
        self.assertEqual(
            result["location_text"],
            "889 W Pender St, Vancouver, BC",
        )
        self.assertEqual(result["location_kind"], "street_address")

    def test_verified_catalog_matches_korean_business_alias(self):
        result = apply_verified_business_location(
            {
                "title": "밴막 다운타운 서버겸 주방 구인",
                "location_text": "Stadium-Chinatown Station, Vancouver, BC",
                "region_hint": "Vancouver",
                "location_kind": "business_or_landmark",
            }
        )
        self.assertEqual(result["location_text"], "82 Keefer Pl, Vancouver, BC V6B 6C1")
        self.assertEqual(result["location_kind"], "street_address")

    def test_multi_location_business_requires_matching_location_context(self):
        original = {
            "title": "K-Well Integrative Wellness Clinic Langley receptionist",
            "location_text": "K-Well Integrative Wellness Clinic Langley",
            "region_hint": "Langley",
            "location_kind": "business_or_landmark",
        }
        self.assertEqual(apply_verified_business_location(original), original)

    def test_business_alias_does_not_match_a_longer_word(self):
        original = {
            "title": "Vanmaker Downtown warehouse role",
            "location_text": "Vanmaker Downtown",
            "region_hint": "Vancouver",
            "location_kind": "business_or_landmark",
        }
        self.assertEqual(apply_verified_business_location(original), original)

    def test_verified_catalog_can_enrich_title_when_source_has_only_downtown(self):
        result = apply_verified_business_location(
            {
                "title": "NinNin Ramen サーバー募集中！",
                "location_text": "Downtown",
                "region_hint": "Vancouver",
                "location_kind": "neighborhood",
            }
        )
        self.assertEqual(result["location_text"], "660 Abbott Street, Vancouver, BC V6B 0E1")
        self.assertEqual(result["location_kind"], "street_address")

    def test_unresolved_neighborhood_is_not_published_as_a_map_point(self):
        with patch("location_resolution.geocode_location") as geocode:
            resolved, lat, lng, confidence = resolve_map_location(
                {
                    "title": "North Vancouver restaurant role",
                    "location_text": "Lonsdale, North Vancouver, BC",
                    "region_hint": "North Vancouver",
                    "location_kind": "neighborhood",
                }
            )
        self.assertEqual(resolved["location_text"], "Lonsdale, North Vancouver, BC")
        self.assertEqual((lat, lng, confidence), (None, None, 0.3))
        geocode.assert_not_called()

    def test_unresolved_business_does_not_fall_back_to_city_center(self):
        with patch(
            "location_resolution.geocode_location",
            return_value=(None, None, 0.3),
        ) as geocode:
            _, lat, lng, confidence = resolve_map_location(
                {
                    "title": "Unknown Clinic receptionist",
                    "location_text": "Unknown Clinic",
                    "region_hint": "Vancouver",
                    "location_kind": "business_or_landmark",
                }
            )
        self.assertEqual((lat, lng, confidence), (None, None, 0.3))
        geocode.assert_called_once_with(
            "Unknown Clinic",
            "Vancouver",
            allow_region_fallback=False,
        )


if __name__ == "__main__":
    unittest.main()

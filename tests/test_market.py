"""Market Intelligence and Partner share one demonstration snapshot."""

import unittest

from app.market import DEMONSTRATION_LABEL, assessment_implications, market_framework
from app.pages import market_page, partner_page


class TestMarketDemonstration(unittest.TestCase):
    def test_one_framework_feeds_market_and_partner(self) -> None:
        snapshot = market_framework()
        self.assertEqual(snapshot["mode"], "demonstration")
        self.assertFalse(snapshot["live_feed"])
        self.assertFalse(snapshot["monitoring_active"])
        self.assertIsNone(snapshot["source_dataset"])
        self.assertEqual(snapshot["observations"], [])
        self.assertTrue(all(item.startswith("Synthetic example only") for item in snapshot["synthetic_examples"]))

        market = market_page()
        partner = partner_page()
        for page in (market, partner):
            self.assertIn(DEMONSTRATION_LABEL, page)
            self.assertIn("Synthetic example only", page)
            self.assertIn("Live feed connected: false", page)
            self.assertIn("Monitoring active: false", page)
            self.assertIn("Source dataset: none", page)
        self.assertIn("Recurring monitoring has not been implemented", partner)
        self.assertIn("Recurring monitoring is not active", partner)
        self.assertNotIn("Monitoring active: true", partner)
        selected = market_framework("Restaurant", "Example county")
        self.assertEqual(selected["industry"], "Restaurant")
        self.assertEqual(selected["geographic_market"], "Example county")
        self.assertFalse(selected["live_feed"])
        self.assertIsNone(selected["source_dataset"])
        self.assertEqual(selected["synthetic_examples"], snapshot["synthetic_examples"])
        rejected = market_framework("Census extract", "Live metro")
        self.assertEqual(rejected["industry"], "Not selected")
        self.assertEqual(rejected["geographic_market"], "Not selected")
        notes = assessment_implications(
            [
                {
                    "business_name": "Market Cafe",
                    "read_only": False,
                    "profile": {"industry": "Restaurant", "stage": "Idea"},
                }
            ],
            "Restaurant",
            "Example county",
        )
        joined = " ".join(notes)
        self.assertIn("Market Cafe lists industry Restaurant and stage Idea", joined)
        self.assertIn("No market fact is supplied", joined)
        self.assertIn("does not describe a real market", joined)
        page = market_page(
            [{"business_name": "Market Cafe", "read_only": False, "profile": {"industry": "Restaurant", "stage": "Idea"}}],
            "Restaurant",
            "Example county",
        )
        self.assertIn("Demonstration only", page)
        self.assertIn("Implications for this assessment", page)
        self.assertIn("Synthetic example only", page)
        self.assertIn("Market Intelligence (demonstration)", page)
        self.assertIn("Partner (demonstration)", page)
        self.assertIn("Validate (demonstration)", page)


if __name__ == "__main__":
    unittest.main()

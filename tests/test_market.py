"""Market Intelligence and Partner share one demonstration snapshot."""

import copy
import hashlib
import unittest
from pathlib import Path

from app.market import (
    DEMONSTRATION_LABEL,
    FALLBACK_LABEL,
    PUBLIC_SOURCE,
    BlsQcewProvider,
    assessment_implications,
    get_market_provider,
    load_market,
    market_framework,
)
from app.pages import market_page, partner_page
from app.store import SAMPLE

ROOT = Path(__file__).resolve().parent.parent
_QCEW = """area_fips,own_code,industry_code,size_code,disclosure_code,annual_avg_estabs,annual_avg_emplvl,annual_avg_wkly_wage,total_annual_wages,avg_annual_pay
01033,0,10,0,,1621,24495,1116,1420955338,58010
01033,5,722,0,,112,1842,364,34800000,18900
01033,5,54,0,N,101,0,0,0,0
01033,5,44-45,0,,246,3207,771,128000000,39900
01033,5,23,0,,139,1738,1268,114635543,65943
01033,5,31-33,0,,126,6242,1347,437408547,70072
01033,5,721,0,,10,85,509,2240287,26460
01033,5,62,0,,251,1994,1040,107843246,54073
"""
_QCEW_CORE_ONLY = """area_fips,own_code,industry_code,disclosure_code,annual_avg_estabs,annual_avg_emplvl,annual_avg_wkly_wage
01033,5,722,,112,1842,364
"""


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

    def test_public_provider_returns_provenance_and_fallback_stays_synthetic(self) -> None:
        seen: list[str] = []

        def transport(url: str) -> str:
            seen.append(url)
            return _QCEW

        provider = BlsQcewProvider(year="2024", transport=transport, retrieved_on="2026-11-08")
        observations = provider.observations("Restaurant", "Colbert County, Alabama")
        self.assertEqual(seen, ["https://data.bls.gov/cew/data/api/2024/a/area/01033.csv"])
        self.assertEqual(len(observations), 6)
        employment = observations[0]
        for field in (
            "source",
            "geographic_coverage",
            "industry_classification",
            "measurement_period",
            "retrieval_date",
            "limitations",
        ):
            self.assertTrue(employment[field], field)
        self.assertEqual(employment["source"], PUBLIC_SOURCE)
        self.assertIn("Colbert County, Alabama", employment["geographic_coverage"])
        self.assertIn("NAICS 722", employment["industry_classification"])
        self.assertEqual(employment["measurement_period"], "2024 annual")
        self.assertEqual(employment["retrieval_date"], "2026-11-08")
        self.assertIn("does not clear INSUFFICIENT_DEMAND_EVIDENCE", employment["limitations"])
        self.assertEqual(employment["measure"], "Private annual average employment")
        self.assertEqual(employment["value"], "1842")
        by_measure = {item["measure"]: item["value"] for item in observations}
        self.assertEqual(by_measure["Private total annual wages"], "34800000")
        self.assertEqual(by_measure["Private average annual pay"], "18900")
        self.assertEqual(by_measure["Establishment size coverage"], "All size classes combined")
        for item in observations:
            self.assertEqual(item["source"], PUBLIC_SOURCE)
            self.assertEqual(item["retrieval_date"], "2026-11-08")
        construction = provider.observations("Construction", "Colbert County, Alabama")
        self.assertIn("NAICS 23", construction[0]["industry_classification"])
        self.assertEqual(construction[0]["value"], "1738")
        manufacturing = provider.observations("Manufacturing", "United States")
        self.assertIn("NAICS 31-33", manufacturing[0]["industry_classification"])
        self.assertIn("area/US000.csv", seen[-1])
        accommodation = provider.observations("Accommodation", "Alabama")
        self.assertIn("NAICS 721", accommodation[0]["industry_classification"])
        health = provider.observations("Health care", "Alabama")
        self.assertIn("NAICS 62", health[0]["industry_classification"])
        core_only = BlsQcewProvider(year="2024", transport=lambda url: _QCEW_CORE_ONLY, retrieved_on="2026-11-08")
        core_measures = [item["measure"] for item in core_only.observations("Restaurant", "Alabama")]
        self.assertEqual(
            core_measures,
            [
                "Private annual average employment",
                "Private annual average weekly wage",
                "Private annual average establishments",
            ],
        )
        suppressed = provider.observations("Professional services", "Alabama")
        self.assertEqual(suppressed[0]["value"], "Not disclosed")
        self.assertIn("total annual wages", suppressed[0]["measure"])
        self.assertNotEqual(suppressed[0]["value"], "0")
        self.assertIn("disclosure code N", suppressed[0]["limitations"])
        self.assertIn("area/01000.csv", seen[-1])

        def fail(url: str) -> str:
            raise RuntimeError("down")

        failed = load_market("Restaurant", "Alabama", BlsQcewProvider(transport=fail))
        self.assertEqual(failed["status"], "fallback")
        self.assertEqual(failed["observations"], [])
        self.assertEqual(failed["label"], FALLBACK_LABEL)
        self.assertTrue(all(item.startswith("Synthetic example only") for item in failed["snapshot"]["synthetic_examples"]))
        uncovered = load_market("Restaurant", "Example county", provider)
        self.assertEqual(uncovered["status"], "fallback")
        self.assertIn("not covered by the public provider", uncovered["label"])
        self.assertEqual(get_market_provider(environ={}).name, "synthetic")
        self.assertEqual(get_market_provider(environ={"MARKET_PROVIDER": "bls", "MARKET_YEAR": "2023"}, transport=transport).year, "2023")

        page = market_page([], "Restaurant", "Alabama", provider=BlsQcewProvider(transport=fail))
        self.assertIn(FALLBACK_LABEL, page)
        self.assertIn("Active provider: BLS Quarterly Census of Employment and Wages. Year: 2024.", page)
        self.assertIn("Construction", page)
        self.assertIn("Manufacturing", page)
        self.assertIn("Colbert County, Alabama", page)
        self.assertIn("Synthetic example only", page)
        self.assertIn("Live feed connected: false", page)
        self.assertIn("Monitoring active: false", page)
        self.assertNotIn("Monitoring active: true", page)

    def test_market_data_cannot_change_flags_or_the_baseline(self) -> None:
        before_sample = hashlib.sha256(SAMPLE.read_bytes()).hexdigest()
        before_report = hashlib.sha256((ROOT / "reports" / "output" / "rugd-intelligence-draft.md").read_bytes()).hexdigest()
        result = {
            "recommendation": "do-not-proceed",
            "blocking_flags": ["INSUFFICIENT_DEMAND_EVIDENCE"],
            "readiness_status": "internal",
            "human_review_approved": False,
            "is_final": False,
        }
        record = {
            "business_name": "Market Cafe",
            "read_only": False,
            "human_review_approved": False,
            "profile": {"industry": "Restaurant", "stage": "Idea"},
        }
        before_result = copy.deepcopy(result)
        before_record = copy.deepcopy(record)
        provider = BlsQcewProvider(year="2024", transport=lambda url: _QCEW, retrieved_on="2026-11-08")
        view = load_market("Restaurant", "Alabama", provider)
        page = market_page([record], "Restaurant", "Alabama", provider=provider)
        self.assertEqual(view["status"], "public")
        self.assertEqual(view["provider_name"], "bls-qcew")
        self.assertEqual(view["year"], "2024")
        self.assertEqual(result, before_result)
        self.assertEqual(record, before_record)
        self.assertIn(PUBLIC_SOURCE, page)
        self.assertIn("2024 annual", page)
        self.assertIn("2026-11-08", page)
        self.assertIn("Private annual average employment:", page)
        self.assertIn("1842", page)
        self.assertIn("Private total annual wages:", page)
        self.assertIn("34800000", page)
        self.assertIn("Private average annual pay:", page)
        self.assertIn("Active provider: BLS Quarterly Census of Employment and Wages. Year: 2024.", page)
        self.assertIn("Health care", page)
        self.assertIn("does not clear INSUFFICIENT_DEMAND_EVIDENCE", page)
        self.assertNotIn("Synthetic example only: a cost-pressure", page)
        self.assertNotIn("Live feed connected: true", page)
        self.assertNotIn("Monitoring active: true", page)
        self.assertIn("INSUFFICIENT_DEMAND_EVIDENCE", result["blocking_flags"])
        self.assertEqual(result["recommendation"], "do-not-proceed")
        self.assertEqual(result["readiness_status"], "internal")
        self.assertFalse(result["human_review_approved"])
        self.assertEqual(hashlib.sha256(SAMPLE.read_bytes()).hexdigest(), before_sample)
        self.assertEqual(
            hashlib.sha256((ROOT / "reports" / "output" / "rugd-intelligence-draft.md").read_bytes()).hexdigest(),
            before_report,
        )


if __name__ == "__main__":
    unittest.main()

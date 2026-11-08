"""Market Intelligence and Partner share one demonstration snapshot."""

import copy
import hashlib
import json
import unittest
from pathlib import Path

from app.market import (
    CENSUS_SOURCE,
    DEMONSTRATION_LABEL,
    FALLBACK_LABEL,
    PUBLIC_SOURCE,
    BlsQcewProvider,
    CensusAcsProvider,
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

    def test_census_acs_is_labeled_and_can_sit_beside_bls(self) -> None:
        population = json.dumps(
            {
                "response": {
                    "data": [
                        ["GEO_ID", "B01003_001E", "NAME"],
                        ["0500000US01033", "58022", "Colbert County, Alabama"],
                    ]
                }
            }
        )
        income = json.dumps(
            {
                "response": {
                    "data": [
                        ["NAME", "B19013_001E"],
                        ["Colbert County, Alabama", "60628"],
                    ]
                }
            }
        )
        suppressed_income = json.dumps(
            {"response": {"data": [["B19013_001E", "NAME"], ["-666666666", "Colbert County, Alabama"]]}}
        )
        seen: list[str] = []

        def transport(url: str) -> str:
            seen.append(url)
            self.assertNotIn("secret-census-key", url)
            if "B19013" in url:
                return suppressed_income if "suppress" in url else income
            if "B01003" in url:
                return population
            return _QCEW

        provider = CensusAcsProvider(year="2024", transport=transport, retrieved_on="2026-11-08")
        observations = provider.observations("Restaurant", "Colbert County, Alabama")
        self.assertEqual(
            seen[:2],
            [
                "https://data.census.gov/api/access/data/table?id=ACSDT5Y2024.B01003&g=050XX00US01033",
                "https://data.census.gov/api/access/data/table?id=ACSDT5Y2024.B19013&g=050XX00US01033",
            ],
        )
        self.assertEqual(len(observations), 2)
        self.assertEqual(observations[0]["source"], CENSUS_SOURCE)
        self.assertEqual(observations[0]["measure"], "Total population")
        self.assertEqual(observations[0]["value"], "58022")
        self.assertIn("Demographic", observations[0]["industry_classification"])
        self.assertEqual(observations[0]["measurement_period"], "2020-2024 5-year")
        self.assertEqual(observations[0]["retrieval_date"], "2026-11-08")
        self.assertIn("B01003", observations[0]["limitations"])
        self.assertIn("does not clear INSUFFICIENT_DEMAND_EVIDENCE", observations[0]["limitations"])
        self.assertNotEqual(observations[0]["source"], PUBLIC_SOURCE)
        hidden = CensusAcsProvider(
            year="2024",
            transport=lambda url: suppressed_income if "B19013" in url else population,
            retrieved_on="2026-11-08",
        ).observations("Retail", "Alabama")
        self.assertEqual(hidden[1]["value"], "Not disclosed")
        self.assertNotEqual(hidden[1]["value"], "-666666666")

        def fail(url: str) -> str:
            raise RuntimeError("down")

        failed = load_market("Restaurant", "Alabama", CensusAcsProvider(transport=fail))
        self.assertEqual(failed["status"], "fallback")
        self.assertEqual(failed["label"], FALLBACK_LABEL)
        self.assertTrue(all(item.startswith("Synthetic example only") for item in failed["snapshot"]["synthetic_examples"]))
        configured = get_market_provider(
            environ={"MARKET_CENSUS": "acs", "ACS_YEAR": "2023", "CENSUS_API_KEY": "secret-census-key"},
            transport=transport,
        )
        self.assertEqual(configured.name, "census-acs")
        self.assertEqual(configured.year, "2023")
        page = market_page([], "Restaurant", "Colbert County, Alabama", provider=provider)
        self.assertIn(CENSUS_SOURCE, page)
        self.assertIn("Total population:", page)
        self.assertIn("58022", page)
        self.assertIn("Median household income (dollars):", page)
        self.assertIn("60628", page)
        self.assertIn("Demographic. Not a NAICS industry.", page)
        self.assertIn("Active provider: U.S. Census Bureau, American Community Survey 5-year estimates. Year: 2024.", page)
        self.assertIn("does not clear INSUFFICIENT_DEMAND_EVIDENCE", page)
        self.assertNotIn("secret-census-key", page)
        self.assertNotIn("Synthetic example only: a cost-pressure", page)

        def mixed(url: str) -> str:
            if "census.gov" in url:
                raise RuntimeError("census down")
            return _QCEW

        both = get_market_provider(
            environ={"MARKET_PROVIDER": "bls", "MARKET_CENSUS": "acs", "MARKET_YEAR": "2024", "ACS_YEAR": "2024"},
            transport=mixed,
        )
        view = load_market("Construction", "Colbert County, Alabama", both)
        combined = market_page([], "Construction", "Colbert County, Alabama", provider=both)
        self.assertEqual(view["status"], "public")
        self.assertEqual(view["provider_name"], "combined")
        self.assertIn(PUBLIC_SOURCE, combined)
        self.assertIn("Private annual average employment:", combined)
        self.assertIn("1738", combined)
        self.assertIn("Synthetic example only", combined)
        self.assertIn("did not return observations", combined)
        self.assertIn("Active providers:", combined)
        self.assertIn("BLS Quarterly Census of Employment and Wages (year 2024)", combined)
        self.assertNotIn("Total population:", combined)
        self.assertNotIn("58022", combined)
        result = {
            "recommendation": "do-not-proceed",
            "blocking_flags": ["INSUFFICIENT_DEMAND_EVIDENCE"],
            "readiness_status": "internal",
            "human_review_approved": False,
        }
        before = copy.deepcopy(result)
        before_sample = hashlib.sha256(SAMPLE.read_bytes()).hexdigest()
        load_market("Construction", "Alabama", provider)
        self.assertEqual(result, before)
        self.assertFalse(result["human_review_approved"])
        self.assertEqual(hashlib.sha256(SAMPLE.read_bytes()).hexdigest(), before_sample)

    def test_added_geographies_and_year_label_leave_the_baseline_unchanged(self) -> None:
        seen: list[str] = []

        def transport(url: str) -> str:
            seen.append(url)
            if "census.gov" in url:
                return json.dumps(
                    {"response": {"data": [["B01003_001E", "NAME"], ["100", "Recorded"]]}}
                    if "B01003" in url
                    else {"response": {"data": [["NAME", "B19013_001E"], ["Recorded", "200"]]}}
                )
            return _QCEW

        bls = BlsQcewProvider(year="2024", transport=transport, retrieved_on="2026-11-08")
        census = CensusAcsProvider(year="2024", transport=transport, retrieved_on="2026-11-08")
        for geography, area, acs_code in (
            ("United States", "US000", "010XX00US"),
            ("Alabama", "01000", "040XX00US01"),
            ("Colbert County, Alabama", "01033", "050XX00US01033"),
            ("Tennessee", "47000", "040XX00US47"),
            ("Hamilton County, Tennessee", "47065", "050XX00US47065"),
        ):
            employment = bls.observations("Restaurant", geography)[0]
            population = census.observations("Restaurant", geography)[0]
            self.assertIn(f"area/{area}.csv", seen[-3])
            self.assertIn(geography, employment["geographic_coverage"])
            self.assertIn(area, employment["geographic_coverage"])
            self.assertEqual(employment["measurement_period"], "2024 annual")
            self.assertEqual(employment["source"], PUBLIC_SOURCE)
            self.assertIn(acs_code, seen[-2])
            self.assertIn(geography, population["geographic_coverage"])
            self.assertIn(acs_code, population["geographic_coverage"])
            self.assertEqual(population["source"], CENSUS_SOURCE)
            self.assertEqual(population["measurement_period"], "2020-2024 5-year")
            self.assertIn("does not clear INSUFFICIENT_DEMAND_EVIDENCE", population["limitations"])
        missed = load_market("Restaurant", "Example county", bls)
        self.assertEqual(missed["status"], "fallback")
        self.assertIn("Synthetic example only", missed["label"])

        selected = get_market_provider(environ={"MARKET_PROVIDER": "bls", "MARKET_YEAR": "2023"}, transport=transport)
        self.assertEqual(selected.year, "2023")
        self.assertEqual(get_market_provider(environ={"MARKET_PROVIDER": "bls"}, transport=transport).year, "2024")
        page = market_page([], "Restaurant", "Tennessee", provider=selected)
        self.assertIn("Active provider: BLS Quarterly Census of Employment and Wages. Year: 2023.", page)
        self.assertIn("2023 annual", page)
        self.assertIn("Tennessee", page)
        self.assertIn("Hamilton County, Tennessee", page)
        self.assertIn("MARKET_YEAR selects the QCEW file.", page)
        self.assertIn("ACS_YEAR selects the ACS vintage.", page)
        self.assertIn("Each defaults to 2024 when it is not set.", page)
        self.assertIn("This is prototype behavior.", page)
        aged = CensusAcsProvider(year="2022", transport=transport, retrieved_on="2026-11-08")
        income = aged.observations("Retail", "Hamilton County, Tennessee")[1]
        self.assertEqual(income["measurement_period"], "2018-2022 5-year")
        self.assertIn("050XX00US47065", income["geographic_coverage"])
        census_page = market_page([], "Retail", "Hamilton County, Tennessee", provider=aged)
        self.assertIn("Year: 2022.", census_page)
        self.assertIn("Each defaults to 2024 when it is not set.", census_page)
        result = {
            "recommendation": "do-not-proceed",
            "blocking_flags": ["INSUFFICIENT_DEMAND_EVIDENCE"],
            "readiness_status": "internal",
            "human_review_approved": False,
        }
        before = copy.deepcopy(result)
        before_sample = hashlib.sha256(SAMPLE.read_bytes()).hexdigest()
        load_market("Restaurant", "Hamilton County, Tennessee", bls)
        self.assertEqual(result, before)
        self.assertEqual(hashlib.sha256(SAMPLE.read_bytes()).hexdigest(), before_sample)


if __name__ == "__main__":
    unittest.main()

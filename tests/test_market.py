"""Market Intelligence and Partner share one demonstration snapshot."""

import copy
import hashlib
import json
import os
import tempfile
import threading
import unittest
import urllib.request
from pathlib import Path

from app.market import (
    BEA_SOURCE,
    CBP_SOURCE,
    LAUS_SOURCE,
    CENSUS_SOURCE,
    DEMONSTRATION_LABEL,
    FALLBACK_LABEL,
    NOT_COVERED_LABEL,
    PUBLIC_SOURCE,
    BeaRegionalProvider,
    BlsLausProvider,
    BlsQcewProvider,
    CensusAcsProvider,
    CensusCbpProvider,
    assessment_implications,
    export_market_observations,
    get_market_provider,
    load_market,
    market_framework,
)
from app.pages import market_page, partner_page
from app.server import make_server
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
        self.assertEqual(observations[0]["measure"], "Total population")
        self.assertEqual(observations[1]["measure"], "Median household income (dollars)")
        self.assertEqual(observations[2]["measure"], "Population change between overlapping ACS 5-year vintages")
        self.assertEqual(observations[2]["value"], "0")
        self.assertEqual(observations[2]["detail"], "extended")
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
            ("Georgia", "13000", "040XX00US13"),
            ("Fulton County, Georgia", "13121", "050XX00US13121"),
        ):
            start = len(seen)
            employment = bls.observations("Restaurant", geography)[0]
            population = census.observations("Restaurant", geography)[0]
            called = seen[start:]
            self.assertTrue(any(f"area/{area}.csv" in url for url in called))
            self.assertIn(geography, employment["geographic_coverage"])
            self.assertIn(area, employment["geographic_coverage"])
            self.assertEqual(employment["measurement_period"], "2024 annual")
            self.assertEqual(employment["source"], PUBLIC_SOURCE)
            self.assertTrue(any(acs_code in url and "B01003" in url for url in called))
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
        self.assertIn("Fulton County, Georgia", page)
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

    def test_summary_and_export_leave_assessments_unchanged(self) -> None:
        plain = market_page()
        self.assertIn("<h2>Combined summary</h2>", plain)
        self.assertIn("Download market observations (JSON)", plain)
        self.assertIn("Active provider: Demonstration snapshot. No public provider is active.", plain)
        self.assertIn("Synthetic example only", plain)
        self.assertIn("do not clear INSUFFICIENT_DEMAND_EVIDENCE", plain)

        class DirtyProvider(BlsQcewProvider):
            def observations(self, industry: str | None, geography: str | None) -> list[dict[str, str]]:
                rows = super().observations(industry, geography)
                rows[0]["session_id"] = "raw-session-token"
                rows[0]["reviewer_passphrase"] = "local-prototype-reviewer"
                return rows

        dirty = DirtyProvider(year="2024", transport=lambda url: _QCEW, retrieved_on="2026-11-08")
        shown = market_page([], "Restaurant", "Alabama", provider=dirty)
        self.assertIn("<h2>Combined summary</h2>", shown)
        self.assertIn("Private annual average employment:", shown)
        self.assertIn("1842", shown)
        self.assertIn(PUBLIC_SOURCE, shown)
        self.assertIn("Active provider: BLS Quarterly Census of Employment and Wages. Year: 2024.", shown)
        self.assertIn("do not clear INSUFFICIENT_DEMAND_EVIDENCE", shown)
        self.assertNotIn("raw-session-token", shown)
        payload = export_market_observations("Restaurant", "Alabama", dirty)
        encoded = json.dumps(payload)
        self.assertEqual(payload["kind"], "rugd-market-observations")
        self.assertEqual(payload["status"], "public")
        self.assertEqual(payload["year"], "2024")
        self.assertEqual(payload["observations"][0]["measure"], "Private annual average employment")
        self.assertEqual(payload["observations"][0]["value"], "1842")
        self.assertEqual(payload["observations"][0]["source"], PUBLIC_SOURCE)
        self.assertIn("geographic_coverage", payload["observations"][0])
        self.assertIn("measurement_period", payload["observations"][0])
        self.assertIn("limitations", payload["observations"][0])
        self.assertNotIn("session_id", payload["observations"][0])
        self.assertNotIn("raw-session-token", encoded)
        self.assertNotIn("local-prototype-reviewer", encoded)
        self.assertEqual(payload["synthetic_observations"], [])
        self.assertTrue(payload["does_not_clear_recommend_against_flags"])
        synthetic = export_market_observations()
        self.assertEqual(synthetic["status"], "synthetic")
        self.assertTrue(synthetic["synthetic_observations"][0]["value"].startswith("Synthetic example only"))
        self.assertEqual(synthetic["synthetic_observations"][0]["source"], "Synthetic snapshot")
        result = {
            "recommendation": "do-not-proceed",
            "blocking_flags": ["INSUFFICIENT_DEMAND_EVIDENCE"],
            "readiness_status": "internal",
            "human_review_approved": False,
        }
        before = copy.deepcopy(result)
        before_sample = hashlib.sha256(SAMPLE.read_bytes()).hexdigest()
        export_market_observations("Restaurant", "Alabama", dirty)
        self.assertEqual(result, before)
        self.assertEqual(hashlib.sha256(SAMPLE.read_bytes()).hexdigest(), before_sample)

        directory = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        server = make_server(Path(directory.name) / "analyze.sqlite", port=0)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        host, port = server.server_address
        saved = {
            key: os.environ.pop(key, None)
            for key in (
                "MARKET_PROVIDER",
                "MARKET_CENSUS",
                "MARKET_CBP",
                "MARKET_BEA",
                "BEA_USER_ID",
                "MARKET_LAUS",
            )
        }
        try:
            with urllib.request.urlopen(
                f"http://{host}:{port}/market/export?industry=Restaurant&geographic_market=Example+county"
            ) as response:
                body = json.loads(response.read().decode("utf-8"))
                disposition = response.headers.get("Content-Disposition") or ""
                content_type = response.headers.get("Content-Type") or ""
            self.assertEqual(content_type, "application/json")
            self.assertIn("attachment;", disposition)
            self.assertIn("-market.json", disposition)
            self.assertEqual(body["kind"], "rugd-market-observations")
            self.assertEqual(body["status"], "synthetic")
            self.assertTrue(body["synthetic_observations"][0]["value"].startswith("Synthetic example only"))
            self.assertNotIn("local-prototype-reviewer", json.dumps(body))
            with urllib.request.urlopen(f"http://{host}:{port}/market") as response:
                page = response.read().decode("utf-8")
            self.assertIn("Download market observations (JSON)", page)
            self.assertIn("Combined summary", page)
        finally:
            for key, value in saved.items():
                if value is not None:
                    os.environ[key] = value
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)
            directory.cleanup()

    def test_cbp_synthesis_and_tiers_leave_flags_and_baseline_unchanged(self) -> None:
        trend = """area_fips,own_code,industry_code,size_code,disclosure_code,annual_avg_estabs,annual_avg_emplvl,annual_avg_wkly_wage,total_annual_wages,avg_annual_pay,oty_annual_avg_emplvl_pct_chg,oty_annual_avg_wkly_wage_pct_chg
13121,5,23,0,,1597,20487,900,1000,50000,2.5,-1.2
"""
        cbp = json.dumps(
            {
                "response": {
                    "data": [
                        ["NAICS2017", "LFO", "EMPSZES", "ESTAB", "EMP", "PAYANN", "ESTAB_F", "EMP_F", "PAYANN_F", "NAME"],
                        ["23", "001", "001", "1597", "20487", "1800000", None, None, None, "Fulton County, Georgia"],
                    ]
                }
            }
        )
        brackets = json.dumps(
            {"response": {"data": [["B19001_001E", "B19001_002E", "B19001_017E"], ["1000", "100", "250"]]}}
        )
        seen: list[str] = []

        def transport(url: str) -> str:
            seen.append(url)
            if "bls.gov" in url:
                return trend
            if "CBP" in url:
                return cbp
            if "B19001" in url:
                return brackets
            if "B01003" in url:
                value = "200" if "ACSDT5Y2024" in url else "180"
                return json.dumps({"response": {"data": [["B01003_001E", "NAME"], [value, "Fulton County, Georgia"]]}})
            if "B19013" in url:
                return json.dumps({"response": {"data": [["B19013_001E"], ["70000"]]}})
            raise RuntimeError(url)

        cbp_provider = CensusCbpProvider(year="2023", transport=transport, retrieved_on="2026-11-09")
        rows = cbp_provider.observations("Construction", "Fulton County, Georgia")
        self.assertIn("CBP2023.CB2300CBP", seen[-1])
        self.assertIn("g=050XX00US13121", seen[-1])
        self.assertEqual(rows[0]["source"], CBP_SOURCE)
        self.assertEqual(rows[0]["measure"], "Establishments")
        self.assertEqual(rows[0]["value"], "1597")
        self.assertEqual(rows[0]["detail"], "headline")
        self.assertEqual(rows[1]["measure"], "CBP employment")
        self.assertEqual(rows[2]["measure"], "Annual payroll (thousands of dollars)")
        self.assertEqual(rows[2]["detail"], "extended")
        for field in ("source", "geographic_coverage", "industry_classification", "measurement_period", "retrieval_date", "limitations"):
            self.assertTrue(rows[0][field], field)
        self.assertIn("do not clear INSUFFICIENT_DEMAND_EVIDENCE", rows[0]["limitations"])
        self.assertIn("2023 annual", rows[0]["measurement_period"])
        missed = load_market("Restaurant", "Fulton County, Georgia", cbp_provider)
        self.assertEqual(missed["status"], "fallback")
        self.assertEqual(missed["label"], FALLBACK_LABEL)
        selected = get_market_provider(environ={"MARKET_CBP": "cbp"}, transport=transport)
        self.assertEqual(selected.name, "census-cbp")
        self.assertEqual(selected.year, "2023")
        self.assertEqual(
            get_market_provider(environ={"MARKET_CBP": "cbp", "CBP_YEAR": "2022"}, transport=transport).year,
            "2022",
        )
        georgia = BlsQcewProvider(year="2024", transport=transport, retrieved_on="2026-11-09")
        georgia.observations("Construction", "Georgia")
        self.assertIn("area/13000.csv", seen[-1])

        combined = get_market_provider(
            environ={
                "MARKET_PROVIDER": "bls",
                "MARKET_CENSUS": "acs",
                "MARKET_CBP": "cbp",
                "MARKET_YEAR": "2024",
                "ACS_YEAR": "2024",
                "CBP_YEAR": "2023",
            },
            transport=transport,
        )
        self.assertEqual(combined.name, "combined")
        explore = market_page([], "Construction", "Fulton County, Georgia", provider=combined, tier="explore")
        analyze = market_page([], "Construction", "Fulton County, Georgia", provider=combined, tier="analyze")
        validate = market_page([], "Construction", "Fulton County, Georgia", provider=combined, tier="validate")
        partner = market_page([], "Construction", "Fulton County, Georgia", provider=combined, tier="partner")
        self.assertIn("Private annual average employment:", explore)
        self.assertIn("Total population:", explore)
        self.assertIn("Establishments:", explore)
        self.assertNotIn("Private total annual wages:", explore)
        self.assertNotIn("Market Research Summary", explore)
        self.assertNotIn("Annual payroll (thousands of dollars):", explore)
        self.assertIn("Private total annual wages:", analyze)
        self.assertIn("CBP employment:", analyze)
        self.assertIn("<h2>Market Research Summary</h2>", analyze)
        self.assertIn("derived from the cited public sources", analyze)
        self.assertIn("It is not a recommendation.", analyze)
        self.assertNotIn("Annual payroll (thousands of dollars):", analyze)
        self.assertNotIn("higher than the prior period", analyze)
        for page in (validate, partner):
            self.assertIn("Annual payroll (thousands of dollars):", page)
            self.assertIn("1800000", page)
            self.assertIn("Households under $10,000:", page)
            self.assertIn("derived whole-number share 10 percent, rounded down", page)
            self.assertIn("higher than the prior period", page)
            self.assertIn("lower than the prior period", page)
            self.assertIn("Population change between overlapping ACS 5-year vintages:", page)
            self.assertIn("It is not a recommendation.", page)
            self.assertIn("does not approve the assessment", page)
        self.assertIn("Monitoring active: false", partner)
        self.assertNotIn("Monitoring active: true", partner)
        self.assertIn("20", partner)
        exported = export_market_observations(
            "Construction",
            "Fulton County, Georgia",
            combined,
            tier="explore",
        )
        measures = [item["measure"] for item in exported["observations"]]
        self.assertIn("Establishments", measures)
        self.assertNotIn("Annual payroll (thousands of dollars)", measures)
        self.assertNotIn("detail", json.dumps(exported["observations"]))
        result = {
            "recommendation": "do-not-proceed",
            "blocking_flags": ["INSUFFICIENT_DEMAND_EVIDENCE"],
            "readiness_status": "internal",
            "human_review_approved": False,
        }
        before = copy.deepcopy(result)
        before_sample = hashlib.sha256(SAMPLE.read_bytes()).hexdigest()
        before_report = hashlib.sha256((ROOT / "reports" / "output" / "rugd-intelligence-draft.md").read_bytes()).hexdigest()
        market_page([], "Construction", "Fulton County, Georgia", provider=combined, tier="partner")
        export_market_observations("Construction", "Fulton County, Georgia", combined, tier="partner")
        self.assertEqual(result, before)
        self.assertFalse(result["human_review_approved"])
        self.assertEqual(hashlib.sha256(SAMPLE.read_bytes()).hexdigest(), before_sample)
        self.assertEqual(
            hashlib.sha256((ROOT / "reports" / "output" / "rugd-intelligence-draft.md").read_bytes()).hexdigest(),
            before_report,
        )

    def test_bea_and_naics_cbp_keep_provenance_fallback_and_baseline(self) -> None:
        def bea_body(value: str) -> str:
            return json.dumps(
                {
                    "BEAAPI": {
                        "Results": {
                            "Data": [
                                {
                                    "TimePeriod": "2023",
                                    "DataValue": value,
                                    "CL_UNIT": "Thousands of dollars",
                                }
                            ]
                        }
                    }
                }
            )

        seen: list[str] = []

        def transport(url: str) -> str:
            seen.append(url)
            if "TableName=CAGDP2" in url:
                return bea_body("1,445,132")
            if "TableName=CAINC1" in url:
                return bea_body("2,200,000")
            raise RuntimeError("down")

        provider = BeaRegionalProvider(
            year="2023",
            user_id="bea-test-user",
            transport=transport,
            retrieved_on="2026-11-09",
        )
        rows = provider.observations("Restaurant", "Colbert County, Alabama")
        self.assertEqual(len(rows), 2)
        self.assertIn("TableName=CAGDP2", seen[0])
        self.assertIn("LineCode=1", seen[0])
        self.assertIn("GeoFips=01033", seen[0])
        self.assertIn("UserID=bea-test-user", seen[0])
        self.assertIn("TableName=CAINC1", seen[1])
        self.assertEqual(rows[0]["source"], BEA_SOURCE)
        self.assertEqual(rows[0]["measure"], "Current-dollar GDP, all industries (thousands of dollars)")
        self.assertEqual(rows[0]["value"], "1445132")
        self.assertEqual(rows[0]["detail"], "headline")
        self.assertEqual(rows[1]["measure"], "Personal income (thousands of dollars)")
        self.assertEqual(rows[1]["value"], "2200000")
        self.assertEqual(rows[0]["industry_classification"], "All industries. Not one NAICS code.")
        self.assertEqual(rows[0]["geographic_coverage"], "Colbert County, Alabama (BEA GeoFips 01033)")
        self.assertEqual(rows[0]["measurement_period"], "2023 annual")
        self.assertEqual(rows[0]["retrieval_date"], "2026-11-09")
        for field in (
            "source",
            "geographic_coverage",
            "industry_classification",
            "measurement_period",
            "retrieval_date",
            "limitations",
        ):
            self.assertTrue(rows[0][field], field)
            self.assertNotIn("bea-test-user", rows[0][field])
        self.assertIn("does not clear INSUFFICIENT_DEMAND_EVIDENCE", rows[0]["limitations"])
        self.assertIn("does not approve the assessment", rows[0]["limitations"])

        hidden = BeaRegionalProvider(
            year="2023",
            user_id="bea-test-user",
            transport=lambda url: bea_body("(D)"),
            retrieved_on="2026-11-09",
        ).observations("Restaurant", "Alabama")
        self.assertEqual(hidden[0]["value"], "Not disclosed")
        self.assertNotEqual(hidden[0]["value"], "0")

        called = {"count": 0}

        def refuse(url: str) -> str:
            called["count"] += 1
            raise AssertionError(url)

        missing_key = load_market(
            "Restaurant",
            "Alabama",
            BeaRegionalProvider(year="2023", user_id="", transport=refuse),
        )
        self.assertEqual(missing_key["status"], "fallback")
        self.assertEqual(missing_key["label"], FALLBACK_LABEL)
        self.assertEqual(called["count"], 0)
        uncovered = load_market("Restaurant", "Example county", provider)
        self.assertEqual(uncovered["status"], "fallback")
        self.assertEqual(uncovered["label"], NOT_COVERED_LABEL)
        failed = load_market(
            "Restaurant",
            "Alabama",
            BeaRegionalProvider(year="2023", user_id="bea-test-user", transport=lambda url: (_ for _ in ()).throw(RuntimeError(url))),
        )
        self.assertEqual(failed["status"], "fallback")
        self.assertEqual(failed["label"], FALLBACK_LABEL)
        selected = get_market_provider(
            environ={"MARKET_BEA": "bea", "BEA_YEAR": "2023", "BEA_USER_ID": "bea-test-user"},
            transport=transport,
        )
        self.assertEqual(selected.name, "bea-regional")
        self.assertEqual(selected.year, "2023")
        self.assertEqual(
            get_market_provider(environ={"MARKET_BEA": "regional"}, transport=transport).year,
            "2024",
        )

        sector = json.dumps(
            {
                "response": {
                    "data": [
                        ["NAICS2017", "LFO", "EMPSZES", "ESTAB", "EMP", "PAYANN"],
                        ["23", "001", "001", "10", "20", "30"],
                    ]
                }
            }
        )
        naics = json.dumps(
            [
                ["NAME", "NAICS2017", "ESTAB", "EMP", "PAYANN"],
                ["Colbert County, Alabama", "722", "112", "1842", "34800"],
            ]
        )
        cbp_seen: list[str] = []

        def cbp_transport(url: str) -> str:
            cbp_seen.append(url)
            if "api.census.gov" in url:
                return naics
            if "CBP" in url:
                return sector
            raise RuntimeError(url)

        cbp = CensusCbpProvider(year="2023", transport=cbp_transport, retrieved_on="2026-11-09")
        restaurant = cbp.observations("Restaurant", "Colbert County, Alabama")
        self.assertIn("NAICS2017=722", cbp_seen[-1])
        self.assertIn("for=county:033&in=state:01", cbp_seen[-1])
        self.assertNotIn("key=", cbp_seen[-1])
        self.assertEqual(restaurant[0]["source"], CBP_SOURCE)
        self.assertEqual(restaurant[0]["measure"], "Establishments")
        self.assertEqual(restaurant[0]["value"], "112")
        self.assertEqual(restaurant[1]["measure"], "CBP employment")
        self.assertEqual(restaurant[1]["value"], "1842")
        self.assertEqual(restaurant[2]["measure"], "Annual payroll (thousands of dollars)")
        self.assertEqual(restaurant[2]["value"], "34800")
        self.assertIn("NAICS 722", restaurant[0]["industry_classification"])
        self.assertIn("filtered to this NAICS code", restaurant[0]["limitations"])
        self.assertIn("do not clear INSUFFICIENT_DEMAND_EVIDENCE", restaurant[0]["limitations"])
        empty_api = CensusCbpProvider(
            year="2023",
            transport=lambda url: naics if "api.census.gov" in url else sector,
            retrieved_on="2026-11-09",
        )
        missed = load_market("Accommodation", "Colbert County, Alabama", empty_api)
        self.assertEqual(missed["status"], "fallback")
        self.assertEqual(missed["label"], FALLBACK_LABEL)

        def combined_transport(url: str) -> str:
            if "apps.bea.gov" in url:
                return transport(url)
            if "bls.gov" in url:
                return _QCEW
            if "B01003" in url:
                return json.dumps({"response": {"data": [["B01003_001E"], ["58022"]]}})
            if "B19013" in url:
                return json.dumps({"response": {"data": [["B19013_001E"], ["60628"]]}})
            if "B19001" in url:
                raise RuntimeError("skip brackets")
            raise RuntimeError(url)

        combined = get_market_provider(
            environ={
                "MARKET_PROVIDER": "bls",
                "MARKET_CENSUS": "acs",
                "MARKET_BEA": "bea",
                "BEA_USER_ID": "bea-test-user",
                "BEA_YEAR": "2023",
                "ACS_YEAR": "2024",
            },
            transport=combined_transport,
        )
        page = market_page([], "Restaurant", "Colbert County, Alabama", provider=combined, tier="analyze")
        self.assertIn("<h2>Combined summary</h2>", page)
        self.assertIn("Private annual average employment:", page)
        self.assertIn("Total population:", page)
        self.assertIn("Current-dollar GDP, all industries (thousands of dollars):", page)
        self.assertIn("1445132", page)
        self.assertIn("Personal income (thousands of dollars):", page)
        self.assertIn("2200000", page)
        self.assertIn(BEA_SOURCE, page)
        self.assertIn(PUBLIC_SOURCE, page)
        self.assertIn(CENSUS_SOURCE, page)
        self.assertIn("These figures do not clear INSUFFICIENT_DEMAND_EVIDENCE", page)
        self.assertNotIn("bea-test-user", page)
        self.assertIn("Monitoring active: false", page)
        explore = market_page([], "Restaurant", "Colbert County, Alabama", provider=combined, tier="explore")
        self.assertIn("Current-dollar GDP, all industries (thousands of dollars):", explore)
        self.assertIn("Personal income (thousands of dollars):", explore)
        result = {
            "recommendation": "do-not-proceed",
            "blocking_flags": ["INSUFFICIENT_DEMAND_EVIDENCE"],
            "readiness_status": "internal",
            "human_review_approved": False,
        }
        before = copy.deepcopy(result)
        before_sample = hashlib.sha256(SAMPLE.read_bytes()).hexdigest()
        before_report = hashlib.sha256((ROOT / "reports" / "output" / "rugd-intelligence-draft.md").read_bytes()).hexdigest()
        export_market_observations("Restaurant", "Colbert County, Alabama", combined, tier="analyze")
        market_page([], "Restaurant", "Colbert County, Alabama", provider=combined)
        self.assertEqual(result, before)
        self.assertFalse(result["human_review_approved"])
        self.assertEqual(hashlib.sha256(SAMPLE.read_bytes()).hexdigest(), before_sample)
        self.assertEqual(
            hashlib.sha256((ROOT / "reports" / "output" / "rugd-intelligence-draft.md").read_bytes()).hexdigest(),
            before_report,
        )

    def test_laus_observations_keep_provenance_and_do_not_clear_flags(self) -> None:
        def body(value: str) -> str:
            return json.dumps(
                {
                    "status": "REQUEST_SUCCEEDED",
                    "Results": {
                        "series": [
                            {
                                "data": [
                                    {"year": "2024", "period": "M12", "value": "9.9"},
                                    {"year": "2024", "period": "M13", "value": value},
                                ]
                            }
                        ]
                    },
                }
            )

        seen: list[str] = []

        def transport(url: str) -> str:
            seen.append(url)
            if url.endswith("003"):
                return body("3.4")
            if url.endswith("006"):
                return body("24567")
            raise RuntimeError(url)

        provider = BlsLausProvider(year="2024", transport=transport, retrieved_on="2026-11-09")
        rows = provider.observations("Restaurant", "Colbert County, Alabama")
        self.assertEqual(len(rows), 2)
        self.assertIn("LAUCN010330000000003", seen[0])
        self.assertIn("LAUCN010330000000006", seen[1])
        self.assertNotIn("key=", seen[0])
        self.assertEqual(rows[0]["source"], LAUS_SOURCE)
        self.assertEqual(rows[0]["measure"], "Unemployment rate (percent)")
        self.assertEqual(rows[0]["value"], "3.4")
        self.assertEqual(rows[0]["detail"], "headline")
        self.assertEqual(rows[1]["measure"], "Labor force")
        self.assertEqual(rows[1]["value"], "24567")
        self.assertEqual(rows[0]["measurement_period"], "2024 annual average")
        self.assertEqual(rows[0]["retrieval_date"], "2026-11-09")
        self.assertIn("Not a NAICS industry", rows[0]["industry_classification"])
        for field in (
            "source",
            "geographic_coverage",
            "industry_classification",
            "measurement_period",
            "retrieval_date",
            "limitations",
        ):
            self.assertTrue(rows[0][field], field)
        self.assertIn("do not clear INSUFFICIENT_DEMAND_EVIDENCE", rows[0]["limitations"])
        self.assertIn("do not approve the assessment", rows[0]["limitations"])
        hidden = BlsLausProvider(
            year="2024",
            transport=lambda url: body("-"),
            retrieved_on="2026-11-09",
        ).observations("Restaurant", "Alabama")
        self.assertEqual(hidden[0]["value"], "Not disclosed")
        uncovered = load_market("Restaurant", "Example county", provider)
        self.assertEqual(uncovered["status"], "fallback")
        self.assertEqual(uncovered["label"], NOT_COVERED_LABEL)
        failed = load_market(
            "Restaurant",
            "Georgia",
            BlsLausProvider(year="2024", transport=lambda url: (_ for _ in ()).throw(RuntimeError("down"))),
        )
        self.assertEqual(failed["status"], "fallback")
        self.assertEqual(failed["label"], FALLBACK_LABEL)
        selected = get_market_provider(environ={"MARKET_LAUS": "laus", "LAUS_YEAR": "2023"}, transport=transport)
        self.assertEqual(selected.name, "bls-laus")
        self.assertEqual(selected.year, "2023")
        page = market_page([], "Restaurant", "Colbert County, Alabama", provider=provider, tier="analyze")
        self.assertIn("<h2>Combined summary</h2>", page)
        self.assertIn("Unemployment rate (percent):", page)
        self.assertIn("3.4", page)
        self.assertIn("Labor force:", page)
        self.assertIn("24567", page)
        self.assertIn(LAUS_SOURCE, page)
        self.assertIn("These figures do not clear INSUFFICIENT_DEMAND_EVIDENCE", page)
        self.assertIn("Monitoring active: false", page)
        result = {
            "recommendation": "do-not-proceed",
            "blocking_flags": ["INSUFFICIENT_DEMAND_EVIDENCE"],
            "readiness_status": "internal",
            "human_review_approved": False,
        }
        before = copy.deepcopy(result)
        before_sample = hashlib.sha256(SAMPLE.read_bytes()).hexdigest()
        export_market_observations("Restaurant", "Colbert County, Alabama", provider)
        self.assertEqual(result, before)
        self.assertFalse(result["human_review_approved"])
        self.assertEqual(hashlib.sha256(SAMPLE.read_bytes()).hexdigest(), before_sample)


if __name__ == "__main__":
    unittest.main()

"""Local Analyze app. The 0.1 baseline recommendation stays unchanged."""

import hashlib
import json
import tempfile
import threading
import unittest
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from app.analysis import analyze_record
from app.server import make_server
from app.store import (
    BASELINE_ID,
    RESTAURANT_ID,
    SAMPLE,
    connect,
    create_assessment,
    get_assessment,
    save_profile,
    seed,
)

ROOT = Path(__file__).resolve().parent.parent
BASELINE_FILE = ROOT / "reports" / "output" / "rugd-intelligence-draft.md"


class TestAnalyzeApp(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.db = Path(self.directory.name) / "analyze.sqlite"
        self.connection = connect(self.db)
        seed(self.connection)

    def tearDown(self) -> None:
        self.connection.close()
        self.directory.cleanup()

    def test_baseline_recommendation_is_preserved(self) -> None:
        before = hashlib.sha256(SAMPLE.read_bytes()).hexdigest()
        record = get_assessment(self.connection, BASELINE_ID)
        assert record is not None
        result = analyze_record(record)
        self.assertEqual(result["recommendation"], "do-not-proceed")
        self.assertIn("INSUFFICIENT_DEMAND_EVIDENCE", result["blocking_flags"])
        self.assertEqual(result["demand"]["status"], "uncleared")
        self.assertEqual(result["readiness_status"], "internal")
        self.assertEqual(result["human_review_status"], "pending")
        self.assertFalse(result["human_review_approved"])
        self.assertFalse(result["is_final"])
        self.assertIsNone(result["audit"]["recommendation"]["overall_feasibility_score"])
        self.assertEqual(hashlib.sha256(SAMPLE.read_bytes()).hexdigest(), before)
        self.assertIn("do-not-proceed", BASELINE_FILE.read_text(encoding="utf-8"))

    def test_customer_cannot_approve_or_edit_the_baseline(self) -> None:
        with self.assertRaises(PermissionError):
            save_profile(
                self.connection,
                BASELINE_ID,
                {"human_review_approved": True, "business_name": "Changed"},
            )
        record = get_assessment(self.connection, BASELINE_ID)
        assert record is not None
        self.assertFalse(record["human_review_approved"])
        self.assertEqual(record["business_name"], "RUGD Intelligence")

    def test_draft_save_and_tier_change_keep_the_result(self) -> None:
        assessment_id = create_assessment(
            self.connection,
            business_name="Draft Cafe",
            purpose="startup_feasibility",
            tier="explore",
        )
        save_profile(
            self.connection,
            assessment_id,
            {
                "business_name": "Draft Cafe",
                "purpose": "startup_feasibility",
                "tier": "explore",
                "construction_cost": "100000",
                "hypothetical": True,
            },
        )
        saved = get_assessment(self.connection, assessment_id)
        assert saved is not None
        self.assertEqual(saved["profile"]["construction_cost"], "100000")
        result = analyze_record(saved)
        from app.store import save_result

        save_result(self.connection, assessment_id, result.get("intake"), result)
        save_profile(
            self.connection,
            assessment_id,
            {**saved["profile"], "tier": "partner"},
        )
        again = get_assessment(self.connection, assessment_id)
        assert again is not None
        self.assertEqual(again["tier"], "partner")
        self.assertEqual(again["result"]["recommendation"], result["recommendation"])
        self.assertFalse(again["human_review_approved"])

    def test_customer_demand_yes_does_not_clear_the_gate(self) -> None:
        assessment_id = create_assessment(
            self.connection,
            business_name="Demand Cafe",
            purpose="startup_feasibility",
            tier="explore",
        )
        save_profile(
            self.connection,
            assessment_id,
            {
                "business_name": "Demand Cafe",
                "purpose": "startup_feasibility",
                "tier": "explore",
                "demand_evidence": "yes",
                "operator_capacity_adequate": "yes",
                "unresolved_regulatory_or_liability": "no",
                "extraction_without_reinvestment": "no",
            },
        )
        record = get_assessment(self.connection, assessment_id)
        assert record is not None
        result = analyze_record(record)
        self.assertEqual(result["recommendation"], "conditional")
        self.assertNotIn("INSUFFICIENT_DEMAND_EVIDENCE", result["blocking_flags"])
        self.assertIn("DEMAND_EVIDENCE_UNVERIFIED", result["gap_flags"])
        self.assertEqual(result["demand"]["status"], "unverified")
        self.assertIsNone(result["intake"]["verified_data"]["revenue_trailing_12m"])
        self.assertEqual(result["readiness_status"], "conditional")
        self.assertNotEqual(result["readiness_status"], "investor-ready")
        self.assertFalse(result["human_review_approved"])
        self.assertFalse(result["is_final"])

    def test_verified_record_clears_only_under_the_documented_rule(self) -> None:
        revenue = self._analyzed(
            {
                "verified_record_source": "verified",
                "verified_revenue_trailing_12m": "125000",
                "verified_demand_rationale": "Reviewed trailing revenue statement.",
            }
        )
        self.assertEqual(revenue["demand"]["status"], "cleared")
        self.assertNotIn("INSUFFICIENT_DEMAND_EVIDENCE", revenue["blocking_flags"])
        self.assertNotIn("DEMAND_EVIDENCE_UNVERIFIED", revenue["gap_flags"])
        self.assertEqual(revenue["intake"]["verified_data"]["revenue_trailing_12m"], 125000.0)
        self.assertFalse(revenue["human_review_approved"])
        self.assertFalse(revenue["is_final"])
        self.assertNotEqual(revenue["readiness_status"], "investor-ready")
        self.assertIn("**Status:** cleared", revenue["report_markdown"])
        self.assertEqual(revenue["audit"]["demand_evidence"]["status"], "cleared")
        self.assertFalse(revenue["audit"]["demand_evidence"]["human_review_approved"])
        self.assertFalse(revenue["audit"]["demand_evidence"]["investor_ready"])

        statement = self._analyzed(
            {
                "verified_record_source": "verified",
                "verified_demand_evidence": "true",
                "verified_demand_rationale": "Reviewed signed customer evidence.",
            }
        )
        self.assertEqual(statement["demand"]["status"], "cleared")
        self.assertIsNone(statement["intake"]["verified_data"]["revenue_trailing_12m"])
        verified_claims = [
            item
            for item in statement["intake"]["assumptions"]
            if item["key"] == "demand_evidence" and item["source"] == "verified"
        ]
        self.assertEqual(verified_claims[0]["value"], True)
        self.assertFalse(statement["human_review_approved"])
        self.assertNotEqual(statement["readiness_status"], "investor-ready")

    def test_unverified_demo_and_conflicting_records_stay_uncleared(self) -> None:
        cases = [
            {"verified_revenue_trailing_12m": "125000", "verified_demand_rationale": "No source selected."},
            {
                "verified_record_source": "ai_interpretation",
                "verified_revenue_trailing_12m": "125000",
                "verified_demand_rationale": "Model text.",
            },
            {
                "verified_record_source": "verified",
                "verified_revenue_trailing_12m": "0",
                "verified_demand_rationale": "Zero is not sufficient.",
            },
            {
                "demand_evidence": "no",
                "verified_record_source": "verified",
                "verified_revenue_trailing_12m": "125000",
                "verified_demand_rationale": "Conflicts with the customer denial.",
            },
            {
                "verified_record_source": "verified",
                "verified_demand_evidence": "true",
            },
        ]
        for profile in cases:
            result = self._analyzed(profile)
            self.assertEqual(result["demand"]["status"], "uncleared", profile)
            self.assertIn("INSUFFICIENT_DEMAND_EVIDENCE", result["blocking_flags"])
            self.assertIn("**Status:** uncleared", result["report_markdown"])
            self.assertEqual(result["audit"]["demand_evidence"]["status"], "uncleared")
            self.assertFalse(result["human_review_approved"])

        record = get_assessment(self.connection, RESTAURANT_ID)
        assert record is not None
        record["profile"].update(
            {
                "verified_record_source": "verified",
                "verified_revenue_trailing_12m": "125000",
                "verified_demand_evidence": "true",
                "verified_demand_rationale": "Demonstration numbers are not evidence.",
            }
        )
        demo = analyze_record(record)
        self.assertEqual(demo["demand"]["status"], "uncleared")
        self.assertIsNone(demo["intake"]["verified_data"]["revenue_trailing_12m"])
        self.assertIn("hypothetical demonstration", " ".join(demo["missing"]))

    def _analyzed(self, profile: dict) -> dict:
        assessment_id = create_assessment(
            self.connection,
            business_name="Verified Path",
            purpose="startup_feasibility",
            tier="analyze",
        )
        current = get_assessment(self.connection, assessment_id)
        assert current is not None
        save_profile(self.connection, assessment_id, {**current["profile"], **profile})
        saved = get_assessment(self.connection, assessment_id)
        assert saved is not None
        return analyze_record(saved)

    def test_restaurant_seed_is_hypothetical_and_not_verified(self) -> None:
        record = get_assessment(self.connection, RESTAURANT_ID)
        assert record is not None
        self.assertTrue(record["hypothetical"])
        self.assertEqual(record["profile"]["industry"], "Restaurant")
        self.assertEqual(record["profile"]["construction_cost"], "100000")
        self.assertEqual(record["profile"]["stage"], "Idea")
        result = analyze_record(record)
        self.assertTrue(any("Insufficient" in item for item in result["missing"]))
        self.assertNotEqual(result["recommendation"], "go")

    def test_http_journey_refuses_customer_approval(self) -> None:
        server = make_server(self.db, port=0)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        host, port = server.server_address
        base = f"http://{host}:{port}"
        try:
            with urllib.request.urlopen(base + "/") as response:
                page = response.read().decode("utf-8")
            self.assertIn("RUGD", page)
            self.assertIn("Hypothetical Restaurant Startup", page)
            with urllib.request.urlopen(base + "/market") as response:
                market = response.read().decode("utf-8")
            self.assertIn("Hypothetical demonstration", market)
            request = urllib.request.Request(
                base + "/assessments",
                data=b"business_name=Journey+Cafe&purpose=startup_feasibility&tier=explore&human_review_approved=true",
                method="POST",
            )
            try:
                urllib.request.urlopen(request)
                self.fail("approval field should be refused")
            except urllib.error.HTTPError as exc:
                self.assertEqual(exc.code, 403)
            opener = urllib.request.build_opener(urllib.request.HTTPRedirectHandler)
            created = urllib.request.Request(
                base + "/assessments",
                data=b"business_name=Journey+Cafe&purpose=startup_feasibility&tier=explore",
                method="POST",
            )
            with opener.open(created) as response:
                body = response.read().decode("utf-8")
                assessment_url = response.geturl()
            self.assertIn("Journey Cafe", body)
            self.assertIn("Save draft", body)
            saved = urllib.request.Request(
                assessment_url.rstrip("/") + "/save",
                data=b"business_name=Journey+Cafe&purpose=startup_feasibility&tier=explore&concept=Guided+draft",
                method="POST",
            )
            with opener.open(saved) as response:
                draft = response.read().decode("utf-8")
            self.assertIn("Guided draft", draft)
            analyzed = urllib.request.Request(
                assessment_url.rstrip("/") + "/analyze",
                data=b"business_name=Journey+Cafe&purpose=startup_feasibility&tier=explore&concept=Guided+draft",
                method="POST",
            )
            with opener.open(analyzed) as response:
                results = response.read().decode("utf-8")
                results_url = response.geturl()
            self.assertIn("do-not-proceed", results)
            self.assertIn("INSUFFICIENT_DEMAND_EVIDENCE", results)
            self.assertIn("human_review_approved", results)
            self.assertIn("false", results)
            with urllib.request.urlopen(results_url.replace("/results", "/report")) as response:
                report = response.read().decode("utf-8")
            self.assertIn("do-not-proceed", report)
            self.assertIn("INSUFFICIENT_DEMAND_EVIDENCE", report)
            with urllib.request.urlopen(results_url.replace("/results", "/audit")) as response:
                audit = json.loads(response.read().decode("utf-8"))
            self.assertIn(
                "INSUFFICIENT_DEMAND_EVIDENCE",
                audit["recommendation"]["blocking_flags"],
            )
            self.assertFalse(audit["human_review_approved"])
            self.assertEqual(audit["investor_readiness"]["status"], "internal")
            with urllib.request.urlopen(base + "/assessments/rugd-intelligence-baseline/results") as response:
                baseline_page = response.read().decode("utf-8")
            self.assertIn("do-not-proceed", baseline_page)
            self.assertIn("INSUFFICIENT_DEMAND_EVIDENCE", baseline_page)
            self.assertIn("do-not-proceed", BASELINE_FILE.read_text(encoding="utf-8"))
            verified = urllib.parse.urlencode(
                {
                    "business_name": "Verified Path",
                    "purpose": "startup_feasibility",
                    "tier": "analyze",
                    "verified_record_source": "verified",
                    "verified_revenue_trailing_12m": "125000",
                    "verified_demand_rationale": "Reviewed trailing revenue statement.",
                }
            ).encode()
            created_verified = urllib.request.Request(
                base + "/assessments",
                data=b"business_name=Verified+Path&purpose=startup_feasibility&tier=analyze",
                method="POST",
            )
            with opener.open(created_verified) as response:
                verified_url = response.geturl()
            analyzed_verified = urllib.request.Request(
                verified_url.rstrip("/") + "/analyze",
                data=verified,
                method="POST",
            )
            with opener.open(analyzed_verified) as response:
                verified_results = response.read().decode("utf-8")
                verified_results_url = response.geturl()
            self.assertIn("Status:", verified_results)
            self.assertIn("cleared", verified_results)
            self.assertIn("human_review_approved", verified_results)
            self.assertNotIn("Investor readiness: investor-ready", verified_results)
            with urllib.request.urlopen(verified_results_url.replace("/results", "/report")) as response:
                verified_report = response.read().decode("utf-8")
            self.assertIn("**Status:** cleared", verified_report)
            self.assertIn("human_review_approved remains false", verified_report)
            with urllib.request.urlopen(verified_results_url.replace("/results", "/audit")) as response:
                verified_audit = json.loads(response.read().decode("utf-8"))
            self.assertEqual(verified_audit["demand_evidence"]["status"], "cleared")
            self.assertFalse(verified_audit["human_review_approved"])
            self.assertFalse(verified_audit["investor_readiness"]["human_review_approved"])
            self.assertNotEqual(verified_audit["investor_readiness"]["status"], "investor-ready")
            self.assertIn("do-not-proceed", BASELINE_FILE.read_text(encoding="utf-8"))
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=3)


if __name__ == "__main__":
    unittest.main()

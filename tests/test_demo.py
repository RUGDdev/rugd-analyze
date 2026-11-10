"""The seeded restaurant demonstrations stay labeled and follow the demand rule."""

import hashlib
import unittest

from app.analysis import analyze_record
from app.pages import assessment_form, dashboard, results_page
from app.store import (
    BASELINE_ID,
    HYPOTHETICAL_DEMO_LABEL,
    RESTAURANT_ID,
    RESTAURANT_VERIFIED_ID,
    SAMPLE,
    connect,
    get_assessment,
    list_assessments,
    seed,
)


class TestRestaurantDemonstration(unittest.TestCase):
    def setUp(self) -> None:
        import tempfile
        from pathlib import Path

        self.directory = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.connection = connect(Path(self.directory.name) / "analyze.sqlite")
        seed(self.connection)

    def tearDown(self) -> None:
        self.connection.close()
        self.directory.cleanup()

    def test_unanswered_and_verified_demos_keep_the_baseline(self) -> None:
        before = hashlib.sha256(SAMPLE.read_bytes()).hexdigest()
        primary = get_assessment(self.connection, RESTAURANT_ID)
        verified = get_assessment(self.connection, RESTAURANT_VERIFIED_ID)
        baseline = get_assessment(self.connection, BASELINE_ID)
        assert primary is not None and verified is not None and baseline is not None
        self.assertTrue(primary["hypothetical"])
        self.assertFalse(primary["read_only"])
        self.assertNotEqual(primary["id"], BASELINE_ID)
        self.assertEqual(primary["pilot_label"], HYPOTHETICAL_DEMO_LABEL)
        self.assertEqual(primary["profile"]["demand_evidence"], "")
        self.assertEqual(primary["profile"]["seats"], "48")
        self.assertEqual(primary["profile"]["average_ticket"], "28")
        self.assertEqual(primary["profile"]["construction_cost"], "100000")
        self.assertFalse(primary["human_review_approved"])
        unanswered = analyze_record(primary)
        self.assertEqual(unanswered["recommendation"], "do-not-proceed")
        self.assertIn("INSUFFICIENT_DEMAND_EVIDENCE", unanswered["blocking_flags"])
        self.assertTrue((unanswered.get("projection") or {}).get("calculated"))
        self.assertFalse(unanswered["human_review_approved"])
        self.assertNotEqual(unanswered["readiness_status"], "investor-ready")
        self.assertFalse(unanswered["audit"]["investor_readiness"]["investor_ready"])

        self.assertFalse(verified["hypothetical"])
        self.assertFalse(verified["read_only"])
        self.assertNotEqual(verified["id"], BASELINE_ID)
        self.assertEqual(verified["profile"]["verified_record_source"], "verified")
        self.assertEqual(verified["profile"]["verified_demand_evidence"], "true")
        self.assertTrue(verified["profile"]["verified_demand_rationale"])
        self.assertEqual(verified["profile"]["demand_evidence"], "")
        cleared = analyze_record(verified)
        self.assertNotIn("INSUFFICIENT_DEMAND_EVIDENCE", cleared["blocking_flags"])
        self.assertEqual(cleared["demand"]["status"], "cleared")
        self.assertFalse(cleared["human_review_approved"])
        self.assertFalse(cleared["is_final"])
        self.assertNotEqual(cleared["readiness_status"], "investor-ready")
        self.assertFalse(cleared["audit"]["investor_readiness"]["investor_ready"])

        records = list_assessments(self.connection)
        home = dashboard(records)
        self.assertIn("Welcome to RUGD Intelligence", home)
        self.assertNotIn(HYPOTHETICAL_DEMO_LABEL, home)
        self.assertNotIn("Official baseline", home)
        self.assertNotIn("Verified-demand demonstration — not a real assessment", home)
        form = assessment_form(primary)
        self.assertIn(HYPOTHETICAL_DEMO_LABEL, form)
        self.assertIn("Open the verified-demand demonstration", form)
        results = results_page(primary, unanswered)
        self.assertIn(HYPOTHETICAL_DEMO_LABEL, results)
        self.assertIn("INSUFFICIENT_DEMAND_EVIDENCE:</strong> present", results)
        self.assertNotIn("Investor readiness:</strong> investor-ready", results)
        verified_results = results_page(verified, cleared)
        self.assertIn("Verified-demand demonstration — not a real assessment", verified_results)
        self.assertIn("INSUFFICIENT_DEMAND_EVIDENCE:</strong> not present", verified_results)
        self.assertNotIn("Investor readiness:</strong> investor-ready", verified_results)
        self.assertTrue(baseline["read_only"])
        self.assertFalse(baseline["human_review_approved"])
        baseline_result = analyze_record(baseline)
        self.assertEqual(baseline_result["recommendation"], "do-not-proceed")
        self.assertIn("INSUFFICIENT_DEMAND_EVIDENCE", baseline_result["blocking_flags"])
        self.assertEqual(hashlib.sha256(SAMPLE.read_bytes()).hexdigest(), before)

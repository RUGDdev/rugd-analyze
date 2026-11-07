"""End-to-end tests for the pilot runner and the RUGD Intelligence sample."""

import json
import tempfile
import unittest
from pathlib import Path

from run_assessment import ROOT, run_assessment, validate_intake


SAMPLE = ROOT / "intake" / "samples" / "rugd_intelligence.json"


class TestRunner(unittest.TestCase):
    def test_sample_self_assessment_writes_a_draft(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as directory:
            output = Path(directory) / "rugd-intelligence-draft.md"
            artifacts = run_assessment(SAMPLE, output)
            text = artifacts.report_text
            self.assertEqual(artifacts.recommendation.draft_recommendation, "do-not-proceed")
            self.assertFalse(artifacts.recommendation.is_final)
            self.assertTrue(artifacts.recommendation.requires_human_review)
            self.assertIn("**Recommendation:** do-not-proceed", text)
            self.assertIn("pending — draft only, not a final recommendation", text)
            self.assertIn("INSUFFICIENT_DEMAND_EVIDENCE", text)
            self.assertIn("FINANCIAL_INPUTS_NOT_MEASURED", text)
            self.assertIn("Not computed.", text)
            self.assertIn("2026-10-26", text)
            self.assertIn("0.00 (arithmetic on unmeasured inputs; not a cash-flow finding)", text)
            self.assertNotIn("{{", text)
            self.assertIn("Human approval required", text)
            self.assertIn("## Startup Capital and Projection", text)
            self.assertIn("Construction cost was not supplied.", text)
            self.assertIn("investor_ready: false", text)
            self.assertIn("## Financial Summary", text)
            self.assertIn("### Reasonableness check", text)
            self.assertIn("Secondary industry benchmark", text)
            self.assertIn("Labor %: not calculated", text)
            self.assertIn("Occupancy %: not calculated", text)
            self.assertIn("Pre-tax margin: not calculated", text)
            self.assertIn("## Investor Readiness", text)
            self.assertIn("**Status:** internal", text)
            self.assertIn("**human_review_approved:** false", text)
            self.assertIn(
                "**No recommend-against flags are active:** failed.",
                text,
            )
            self.assertIn(
                "**Stewardship does not show extraction without reinvestment capacity:** passed.",
                text,
            )
            self.assertIn(
                "Downside DSCR was not supplied by the deterministic engine.",
                text,
            )
            self.assertIn(
                "Release for investors still requires explicit human approval.",
                text,
            )
            audit = json.loads(artifacts.audit_path.read_text(encoding="utf-8"))
            self.assertEqual(audit["investor_readiness"]["status"], "internal")
            self.assertFalse(audit["investor_readiness"]["human_review_approved"])
            self.assertFalse(audit["startup_capital"]["calculated"])
            self.assertFalse(audit["startup_capital"]["investor_ready"])
            self.assertFalse(audit["startup_capital"]["is_final"])
            self.assertFalse(audit["human_review"]["is_final"])
            self.assertIsNone(audit["human_review"]["recorded_by"])
            self.assertEqual(audit["recommendation"]["overall_feasibility_score"], None)
            self.assertEqual(audit["model_version"], "0.1-pilot")
            self.assertTrue(audit["ai_contributions"])
            benchmarks = audit["secondary_industry_benchmarks"]
            self.assertEqual(benchmarks["label"], "secondary industry benchmark")
            self.assertFalse(benchmarks["may_raise_recommend_against_flags"])
            self.assertFalse(benchmarks["may_clear_recommend_against_flags"])
            stored = {item["id"]: item["value"] for item in benchmarks["benchmarks"]}
            self.assertEqual(stored["full_service_income_before_taxes"], 0.028)
            self.assertEqual(stored["full_service_labor"], 0.365)

    def test_output_outside_the_project_is_rejected(self):
        with self.assertRaises(ValueError):
            run_assessment(SAMPLE, Path(tempfile.gettempdir()) / "rugd-outside.md")

    def test_invalid_engagement_is_rejected(self):
        intake = json.loads(SAMPLE.read_text(encoding="utf-8"))
        intake["engagement_type"] = "new_vertical"
        errors = validate_intake(intake)
        self.assertTrue(any("engagement_type" in error for error in errors))

    def test_missing_date_is_not_taken_from_the_clock(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as directory:
            intake_path = Path(directory) / "intake.json"
            payload = json.loads(SAMPLE.read_text(encoding="utf-8"))
            del payload["as_of_date"]
            intake_path.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaises(ValueError) as raised:
                run_assessment(intake_path, Path(directory) / "draft.md")
            self.assertIn("does not read the system clock", str(raised.exception))


if __name__ == "__main__":
    unittest.main()

"""The Demonstration Analyst explains results and cannot change them."""

import copy
import unittest

from app.analyst import DemonstrationAnalyst, explain, get_analyst
from app.store import BASELINE_ID, connect, create_assessment, get_assessment, save_profile, seed
from app.analysis import analyze_record
import tempfile
from pathlib import Path


class TestDemonstrationAnalyst(unittest.TestCase):
    def test_analyst_is_the_labeled_demonstration_stand_in(self) -> None:
        analyst = get_analyst()
        self.assertIsInstance(analyst, DemonstrationAnalyst)
        self.assertIn("Demonstration Analyst", analyst.label)
        self.assertIn("No external AI service", analyst.label)

    def test_explain_cannot_mutate_engine_outputs_or_flags(self) -> None:
        directory = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        connection = connect(Path(directory.name) / "analyze.sqlite")
        seed(connection)
        record = get_assessment(connection, BASELINE_ID)
        assert record is not None
        result = analyze_record(record)
        result["financial"] = {
            "base_monthly_cash_flow": 12.5,
            "downside_monthly_cash_flow": -3.0,
        }
        before_result = copy.deepcopy(result)
        before_record = copy.deepcopy(record)
        lines = explain(record, result)
        self.assertEqual(result, before_result)
        self.assertEqual(record["business_name"], before_record["business_name"])
        self.assertEqual(result["recommendation"], "do-not-proceed")
        self.assertIn("INSUFFICIENT_DEMAND_EVIDENCE", result["blocking_flags"])
        self.assertEqual(result["readiness_status"], "internal")
        self.assertFalse(result["human_review_approved"])
        self.assertFalse(result["is_final"])
        self.assertEqual(result["financial"]["base_monthly_cash_flow"], 12.5)
        self.assertEqual(result["audit"]["view_summary"]["human_review_status"], "pending")
        text = " ".join(lines)
        self.assertIn("Demonstration Analyst", text)
        self.assertIn("do-not-proceed", text)
        self.assertIn("INSUFFICIENT_DEMAND_EVIDENCE is present", text)
        self.assertIn("cannot change the Investor Readiness Gate", text)
        self.assertIn("human_review_approved remains false", text)
        self.assertNotIn("human_review_approved remains true", text)
        connection.close()
        directory.cleanup()

    def test_explain_quotes_engine_projection_without_changing_it(self) -> None:
        directory = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        connection = connect(Path(directory.name) / "analyze.sqlite")
        seed(connection)
        assessment_id = create_assessment(
            connection,
            business_name="Analyst Cafe",
            purpose="startup_feasibility",
            tier="analyze",
        )
        current = get_assessment(connection, assessment_id)
        assert current is not None
        save_profile(
            connection,
            assessment_id,
            {
                **current["profile"],
                "industry": "Restaurant",
                "stage": "Idea",
                "construction_cost": "100000",
                "seats": "40",
                "average_ticket": "25",
                "weekday_occupancy": "0.4",
                "weekend_occupancy": "0.7",
                "operating_days": "6",
                "contribution_margin": "0.6",
            },
        )
        record = get_assessment(connection, assessment_id)
        assert record is not None
        result = analyze_record(record)
        before = copy.deepcopy(result)
        lines = explain(record, result)
        text = " ".join(lines)
        self.assertEqual(result, before)
        self.assertEqual(lines[0], "Demonstration Analyst. No external AI service is connected.")
        self.assertIn("Sources and uses from the engine", text)
        self.assertIn("Base case from the engine", text)
        self.assertIn("Downside case from the engine", text)
        self.assertIn("DSCR", text)
        self.assertIn("INSUFFICIENT_DEMAND_EVIDENCE", text)
        self.assertIn("Recommend-against flag still active: INSUFFICIENT_DEMAND_EVIDENCE", text)
        self.assertFalse(result["human_review_approved"])
        self.assertEqual(result["readiness_status"], "internal")
        self.assertEqual(result["recommendation"], before["recommendation"])
        self.assertEqual(result["projection"], before["projection"])
        self.assertIn("INSUFFICIENT_DEMAND_EVIDENCE", result["blocking_flags"])
        connection.close()
        directory.cleanup()


if __name__ == "__main__":
    unittest.main()

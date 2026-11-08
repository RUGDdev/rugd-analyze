"""The analyst explains results and cannot change them."""

import copy
import os
import unittest

from app.analyst import SAFETY_PROMPT, DemonstrationAnalyst, explain, get_analyst
from app.pages import analyst_page, results_page
from app.store import BASELINE_ID, connect, create_assessment, get_assessment, save_profile, seed
from app.analysis import analyze_record
import tempfile
from pathlib import Path


_ANALYST_ENV = (
    "ANALYST_PROVIDER",
    "ANALYST_MODEL",
    "ANTHROPIC_API_KEY",
    "OPENAI_API_KEY",
    "XAI_API_KEY",
)


class TestDemonstrationAnalyst(unittest.TestCase):
    def setUp(self) -> None:
        self._saved = {key: os.environ.get(key) for key in _ANALYST_ENV}
        for key in _ANALYST_ENV:
            os.environ.pop(key, None)

    def tearDown(self) -> None:
        for key, value in self._saved.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value

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

    def test_missing_key_and_failed_call_fall_back_without_mutation(self) -> None:
        record = {"business_name": "Prompt Cafe", "profile": {"token": "raw-session-token", "concept": "Keep"}}
        result = {
            "engine_ran": True,
            "recommendation": "do-not-proceed",
            "blocking_flags": ["INSUFFICIENT_DEMAND_EVIDENCE"],
            "gap_flags": [],
            "readiness_status": "internal",
            "human_review_approved": False,
            "is_final": False,
            "financial": {"base_monthly_cash_flow": 4},
            "demand": {"status": "uncleared", "provenance": []},
            "view_summary": {
                "insufficient_demand_evidence": "present",
                "demand_status": "uncleared",
                "human_review_status": "pending",
            },
        }
        before_record = copy.deepcopy(record)
        before_result = copy.deepcopy(result)
        missing = explain(record, result, environ={"ANALYST_PROVIDER": "claude"})
        self.assertTrue(missing[0].startswith("Fallback: Demonstration Analyst."))
        self.assertIn("No API key is configured.", missing[0])
        self.assertIn("Demonstration Analyst. No external AI service is connected.", missing)
        self.assertEqual(record, before_record)
        self.assertEqual(result, before_result)
        seen: dict[str, object] = {}

        def transport(url: str, headers: dict[str, str], payload: dict[str, object]) -> dict[str, object]:
            seen["url"] = url
            seen["headers"] = headers
            seen["payload"] = payload
            raise RuntimeError("provider down")

        failed = explain(
            record,
            result,
            environ={"ANALYST_PROVIDER": "openai", "OPENAI_API_KEY": "sk-test-key"},
            transport=transport,
        )
        self.assertTrue(failed[0].startswith("Fallback: Demonstration Analyst."))
        self.assertIn("The external analyst call failed.", failed[0])
        self.assertEqual(record, before_record)
        self.assertEqual(result, before_result)
        self.assertIn("sk-test-key", str(seen["headers"]))
        body = str(seen["payload"])
        self.assertIn(SAFETY_PROMPT, body)
        self.assertNotIn("sk-test-key", body)
        self.assertNotIn("raw-session-token", body)

    def test_mock_provider_is_labeled_and_cannot_change_the_result(self) -> None:
        record = {
            "id": "mock-cafe",
            "business_name": "Mock Cafe",
            "profile": {"concept": "Keep", "session_id": "abc123secret"},
        }
        result = {
            "engine_ran": True,
            "recommendation": "do-not-proceed",
            "blocking_flags": ["INSUFFICIENT_DEMAND_EVIDENCE"],
            "gap_flags": ["DEMAND_EVIDENCE_UNVERIFIED"],
            "readiness_status": "internal",
            "human_review_approved": False,
            "is_final": False,
            "financial": {"base_monthly_cash_flow": 9},
            "projection": {"calculated": False},
        }
        before = copy.deepcopy(result)

        def claude(url: str, headers: dict[str, str], payload: dict[str, object]) -> dict[str, object]:
            self.assertIn("api.anthropic.com", url)
            self.assertEqual(payload["system"], SAFETY_PROMPT)
            self.assertNotIn("abc123secret", str(payload))
            return {"content": [{"text": "The draft recommendation is do-not-proceed. human_review_approved stays false."}]}

        lines = explain(
            record,
            result,
            environ={"ANALYST_PROVIDER": "anthropic", "ANTHROPIC_API_KEY": "claude-test"},
            transport=claude,
        )
        self.assertTrue(lines[0].startswith("External analyst (claude)."))
        self.assertIn("Not the Demonstration Analyst", lines[0])
        self.assertIn(SAFETY_PROMPT, lines[1])
        self.assertIn("do-not-proceed", " ".join(lines))
        self.assertEqual(result, before)
        self.assertIn("INSUFFICIENT_DEMAND_EVIDENCE", result["blocking_flags"])
        self.assertFalse(result["human_review_approved"])
        self.assertEqual(result["readiness_status"], "internal")

        def grok(url: str, headers: dict[str, str], payload: dict[str, object]) -> dict[str, object]:
            self.assertIn("api.x.ai", url)
            self.assertIn(SAFETY_PROMPT, str(payload["messages"]))
            return {"choices": [{"message": {"content": "Downside cash flow stays the engine figure."}}]}

        grok_lines = explain(
            record,
            result,
            environ={"ANALYST_PROVIDER": "grok", "XAI_API_KEY": "xai-test"},
            transport=grok,
        )
        self.assertTrue(grok_lines[0].startswith("External analyst (grok)."))
        self.assertEqual(result, before)
        page = analyst_page(record, grok_lines)
        self.assertIn("External analyst (grok).", page)
        self.assertIn("cannot alter authoritative results", page)
        os.environ["ANALYST_PROVIDER"] = "openai"
        os.environ["OPENAI_API_KEY"] = "page-key"
        try:
            shown = results_page(
                {"id": "draft-1", "business_name": "Mock Cafe", "tier": "explore", "pilot_label": "Draft", "profile": {}},
                result,
            )
        finally:
            os.environ.pop("ANALYST_PROVIDER", None)
            os.environ.pop("OPENAI_API_KEY", None)
        self.assertIn("External analyst (openai).", shown)
        self.assertIn("Open the optional analyst explanation", shown)
        self.assertIn("cannot alter authoritative results", shown)
        self.assertEqual(result, before)


if __name__ == "__main__":
    unittest.main()

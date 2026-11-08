"""The 0.2 acceptance checklist stays aligned with the prototype boundaries."""

import unittest
from pathlib import Path

from app.pages import (
    analyze_index,
    audit_html_page,
    dashboard,
    explore_page,
    market_page,
    partner_page,
    reports_page,
    results_page,
    validate_page,
)

ROOT = Path(__file__).resolve().parent.parent
_NOTE = "Local prototype. Not production security. This screen does not grant investor-ready status."


class TestAcceptanceChecklist(unittest.TestCase):
    def test_checklist_maps_criteria_and_owner_decisions(self) -> None:
        text = (ROOT / "ACCEPTANCE.md").read_text(encoding="utf-8")
        for status in ("Met", "Partially met", "Demonstration-only"):
            self.assertIn(status, text)
        self.assertIn("do-not-proceed", text)
        self.assertIn("INSUFFICIENT_DEMAND_EVIDENCE", text)
        self.assertIn("internal investor readiness", text)
        self.assertIn("pending human review", text)
        self.assertIn("human_review_approved", text)
        self.assertIn("Owner decisions required before further work", text)
        for item in (
            "Production authentication",
            "Real market data sources",
            "approved scoring methodology",
            "Billing",
            "Investor matchmaking",
        ):
            self.assertIn(item, text)
        self.assertIn("No feasibility score is calculated.", text)

    def test_customer_pages_share_prototype_warnings(self) -> None:
        baseline = {
            "id": "rugd-intelligence-baseline",
            "business_name": "RUGD Intelligence",
            "tier": "analyze",
            "read_only": True,
            "hypothetical": False,
            "pilot_label": "Official baseline. Not a completed customer study.",
            "profile": {},
            "result": None,
            "human_review_approved": False,
        }
        engine_result = {
            "engine_ran": True,
            "model_version": "0.1-pilot",
            "recommendation": "do-not-proceed",
            "blocking_flags": ["INSUFFICIENT_DEMAND_EVIDENCE"],
            "gap_flags": [],
            "missing": [],
            "human_review_approved": False,
            "human_review_status": "pending",
            "readiness_status": "internal",
            "financial": None,
            "projection": None,
            "projection_text": "",
            "demand": {"status": "uncleared"},
            "view_summary": {
                "recommendation": "do-not-proceed",
                "insufficient_demand_evidence": "present",
                "investor_readiness": "internal",
                "human_review_status": "pending",
                "human_review_approved": False,
                "demand_provenance": [],
            },
        }
        pages = {
            "dashboard": dashboard([baseline]),
            "explore": explore_page([baseline]),
            "analyze": analyze_index([baseline]),
            "results": results_page(baseline, engine_result),
            "validate": validate_page(None),
            "partner": partner_page(),
            "market": market_page(),
            "reports": reports_page([baseline]),
            "audit": audit_html_page(baseline, {"engine_ran": False, "message": "Analyze did not run."}),
        }
        for name, page in pages.items():
            self.assertIn(_NOTE, page, name)
            self.assertIn("local prototype", page, name)
            self.assertNotIn("Investor readiness:</strong> investor-ready", page, name)
            self.assertNotIn("Live feed connected: true", page, name)
            self.assertNotIn("Monitoring active: true", page, name)
        self.assertIn("Validate (demonstration)", pages["validate"])
        self.assertIn("Partner (demonstration)", pages["partner"])
        self.assertIn("Market Intelligence (demonstration)", pages["market"])
        self.assertIn("Authoritative financial numbers come only from the 0.1 engine.", pages["analyze"])
        self.assertIn("Authoritative financial numbers below come only from the 0.1 engine.", pages["results"])
        self.assertIn("Insufficient verified information to calculate.", pages["results"])
        self.assertIn("Recurring monitoring is not active", pages["partner"])
        self.assertIn("This screen cannot set human_review_approved.", pages["validate"])


if __name__ == "__main__":
    unittest.main()

"""Disabled future seams stay off and do not change the baseline."""

import copy
import hashlib
import unittest
from pathlib import Path

from app.future import billing_hooks, deployment_settings, future_status, production_auth_provider, scoring_methodology
from app.pages import (
    analyst_page,
    assessment_form,
    explore_page,
    market_page,
    new_assessment_page,
    results_page,
    settings_page,
)
from app.store import SAMPLE

ROOT = Path(__file__).resolve().parent.parent
REPORT = ROOT / "reports" / "output" / "rugd-intelligence-draft.md"


class TestFutureSeams(unittest.TestCase):
    def test_owner_seams_stay_disabled_and_do_not_change_flags(self) -> None:
        result = {
            "recommendation": "do-not-proceed",
            "blocking_flags": ["INSUFFICIENT_DEMAND_EVIDENCE"],
            "readiness_status": "internal",
            "human_review_approved": False,
        }
        before = copy.deepcopy(result)
        before_sample = hashlib.sha256(SAMPLE.read_bytes()).hexdigest()
        before_report = hashlib.sha256(REPORT.read_bytes()).hexdigest()
        status = future_status()
        authentication = production_auth_provider()
        scoring = scoring_methodology()
        deployment = deployment_settings()
        billing = billing_hooks()
        self.assertFalse(status["enabled"])
        self.assertFalse(authentication["enabled"])
        self.assertIsNone(authentication["provider"])
        self.assertFalse(scoring["enabled"])
        self.assertIsNone(scoring["score"])
        self.assertIn("methodology pending approval", scoring["message"])
        self.assertFalse(deployment["enabled"])
        self.assertEqual(deployment["bind_host"], "127.0.0.1")
        self.assertFalse(deployment["public_deployment"])
        self.assertFalse(billing["enabled"])
        self.assertIsNone(billing["charge"])
        identifiers = {item["id"] for item in status["decisions"]}
        self.assertEqual(
            identifiers,
            {"production_authentication", "scoring_methodology", "deployment", "billing"},
        )
        for item in status["decisions"]:
            self.assertEqual(item["status"], "disabled")
            self.assertTrue(item["owner_input"])
        self.assertEqual(result, before)
        self.assertFalse(result["human_review_approved"])
        self.assertEqual(hashlib.sha256(SAMPLE.read_bytes()).hexdigest(), before_sample)
        self.assertEqual(hashlib.sha256(REPORT.read_bytes()).hexdigest(), before_report)

    def test_customer_pages_share_the_warning_and_the_baseline_stays_visible(self) -> None:
        note = "This screen does not grant investor-ready status."
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
        before_sample = hashlib.sha256(SAMPLE.read_bytes()).hexdigest()
        pages = {
            "settings": settings_page(),
            "new": new_assessment_page(),
            "explore": explore_page([]),
            "form": assessment_form(baseline),
            "analyst": analyst_page(baseline, ["Demonstration Analyst. No external AI service is connected."]),
            "market": market_page(),
            "baseline": results_page(baseline, {"engine_ran": False, "message": "Analyze has not been run."}),
        }
        for name, page in pages.items():
            self.assertIn("Local prototype. Not production security.", page, name)
            self.assertIn(note, page, name)
        self.assertIn("Service tier: Explore.", pages["explore"])
        self.assertIn("Tier analyze.", pages["form"])
        self.assertIn("Service tier on this file: analyze.", pages["analyst"])
        self.assertIn("methodology pending approval", pages["settings"])
        self.assertIn("Production authentication provider", pages["settings"])
        self.assertIn("Billing hooks", pages["settings"])
        self.assertIn("not authoritative", pages["analyst"])
        self.assertIn("Synthetic example only", pages["market"])
        self.assertNotIn("Live feed connected: true", pages["market"])
        self.assertIn("Recommendation:</strong> do-not-proceed", pages["baseline"])
        self.assertIn("INSUFFICIENT_DEMAND_EVIDENCE:</strong> present", pages["baseline"])
        self.assertIn("Investor readiness:</strong> internal", pages["baseline"])
        self.assertIn("Human review status:</strong> pending", pages["baseline"])
        self.assertNotIn("Investor readiness:</strong> investor-ready", pages["baseline"])
        self.assertEqual(hashlib.sha256(SAMPLE.read_bytes()).hexdigest(), before_sample)

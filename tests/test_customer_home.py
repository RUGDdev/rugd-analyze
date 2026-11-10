"""The home page is per account, and each section explains itself."""

import hashlib
import tempfile
import unittest
from pathlib import Path

from app.analysis import analyze_record
from app.export import export_advisor_package
from app.pages import (
    _engine_status_line,
    advisor_summary_page,
    analyze_index,
    assessment_form,
    dashboard,
    explore_page,
    market_page,
    market_pulse_page,
    partner_page,
    reports_page,
    results_page,
    validate_page,
)
from app.store import BASELINE_ID, SAMPLE, connect, get_assessment, seed

NOTE = "Local prototype. Not production security. This screen does not grant investor-ready status."


class TestCustomerHome(unittest.TestCase):
    def test_status_line_uses_only_stored_engine_output(self) -> None:
        self.assertEqual(_engine_status_line({}), "Analyze has not been run.")
        missing = _engine_status_line(
            {
                "engine_ran": True,
                "blocking_flags": ["INSUFFICIENT_DEMAND_EVIDENCE"],
                "recommendation": "do-not-proceed",
                "projection": {"views": {"base": {"dscr": 1.4}}},
            }
        )
        self.assertEqual(missing, "Demand evidence missing.")
        self.assertNotIn("1.4", missing)
        covered = _engine_status_line(
            {
                "engine_ran": True,
                "blocking_flags": [],
                "recommendation": "conditional",
                "projection": {"views": {"base": {"dscr": 1.4}}},
            }
        )
        self.assertEqual(covered, "Base case DSCR available.")
        self.assertNotIn("1.4", covered)
        absent = _engine_status_line(
            {
                "engine_ran": True,
                "blocking_flags": [],
                "recommendation": "conditional",
                "projection": {"views": {"base": {"dscr": None}}},
            }
        )
        self.assertEqual(absent, "Stored recommendation: conditional.")
        self.assertNotIn("DSCR", absent)

    def test_section_welcomes_keep_the_warnings(self) -> None:
        pages = {
            "Explore": explore_page([]),
            "Analyze": analyze_index([]),
            "Validate": validate_page(None),
            "Partner": partner_page(),
            "Market Intelligence": market_page(),
            "Market Pulse": market_pulse_page(),
            "Reports": reports_page([]),
        }
        for title, page in pages.items():
            self.assertIn(f"Welcome to RUGD {title}", page)
            self.assertIn('id="section-welcome"', page)
            self.assertIn('class="sidebar"', page)
            self.assertIn(NOTE, page)
        self.assertIn("Validate (demonstration)", pages["Validate"])
        self.assertIn("Partner (demonstration)", pages["Partner"])
        self.assertIn("Market Intelligence (demonstration)", pages["Market Intelligence"])
        self.assertIn("Market Pulse (demonstration)", pages["Market Pulse"])
        self.assertIn("does not clear a flag", pages["Explore"])
        self.assertIn("forces do-not-proceed", pages["Analyze"])
        self.assertIn("cannot approve an assessment", pages["Validate"])
        self.assertIn("Monitoring is not running", pages["Partner"])
        self.assertIn("Monitoring is not active", pages["Market Pulse"])
        self.assertIn("Authoritative financial numbers come only from the 0.1 engine.", pages["Analyze"])
        mine = dashboard([], signed_in=True, viewer_id="guide-reader", surface="assessments")
        self.assertIn("Welcome to RUGD My Assessments", mine)
        self.assertIn('id="section-welcome"', mine)
        self.assertIn('href="/assessments" class="active"', mine)

    def test_progress_and_next_step_stay_informational(self) -> None:
        draft = {
            "id": "guide-1",
            "business_name": "Guide Cafe",
            "tier": "explore",
            "owner_user_id": "guide-reader",
            "read_only": False,
            "hypothetical": False,
            "pilot_label": "Customer draft. Not a completed assessment.",
            "purpose": "startup_feasibility",
            "profile": {"business_name": "Guide Cafe", "purpose": "startup_feasibility", "tier": "explore", "venture_path": "startup"},
            "result": None,
            "human_review_approved": False,
        }
        form = assessment_form(draft)
        self.assertIn('id="journey-progress"', form)
        self.assertIn('class="current" aria-current="step">Intake', form)
        self.assertIn("does not change a flag or a recommendation", form)
        self.assertIn('id="your-next-step"', form)
        self.assertIn("Your next step", form)
        self.assertIn('href="/assessments/guide-1#intake">Continue Intake', form)
        self.assertIn("does not clear a hard gate", form)
        analyzed = {
            **draft,
            "result": {
                "engine_ran": True,
                "recommendation": "do-not-proceed",
                "blocking_flags": ["INSUFFICIENT_DEMAND_EVIDENCE"],
                "readiness_status": "internal",
                "human_review_approved": False,
                "score_line": "Not calculated — methodology pending approval.",
            },
        }
        shown = results_page(analyzed, analyzed["result"])
        self.assertIn('class="current" aria-current="step">Analyze', shown)
        self.assertIn("does not change a flag or a recommendation", shown)
        home = dashboard([analyzed], signed_in=True, viewer_id="guide-reader")
        self.assertIn("Guide Cafe", home)
        self.assertIn("Demand evidence missing.", home)
        self.assertIn(">View Results<", home)
        self.assertIn('class="card assessment-card"', home)
        self.assertIn('class="badge badge-blocked"', home)
        self.assertIn("Gate status:</strong> Blocked", home)
        self.assertIn('class="button primary"', home)
        self.assertIn("Ask about this assessment", home)
        self.assertIn('class="figure-block"', shown)
        self.assertNotIn("Other Cafe", home)
        package = export_advisor_package(analyzed, analyzed["result"], [])
        advisor = advisor_summary_page(package, review_requested=True)
        self.assertIn('class="current" aria-current="step">Review', advisor)
        self.assertEqual(analyzed["result"]["recommendation"], "do-not-proceed")
        self.assertIn("INSUFFICIENT_DEMAND_EVIDENCE", analyzed["result"]["blocking_flags"])
        self.assertIn('id="results-lead"', shown)
        self.assertIn("Key engine figures", shown)
        self.assertIn("In everyday words: a hard gate is still closed", shown)
        self.assertIn("Draft.", advisor)
        self.assertIn('id="advisor-sheet"', advisor)
        self.assertIn('class="advisor-page"', advisor)
        self.assertIn('id="market-provenance"', advisor)
        market = market_page()
        self.assertIn('id="market-provenance"', market)
        self.assertIn("Source, period, and limits", market)
        self.assertIn("do not grant investor-ready status", market)

    def test_baseline_file_is_unchanged(self) -> None:
        before = hashlib.sha256(SAMPLE.read_bytes()).hexdigest()
        directory = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        connection = connect(Path(directory.name) / "analyze.sqlite")
        seed(connection)
        try:
            baseline = get_assessment(connection, BASELINE_ID)
            assert baseline is not None
            result = analyze_record(baseline)
            page = dashboard([baseline], signed_in=True, viewer_id="not-the-owner")
            self.assertNotIn("rugd-intelligence-baseline", page)
            self.assertEqual(result["recommendation"], "do-not-proceed")
            self.assertIn("INSUFFICIENT_DEMAND_EVIDENCE", result["blocking_flags"])
            self.assertEqual(result["readiness_status"], "internal")
            self.assertFalse(result["human_review_approved"])
            self.assertFalse(baseline["human_review_approved"])
            self.assertEqual(hashlib.sha256(SAMPLE.read_bytes()).hexdigest(), before)
        finally:
            connection.close()
            directory.cleanup()

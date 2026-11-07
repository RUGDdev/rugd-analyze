"""Dashboard, intake, and results presentation stay tied to stored drafts and engine output."""

import tempfile
import threading
import unittest
import urllib.parse
import urllib.request
from pathlib import Path

from app.analysis import analyze_record
from app.pages import assessment_form, dashboard, results_page
from app.server import make_server
from app.store import connect, create_assessment, get_assessment, list_assessments, save_profile, seed


class TestPresentation(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.db = Path(self.directory.name) / "analyze.sqlite"
        self.connection = connect(self.db)
        seed(self.connection)

    def tearDown(self) -> None:
        self.connection.close()
        self.directory.cleanup()

    def test_dashboard_distinguishes_baseline_and_offers_actions(self) -> None:
        page = dashboard(list_assessments(self.connection))
        self.assertIn("Official baseline", page)
        self.assertIn("RUGD Intelligence", page)
        self.assertIn("Continue", page)
        self.assertIn("View results", page)
        self.assertIn("Human review status:</strong> pending", page)
        self.assertIn("Investor readiness:</strong> not run", page)
        self.assertNotIn("Investor readiness:</strong> investor-ready", page)
        self.assertNotIn("Record reviewer approval", page)

    def test_results_use_engine_tables_and_leave_monthly_uncalculated(self) -> None:
        assessment_id = create_assessment(
            self.connection,
            business_name="Table Cafe",
            purpose="startup_feasibility",
            tier="analyze",
        )
        current = get_assessment(self.connection, assessment_id)
        assert current is not None
        save_profile(
            self.connection,
            assessment_id,
            {
                **current["profile"],
                "construction_cost": "100000",
                "seats": "40",
                "average_ticket": "25",
                "weekday_occupancy": "0.4",
                "weekend_occupancy": "0.7",
                "operating_days": "6",
                "contribution_margin": "0.6",
                "annual_fixed_costs": "120000",
            },
        )
        stored = get_assessment(self.connection, assessment_id)
        assert stored is not None
        result = analyze_record(stored)
        page = results_page(stored, result)
        self.assertIn("Sources and uses", page)
        self.assertIn("Base and downside", page)
        self.assertIn("DSCR", page)
        self.assertIn("Insufficient verified information to calculate", page)
        self.assertIn(f"/assessments/{assessment_id}/audit/html", page)
        self.assertIn(f"/assessments/{assessment_id}/report", page)
        self.assertIn("INSUFFICIENT_DEMAND_EVIDENCE", page)
        self.assertIn("Investor readiness:</strong> internal", page)
        self.assertNotIn("Investor readiness:</strong> investor-ready", page)
        self.assertIn("Human review is pending", page)

    def test_saved_draft_restores_entered_values(self) -> None:
        server = make_server(self.db, port=0)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        host, port = server.server_address
        base = f"http://{host}:{port}"
        opener = urllib.request.build_opener(urllib.request.HTTPRedirectHandler)
        try:
            created = urllib.request.Request(
                base + "/assessments",
                data=b"business_name=Resume+Cafe&purpose=startup_feasibility&tier=explore",
                method="POST",
            )
            with opener.open(created) as response:
                assessment_url = response.geturl().rstrip("/")
            first = urllib.request.urlopen(assessment_url).read().decode("utf-8")
            self.assertIn("User-supplied assumptions", first)
            self.assertIn("Verified data", first)
            self.assertIn("Unmeasured placeholders", first)
            self.assertIn("Missing required startup fields", first)
            self.assertIn("Insufficient verified information to calculate", first)
            payload = urllib.parse.urlencode(
                {
                    "business_name": "Resume Cafe",
                    "purpose": "startup_feasibility",
                    "tier": "explore",
                    "concept": "Keep this concept.",
                    "seats": "42",
                    "equipment": "",
                    "contingency_pct": "0.15",
                    "demand_evidence": "yes",
                }
            ).encode()
            saved = urllib.request.Request(assessment_url + "/save", data=payload, method="POST")
            with opener.open(saved) as response:
                restored = response.read().decode("utf-8")
            self.assertIn("Keep this concept.", restored)
            self.assertIn('value="42"', restored)
            self.assertIn('value="0.15"', restored)
            self.assertIn('name="equipment" value=""', restored)
            self.assertIn("Missing required startup fields", restored)
            self.assertNotIn('value="42.0"', restored)
            assessment_id = assessment_url.rsplit("/", 1)[-1]
            stored = get_assessment(self.connection, assessment_id)
            assert stored is not None
            self.assertEqual(stored["profile"]["seats"], "42")
            self.assertEqual(stored["profile"]["concept"], "Keep this concept.")
            self.assertEqual(stored["profile"]["equipment"], "")
            self.assertEqual(stored["profile"]["contingency_pct"], "0.15")
            self.assertFalse(stored["profile"]["inputs_are_measured"])
            self.assertFalse(stored["human_review_approved"])
            form = assessment_form(stored)
            self.assertIn('value="42"', form)
            self.assertIn("Keep this concept.", form)
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=3)


if __name__ == "__main__":
    unittest.main()

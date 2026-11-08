"""Dashboard, intake, and results presentation stay tied to stored drafts and engine output."""

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
from app.pages import assessment_form, dashboard, results_page
from app.server import make_server
from app.store import (
    SAMPLE,
    connect,
    create_assessment,
    get_assessment,
    list_assessments,
    save_profile,
    save_result,
    seed,
)


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

    def test_dashboard_next_step_names_demand_without_clearing_it(self) -> None:
        assessment_id = create_assessment(
            self.connection,
            business_name="Step Cafe",
            purpose="startup_feasibility",
            tier="explore",
        )
        current = get_assessment(self.connection, assessment_id)
        assert current is not None
        result = analyze_record(current)
        save_result(self.connection, assessment_id, result.get("intake"), result)
        page = dashboard(list_assessments(self.connection))
        self.assertIn("Next recommended step:", page)
        self.assertIn("Continue Step Cafe", page)
        self.assertIn("INSUFFICIENT_DEMAND_EVIDENCE is present", page)
        self.assertIn("does not clear the flag", page)
        self.assertNotIn("Investor readiness:</strong> investor-ready", page)
        stored = get_assessment(self.connection, assessment_id)
        assert stored is not None
        self.assertIn("INSUFFICIENT_DEMAND_EVIDENCE", stored["result"]["blocking_flags"])
        self.assertFalse(stored["human_review_approved"])

    def test_customer_approval_stays_forbidden_and_baseline_file_is_unchanged(self) -> None:
        before = hashlib.sha256(SAMPLE.read_bytes()).hexdigest()
        server = make_server(self.db, port=0)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        host, port = server.server_address
        base = f"http://{host}:{port}"
        try:
            request = urllib.request.Request(
                base + "/assessments",
                data=b"business_name=Cafe&human_review_approved=true",
                method="POST",
            )
            with self.assertRaises(urllib.error.HTTPError) as caught:
                urllib.request.urlopen(request)
            self.assertEqual(caught.exception.code, 403)
            with urllib.request.urlopen(base + "/") as response:
                page = response.read().decode("utf-8")
            self.assertIn("Official baseline", page)
            self.assertIn("Dashboard", page)
            self.assertIn("Explore", page)
            self.assertIn("Analyze", page)
            self.assertIn("Validate (demonstration)", page)
            self.assertIn("Partner (demonstration)", page)
            self.assertIn("Market Intelligence (demonstration)", page)
            self.assertIn("Reports", page)
            self.assertNotIn("Investor readiness:</strong> investor-ready", page)
            self.assertEqual(hashlib.sha256(SAMPLE.read_bytes()).hexdigest(), before)
            self.assertFalse(get_assessment(self.connection, "rugd-intelligence-baseline")["human_review_approved"])
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=3)

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
            self.assertIn("Guidance. Not a decision.", form)
            self.assertIn("The next missing required item is", form)
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=3)

    def test_explore_guidance_does_not_change_a_saved_flag(self) -> None:
        assessment_id = create_assessment(
            self.connection,
            business_name="Guide Cafe",
            purpose="startup_feasibility",
            tier="explore",
        )
        current = get_assessment(self.connection, assessment_id)
        assert current is not None
        before_profile = dict(current["profile"])
        unanswered = assessment_form(current)
        self.assertIn("Guidance. Not a decision.", unanswered)
        self.assertIn("The next missing required item is demand evidence", unanswered)
        self.assertEqual(get_assessment(self.connection, assessment_id)["profile"], before_profile)
        result = analyze_record(current)
        save_result(self.connection, assessment_id, result.get("intake"), result)
        stored = get_assessment(self.connection, assessment_id)
        assert stored is not None
        flags = list(stored["result"]["blocking_flags"])
        page = assessment_form(stored)
        self.assertIn("INSUFFICIENT_DEMAND_EVIDENCE is present", page)
        self.assertIn("This note does not clear the flag", page)
        self.assertIn("Recommendation:</strong> do-not-proceed", page)
        self.assertIn("Investor readiness:</strong> internal", page)
        self.assertIn("Human review status:</strong> pending", page)
        self.assertIn("Demand evidence provenance:", page)
        again = get_assessment(self.connection, assessment_id)
        assert again is not None
        self.assertEqual(again["result"]["blocking_flags"], flags)
        self.assertEqual(again["result"]["recommendation"], "do-not-proceed")
        self.assertFalse(again["human_review_approved"])

    def test_restaurant_and_baseline_views_share_status(self) -> None:
        before = hashlib.sha256(SAMPLE.read_bytes()).hexdigest()
        server = make_server(self.db, port=0)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        host, port = server.server_address
        base = f"http://{host}:{port}"
        opener = urllib.request.build_opener(urllib.request.HTTPRedirectHandler)
        payload = urllib.parse.urlencode(
            {
                "business_name": "Regression Restaurant",
                "purpose": "startup_feasibility",
                "tier": "explore",
                "concept": "A small restaurant draft.",
                "industry": "Restaurant",
                "construction_cost": "100000",
                "seats": "40",
                "average_ticket": "25",
                "weekday_occupancy": "0.4",
                "weekend_occupancy": "0.7",
                "operating_days": "6",
                "contribution_margin": "0.6",
                "demand_evidence": "",
            }
        ).encode()
        try:
            denied = urllib.request.Request(
                base + "/assessments",
                data=b"business_name=Cafe&human_review_approved=true",
                method="POST",
            )
            with self.assertRaises(urllib.error.HTTPError) as caught:
                urllib.request.urlopen(denied)
            self.assertEqual(caught.exception.code, 403)
            created = urllib.request.Request(
                base + "/assessments",
                data=b"business_name=Regression+Restaurant&purpose=startup_feasibility&tier=explore",
                method="POST",
            )
            with opener.open(created) as response:
                assessment_url = response.geturl().rstrip("/")
            assessment_id = assessment_url.rsplit("/", 1)[-1]
            saved = urllib.request.Request(assessment_url + "/save", data=payload, method="POST")
            with opener.open(saved) as response:
                intake = response.read().decode("utf-8")
            self.assertIn("Guidance. Not a decision.", intake)
            self.assertIn("A small restaurant draft.", intake)
            self.assertIn('value="40"', intake)
            analyzed = urllib.request.Request(assessment_url + "/analyze", data=payload, method="POST")
            with opener.open(analyzed) as response:
                results = response.read().decode("utf-8")
            self._assert_shared_status(results)
            self.assertIn("Limitations", results)
            self.assertIn("Demonstration data is not real market research", results)
            with urllib.request.urlopen(assessment_url + "/report") as response:
                report = response.read().decode("utf-8")
            self.assertIn("**Recommendation:** do-not-proceed", report)
            self.assertIn("**INSUFFICIENT_DEMAND_EVIDENCE:** present", report)
            self.assertIn("**Investor readiness:** internal", report)
            self.assertIn("**Human review status:** pending", report)
            self.assertIn("**Demand evidence provenance:**", report)
            with urllib.request.urlopen(assessment_url + "/audit/html") as response:
                html_audit = response.read().decode("utf-8")
            self._assert_shared_status(html_audit)
            self.assertIn("Limitations", html_audit)
            self.assertIn("Demonstration data is not real market research", html_audit)
            self.assertNotIn("<form", html_audit)
            with urllib.request.urlopen(assessment_url + "/audit") as response:
                audit = json.loads(response.read().decode("utf-8"))
            self.assertEqual(audit["recommendation"]["draft_recommendation"], "do-not-proceed")
            self.assertIn("INSUFFICIENT_DEMAND_EVIDENCE", audit["recommendation"]["blocking_flags"])
            self.assertEqual(audit["investor_readiness"]["status"], "internal")
            self.assertEqual(audit["view_summary"]["human_review_status"], "pending")
            self.assertFalse(audit["human_review_approved"])
            self.assertTrue(audit["view_summary"]["demand_provenance"])
            with urllib.request.urlopen(assessment_url) as response:
                resumed = response.read().decode("utf-8")
            self.assertIn("A small restaurant draft.", resumed)
            self.assertIn('value="40"', resumed)
            stored = get_assessment(self.connection, assessment_id)
            assert stored is not None
            self.assertEqual(stored["profile"]["concept"], "A small restaurant draft.")
            self.assertEqual(stored["profile"]["seats"], "40")
            self.assertEqual(stored["profile"]["industry"], "Restaurant")
            self.assertIn("INSUFFICIENT_DEMAND_EVIDENCE", stored["result"]["blocking_flags"])
            with urllib.request.urlopen(base + "/assessments/rugd-intelligence-baseline/results") as response:
                baseline_results = response.read().decode("utf-8")
            self._assert_shared_status(baseline_results)
            with urllib.request.urlopen(base + "/assessments/rugd-intelligence-baseline/report") as response:
                baseline_report = response.read().decode("utf-8")
            self.assertIn("**Recommendation:** do-not-proceed", baseline_report)
            self.assertIn("**INSUFFICIENT_DEMAND_EVIDENCE:** present", baseline_report)
            self.assertIn("**Investor readiness:** internal", baseline_report)
            with urllib.request.urlopen(base + "/assessments/rugd-intelligence-baseline/audit/html") as response:
                baseline_html = response.read().decode("utf-8")
            self._assert_shared_status(baseline_html)
            with urllib.request.urlopen(base + "/assessments/rugd-intelligence-baseline/audit") as response:
                baseline_audit = json.loads(response.read().decode("utf-8"))
            self.assertEqual(baseline_audit["recommendation"]["draft_recommendation"], "do-not-proceed")
            self.assertIn("INSUFFICIENT_DEMAND_EVIDENCE", baseline_audit["recommendation"]["blocking_flags"])
            self.assertEqual(baseline_audit["investor_readiness"]["status"], "internal")
            self.assertFalse(baseline_audit["human_review_approved"])
            self.assertEqual(baseline_audit["approvals"], [])
            approve = urllib.request.Request(
                base + "/reviewer/assessments/rugd-intelligence-baseline/approve",
                data=b"",
                method="POST",
            )
            with self.assertRaises(urllib.error.HTTPError) as caught:
                urllib.request.urlopen(approve)
            self.assertEqual(caught.exception.code, 403)
            self.assertFalse(get_assessment(self.connection, "rugd-intelligence-baseline")["human_review_approved"])
            self.assertEqual(hashlib.sha256(SAMPLE.read_bytes()).hexdigest(), before)
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=3)

    def _assert_shared_status(self, page: str) -> None:
        self.assertIn("Recommendation:</strong> do-not-proceed", page)
        self.assertIn("INSUFFICIENT_DEMAND_EVIDENCE:</strong> present", page)
        self.assertIn("Investor readiness:</strong> internal", page)
        self.assertIn("Human review status:</strong> pending", page)
        self.assertIn("Demand evidence provenance", page)
        self.assertNotIn("Investor readiness:</strong> investor-ready", page)


if __name__ == "__main__":
    unittest.main()

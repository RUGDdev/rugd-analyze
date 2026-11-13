"""Dashboard, intake, and results presentation stay tied to stored drafts and engine output."""

import copy
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
from app.pages import assessment_form, dashboard, partner_page, results_page, reviewer_page, validate_page
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

    def test_dashboard_lists_only_the_signed_in_account(self) -> None:
        guest = dashboard(list_assessments(self.connection))
        self.assertIn("Welcome to RUGD Intelligence", guest)
        self.assertIn('href="/login"', guest)
        self.assertIn('href="/register"', guest)
        self.assertNotIn("Official baseline", guest)
        self.assertNotIn("Hypothetical Restaurant", guest)
        create_assessment(
            self.connection,
            business_name="Owned Cafe",
            purpose="startup_feasibility",
            tier="explore",
            owner_user_id="owner-1",
        )
        create_assessment(
            self.connection,
            business_name="Other Cafe",
            purpose="startup_feasibility",
            tier="explore",
            owner_user_id="owner-2",
        )
        page = dashboard(list_assessments(self.connection), signed_in=True, viewer_id="owner-1")
        self.assertIn("Your assessments", page)
        self.assertIn("Owned Cafe", page)
        self.assertIn("Continue", page)
        self.assertNotIn("Other Cafe", page)
        self.assertNotIn("Official baseline", page)
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
            owner_user_id="step-owner",
        )
        current = get_assessment(self.connection, assessment_id)
        assert current is not None
        result = analyze_record(current)
        save_result(self.connection, assessment_id, result.get("intake"), result)
        page = dashboard(
            list_assessments(self.connection),
            signed_in=True,
            viewer_id="step-owner",
        )
        self.assertIn("Next recommended step:", page)
        self.assertIn("Next step: show evidence that customers will buy.", page)
        self.assertIn("Important information still needed", page)
        self.assertIn('data-gate="Blocked"', page)
        self.assertIn("Continue Step Cafe", page)
        self.assertIn("add evidence that customers will buy", page)
        self.assertNotIn("INSUFFICIENT_DEMAND_EVIDENCE is present", page)
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
            self.assertIn("Welcome to RUGD Intelligence", page)
            self.assertNotIn("Official baseline", page)
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
        from tests.session_cookie import open_customer

        cookie, _user_id = open_customer(self.connection, base)
        try:
            created = urllib.request.Request(
                base + "/assessments",
                data=b"business_name=Resume+Cafe&purpose=startup_feasibility&tier=explore",
                method="POST",
                headers={"Cookie": cookie},
            )
            with opener.open(created) as response:
                assessment_url = response.geturl().rstrip("/")
            first = urllib.request.urlopen(
                urllib.request.Request(assessment_url, headers={"Cookie": cookie})
            ).read().decode("utf-8")
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
            saved = urllib.request.Request(
                assessment_url + "/save",
                data=payload,
                method="POST",
                headers={"Cookie": cookie},
            )
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
            self.assertIn("The next thing to add is", form)
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
        self.assertIn("The next thing to add is evidence that customers will buy.", unanswered)
        self.assertEqual(get_assessment(self.connection, assessment_id)["profile"], before_profile)
        result = analyze_record(current)
        save_result(self.connection, assessment_id, result.get("intake"), result)
        stored = get_assessment(self.connection, assessment_id)
        assert stored is not None
        flags = list(stored["result"]["blocking_flags"])
        page = assessment_form(stored)
        self.assertIn("The next step is to add evidence that customers will buy", page)
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
            from tests.session_cookie import open_customer

            cookie, _user_id = open_customer(self.connection, base)
            created = urllib.request.Request(
                base + "/assessments",
                data=b"business_name=Regression+Restaurant&purpose=startup_feasibility&tier=explore",
                method="POST",
                headers={"Cookie": cookie},
            )
            with opener.open(created) as response:
                assessment_url = response.geturl().rstrip("/")
            assessment_id = assessment_url.rsplit("/", 1)[-1]
            saved = urllib.request.Request(
                assessment_url + "/save",
                data=payload,
                method="POST",
                headers={"Cookie": cookie},
            )
            with opener.open(saved) as response:
                intake = response.read().decode("utf-8")
            self.assertIn("Guidance. Not a decision.", intake)
            self.assertIn("A small restaurant draft.", intake)
            self.assertIn('value="40"', intake)
            analyzed = urllib.request.Request(
                assessment_url + "/analyze",
                data=payload,
                method="POST",
                headers={"Cookie": cookie},
            )
            with opener.open(analyzed) as response:
                results = response.read().decode("utf-8")
            self._assert_shared_status(results)
            self.assertIn("Limitations", results)
            self.assertIn("Demonstration data is not real market research", results)
            with urllib.request.urlopen(
                urllib.request.Request(assessment_url + "/report", headers={"Cookie": cookie})
            ) as response:
                report = response.read().decode("utf-8")
            self.assertIn("**Recommendation:** do-not-proceed", report)
            self.assertIn("**INSUFFICIENT_DEMAND_EVIDENCE:** present", report)
            self.assertIn("**Investor readiness:** internal", report)
            self.assertIn("**Human review status:** pending", report)
            self.assertIn("**Demand evidence provenance:**", report)
            with urllib.request.urlopen(
                urllib.request.Request(assessment_url + "/audit/html", headers={"Cookie": cookie})
            ) as response:
                html_audit = response.read().decode("utf-8")
            self._assert_shared_status(html_audit)
            self.assertIn("Limitations", html_audit)
            self.assertIn("Demonstration data is not real market research", html_audit)
            self.assertNotIn("<form", html_audit)
            with urllib.request.urlopen(
                urllib.request.Request(assessment_url + "/audit", headers={"Cookie": cookie})
            ) as response:
                audit = json.loads(response.read().decode("utf-8"))
            self.assertEqual(audit["recommendation"]["draft_recommendation"], "do-not-proceed")
            self.assertIn("INSUFFICIENT_DEMAND_EVIDENCE", audit["recommendation"]["blocking_flags"])
            self.assertEqual(audit["investor_readiness"]["status"], "internal")
            self.assertEqual(audit["view_summary"]["human_review_status"], "pending")
            self.assertFalse(audit["human_review_approved"])
            self.assertTrue(audit["view_summary"]["demand_provenance"])
            with urllib.request.urlopen(
                urllib.request.Request(assessment_url, headers={"Cookie": cookie})
            ) as response:
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

    def test_named_pilots_are_empty_drafts_and_are_not_the_baseline(self) -> None:
        before = hashlib.sha256(SAMPLE.read_bytes()).hexdigest()
        root = Path(__file__).resolve().parent.parent
        for relative in (
            "scoring/rules.py",
            "scoring/industry_benchmarks.py",
            "engine/financial.py",
            "engine/startup_projection.py",
            "engine/startup_capital_calculator.py",
            "run_assessment.py",
        ):
            source = (root / relative).read_text(encoding="utf-8")
            self.assertNotIn("Bunny Hive", source)
            self.assertNotIn("Small Town Pub", source)
        server = make_server(self.db, port=0)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        host, port = server.server_address
        base = f"http://{host}:{port}"
        opener = urllib.request.build_opener(urllib.request.HTTPRedirectHandler)
        from tests.session_cookie import open_customer

        cookie, _user_id = open_customer(self.connection, base)
        try:
            with urllib.request.urlopen(base + "/assessments/new") as response:
                new_page = response.read().decode("utf-8")
            self.assertIn("Only the RUGD Intelligence assessment is the official baseline.", new_page)
            self.assertIn("Start Bunny Hive draft", new_page)
            self.assertIn("Start Small Town Pub draft", new_page)
            created_ids = []
            for name in ("Bunny Hive", "Small Town Pub"):
                request = urllib.request.Request(
                    base + "/assessments",
                    data=urllib.parse.urlencode(
                        {
                            "business_name": name,
                            "purpose": "startup_feasibility",
                            "tier": "explore",
                        }
                    ).encode(),
                    method="POST",
                    headers={"Cookie": cookie},
                )
                with opener.open(request) as response:
                    page = response.read().decode("utf-8")
                    created_ids.append(response.geturl().rstrip("/").rsplit("/", 1)[-1])
                self.assertIn("Empty named-pilot draft", page)
                self.assertIn("Empty named-pilot draft.", page)
                self.assertIn("Not a completed assessment", page)
                self.assertIn("Only the RUGD Intelligence assessment is the official baseline.", page)
                self.assertIn('name="concept"', page)
                self.assertIn('name="seats" value=""', page)
                self.assertIn('name="demand_evidence"', page)
            with urllib.request.urlopen(base + "/") as response:
                home = response.read().decode("utf-8")
            self.assertIn("Welcome to RUGD Intelligence", home)
            self.assertNotIn("Empty named-pilot draft", home)
            self.assertNotIn("Official baseline", home)
            for assessment_id in created_ids:
                with urllib.request.urlopen(
                    urllib.request.Request(
                        base + f"/assessments/{assessment_id}",
                        headers={"Cookie": cookie},
                    )
                ) as response:
                    draft_page = response.read().decode("utf-8")
                self.assertIn("Empty named-pilot draft", draft_page)
            baseline = get_assessment(self.connection, "rugd-intelligence-baseline")
            assert baseline is not None
            self.assertTrue(baseline["read_only"])
            self.assertFalse(baseline["human_review_approved"])
            self.assertNotIn(baseline["id"], created_ids)
            for assessment_id, name in zip(created_ids, ("Bunny Hive", "Small Town Pub")):
                stored = get_assessment(self.connection, assessment_id)
                assert stored is not None
                self.assertEqual(stored["business_name"], name)
                self.assertNotEqual(stored["id"], "rugd-intelligence-baseline")
                self.assertFalse(stored["read_only"])
                self.assertFalse(stored["hypothetical"])
                self.assertIsNone(stored["intake"])
                self.assertIsNone(stored["result"])
                self.assertFalse(stored["human_review_approved"])
                self.assertEqual(stored["profile"]["concept"], "")
                self.assertEqual(stored["profile"]["seats"], "")
                self.assertEqual(stored["profile"]["construction_cost"], "")
                self.assertEqual(stored["profile"]["demand_evidence"], "")
                self.assertEqual(stored["profile"]["industry"], "")
                self.assertNotEqual(stored["profile"], baseline["profile"])
                result = analyze_record(stored)
                self.assertEqual(result["recommendation"], "do-not-proceed")
                self.assertIn("INSUFFICIENT_DEMAND_EVIDENCE", result["blocking_flags"])
                self.assertEqual(result["readiness_status"], "internal")
                self.assertFalse(result["human_review_approved"])
                untouched = get_assessment(self.connection, assessment_id)
                assert untouched is not None
                self.assertIsNone(untouched["result"])
            self.assertEqual(hashlib.sha256(SAMPLE.read_bytes()).hexdigest(), before)
            baseline_after = analyze_record(get_assessment(self.connection, "rugd-intelligence-baseline"))
            self.assertEqual(baseline_after["recommendation"], "do-not-proceed")
            self.assertIn("INSUFFICIENT_DEMAND_EVIDENCE", baseline_after["blocking_flags"])
            self.assertFalse(get_assessment(self.connection, "rugd-intelligence-baseline")["human_review_approved"])
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=3)

    def test_tier_research_leaves_flags_and_baseline_unchanged(self) -> None:
        baseline = get_assessment(self.connection, "rugd-intelligence-baseline")
        assert baseline is not None
        result = analyze_record(baseline)
        before = copy.deepcopy(result)
        before_sample = hashlib.sha256(SAMPLE.read_bytes()).hexdigest()
        before_report = hashlib.sha256(
            (Path(__file__).resolve().parent.parent / "reports" / "output" / "rugd-intelligence-draft.md").read_bytes()
        ).hexdigest()
        explore = dict(baseline)
        explore["tier"] = "explore"
        explore_page = results_page(explore, result)
        analyze_page = results_page(baseline, result)
        self.assertIn("<h2>Research depth</h2>", explore_page)
        self.assertNotIn("<h2>Key Assumptions</h2>", explore_page)
        self.assertNotIn("<h2>Risk Summary</h2>", explore_page)
        self.assertNotIn("<h2>Suggested Next Research Steps</h2>", explore_page)
        for heading in (
            "<h2>Evidence Gaps</h2>",
            "<h2>Key Assumptions</h2>",
            "<h2>Risk Summary</h2>",
            "<h2>Suggested Next Research Steps</h2>",
        ):
            self.assertIn(heading, analyze_page)
        self.assertIn("INSUFFICIENT_DEMAND_EVIDENCE", analyze_page)
        self.assertIn("It is not a new score", analyze_page)
        self.assertIn("Synthetic example only", analyze_page)
        self.assertIn("do not clear INSUFFICIENT_DEMAND_EVIDENCE", analyze_page)
        self.assertNotIn("Investor readiness:</strong> investor-ready", analyze_page)
        customer = {
            "id": "draft-cafe",
            "business_name": "Draft Cafe",
            "tier": "validate",
            "read_only": False,
            "review_requested": False,
            "human_review_approved": False,
            "hypothetical": False,
            "profile": {"industry": "Restaurant", "market": "Example county"},
            "result": result,
        }
        validate = validate_page(customer)
        self.assertIn("<h2>Review Package</h2>", validate)
        self.assertIn("Current flags", validate)
        self.assertIn("Market context", validate)
        self.assertIn("Evidence gaps", validate)
        self.assertIn("Reviewer notes placeholder", validate)
        self.assertIn("Request review", validate)
        self.assertIn("INSUFFICIENT_DEMAND_EVIDENCE", validate)
        self.assertIn("This screen cannot approve an assessment.", validate)
        self.assertNotIn("Record reviewer approval", validate)
        session = {
            "active": True,
            "state": "active",
            "reviewer_identity": "reviewer@pilot.example",
            "authentication_method": "local-account",
            "role": "reviewer",
            "remaining_seconds": 60,
        }
        reviewer = reviewer_page(customer, result, session)
        self.assertIn("Record reviewer approval", reviewer)
        self.assertIn("Prototype-grade local session", reviewer)
        self.assertIn("not production authentication", reviewer.lower())
        partner = partner_page()
        self.assertIn("<h2>Ongoing Intelligence</h2>", partner)
        self.assertIn("Hypothetical trend alert.", partner)
        self.assertIn("Hypothetical management action:", partner)
        self.assertIn("Monitoring active: false", partner)
        self.assertIn("Recurring monitoring is not active", partner)
        self.assertNotIn("Monitoring active: true", partner)
        self.assertNotIn("Record reviewer approval", partner)
        results_page(baseline, result)
        validate_page(customer)
        partner_page()
        self.assertEqual(result, before)
        self.assertEqual(result["recommendation"], "do-not-proceed")
        self.assertIn("INSUFFICIENT_DEMAND_EVIDENCE", result["blocking_flags"])
        self.assertEqual(result["readiness_status"], "internal")
        self.assertFalse(result["human_review_approved"])
        self.assertEqual(hashlib.sha256(SAMPLE.read_bytes()).hexdigest(), before_sample)
        self.assertEqual(
            hashlib.sha256(
                (Path(__file__).resolve().parent.parent / "reports" / "output" / "rugd-intelligence-draft.md").read_bytes()
            ).hexdigest(),
            before_report,
        )

    def _assert_shared_status(self, page: str) -> None:
        self.assertIn("Recommendation:</strong> do-not-proceed", page)
        self.assertIn("INSUFFICIENT_DEMAND_EVIDENCE:</strong> present", page)
        self.assertIn("Investor readiness:</strong> internal", page)
        self.assertIn("Human review status:</strong> pending", page)
        self.assertIn("Demand evidence provenance", page)
        self.assertNotIn("Investor readiness:</strong> investor-ready", page)


if __name__ == "__main__":
    unittest.main()

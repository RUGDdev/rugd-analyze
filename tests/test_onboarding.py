"""Startup ideas keep the Explore intake. Existing businesses use a shorter path."""

import hashlib
import tempfile
import threading
import unittest
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from app.analysis import analyze_record
from app.server import make_server
from app.store import BASELINE_ID, SAMPLE, connect, get_assessment, seed

ROOT = Path(__file__).resolve().parent.parent
DRAFT_REPORT = ROOT / "reports" / "output" / "rugd-intelligence-draft.md"


class TestOnboardingPaths(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.db = Path(self.directory.name) / "analyze.sqlite"
        self.connection = connect(self.db)
        seed(self.connection)
        self.server = make_server(self.db, port=0)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        host, port = self.server.server_address
        self.base = f"http://{host}:{port}"
        self.opener = urllib.request.build_opener(urllib.request.HTTPRedirectHandler)
        from tests.session_cookie import open_customer

        self.cookie, _user_id = open_customer(self.connection, self.base)

    def tearDown(self) -> None:
        self.server.shutdown()
        self.thread.join(timeout=5)
        self.connection.close()
        self.directory.cleanup()

    def _post(self, path: str, fields: dict[str, str]) -> tuple[str, str]:
        request = urllib.request.Request(
            self.base + path,
            data=urllib.parse.urlencode(fields).encode("utf-8"),
            method="POST",
            headers={"Cookie": self.cookie},
        )
        with self.opener.open(request) as response:
            return response.read().decode("utf-8"), response.geturl()

    def test_new_page_asks_and_both_paths_keep_the_baseline(self) -> None:
        sample_before = hashlib.sha256(SAMPLE.read_bytes()).hexdigest()
        report_before = hashlib.sha256(DRAFT_REPORT.read_bytes()).hexdigest()
        with urllib.request.urlopen(self.base + "/assessments/new") as response:
            page = response.read().decode("utf-8")
        self.assertIn("Is this a startup idea or an existing or expanding business?", page)
        self.assertIn("A startup idea", page)
        self.assertIn("An existing or expanding business", page)
        self.assertIn("Local prototype. Not production security.", page)

        startup, startup_url = self._post(
            "/assessments",
            {
                "venture_path": "startup",
                "business_name": "Idea Cafe",
                "purpose": "startup_feasibility",
                "tier": "explore",
            },
        )
        self.assertIn("Startup capital", startup)
        self.assertIn('name="construction_cost"', startup)
        self.assertIn('name="seats"', startup)
        self.assertIn('name="initial_capital"', startup)
        self.assertIn("Onboarding path:</strong> Startup idea", startup)
        startup_id = startup_url.rstrip("/").split("/")[-1]
        startup_record = get_assessment(self.connection, startup_id)
        assert startup_record is not None
        self.assertEqual(startup_record["tier"], "explore")
        self.assertEqual(startup_record["profile"]["venture_path"], "startup")
        self.assertEqual(startup_record["business_profile"]["venture_path"], "startup")

        existing, existing_url = self._post(
            "/assessments",
            {
                "venture_path": "existing",
                "business_name": "Main Street Shop",
                "purpose": "expansion_feasibility",
                "tier": "explore",
            },
        )
        self.assertNotIn('name="construction_cost"', existing)
        self.assertNotIn('name="seats"', existing)
        self.assertNotIn("<summary>Startup capital</summary>", existing)
        self.assertIn('name="initial_capital"', existing)
        self.assertIn('name="monthly_fixed_costs"', existing)
        self.assertIn('name="gross_margin_pct"', existing)
        self.assertIn('name="projected_monthly_revenue_base"', existing)
        self.assertIn('name="demand_evidence"', existing)
        self.assertIn('name="operator_capacity_adequate"', existing)
        self.assertIn('name="unresolved_regulatory_or_liability"', existing)
        self.assertIn('name="extraction_without_reinvestment"', existing)
        self.assertIn("Onboarding path:</strong> Existing or expanding business", existing)
        self.assertNotIn("The next missing required item is Construction cost", existing)
        existing_id = existing_url.rstrip("/").split("/")[-1]
        existing_record = get_assessment(self.connection, existing_id)
        assert existing_record is not None
        self.assertEqual(existing_record["profile"]["venture_path"], "existing")
        self.assertEqual(existing_record["profile"]["construction_cost"], "")
        self.assertEqual(existing_record["profile"]["seats"], "")
        self.assertEqual(existing_record["business_profile"]["venture_path"], "existing")

        omitted, _omitted_url = self._post(
            "/assessments",
            {
                "business_name": "Bunny Hive",
                "purpose": "startup_feasibility",
                "tier": "explore",
            },
        )
        self.assertIn("Startup capital", omitted)
        self.assertIn('name="construction_cost"', omitted)

        reused, _reused_url = self._post(
            "/assessments",
            {
                "venture_path": "startup",
                "business_name": "Ignored name",
                "business_profile_id": existing_record["business_profile_id"],
                "purpose": "startup_feasibility",
                "tier": "analyze",
            },
        )
        self.assertNotIn('name="construction_cost"', reused)
        self.assertIn("Onboarding path:</strong> Existing or expanding business", reused)

        saved, _saved_url = self._post(
            f"/assessments/{existing_id}/save",
            {
                "business_name": "Main Street Shop",
                "purpose": "expansion_feasibility",
                "tier": "explore",
                "venture_path": "startup",
                "initial_capital": "50000",
                "monthly_fixed_costs": "4000",
                "gross_margin_pct": "0.6",
                "projected_monthly_revenue_base": "8000",
            },
        )
        self.assertNotIn('name="construction_cost"', saved)
        self.assertIn("Monthly fields are filled.", saved)
        self.assertNotIn("The next missing required item is Construction cost", saved)
        with urllib.request.urlopen(self.base + "/") as response:
            dashboard = response.read().decode("utf-8")
        self.assertIn("Welcome to RUGD Intelligence", dashboard)
        self.assertNotIn("Main Street Shop", dashboard)
        stored = get_assessment(self.connection, existing_id)
        assert stored is not None
        self.assertEqual(stored["profile"]["venture_path"], "existing")
        self.assertEqual(stored["profile"]["construction_cost"], "")
        self.assertEqual(stored["profile"]["initial_capital"], "50000")
        self.assertFalse(stored["human_review_approved"])

        analyzed, _analyzed_url = self._post(
            f"/assessments/{existing_id}/analyze",
            {
                "business_name": "Main Street Shop",
                "purpose": "expansion_feasibility",
                "tier": "explore",
                "initial_capital": "50000",
                "monthly_fixed_costs": "4000",
                "gross_margin_pct": "0.6",
                "projected_monthly_revenue_base": "8000",
            },
        )
        self.assertIn("do-not-proceed", analyzed)
        self.assertIn("INSUFFICIENT_DEMAND_EVIDENCE", analyzed)
        self.assertIn("human_review_approved", analyzed)
        after = get_assessment(self.connection, existing_id)
        assert after is not None
        self.assertEqual(after["profile"]["construction_cost"], "")
        self.assertEqual(after["profile"]["venture_path"], "existing")
        self.assertFalse(after["human_review_approved"])
        self.assertTrue(after["result"]["engine_ran"])
        self.assertTrue(
            any("startup cost build" in item for item in after["result"]["missing"])
        )

        record = get_assessment(self.connection, BASELINE_ID)
        assert record is not None
        result = analyze_record(record)
        self.assertEqual(result["recommendation"], "do-not-proceed")
        self.assertIn("INSUFFICIENT_DEMAND_EVIDENCE", result["blocking_flags"])
        self.assertEqual(result["readiness_status"], "internal")
        self.assertFalse(result["human_review_approved"])
        self.assertEqual(record["business_profile"]["venture_path"], "startup")
        self.assertEqual(hashlib.sha256(SAMPLE.read_bytes()).hexdigest(), sample_before)
        self.assertEqual(hashlib.sha256(DRAFT_REPORT.read_bytes()).hexdigest(), report_before)

    def test_unknown_path_and_approval_field_are_refused(self) -> None:
        request = urllib.request.Request(
            self.base + "/assessments",
            data=b"venture_path=reviewer&business_name=Bad+Path&purpose=startup_feasibility&tier=explore",
            method="POST",
            headers={"Cookie": self.cookie},
        )
        with self.assertRaises(urllib.error.HTTPError) as refused:
            urllib.request.urlopen(request)
        self.assertEqual(refused.exception.code, 403)
        body = refused.exception.read().decode("utf-8")
        self.assertIn("Choose a startup idea or an existing or expanding business.", body)
        approval = urllib.request.Request(
            self.base + "/assessments",
            data=b"venture_path=existing&business_name=Shop&human_review_approved=true",
            method="POST",
        )
        with self.assertRaises(urllib.error.HTTPError) as blocked:
            urllib.request.urlopen(approval)
        self.assertEqual(blocked.exception.code, 403)

"""The Advisor Summary reads stored results and does not change them."""

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

from app.accounts import register_account
from app.export import export_advisor_package
from app.review import open_account_session
from app.server import make_server
from app.share import issue_share_link
from app.store import (
    BASELINE_ID,
    SAMPLE,
    connect,
    create_assessment,
    get_assessment,
    save_guidance_note,
    save_profile,
    save_result,
    seed,
)

ROOT = Path(__file__).resolve().parent.parent
DRAFT_REPORT = ROOT / "reports" / "output" / "rugd-intelligence-draft.md"
EMAIL = "advisor-owner@pilot.example"
PASSWORD = "advisor-pass-1"


class TestAdvisorPackage(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.db = Path(self.directory.name) / "analyze.sqlite"
        self.connection = connect(self.db)
        seed(self.connection)
        self.owner = register_account(self.connection, email=EMAIL, password=PASSWORD)
        self.assessment_id = create_assessment(
            self.connection,
            business_name="Advisor Cafe",
            purpose="startup_feasibility",
            tier="analyze",
            owner_user_id=self.owner["id"],
        )
        save_profile(
            self.connection,
            self.assessment_id,
            {
                "business_name": "Advisor Cafe",
                "purpose": "startup_feasibility",
                "tier": "analyze",
                "industry": "Restaurant",
                "market": "Example county",
                "stage": "Idea",
            },
        )
        save_result(self.connection, self.assessment_id, None, _engine_result())
        save_guidance_note(
            self.connection,
            self.assessment_id,
            "stewardship",
            "Reinvestment stays a question.",
        )

    def tearDown(self) -> None:
        self.connection.close()
        self.directory.cleanup()

    def test_package_matches_the_stored_result_and_does_not_change_it(self) -> None:
        sample_before = hashlib.sha256(SAMPLE.read_bytes()).hexdigest()
        report_before = hashlib.sha256(DRAFT_REPORT.read_bytes()).hexdigest()
        record = get_assessment(self.connection, self.assessment_id)
        assert record is not None
        before_record = copy.deepcopy(record)
        before_result = copy.deepcopy(record["result"])
        notes = [
            {
                "pillar_id": "stewardship",
                "pillar_title": "Stewardship Indicators (reinvestment capacity, resilience, continuity potential)",
                "note": "Reinvestment stays a question.",
                "created_at": "2026-11-09T00:00:00+00:00",
                "authoritative": False,
            }
        ]
        notes_before = copy.deepcopy(notes)
        package = export_advisor_package(record, record["result"], notes)
        self.assertEqual(record, before_record)
        self.assertEqual(record["result"], before_result)
        self.assertEqual(notes, notes_before)
        self.assertEqual(package["kind"], "rugd-advisor-package")
        self.assertEqual(package["assessment"]["recommendation"], "do-not-proceed")
        self.assertEqual(package["assessment"]["readiness_status"], "internal")
        self.assertFalse(package["assessment"]["human_review_approved"])
        self.assertIsNone(package["assessment"]["feasibility_score"])
        self.assertEqual(
            package["assessment"]["score_line"],
            "Not calculated — methodology pending approval.",
        )
        indicative = package["indicative"]
        self.assertEqual(indicative["gate_status"], "Blocked")
        self.assertEqual(indicative["band"], "Blocked")
        self.assertEqual(indicative["gate_recommendation"], "do-not-proceed")
        self.assertFalse(indicative["overrides_flags"])
        self.assertFalse(indicative["sets_human_review_approved"])
        self.assertFalse(indicative["changes_recommendation"])
        self.assertEqual(indicative["components"]["market_validity"]["name"], "Market Validity")
        self.assertEqual(indicative["components"]["financial_viability"]["name"], "Financial Viability")
        self.assertEqual(
            indicative["components"]["stewardship_readiness"]["name"],
            "Stewardship Readiness",
        )
        self.assertEqual(package["key_flags"], ["INSUFFICIENT_DEMAND_EVIDENCE"])
        self.assertEqual(package["market_snapshot"]["industry"], "Restaurant")
        self.assertEqual(package["market_snapshot"]["geography"], "Example county")
        self.assertFalse(package["market_snapshot"]["live_feed"])
        self.assertFalse(package["market_snapshot"]["monitoring_active"])
        self.assertEqual(package["market_snapshot"]["provenance"]["source"], "none")
        self.assertIn("do not set human_review_approved", package["market_snapshot"]["provenance"]["limitations"])
        self.assertEqual(package["durable_value"]["notes"][0]["note"], "Reinvestment stays a question.")
        self.assertFalse(package["durable_value"]["authoritative"])
        self.assertIn("Educational guidance — not a DVT evaluation.", package["durable_value"]["label"])

        forced = export_advisor_package(
            {
                "id": "draft",
                "business_name": "Forced Gate",
                "tier": "analyze",
                "read_only": False,
                "human_review_approved": False,
                "profile": {"industry": "Retail", "market": "Example county", "stage": "Operating"},
            },
            {
                "engine_ran": True,
                "recommendation": "go",
                "blocking_flags": ["EXTRACTION_WITHOUT_REINVESTMENT"],
                "gap_flags": [],
                "human_review_approved": True,
                "human_review_status": "pending",
                "readiness_status": "internal",
                "demand": {"status": "cleared"},
                "score_line": "Not calculated — methodology pending approval.",
            },
        )
        self.assertEqual(forced["assessment"]["recommendation"], "go")
        self.assertFalse(forced["assessment"]["human_review_approved"])
        self.assertEqual(forced["indicative"]["gate_status"], "Blocked")
        self.assertEqual(forced["indicative"]["band"], "Blocked")
        self.assertEqual(forced["indicative"]["gate_recommendation"], "do-not-proceed")
        self.assertFalse(forced["indicative"]["changes_recommendation"])

        baseline = get_assessment(self.connection, BASELINE_ID)
        assert baseline is not None
        baseline_before = copy.deepcopy(baseline)
        official = export_advisor_package(baseline, baseline.get("result"), [])
        self.assertEqual(baseline, baseline_before)
        self.assertEqual(official["assessment"]["recommendation"], "do-not-proceed")
        self.assertIn("INSUFFICIENT_DEMAND_EVIDENCE", official["key_flags"])
        self.assertEqual(official["assessment"]["readiness_status"], "internal")
        self.assertFalse(official["assessment"]["human_review_approved"])
        self.assertFalse(get_assessment(self.connection, BASELINE_ID)["human_review_approved"])
        self.assertEqual(hashlib.sha256(SAMPLE.read_bytes()).hexdigest(), sample_before)
        self.assertEqual(hashlib.sha256(DRAFT_REPORT.read_bytes()).hexdigest(), report_before)

    def test_share_link_opens_the_summary_without_changing_the_assessment(self) -> None:
        sample_before = hashlib.sha256(SAMPLE.read_bytes()).hexdigest()
        stored = json.dumps(get_assessment(self.connection, self.assessment_id)["result"], sort_keys=True)
        session = open_account_session(self.connection, email=EMAIL, password=PASSWORD)
        record = get_assessment(self.connection, self.assessment_id)
        assert record is not None
        issued = issue_share_link(self.connection, record, session, "7d")
        server = make_server(self.db, port=0)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        host, port = server.server_address
        base = f"http://{host}:{port}"
        try:
            summary = _get(base + f"/assessments/{self.assessment_id}/advisor")
            self.assertIn("Advisor Summary", summary)
            self.assertIn("Gate status:</strong> Blocked", summary)
            self.assertIn("Band:</strong> Blocked", summary)
            self.assertIn("Market Validity:", summary)
            self.assertIn("Financial Viability:", summary)
            self.assertIn("Stewardship Readiness:", summary)
            self.assertIn("INSUFFICIENT_DEMAND_EVIDENCE", summary)
            self.assertIn("Reinvestment stays a question.", summary)
            self.assertIn("Live feed connected: false", summary)
            self.assertIn("human_review_approved:</strong> false", summary)
            self.assertIn('class="sidebar"', summary)
            self.assertNotIn("<form", summary.lower())
            downloaded = _get(base + f"/assessments/{self.assessment_id}/advisor/download")
            package = json.loads(downloaded)
            self.assertEqual(package["key_flags"], ["INSUFFICIENT_DEMAND_EVIDENCE"])
            self.assertNotIn(issued["token"], downloaded)
            printed = _get(base + f"/assessments/{self.assessment_id}/advisor/print")
            self.assertIn("print-view", printed)
            self.assertIn("Provenance", printed)
            shared = _get(base + issued["path"])
            self.assertIn("Open Advisor Summary", shared)
            self.assertNotIn("<form", shared.lower())
            shared_summary = _get(base + issued["path"] + "/advisor")
            self.assertIn("Read-only share.", shared_summary)
            self.assertIn("Gate status:</strong> Blocked", shared_summary)
            self.assertNotIn("<form", shared_summary.lower())
            shared_download = json.loads(_get(base + issued["path"] + "/advisor/download"))
            self.assertEqual(shared_download["assessment"]["recommendation"], "do-not-proceed")
            self.assertNotIn(issued["token"], json.dumps(shared_download))
            request = urllib.request.Request(
                base + issued["path"] + "/advisor",
                data=b"human_review_approved=true&role=reviewer",
                method="POST",
            )
            with self.assertRaises(urllib.error.HTTPError) as blocked:
                urllib.request.urlopen(request)
            self.assertEqual(blocked.exception.code, 403)
            current = get_assessment(self.connection, self.assessment_id)
            assert current is not None
            self.assertEqual(json.dumps(current["result"], sort_keys=True), stored)
            self.assertEqual(current["business_name"], "Advisor Cafe")
            self.assertFalse(current["human_review_approved"])
            self.assertEqual(current["result"]["recommendation"], "do-not-proceed")
            baseline = get_assessment(self.connection, BASELINE_ID)
            assert baseline is not None
            self.assertFalse(baseline["human_review_approved"])
            self.assertEqual(hashlib.sha256(SAMPLE.read_bytes()).hexdigest(), sample_before)
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)


def _engine_result() -> dict:
    return {
        "engine_ran": True,
        "model_version": "0.1-pilot",
        "recommendation": "do-not-proceed",
        "blocking_flags": ["INSUFFICIENT_DEMAND_EVIDENCE"],
        "gap_flags": [],
        "missing": [],
        "human_review_approved": False,
        "human_review_status": "pending",
        "readiness_status": "internal",
        "is_final": False,
        "score_line": "Not calculated — methodology pending approval.",
        "financial": None,
        "projection": {"calculated": False, "views": None},
        "demand": {"status": "uncleared"},
    }


def _get(url: str) -> str:
    with urllib.request.urlopen(url) as response:
        return response.read().decode("utf-8")

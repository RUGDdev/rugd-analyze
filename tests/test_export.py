"""Empty states stay honest, and JSON export omits session secrets."""

import copy
import hashlib
import json
import os
import tempfile
import threading
import unittest
import urllib.request
from pathlib import Path

from app.analysis import analyze_record
from app.export import export_research_package, research_package_markdown
from app.pages import dashboard, research_brief_page, results_page
from app.accounts import bootstrap_reviewer
from app.review import open_account_session
from app.server import make_server
from app.store import (
    BASELINE_ID,
    RESTAURANT_ID,
    SAMPLE,
    connect,
    create_assessment,
    get_assessment,
    save_profile,
    seed,
    start_reviewer_session,
)
ROOT = Path(__file__).resolve().parent.parent
OUTPUT = ROOT / "reports" / "output"


class TestEmptyStatesAndExport(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.db = Path(self.directory.name) / "analyze.sqlite"
        self.connection = connect(self.db)
        seed(self.connection)

    def tearDown(self) -> None:
        self.connection.close()
        self.directory.cleanup()

    def test_empty_states_do_not_invent_values(self) -> None:
        self.assertIn("No drafts yet", dashboard([]))
        self.assertIn("Blank fields stay blank", dashboard([]))
        baseline = get_assessment(self.connection, BASELINE_ID)
        assert baseline is not None
        only_baseline = dashboard([baseline])
        self.assertIn("No customer drafts are saved", only_baseline)
        self.assertIn("Official baseline", only_baseline)
        self.assertIn("does not copy baseline figures", only_baseline)
        draft_id = create_assessment(
            self.connection,
            business_name="Empty Cafe",
            purpose="startup_feasibility",
            tier="explore",
        )
        draft = get_assessment(self.connection, draft_id)
        assert draft is not None
        page = results_page(draft, {"engine_ran": False, "message": "Analyze has not been run."})
        self.assertIn("Analyze has not been run", page)
        self.assertIn("did not fill any blank fields", page)
        self.assertIn("Insufficient verified information to calculate", page)
        self.assertIn("Missing required startup fields", page)
        self.assertNotIn('value="48"', page)
        self.assertIn("Recommendation:</strong> do-not-proceed", results_page(baseline, {"engine_ran": False}))
        self.assertIn("did not run Analyze", results_page(baseline, {"engine_ran": False}))

    def test_export_includes_intake_and_omits_secrets(self) -> None:
        before = hashlib.sha256(SAMPLE.read_bytes()).hexdigest()
        output_before = sorted(path.name for path in OUTPUT.iterdir())
        draft_id = create_assessment(
            self.connection,
            business_name="Export Cafe",
            purpose="startup_feasibility",
            tier="explore",
        )
        current = get_assessment(self.connection, draft_id)
        assert current is not None
        secret = "session-token-should-not-export"
        save_profile(
            self.connection,
            draft_id,
            {
                **current["profile"],
                "concept": "Keep this concept.",
                "token": secret,
                "reviewer_passphrase": "local-prototype-reviewer",
            },
        )
        bootstrap_reviewer(
            self.connection,
            email="reviewer@pilot.example",
            password="reviewer-pass-1",
        )
        session = open_account_session(
            self.connection,
            email="reviewer@pilot.example",
            password="reviewer-pass-1",
        )
        start_reviewer_session(
            self.connection,
            token="second-raw-token",
            reviewer_identity="reviewer@pilot.example",
            authentication_method="local-account",
            expires_at="2027-01-01T00:00:00+00:00",
        )
        stamp = get_assessment(self.connection, draft_id)["updated_at"]
        server = make_server(self.db, port=0)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        host, port = server.server_address
        base = f"http://{host}:{port}"
        try:
            with urllib.request.urlopen(base + f"/assessments/{draft_id}/results") as response:
                empty = response.read().decode("utf-8")
            self.assertIn("Analyze has not been run", empty)
            self.assertEqual(get_assessment(self.connection, draft_id)["result"], None)
            self.assertEqual(get_assessment(self.connection, draft_id)["updated_at"], stamp)
            with urllib.request.urlopen(base + f"/assessments/{draft_id}/export") as response:
                one = json.loads(response.read().decode("utf-8"))
                self.assertEqual(response.headers.get_content_type(), "application/json")
                disposition = response.headers.get("Content-Disposition", "")
            self.assertIn("attachment;", disposition)
            self.assertIn("Export-Cafe-", disposition)
            self.assertRegex(disposition, r"\d{4}-\d{2}-\d{2}-export\.json")
            assessment = one["assessment"]
            self.assertEqual(assessment["profile"]["concept"], "Keep this concept.")
            self.assertNotIn("token", assessment["profile"])
            self.assertNotIn("reviewer_passphrase", assessment["profile"])
            self.assertIsNone(assessment["result"])
            self.assertFalse(assessment["human_review_approved"])
            encoded = json.dumps(one)
            self.assertNotIn(secret, encoded)
            self.assertNotIn(session["token"], encoded)
            self.assertNotIn("second-raw-token", encoded)
            self.assertNotIn("local-prototype-reviewer", encoded)
            with urllib.request.urlopen(base + "/assessments/export") as response:
                bundle = json.loads(response.read().decode("utf-8"))
                self.assertEqual(response.headers.get_content_type(), "application/json")
                self.assertIn("rugd-drafts-", response.headers.get("Content-Disposition", ""))
            self.assertFalse(bundle["official_baseline_included"])
            ids = {item["id"] for item in bundle["drafts"]}
            self.assertIn(draft_id, ids)
            self.assertIn(RESTAURANT_ID, ids)
            self.assertNotIn(BASELINE_ID, ids)
            bundle_text = json.dumps(bundle)
            self.assertNotIn(secret, bundle_text)
            self.assertNotIn(session["token"], bundle_text)
            self.assertNotIn("second-raw-token", bundle_text)
            self.assertFalse(get_assessment(self.connection, BASELINE_ID)["human_review_approved"])
            self.assertEqual(hashlib.sha256(SAMPLE.read_bytes()).hexdigest(), before)
            self.assertEqual(sorted(path.name for path in OUTPUT.iterdir()), output_before)
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=3)

    def test_research_package_is_complete_and_leaves_the_baseline_unchanged(self) -> None:
        baseline = get_assessment(self.connection, BASELINE_ID)
        assert baseline is not None
        result = analyze_record(baseline)
        before = copy.deepcopy(result)
        before_sample = hashlib.sha256(SAMPLE.read_bytes()).hexdigest()
        before_report = hashlib.sha256((OUTPUT / "rugd-intelligence-draft.md").read_bytes()).hexdigest()
        dirty = copy.deepcopy(result)
        dirty["session_id"] = "raw-session-token"
        dirty["reviewer_passphrase"] = "local-prototype-reviewer"
        record = copy.deepcopy(baseline)
        record["profile"]["token"] = "raw-session-token"
        market = {
            "status": "synthetic",
            "label": "Demonstration. Not market research and not active monitoring.",
            "observations": [],
            "synthetic_observations": [
                {
                    "source": "Synthetic snapshot",
                    "geographic_coverage": "Example county",
                    "industry_classification": "Restaurant",
                    "measurement_period": "not a measurement period",
                    "retrieval_date": "not retrieved",
                    "limitations": "Synthetic example only. These figures do not clear INSUFFICIENT_DEMAND_EVIDENCE.",
                    "measure": "Synthetic example",
                    "value": "Synthetic example only: a cost-pressure note",
                    "session_id": "raw-session-token",
                    "reviewer_passphrase": "local-prototype-reviewer",
                }
            ],
        }
        package = export_research_package(
            record,
            dirty,
            market=market,
            analyst_lines=["Demonstration Analyst. No external AI service is connected."],
        )
        encoded = json.dumps(package)
        self.assertEqual(package["kind"], "rugd-research-package")
        self.assertEqual(package["assessment_summary"]["business_name"], "RUGD Intelligence")
        self.assertEqual(package["assessment_summary"]["recommendation"], "do-not-proceed")
        self.assertFalse(package["assessment_summary"]["human_review_approved"])
        self.assertIn("INSUFFICIENT_DEMAND_EVIDENCE", package["flags"]["blocking_flags"])
        self.assertIn("INSUFFICIENT_DEMAND_EVIDENCE", package["evidence_gaps"][0])
        self.assertIn("Local prototype", package["prototype_disclaimer"])
        self.assertIn(package["tier"], package["tier_disclaimer"] and package["tier"])
        self.assertTrue(package["tier_disclaimer"])
        observation = package["market"]["synthetic_observations"][0]
        for field in (
            "source",
            "geographic_coverage",
            "industry_classification",
            "measurement_period",
            "retrieval_date",
            "limitations",
            "measure",
            "value",
        ):
            self.assertTrue(observation[field], field)
        self.assertNotIn("session_id", observation)
        self.assertEqual(package["analyst_explanation"][0], "Demonstration Analyst. No external AI service is connected.")
        self.assertNotIn("raw-session-token", encoded)
        self.assertNotIn("local-prototype-reviewer", encoded)
        markdown = research_package_markdown(package)
        self.assertIn("INSUFFICIENT_DEMAND_EVIDENCE", markdown)
        self.assertIn("Source: Synthetic snapshot", markdown)
        self.assertIn("Limitations:", markdown)
        self.assertNotIn("raw-session-token", markdown)
        brief = research_brief_page(package)
        self.assertIn("<h1>Research Brief</h1>", brief)
        self.assertIn("Source:", brief)
        self.assertIn("<h2>Limitations</h2>", brief)
        self.assertIn("Print-friendly research brief", brief)
        self.assertNotIn("raw-session-token", brief)
        self.assertNotIn("local-prototype-reviewer", brief)
        shown = results_page(baseline, result)
        self.assertIn("Download Research Package", shown)
        self.assertEqual(result, before)
        self.assertEqual(result["recommendation"], "do-not-proceed")
        self.assertIn("INSUFFICIENT_DEMAND_EVIDENCE", result["blocking_flags"])
        self.assertEqual(result["readiness_status"], "internal")
        self.assertFalse(result["human_review_approved"])
        self.assertEqual(hashlib.sha256(SAMPLE.read_bytes()).hexdigest(), before_sample)
        self.assertEqual(hashlib.sha256((OUTPUT / "rugd-intelligence-draft.md").read_bytes()).hexdigest(), before_report)

        server = make_server(self.db, port=0)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        host, port = server.server_address
        base = f"http://{host}:{port}"
        keys = (
            "MARKET_PROVIDER",
            "MARKET_CENSUS",
            "MARKET_CBP",
            "ANALYST_PROVIDER",
            "ANALYST_MODEL",
            "ANTHROPIC_API_KEY",
            "OPENAI_API_KEY",
            "XAI_API_KEY",
        )
        saved = {key: os.environ.pop(key, None) for key in keys}
        try:
            with urllib.request.urlopen(base + f"/assessments/{BASELINE_ID}/research") as response:
                body = json.loads(response.read().decode("utf-8"))
                disposition = response.headers.get("Content-Disposition") or ""
                self.assertEqual(response.headers.get_content_type(), "application/json")
            self.assertIn("attachment;", disposition)
            self.assertIn("-research.json", disposition)
            self.assertEqual(body["kind"], "rugd-research-package")
            self.assertEqual(body["assessment_summary"]["business_name"], "RUGD Intelligence")
            self.assertNotIn("raw-session-token", json.dumps(body))
            with urllib.request.urlopen(base + f"/assessments/{BASELINE_ID}/research/brief") as response:
                page = response.read().decode("utf-8")
            self.assertIn("<h1>Research Brief</h1>", page)
            self.assertIn("Limitations", page)
            self.assertIn("local prototype", page)
            self.assertNotIn("Investor readiness:</strong> investor-ready", page)
        finally:
            for key, value in saved.items():
                if value is not None:
                    os.environ[key] = value
            server.shutdown()
            server.server_close()
            thread.join(timeout=3)

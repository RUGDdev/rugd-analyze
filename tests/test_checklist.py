"""The evidence checklist updates guidance and does not clear a hard gate."""

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
from app.checklist import DISCLAIMER, apply_posted, build_checklist, posted_checks
from app.pages import assessment_form, explore_page, results_page
from app.server import make_server
from app.store import (
    BASELINE_ID,
    SAMPLE,
    connect,
    create_assessment,
    get_assessment,
    list_guidance_notes,
    save_checklist,
    save_guidance_note,
    save_profile,
    save_result,
    seed,
)

ROOT = Path(__file__).resolve().parent.parent
DRAFT_REPORT = ROOT / "reports" / "output" / "rugd-intelligence-draft.md"


class TestEvidenceChecklist(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.db = Path(self.directory.name) / "analyze.sqlite"
        self.connection = connect(self.db)
        seed(self.connection)
        self.assessment_id = create_assessment(
            self.connection,
            business_name="Checklist Cafe",
            purpose="startup_feasibility",
            tier="explore",
        )

    def tearDown(self) -> None:
        self.connection.close()
        self.directory.cleanup()

    def test_items_follow_the_draft_and_checks_do_not_clear_flags(self) -> None:
        sample_before = hashlib.sha256(SAMPLE.read_bytes()).hexdigest()
        report_before = hashlib.sha256(DRAFT_REPORT.read_bytes()).hexdigest()
        record = get_assessment(self.connection, self.assessment_id)
        assert record is not None
        before = json.dumps(record, sort_keys=True)
        view = build_checklist(record, record.get("result"), [])
        self.assertEqual(json.dumps(record, sort_keys=True), before)
        self.assertEqual(view["disclaimer"], DISCLAIMER)
        self.assertFalse(view["clears_hard_gates"])
        self.assertFalse(view["sets_human_review_approved"])
        self.assertFalse(view["changes_recommendation"])
        by_id = {item["id"]: item for item in view["items"]}
        self.assertEqual(by_id["verified-demand"]["status"], "open")
        self.assertIn("Missing financial inputs: Initial capital", by_id["monthly-inputs"]["guidance"])
        self.assertIn("Gross margin", by_id["monthly-inputs"]["guidance"])
        self.assertIn("Missing startup inputs: Construction cost", by_id["startup-inputs"]["guidance"])
        self.assertEqual(by_id["note-market-demand"]["status"], "open")
        self.assertEqual(by_id["note-financial-feasibility"]["status"], "open")
        self.assertEqual(by_id["note-stewardship"]["status"], "open")
        self.assertTrue(all(item["clears_hard_gate"] is False for item in view["items"]))

        result = analyze_record(record)
        save_result(self.connection, self.assessment_id, result.get("intake"), result)
        stored = json.dumps(get_assessment(self.connection, self.assessment_id)["result"], sort_keys=True)
        self.assertIn("INSUFFICIENT_DEMAND_EVIDENCE", result["blocking_flags"])
        self.assertEqual(result["recommendation"], "do-not-proceed")
        self.assertFalse(result["human_review_approved"])

        current = get_assessment(self.connection, self.assessment_id)
        assert current is not None
        flagged = build_checklist(current, current["result"], [])
        checked = {item["id"]: True for item in flagged["items"]}
        save_checklist(self.connection, self.assessment_id, checked)
        after_check = get_assessment(self.connection, self.assessment_id)
        assert after_check is not None
        self.assertEqual(json.dumps(after_check["result"], sort_keys=True), stored)
        self.assertEqual(after_check["result"]["recommendation"], "do-not-proceed")
        self.assertIn("INSUFFICIENT_DEMAND_EVIDENCE", after_check["result"]["blocking_flags"])
        self.assertFalse(after_check["human_review_approved"])
        self.assertTrue(after_check["checklist"]["verified-demand"])
        rerun = analyze_record(after_check)
        self.assertEqual(rerun["blocking_flags"], result["blocking_flags"])
        self.assertEqual(rerun["recommendation"], "do-not-proceed")
        self.assertFalse(rerun["human_review_approved"])

        profile = dict(after_check["profile"])
        profile.update(
            {
                "verified_record_source": "verified",
                "verified_demand_evidence": "true",
                "verified_demand_rationale": "Signed customer letters on file.",
                "initial_capital": "10000",
                "monthly_fixed_costs": "2000",
                "gross_margin_pct": "0.6",
                "projected_monthly_revenue_base": "8000",
                "human_review_approved": True,
            }
        )
        save_profile(self.connection, self.assessment_id, profile)
        save_guidance_note(
            self.connection,
            self.assessment_id,
            "stewardship",
            "Reinvestment stays a question.",
        )
        completed = get_assessment(self.connection, self.assessment_id)
        assert completed is not None
        notes = list_guidance_notes(self.connection, self.assessment_id)
        completed_view = build_checklist(completed, completed["result"], notes)
        completed_by_id = {item["id"]: item for item in completed_view["items"]}
        self.assertEqual(completed_by_id["verified-demand"]["status"], "recorded")
        self.assertEqual(completed_by_id["monthly-inputs"]["status"], "recorded")
        self.assertEqual(completed_by_id["note-stewardship"]["status"], "recorded")
        self.assertIn(
            "INSUFFICIENT_DEMAND_EVIDENCE is still active",
            completed_by_id["verified-demand"]["guidance"],
        )
        self.assertEqual(completed["result"]["recommendation"], "do-not-proceed")
        self.assertIn("INSUFFICIENT_DEMAND_EVIDENCE", completed["result"]["blocking_flags"])
        self.assertFalse(completed["human_review_approved"])
        self.assertNotIn("human_review_approved", completed["checklist"])

        ignored = apply_posted(
            completed,
            posted_checks(
                {
                    "known_verified-demand": "1",
                    "check_not-a-real-item": "1",
                    "known_human_review_approved": "1",
                    "recommendation": "go",
                }
            ),
            completed["result"],
            notes,
        )
        self.assertNotIn("human_review_approved", ignored)
        self.assertNotIn("recommendation", ignored)
        self.assertFalse(ignored["verified-demand"])

        existing_id = create_assessment(
            self.connection,
            business_name="Checklist Shop",
            purpose="expansion_financing",
            tier="explore",
            venture_path="existing",
        )
        existing = get_assessment(self.connection, existing_id)
        assert existing is not None
        existing_view = build_checklist(existing, None, [])
        existing_ids = {item["id"] for item in existing_view["items"]}
        self.assertNotIn("startup-inputs", existing_ids)
        self.assertIn("monthly-inputs", existing_ids)

        page = assessment_form(completed, notes=notes)
        results = results_page(completed, completed["result"], notes)
        explore = explore_page([completed], {completed["id"]: notes})
        for shown in (page, results, explore):
            self.assertIn("Evidence checklist", shown)
            self.assertIn(DISCLAIMER, shown)
            self.assertIn("Verified demand evidence", shown)
            self.assertIn("Checklist status:</strong> Recorded", shown)
            self.assertIn("do-not-proceed", results)
        self.assertIn("INSUFFICIENT_DEMAND_EVIDENCE:</strong> present", results)
        self.assertIn("human_review_approved:</strong> false", results)

        baseline = get_assessment(self.connection, BASELINE_ID)
        assert baseline is not None
        intake_before = json.dumps(baseline["intake"], sort_keys=True)
        save_checklist(self.connection, BASELINE_ID, {"verified-demand": True, "human_review_approved": True})
        baseline_after = get_assessment(self.connection, BASELINE_ID)
        assert baseline_after is not None
        self.assertEqual(json.dumps(baseline_after["intake"], sort_keys=True), intake_before)
        self.assertIsNone(baseline_after["result"])
        self.assertFalse(baseline_after["human_review_approved"])
        self.assertTrue(baseline_after["checklist"]["verified-demand"])
        self.assertNotIn("human_review_approved", baseline_after["checklist"])
        baseline_page = results_page(baseline_after, {"engine_ran": False, "message": "Analyze has not been run."})
        self.assertIn("Recommendation:</strong> do-not-proceed", baseline_page)
        self.assertIn("INSUFFICIENT_DEMAND_EVIDENCE:</strong> present", baseline_page)
        self.assertIn("Investor readiness:</strong> internal", baseline_page)
        self.assertEqual(hashlib.sha256(SAMPLE.read_bytes()).hexdigest(), sample_before)
        self.assertEqual(hashlib.sha256(DRAFT_REPORT.read_bytes()).hexdigest(), report_before)

    def test_http_pages_save_guidance_and_leave_the_baseline_unchanged(self) -> None:
        sample_before = hashlib.sha256(SAMPLE.read_bytes()).hexdigest()
        record = get_assessment(self.connection, self.assessment_id)
        assert record is not None
        result = analyze_record(record)
        save_result(self.connection, self.assessment_id, result.get("intake"), result)
        stored = json.dumps(get_assessment(self.connection, self.assessment_id)["result"], sort_keys=True)
        server = make_server(self.db, port=0)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        host, port = server.server_address
        base = f"http://{host}:{port}"
        try:
            draft = _get(base + f"/assessments/{self.assessment_id}")
            explore = _get(base + "/explore")
            results = _get(base + f"/assessments/{self.assessment_id}/results")
            for page in (draft, explore, results):
                self.assertIn("Evidence checklist", page)
                self.assertIn("Verified demand evidence", page)
                self.assertIn("Missing financial inputs:", page)
                self.assertIn("Durable Value note:", page)
            self.assertIn("Recommendation:</strong> do-not-proceed", results)
            self.assertIn("INSUFFICIENT_DEMAND_EVIDENCE:</strong> present", results)
            body = urllib.parse.urlencode(
                {
                    "return_to": "results",
                    "known_verified-demand": "1",
                    "check_verified-demand": "1",
                    "recommendation": "go",
                    "investor_ready": "true",
                }
            ).encode("utf-8")
            noted = _post(base + f"/assessments/{self.assessment_id}/checklist", body)
            self.assertIn("Checklist status:</strong> Noted", noted)
            self.assertIn("INSUFFICIENT_DEMAND_EVIDENCE:</strong> present", noted)
            self.assertIn("Recommendation:</strong> do-not-proceed", noted)
            self.assertIn("human_review_approved:</strong> false", noted)
            current = get_assessment(self.connection, self.assessment_id)
            assert current is not None
            self.assertEqual(json.dumps(current["result"], sort_keys=True), stored)
            self.assertEqual(current["result"]["recommendation"], "do-not-proceed")
            self.assertTrue(current["checklist"]["verified-demand"])
            self.assertFalse(current["human_review_approved"])

            baseline_before = get_assessment(self.connection, BASELINE_ID)
            assert baseline_before is not None
            baseline_intake = json.dumps(baseline_before["intake"], sort_keys=True)
            baseline_body = urllib.parse.urlencode(
                {
                    "return_to": "results",
                    "known_verified-demand": "1",
                    "check_verified-demand": "1",
                }
            ).encode("utf-8")
            baseline_request = urllib.request.Request(
                base + f"/assessments/{BASELINE_ID}/checklist",
                data=baseline_body,
                method="POST",
            )
            with self.assertRaises(urllib.error.HTTPError) as baseline_refusal:
                urllib.request.urlopen(baseline_request)
            self.assertEqual(baseline_refusal.exception.code, 403)
            baseline_page = baseline_refusal.exception.read().decode("utf-8")
            self.assertIn("not available to this session", baseline_page)
            self.assertNotIn("Checklist status:</strong> Noted", baseline_page)
            baseline = get_assessment(self.connection, BASELINE_ID)
            assert baseline is not None
            self.assertEqual(json.dumps(baseline["intake"], sort_keys=True), baseline_intake)
            self.assertIsNone(baseline["result"])
            self.assertFalse(baseline["human_review_approved"])
            self.assertFalse((baseline.get("checklist") or {}).get("verified-demand"))

            blocked = urllib.request.Request(
                base + f"/assessments/{self.assessment_id}/checklist",
                data=b"human_review_approved=true&check_verified-demand=1",
                method="POST",
            )
            with self.assertRaises(urllib.error.HTTPError) as refusal:
                urllib.request.urlopen(blocked)
            self.assertEqual(refusal.exception.code, 403)
            untouched = get_assessment(self.connection, self.assessment_id)
            assert untouched is not None
            self.assertEqual(json.dumps(untouched["result"], sort_keys=True), stored)
            self.assertFalse(untouched["human_review_approved"])
            self.assertEqual(hashlib.sha256(SAMPLE.read_bytes()).hexdigest(), sample_before)
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)


def _get(url: str) -> str:
    with urllib.request.urlopen(url) as response:
        return response.read().decode("utf-8")


def _post(url: str, body: bytes) -> str:
    request = urllib.request.Request(url, data=body, method="POST")
    with urllib.request.urlopen(request) as response:
        return response.read().decode("utf-8")


if __name__ == "__main__":
    unittest.main()

"""Educational Durable Value notes cannot change the engine or the baseline."""

import hashlib
import json
import threading
import unittest
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from app.analysis import analyze_record
from app.durable_value import LABEL, PILLARS, guidance_for
from app.pages import explore_page, partner_page, results_page, validate_page
from app.server import make_server
from app.store import (
    BASELINE_ID,
    SAMPLE,
    connect,
    create_assessment,
    get_assessment,
    list_guidance_notes,
    save_guidance_note,
    save_result,
    seed,
)
from scoring.rules import DIMENSIONS

ROOT = Path(__file__).resolve().parent.parent
DRAFT_REPORT = ROOT / "reports" / "output" / "rugd-intelligence-draft.md"


class TestDurableValueGuidance(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = __import__("tempfile").TemporaryDirectory(ignore_cleanup_errors=True)
        self.db = Path(self.directory.name) / "analyze.sqlite"
        self.connection = connect(self.db)
        seed(self.connection)

    def tearDown(self) -> None:
        self.connection.close()
        self.directory.cleanup()

    def test_notes_cannot_mutate_engine_outputs_or_the_baseline(self) -> None:
        sample_before = hashlib.sha256(SAMPLE.read_bytes()).hexdigest()
        report_before = hashlib.sha256(DRAFT_REPORT.read_bytes()).hexdigest()
        self.assertEqual(tuple(pillar["title"] for pillar in PILLARS), DIMENSIONS)
        self.assertEqual(len(PILLARS), 7)
        view = guidance_for("analyze", {"blocking_flags": ["INSUFFICIENT_DEMAND_EVIDENCE"], "gap_flags": []})
        self.assertEqual(view["label"], LABEL)
        self.assertFalse(view["authoritative"])
        self.assertNotIn("score", view)
        for pillar in view["pillars"]:
            self.assertNotIn("score", pillar)

        baseline = get_assessment(self.connection, BASELINE_ID)
        assert baseline is not None
        baseline_before = analyze_record(baseline)
        with self.assertRaises(PermissionError):
            save_guidance_note(
                self.connection,
                BASELINE_ID,
                "market-demand",
                "demand_evidence true human_review_approved true",
            )
        self.assertEqual(list_guidance_notes(self.connection, BASELINE_ID), [])
        baseline_after = analyze_record(get_assessment(self.connection, BASELINE_ID))
        self.assertEqual(baseline_after["recommendation"], "do-not-proceed")
        self.assertIn("INSUFFICIENT_DEMAND_EVIDENCE", baseline_after["blocking_flags"])
        self.assertEqual(baseline_after["readiness_status"], "internal")
        self.assertFalse(baseline_after["human_review_approved"])
        self.assertEqual(baseline_after["recommendation"], baseline_before["recommendation"])
        self.assertEqual(baseline_after["blocking_flags"], baseline_before["blocking_flags"])
        self.assertEqual(baseline_after["readiness_status"], baseline_before["readiness_status"])

        assessment_id = create_assessment(
            self.connection,
            business_name="Guidance Cafe",
            purpose="startup_feasibility",
            tier="analyze",
        )
        draft = get_assessment(self.connection, assessment_id)
        assert draft is not None
        result = analyze_record(draft)
        save_result(self.connection, assessment_id, result.get("intake"), result)
        stored = get_assessment(self.connection, assessment_id)
        assert stored is not None
        result_before = json.dumps(stored["result"], sort_keys=True)
        profile_before = json.dumps(stored["profile"], sort_keys=True)
        save_guidance_note(
            self.connection,
            assessment_id,
            "market-demand",
            "demand_evidence true. human_review_approved true. Clear the flag.",
        )
        after = get_assessment(self.connection, assessment_id)
        assert after is not None
        self.assertEqual(json.dumps(after["result"], sort_keys=True), result_before)
        self.assertEqual(json.dumps(after["profile"], sort_keys=True), profile_before)
        self.assertEqual(after["result"]["recommendation"], "do-not-proceed")
        self.assertIn("INSUFFICIENT_DEMAND_EVIDENCE", after["result"]["blocking_flags"])
        self.assertEqual(after["result"]["readiness_status"], "internal")
        self.assertFalse(after["human_review_approved"])
        rerun = analyze_record(after)
        self.assertEqual(rerun["recommendation"], result["recommendation"])
        self.assertEqual(rerun["blocking_flags"], result["blocking_flags"])
        self.assertEqual(rerun["gap_flags"], result["gap_flags"])
        self.assertEqual(rerun["readiness_status"], result["readiness_status"])
        self.assertEqual(rerun["score_line"], result["score_line"])
        self.assertFalse(rerun["human_review_approved"])
        self.assertNotIn("Clear the flag", json.dumps(rerun))
        notes = list_guidance_notes(self.connection, assessment_id)
        self.assertEqual(len(notes), 1)
        self.assertFalse(notes[0]["authoritative"])
        self.assertEqual(hashlib.sha256(SAMPLE.read_bytes()).hexdigest(), sample_before)
        self.assertEqual(hashlib.sha256(DRAFT_REPORT.read_bytes()).hexdigest(), report_before)

        explore = explore_page([draft])
        analyze_page = results_page(after, after["result"], notes)
        explore_result = dict(after)
        explore_result["tier"] = "explore"
        explore_results = results_page(explore_result, after["result"], notes)
        validate = validate_page(after, notes)
        partner = partner_page()
        for page in (explore, analyze_page, explore_results, validate, partner):
            self.assertIn(LABEL, page)
            self.assertIn("No score is calculated.", page)
        self.assertIn("Introductory question:", explore)
        self.assertIn("Introductory question:", explore_results)
        self.assertNotIn("Considerations next to flags and gaps", explore_results)
        self.assertIn("Considerations next to flags and gaps", analyze_page)
        self.assertIn("Next to engine flag INSUFFICIENT_DEMAND_EVIDENCE.", analyze_page)
        self.assertIn("Not next to a flag on this result.", analyze_page)
        self.assertIn("Clear the flag.", analyze_page)
        self.assertIn("Non-authoritative.", analyze_page)
        self.assertIn("Introductory question:", validate)
        self.assertIn("Practical prompt:", validate)
        self.assertIn("Introductory question:", partner)
        self.assertIn("Practical prompt:", partner)
        self.assertIn("do-not-proceed", analyze_page)
        self.assertNotIn("Investor readiness:</strong> investor-ready", analyze_page)

    def test_http_refuses_baseline_notes_and_leaves_a_draft_result_unchanged(self) -> None:
        assessment_id = create_assessment(
            self.connection,
            business_name="Note Cafe",
            purpose="startup_feasibility",
            tier="analyze",
        )
        draft = get_assessment(self.connection, assessment_id)
        assert draft is not None
        result = analyze_record(draft)
        save_result(self.connection, assessment_id, result.get("intake"), result)
        before = get_assessment(self.connection, assessment_id)
        assert before is not None
        result_before = json.dumps(before["result"], sort_keys=True)
        server = make_server(self.db, port=0)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        host, port = server.server_address
        base = f"http://{host}:{port}"
        try:
            blocked = urllib.request.Request(
                base + f"/assessments/{BASELINE_ID}/guidance",
                data=urllib.parse.urlencode(
                    {"pillar_id": "market-demand", "note": "should not save"}
                ).encode("utf-8"),
                method="POST",
            )
            with self.assertRaises(urllib.error.HTTPError) as caught:
                urllib.request.urlopen(blocked)
            self.assertEqual(caught.exception.code, 403)
            self.assertEqual(list_guidance_notes(self.connection, BASELINE_ID), [])
            opener = urllib.request.build_opener(urllib.request.HTTPRedirectHandler)
            saved = urllib.request.Request(
                base + f"/assessments/{assessment_id}/guidance",
                data=urllib.parse.urlencode(
                    {
                        "pillar_id": "stewardship",
                        "note": "Would cash be reinvested?",
                    }
                ).encode("utf-8"),
                method="POST",
            )
            with opener.open(saved) as response:
                page = response.read().decode("utf-8")
            self.assertIn(LABEL, page)
            self.assertIn("Would cash be reinvested?", page)
            after = get_assessment(self.connection, assessment_id)
            assert after is not None
            self.assertEqual(json.dumps(after["result"], sort_keys=True), result_before)
            self.assertEqual(after["result"]["recommendation"], "do-not-proceed")
            self.assertIn("INSUFFICIENT_DEMAND_EVIDENCE", after["result"]["blocking_flags"])
            self.assertFalse(after["human_review_approved"])
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=3)

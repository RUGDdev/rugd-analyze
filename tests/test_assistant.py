"""Plain-language notes and the assistant leave the engine result unchanged."""

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
from app.analysis import analyze_record
from app.analyst import ASSISTANCE_LABEL, STARTER_QUESTIONS, answer
from app.pages import assessment_form, dashboard, explore_page, market_page, results_page
from app.server import make_server
from app.store import BASELINE_ID, SAMPLE, connect, get_assessment, get_user_by_id, seed

ROOT = Path(__file__).resolve().parent.parent
DRAFT_REPORT = ROOT / "reports" / "output" / "rugd-intelligence-draft.md"
NOTE = "Local prototype. Not production security. This screen does not grant investor-ready status."
EMAIL = "plain-owner@pilot.example"
PASSWORD = "plain-pass-1"


class TestPlainLanguageAndAssistant(unittest.TestCase):
    def test_continue_intake_points_at_the_draft_form(self) -> None:
        draft = {
            "id": "pilot-1-draft",
            "business_name": "Pilot 1",
            "tier": "explore",
            "read_only": False,
            "hypothetical": False,
            "pilot_label": "Customer draft. Not a completed assessment.",
            "profile": {"business_name": "Pilot 1", "purpose": "startup_feasibility", "tier": "explore"},
            "result": None,
            "human_review_approved": False,
        }
        page = assessment_form(draft)
        self.assertIn("Continue Intake", page)
        self.assertIn('class="button" href="/assessments/pilot-1-draft#intake"', page)
        self.assertIn('id="intake"', page)
        self.assertIn("does not clear a recommend-against flag", page)
        self.assertNotIn(">Edit Intake<", page)
        analyzed = {
            **draft,
            "result": {
                "engine_ran": True,
                "recommendation": "do-not-proceed",
                "blocking_flags": ["INSUFFICIENT_DEMAND_EVIDENCE"],
                "human_review_approved": False,
                "readiness_status": "internal",
            },
        }
        edited = assessment_form(analyzed)
        self.assertIn(">Edit Intake<", edited)
        self.assertIn('class="button" href="/assessments/pilot-1-draft#intake"', edited)
        self.assertIn("Editing the intake does not clear a recommend-against flag", edited)
        self.assertNotIn(">Continue Intake<", edited)
        self.assertIn("INSUFFICIENT_DEMAND_EVIDENCE", edited)

    def test_notes_keep_the_warnings_and_precise_terms(self) -> None:
        directory = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        connection = connect(Path(directory.name) / "analyze.sqlite")
        seed(connection)
        sample_before = hashlib.sha256(SAMPLE.read_bytes()).hexdigest()
        report_before = hashlib.sha256(DRAFT_REPORT.read_bytes()).hexdigest()
        record = get_assessment(connection, BASELINE_ID)
        assert record is not None
        result = analyze_record(record)
        home = dashboard([], signed_in=True, viewer_id="plain-reader")
        explore = explore_page([record])
        intake = assessment_form(record)
        market = market_page()
        shown = results_page(record, result)
        for name, page in {
            "dashboard": home,
            "explore": explore,
            "intake": intake,
            "market": market,
            "results": shown,
        }.items():
            self.assertIn(NOTE, page, name)
            self.assertIn('class="sidebar"', page, name)
        self.assertIn("No assessments yet", home)
        self.assertIn("You have not created an assessment", home)
        self.assertIn("What to do first:", home)
        self.assertIn("INSUFFICIENT_DEMAND_EVIDENCE.", home)
        self.assertIn("Learn more", home)
        self.assertIn('class="plain"', home)
        self.assertIn("Verified demand evidence", explore)
        self.assertIn("In everyday words: show proof that people will pay", explore)
        self.assertIn("Ask about this assessment", intake)
        self.assertIn(ASSISTANCE_LABEL, intake)
        self.assertIn('id="assistant-empty"', intake)
        self.assertIn("Choose a starter or type a question", intake)
        self.assertEqual(len(STARTER_QUESTIONS), 7)
        self.assertIn("What should I work on next?", STARTER_QUESTIONS)
        self.assertIn("What does this gate mean?", STARTER_QUESTIONS)
        for question in STARTER_QUESTIONS:
            self.assertIn(question, intake)
        self.assertIn("What this means", intake)
        self.assertIn("Market snapshot.", market)
        self.assertIn("Indicative assessment — market validity, financial viability, and stewardship readiness.", shown)
        self.assertIn("Does not override engine flags or human review.", shown)
        self.assertIn("Sources and uses, scenarios, and DSCR", shown)
        self.assertIn("DSCR.", shown)
        self.assertIn("Recommend-against flag.", shown)
        self.assertIn("Investor readiness:</strong> internal", shown)
        self.assertNotIn("Investor readiness:</strong> investor-ready", shown)
        self.assertIn("INSUFFICIENT_DEMAND_EVIDENCE", result["blocking_flags"])
        self.assertEqual(result["recommendation"], "do-not-proceed")
        self.assertEqual(result["readiness_status"], "internal")
        self.assertFalse(result["human_review_approved"])
        self.assertEqual(result["score_line"], "Not calculated — methodology pending approval.")
        self.assertEqual(hashlib.sha256(SAMPLE.read_bytes()).hexdigest(), sample_before)
        self.assertEqual(hashlib.sha256(DRAFT_REPORT.read_bytes()).hexdigest(), report_before)
        connection.close()
        directory.cleanup()

    def test_assistant_cannot_mutate_the_result_or_the_baseline(self) -> None:
        directory = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        connection = connect(Path(directory.name) / "analyze.sqlite")
        seed(connection)
        sample_before = hashlib.sha256(SAMPLE.read_bytes()).hexdigest()
        record = get_assessment(connection, BASELINE_ID)
        assert record is not None
        result = analyze_record(record)
        before_result = copy.deepcopy(result)
        before_record = copy.deepcopy(record)
        lines = answer(record, result, "What does my score mean?")
        self.assertEqual(result, before_result)
        self.assertEqual(record["business_name"], before_record["business_name"])
        self.assertEqual(lines[0], ASSISTANCE_LABEL)
        text = " ".join(lines)
        self.assertIn("cannot change numbers", text)
        self.assertIn("Not calculated — methodology pending approval.", text)
        self.assertIn("do-not-proceed", text)
        self.assertIn("INSUFFICIENT_DEMAND_EVIDENCE", text)
        self.assertIn("Blocked", text)
        demand = answer(record, result, "Why is demand evidence missing?")
        self.assertEqual(result, before_result)
        self.assertIn("does not clear the flag", " ".join(demand))
        nxt = answer(record, result, "What should I do next?")
        self.assertEqual(result["blocking_flags"], before_result["blocking_flags"])
        self.assertIn("This reply does not", " ".join(nxt))
        self.assertIn("INSUFFICIENT_DEMAND_EVIDENCE", " ".join(nxt))
        recommendation = answer(record, result, "What does the recommendation mean?")
        self.assertEqual(recommendation[0], ASSISTANCE_LABEL)
        self.assertIn("do-not-proceed", " ".join(recommendation))
        self.assertIn("does not change the recommendation", " ".join(recommendation))
        ready = answer(record, result, "Am I investor-ready?")
        self.assertEqual(ready[0], ASSISTANCE_LABEL)
        self.assertIn("internal", " ".join(ready))
        self.assertIn("does not grant investor-ready status", " ".join(ready))
        self.assertEqual(result, before_result)
        self.assertFalse(result["human_review_approved"])
        self.assertEqual(result["readiness_status"], "internal")

        owner = register_account(connection, email=EMAIL, password=PASSWORD)
        self.assertEqual(owner["role"], "customer")
        server = make_server(Path(directory.name) / "analyze.sqlite", port=0)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        base = f"http://127.0.0.1:{server.server_address[1]}"
        try:
            cookie = self._login(base)
            stored = json.dumps(get_assessment(connection, BASELINE_ID)["result"], sort_keys=True)
            asked = self._raw(
                base + f"/assessments/{BASELINE_ID}/assistant",
                {"starter": "What does my score mean?"},
                cookie,
            )
            self.assertEqual(asked[0], 200, asked[1])
            self.assertIn(ASSISTANCE_LABEL, asked[1])
            self.assertIn(NOTE, asked[1])
            self.assertIn('class="sidebar"', asked[1])
            self.assertIn("This reply does not run the engine", asked[1])
            denied = self._raw(
                base + f"/assessments/{BASELINE_ID}/assistant",
                {"starter": "What does my score mean?", "human_review_approved": "true"},
                cookie,
            )
            self.assertEqual(denied[0], 403)
            after = get_assessment(connection, BASELINE_ID)
            assert after is not None
            self.assertEqual(json.dumps(after["result"], sort_keys=True), stored)
            self.assertFalse(after["human_review_approved"])
            rerun = analyze_record(after)
            self.assertEqual(rerun["recommendation"], "do-not-proceed")
            self.assertIn("INSUFFICIENT_DEMAND_EVIDENCE", rerun["blocking_flags"])
            self.assertEqual(rerun["readiness_status"], "internal")
            self.assertFalse(rerun["human_review_approved"])
            self.assertEqual(get_user_by_id(connection, owner["id"])["role"], "customer")
            self.assertEqual(hashlib.sha256(SAMPLE.read_bytes()).hexdigest(), sample_before)
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=3)
            connection.close()
            directory.cleanup()

    def _login(self, base: str) -> str:
        status, _body, headers = self._raw(base + "/login", {"email": EMAIL, "password": PASSWORD})
        self.assertEqual(status, 303)
        return (headers.get("Set-Cookie") or "").split(";", 1)[0]

    def _raw(
        self,
        url: str,
        fields: dict[str, str],
        cookie: str = "",
    ) -> tuple[int, str, dict[str, str]]:
        class NoRedirect(urllib.request.HTTPRedirectHandler):
            def redirect_request(self, req, fp, code, msg, headers, newurl):
                return None

        headers = {"Cookie": cookie} if cookie else {}
        opener = urllib.request.build_opener(NoRedirect)
        request = urllib.request.Request(
            url,
            data=urllib.parse.urlencode(fields).encode(),
            method="POST",
            headers=headers,
        )
        try:
            response = opener.open(request)
        except urllib.error.HTTPError as exc:
            return exc.code, exc.read().decode("utf-8"), dict(exc.headers)
        return response.status, response.read().decode("utf-8"), dict(response.headers)

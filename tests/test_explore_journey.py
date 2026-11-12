"""An objective opens a saved Explore conversation. Approval writes one assumption."""

import hashlib
import tempfile
import threading
import unittest
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from app.accounts import register_account
from app.adviser_flow import apply_proposal, receive_answer
from app.server import make_server
from app.store import BASELINE_ID, SAMPLE, connect, get_assessment, seed

EMAIL = "journey-owner@pilot.example"
PASSWORD = "journey-pass-1"


class TestExploreJourney(unittest.TestCase):
    def test_answers_wait_for_approval_and_do_not_change_the_baseline(self) -> None:
        profile = {
            "business_name": "New draft",
            "concept": "",
            "industry": "",
            "market": "",
            "products": "",
            "customers": "",
            "revenue_model": "",
            "competition": "",
            "human_review_approved": False,
        }
        receive_answer(profile, "Harbor Coffee")
        self.assertEqual(profile["business_name"], "New draft")
        self.assertEqual(profile["adviser_proposal"]["value"], "Harbor Coffee")
        self.assertFalse(profile["human_review_approved"])
        apply_proposal(profile)
        self.assertEqual(profile["business_name"], "Harbor Coffee")
        self.assertIsNone(profile["adviser_proposal"])
        self.assertFalse(profile["human_review_approved"])
        self.assertEqual(profile.get("industry", ""), "")

        directory = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        connection = connect(Path(directory.name) / "analyze.sqlite")
        seed(connection)
        sample_before = hashlib.sha256(SAMPLE.read_bytes()).hexdigest()
        register_account(connection, email=EMAIL, password=PASSWORD)
        server = make_server(Path(directory.name) / "analyze.sqlite", port=0)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        base = f"http://127.0.0.1:{server.server_address[1]}"
        try:
            guest = urllib.request.urlopen(base + "/")
            guest_body = guest.read().decode("utf-8")
            self.assertIn("What would you like to accomplish with your business?", guest_body)
            self.assertIn("Welcome to RUGD Intelligence", guest_body)
            self.assertIn('class="button" href="/login"', guest_body)
            self.assertIn("Start a Business", guest_body)
            self.assertIn("Demonstration", guest_body)

            cookie = self._login(base)
            started = self._raw(base + "/start", {"objective": "start-business"}, cookie)
            self.assertEqual(started[0], 303)
            location = started[2].get("Location") or ""
            assessment_id = location.rstrip("/").split("/")[-1].split("#")[0]
            self.assertTrue(assessment_id)
            self.assertNotEqual(assessment_id, BASELINE_ID)

            page = self._get(base + location.split("#")[0], cookie)
            self.assertIn("id=\"adviser\"", page)
            self.assertIn("What should we call this business?", page)
            self.assertIn("Deterministic guidance, no live model. Nothing is saved until you approve it.", page)
            self.assertNotIn("ANALYST_PROVIDER", page)
            self.assertNotIn("Streaming is not available", page)
            self.assertNotIn("You are the RUGD analyst", page)
            self.assertIn("Continue to Analyze", page)
            self.assertIn("Educational guidance — not a DVT evaluation.", page)
            self.assertIn("No pillar score is calculated.", page)

            asked = self._raw(
                base + f"/assessments/{assessment_id}/adviser",
                {"message": "Harbor Coffee"},
                cookie,
            )
            self.assertEqual(asked[0], 303)
            waiting = get_assessment(connection, assessment_id)
            assert waiting is not None
            self.assertEqual(waiting["business_name"], "New draft")
            self.assertEqual(waiting["profile"]["adviser_proposal"]["value"], "Harbor Coffee")
            self.assertFalse(waiting["human_review_approved"])
            self.assertIsNone(waiting["result"])

            saved = self._raw(
                base + f"/assessments/{assessment_id}/adviser/apply",
                {"decision": "save"},
                cookie,
            )
            self.assertEqual(saved[0], 303)
            opened = get_assessment(connection, assessment_id)
            assert opened is not None
            self.assertEqual(opened["business_name"], "Harbor Coffee")
            self.assertEqual(opened["profile"]["concept"], "")
            self.assertIn("In a sentence, what are you considering?", str(opened["profile"]["adviser_messages"]))
            self.assertFalse(opened["human_review_approved"])
            self.assertIsNone(opened["result"])
            again = self._get(base + f"/assessments/{assessment_id}", cookie)
            self.assertIn("Harbor Coffee", again)
            self.assertIn("Continue to Analyze", again)
            baseline = get_assessment(connection, BASELINE_ID)
            assert baseline is not None
            self.assertEqual(baseline["read_only"], True)
            blocked = self._raw(
                base + f"/assessments/{BASELINE_ID}/adviser",
                {"message": "Change the baseline"},
                cookie,
            )
            self.assertEqual(blocked[0], 403)
            self.assertEqual(hashlib.sha256(SAMPLE.read_bytes()).hexdigest(), sample_before)
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=3)
            connection.close()
            directory.cleanup()

    def test_a_failed_provider_does_not_invent_a_reply(self) -> None:
        directory = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        connection = connect(Path(directory.name) / "analyze.sqlite")
        seed(connection)
        register_account(connection, email=EMAIL, password=PASSWORD)
        server = make_server(Path(directory.name) / "analyze.sqlite", port=0)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        base = f"http://127.0.0.1:{server.server_address[1]}"

        class Boom:
            uses_network = True

            def reply(self, *_args: object, **_kwargs: object) -> list[str]:
                raise RuntimeError("provider down")

        import app.server as server_module

        original = server_module.get_analyst
        server_module.get_analyst = lambda: Boom()
        try:
            cookie = self._login(base)
            started = self._raw(base + "/start", {"objective": "research-market"}, cookie)
            assessment_id = (started[2].get("Location") or "").split("/")[-1].split("#")[0]
            sent = self._raw(
                base + f"/assessments/{assessment_id}/adviser",
                {"message": "A riverside cafe"},
                cookie,
            )
            self.assertEqual(sent[0], 303)
            record = get_assessment(connection, assessment_id)
            assert record is not None
            text = str(record["profile"]["adviser_messages"])
            self.assertIn("No live reply was invented.", text)
            self.assertEqual(record["profile"]["adviser_proposal"]["value"], "A riverside cafe")
            self.assertEqual(record["business_name"], "New draft")
            self.assertFalse(record["human_review_approved"])
        finally:
            server_module.get_analyst = original
            server.shutdown()
            server.server_close()
            thread.join(timeout=3)
            connection.close()
            directory.cleanup()

    def _login(self, base: str) -> str:
        status, _body, headers = self._raw(base + "/login", {"email": EMAIL, "password": PASSWORD})
        self.assertEqual(status, 303)
        return (headers.get("Set-Cookie") or "").split(";", 1)[0]

    def _get(self, url: str, cookie: str) -> str:
        request = urllib.request.Request(url, headers={"Cookie": cookie})
        with urllib.request.urlopen(request) as response:
            return response.read().decode("utf-8")

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

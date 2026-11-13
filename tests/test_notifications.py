"""Stored email preferences notify the owner and leave the assessment unchanged."""

import hashlib
import json
import tempfile
import threading
import unittest
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from app.accounts import bootstrap_reviewer, register_account
from app.analysis import analyze_record
from app.mail import OUTBOX
from app.pages import settings_page
from app.server import make_server
from app.store import (
    BASELINE_ID,
    SAMPLE,
    connect,
    create_assessment,
    get_assessment,
    get_user_by_id,
    save_profile,
    save_result,
    seed,
)

ROOT = Path(__file__).resolve().parent.parent
DRAFT_REPORT = ROOT / "reports" / "output" / "rugd-intelligence-draft.md"
OWNER_EMAIL = "notice-owner@pilot.example"
REVIEWER_EMAIL = "notice-reviewer@pilot.example"
PASSWORD = "notice-pass-1"
NOTE = "Local prototype. Not production security. This screen does not grant investor-ready status."


class TestNotificationPreferences(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.connection = connect(Path(self.directory.name) / "analyze.sqlite")
        seed(self.connection)
        OUTBOX.clear()
        self.owner = register_account(self.connection, email=OWNER_EMAIL, password=PASSWORD)
        self.reviewer = bootstrap_reviewer(self.connection, email=REVIEWER_EMAIL, password=PASSWORD)
        assert self.reviewer is not None
        self.assertTrue(any(item["subject"] == "Verify your RUGD Analyze email" for item in OUTBOX))
        OUTBOX.clear()
        self.assessment_id = create_assessment(
            self.connection,
            business_name="Notice Cafe",
            purpose="startup_feasibility",
            tier="analyze",
            owner_user_id=self.owner["id"],
        )
        save_profile(
            self.connection,
            self.assessment_id,
            {
                "business_name": "Notice Cafe",
                "purpose": "startup_feasibility",
                "tier": "analyze",
                "industry": "Restaurant",
                "market": "Example county",
                "stage": "Idea",
                "initial_capital": "10000",
                "monthly_fixed_costs": "2000",
                "gross_margin_pct": "0.6",
                "projected_monthly_revenue_base": "8000",
            },
        )
        record = get_assessment(self.connection, self.assessment_id)
        assert record is not None
        result = analyze_record(record)
        save_result(self.connection, self.assessment_id, result.get("intake"), result)
        stored_owner = get_user_by_id(self.connection, self.owner["id"])
        assert stored_owner is not None
        self.password_hash = stored_owner["password_hash"]

    def tearDown(self) -> None:
        self.connection.close()
        self.directory.cleanup()
        OUTBOX.clear()

    def test_preferences_are_branded_and_cannot_approve(self) -> None:
        signed_out = settings_page()
        signed_in = settings_page(get_user_by_id(self.connection, self.owner["id"]))
        for page in (signed_out, signed_in):
            self.assertIn('class="sidebar"', page)
            self.assertIn('src="/static/rugd-logo.png"', page)
            self.assertIn("#263746", page)
            self.assertIn("#A88958", page)
            self.assertIn('class="card"', page)
            self.assertIn(NOTE, page)
            self.assertIn("Email preferences", page)
        self.assertIn("Save email preferences", signed_in)
        self.assertNotIn("Save email preferences", signed_out)
        stored = get_user_by_id(self.connection, self.owner["id"])
        assert stored is not None
        self.assertEqual(
            stored["notification_preferences"],
            {
                "assessment_shared": False,
                "review_requested": False,
                "review_recorded": False,
            },
        )

        server = make_server(Path(self.directory.name) / "analyze.sqlite", port=0)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        base = f"http://127.0.0.1:{server.server_address[1]}"
        try:
            cookie = self._login(base, OWNER_EMAIL, PASSWORD)
            page = self._get(base + "/settings", cookie)
            self.assertIn("Email preferences", page)
            self.assertIn(NOTE, page)
            self.assertNotIn('name="pref_assessment_shared" value="1" checked', page)
            saved = self._raw(
                base + "/settings/notifications",
                {
                    "pref_assessment_shared": "1",
                    "pref_review_requested": "1",
                    "pref_human_review_approved": "1",
                },
                cookie,
            )
            self.assertEqual(saved[0], 303)
            shown = self._get(base + "/settings", cookie)
            self.assertIn('name="pref_assessment_shared" value="1" checked', shown)
            self.assertIn('name="pref_review_requested" value="1" checked', shown)
            self.assertNotIn('name="pref_review_recorded" value="1" checked', shown)
            user = get_user_by_id(self.connection, self.owner["id"])
            assert user is not None
            self.assertEqual(user["role"], "customer")
            self.assertEqual(user["password_hash"], self.password_hash)
            self.assertEqual(
                user["notification_preferences"],
                {
                    "assessment_shared": True,
                    "review_requested": True,
                    "review_recorded": False,
                },
            )
            denied = self._raw(
                base + "/settings/notifications",
                {"pref_assessment_shared": "1", "human_review_approved": "true"},
                cookie,
            )
            self.assertEqual(denied[0], 403)
            self.assertIn("cannot approve an assessment", denied[1])
            after_denial = get_user_by_id(self.connection, self.owner["id"])
            assert after_denial is not None
            self.assertEqual(after_denial["notification_preferences"], user["notification_preferences"])
            self.assertFalse(get_assessment(self.connection, self.assessment_id)["human_review_approved"])
            stranger = self._raw(
                base + "/settings/notifications",
                {"pref_assessment_shared": "1"},
            )
            self.assertEqual(stranger[0], 403)
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=3)

    def test_opted_in_notices_leave_the_result_and_baseline_unchanged(self) -> None:
        sample_before = hashlib.sha256(SAMPLE.read_bytes()).hexdigest()
        report_before = hashlib.sha256(DRAFT_REPORT.read_bytes()).hexdigest()
        before = get_assessment(self.connection, self.assessment_id)
        assert before is not None
        stored_result = json.dumps(before["result"], sort_keys=True)
        self.assertEqual(before["result"]["recommendation"], "do-not-proceed")
        self.assertIn("INSUFFICIENT_DEMAND_EVIDENCE", before["result"]["blocking_flags"])
        self.assertFalse(before["human_review_approved"])
        self.assertEqual(before["result"]["score_line"], "Not calculated — methodology pending approval.")

        server = make_server(Path(self.directory.name) / "analyze.sqlite", port=0)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        base = f"http://127.0.0.1:{server.server_address[1]}"
        try:
            cookie = self._login(base, OWNER_EMAIL, PASSWORD)
            quiet = self._raw(
                base + f"/assessments/{self.assessment_id}/share",
                {"lifetime": "7d"},
                cookie,
            )
            self.assertEqual(quiet[0], 303)
            self.assertEqual(OUTBOX, [])
            unchanged = get_assessment(self.connection, self.assessment_id)
            assert unchanged is not None
            self.assertEqual(json.dumps(unchanged["result"], sort_keys=True), stored_result)
            self.assertFalse(unchanged["human_review_approved"])

            self._raw(
                base + "/settings/notifications",
                {
                    "pref_assessment_shared": "1",
                    "pref_review_requested": "1",
                    "pref_review_recorded": "1",
                },
                cookie,
            )
            shared = self._raw(
                base + f"/assessments/{self.assessment_id}/share",
                {"lifetime": "24h"},
                cookie,
            )
            self.assertEqual(shared[0], 303)
            token = urllib.parse.parse_qs(urllib.parse.urlparse(shared[2].get("Location", "")).query)["share"][0]
            self.assertEqual(len(OUTBOX), 1)
            self.assertEqual(OUTBOX[0]["to"], OWNER_EMAIL)
            self.assertNotIn(token, OUTBOX[0]["body"])
            self.assertIn("does not approve the assessment", OUTBOX[0]["body"])
            after_share = get_assessment(self.connection, self.assessment_id)
            assert after_share is not None
            self.assertEqual(json.dumps(after_share["result"], sort_keys=True), stored_result)
            self.assertEqual(after_share["result"]["recommendation"], "do-not-proceed")
            self.assertFalse(after_share["human_review_approved"])

            requested = self._raw(
                base + f"/assessments/{self.assessment_id}/review-request",
                {},
                cookie,
            )
            self.assertEqual(requested[0], 303)
            self.assertEqual(len(OUTBOX), 2)
            self.assertEqual(OUTBOX[1]["to"], OWNER_EMAIL)
            self.assertIn("does not approve the assessment", OUTBOX[1]["body"])
            after_request = get_assessment(self.connection, self.assessment_id)
            assert after_request is not None
            self.assertEqual(json.dumps(after_request["result"], sort_keys=True), stored_result)
            self.assertTrue(after_request["review_requested"])
            self.assertFalse(after_request["human_review_approved"])

            reviewer_cookie = self._login(base, REVIEWER_EMAIL, PASSWORD)
            approved = self._raw(
                base + f"/reviewer/assessments/{self.assessment_id}/approve",
                {},
                reviewer_cookie,
            )
            self.assertEqual(approved[0], 303, approved[1])
            self.assertEqual(len(OUTBOX), 3)
            self.assertEqual(OUTBOX[2]["to"], OWNER_EMAIL)
            self.assertIn("does not approve the assessment", OUTBOX[2]["body"])
            after_approval = get_assessment(self.connection, self.assessment_id)
            assert after_approval is not None
            self.assertEqual(after_approval["result"]["recommendation"], "do-not-proceed")
            self.assertIn("INSUFFICIENT_DEMAND_EVIDENCE", after_approval["result"]["blocking_flags"])
            self.assertEqual(
                after_approval["result"]["score_line"],
                "Not calculated — methodology pending approval.",
            )
            self.assertTrue(after_approval["human_review_approved"])
            self.assertEqual(get_user_by_id(self.connection, self.owner["id"])["role"], "customer")

            before_baseline_mail = len(OUTBOX)
            baseline_share = self._raw(
                base + f"/assessments/{BASELINE_ID}/share",
                {"lifetime": "7d"},
                reviewer_cookie,
            )
            self.assertEqual(baseline_share[0], 303)
            self.assertEqual(len(OUTBOX), before_baseline_mail)
            baseline = get_assessment(self.connection, BASELINE_ID)
            assert baseline is not None
            analyzed = analyze_record(baseline)
            self.assertEqual(analyzed["recommendation"], "do-not-proceed")
            self.assertIn("INSUFFICIENT_DEMAND_EVIDENCE", analyzed["blocking_flags"])
            self.assertEqual(analyzed["readiness_status"], "internal")
            self.assertFalse(analyzed["human_review_approved"])
            self.assertFalse(baseline["human_review_approved"])
            self.assertEqual(hashlib.sha256(SAMPLE.read_bytes()).hexdigest(), sample_before)
            self.assertEqual(hashlib.sha256(DRAFT_REPORT.read_bytes()).hexdigest(), report_before)
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=3)

    def _login(self, base: str, email: str, password: str) -> str:
        status, _body, headers = self._raw(base + "/login", {"email": email, "password": password})
        self.assertEqual(status, 303)
        return (headers.get("Set-Cookie") or "").split(";", 1)[0]

    def _get(self, url: str, cookie: str) -> str:
        request = urllib.request.Request(url, headers={"Cookie": cookie})
        with urllib.request.urlopen(request) as response:
            self.assertEqual(response.status, 200)
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

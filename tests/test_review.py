"""Reviewer approval is separate from customer controls and the readiness gate."""

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
from app.pages import reviewer_page, validate_page
from app.review import (
    approve_assessment,
    close_reviewer_session,
    open_account_session,
    reviewer_session_state,
)
from app.server import make_server
from app.store import (
    BASELINE_ID,
    SAMPLE,
    connect,
    create_assessment,
    get_assessment,
    list_reviewer_events,
    save_profile,
    save_result,
    seed,
    session_activity,
    session_public_id,
    session_storage_key,
)

REVIEWER_EMAIL = "reviewer@pilot.example"
REVIEWER_PASSWORD = "reviewer-pass-1"
CUSTOMER_EMAIL = "customer@pilot.example"
CUSTOMER_PASSWORD = "customer-pass-1"

ROOT = Path(__file__).resolve().parent.parent
OUTPUT = ROOT / "reports" / "output"


class TestReviewerApproval(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.db = Path(self.directory.name) / "analyze.sqlite"
        self.connection = connect(self.db)
        seed(self.connection)

    def tearDown(self) -> None:
        self.connection.close()
        self.directory.cleanup()

    def test_approval_is_audited_and_does_not_clear_gates(self) -> None:
        before = hashlib.sha256(SAMPLE.read_bytes()).hexdigest()
        output_before = sorted(path.name for path in OUTPUT.iterdir())
        assessment_id = create_assessment(
            self.connection,
            business_name="Review Cafe",
            purpose="startup_feasibility",
            tier="analyze",
        )
        current = get_assessment(self.connection, assessment_id)
        assert current is not None
        save_profile(
            self.connection,
            assessment_id,
            {**current["profile"], "operator_capacity_adequate": "no"},
        )
        session = self._reviewer_session()
        result = approve_assessment(self.connection, assessment_id, session=session)
        self.assertTrue(result["human_review_approved"])
        self.assertEqual(result["human_review_status"], "approved")
        self.assertFalse(result["is_final"])
        self.assertFalse(result["investor_summary_written"])
        self.assertEqual(result["recommendation"], "do-not-proceed")
        self.assertIn("INSUFFICIENT_DEMAND_EVIDENCE", result["blocking_flags"])
        self.assertIn("INADEQUATE_OPERATOR_CAPACITY", result["blocking_flags"])
        self.assertEqual(result["readiness_status"], "internal")
        self.assertNotEqual(result["readiness_status"], "investor-ready")
        self.assertFalse(result["demand"]["human_review_approved"])
        approval = result["audit"]["approvals"][0]
        self.assertEqual(approval["assessment_id"], assessment_id)
        self.assertEqual(approval["reviewer_identity"], REVIEWER_EMAIL)
        self.assertEqual(approval["authentication_method"], "local-account")
        self.assertTrue(approval["approved_at"])
        self.assertIn("does not grant investor-ready", approval["note"])
        stored = get_assessment(self.connection, assessment_id)
        assert stored is not None
        self.assertTrue(stored["human_review_approved"])
        self.assertEqual(stored["result"]["recommendation"], "do-not-proceed")
        customer = validate_page(stored)
        self.assertIn("Human review status:</strong> pending", customer)
        self.assertIn("Request review", customer)
        self.assertNotIn("Record reviewer approval", customer)
        self.assertNotIn("Sign in as reviewer", customer)
        unsigned = reviewer_page(stored, stored["result"], None)
        self.assertIn("Authentication state:</strong> signed out", unsigned)
        self.assertNotIn("Record reviewer approval", unsigned)
        self.assertNotIn("Sign out", unsigned)
        reviewer = reviewer_page(stored, stored["result"], session)
        self.assertIn("Not a customer feature", reviewer)
        self.assertIn("not production authentication", reviewer)
        self.assertIn(
            f"Authentication state:</strong> signed in as {REVIEWER_EMAIL} (local-account, role reviewer)",
            reviewer,
        )
        self.assertIn("Remaining lifetime:", reviewer)
        self.assertIn("Record reviewer approval", reviewer)
        self.assertIn("Log out", reviewer)
        self.assertIn("Not a customer feature", reviewer)
        baseline = get_assessment(self.connection, BASELINE_ID)
        assert baseline is not None
        with self.assertRaises(PermissionError):
            approve_assessment(self.connection, BASELINE_ID, session=session)
        self.assertFalse(get_assessment(self.connection, BASELINE_ID)["human_review_approved"])
        self.assertEqual(hashlib.sha256(SAMPLE.read_bytes()).hexdigest(), before)
        self.assertEqual(sorted(path.name for path in OUTPUT.iterdir()), output_before)

    def test_sign_in_and_sign_out_write_audit_events(self) -> None:
        assessment_id = create_assessment(
            self.connection,
            business_name="Audit Cafe",
            purpose="startup_feasibility",
            tier="analyze",
        )
        current = get_assessment(self.connection, assessment_id)
        assert current is not None
        save_profile(
            self.connection,
            assessment_id,
            {**current["profile"], "operator_capacity_adequate": "no"},
        )
        analyzed = analyze_record(get_assessment(self.connection, assessment_id))
        save_result(self.connection, assessment_id, analyzed.get("intake"), analyzed)
        before = get_assessment(self.connection, assessment_id)
        assert before is not None
        with self.assertRaises(PermissionError):
            open_account_session(
                self.connection,
                email="missing@pilot.example",
                password="wrong-pass-1",
            )
        self.assertEqual(list_reviewer_events(self.connection, assessment_id), [])
        session = self._reviewer_session()
        events = list_reviewer_events(self.connection, assessment_id)
        self.assertEqual([item["action"] for item in events], ["sign-in"])
        event = events[0]
        self.assertEqual(event["reviewer_identity"], REVIEWER_EMAIL)
        self.assertEqual(event["authentication_method"], "local-account")
        self.assertTrue(event["recorded_at"])
        self.assertEqual(event["session_id"], session_public_id(session["token"]))
        self.assertNotIn("token", event)
        self.assertNotIn(session["token"], json.dumps(events))
        after_sign_in = get_assessment(self.connection, assessment_id)
        assert after_sign_in is not None
        self.assertEqual(after_sign_in["result"]["recommendation"], before["result"]["recommendation"])
        self.assertEqual(after_sign_in["result"]["blocking_flags"], before["result"]["blocking_flags"])
        self.assertEqual(after_sign_in["result"]["readiness_status"], before["result"]["readiness_status"])
        self.assertIn("INSUFFICIENT_DEMAND_EVIDENCE", after_sign_in["result"]["blocking_flags"])
        self.assertEqual(after_sign_in["result"]["readiness_status"], "internal")
        self.assertFalse(after_sign_in["human_review_approved"])
        activity = session_activity(self.connection)
        page = reviewer_page(after_sign_in, after_sign_in["result"], session, activity)
        self.assertIn(f"Last sign-in:</strong> {activity['last_sign_in']}", page)
        self.assertIn("Last sign-out:</strong> none recorded", page)
        self.assertIn("Current session status:</strong> signed in", page)
        self.assertIn("Not a customer feature", page)
        self.assertIn("Record reviewer approval", page)
        close_reviewer_session(self.connection, session["token"])
        events = list_reviewer_events(self.connection, assessment_id)
        self.assertEqual([item["action"] for item in events], ["sign-in", "sign-out"])
        signed_out_event = events[1]
        self.assertEqual(signed_out_event["reviewer_identity"], REVIEWER_EMAIL)
        self.assertEqual(signed_out_event["session_id"], event["session_id"])
        self.assertTrue(signed_out_event["recorded_at"])
        self.assertNotIn(session["token"], json.dumps(events))
        with self.assertRaises(PermissionError):
            approve_assessment(self.connection, assessment_id, session=session)
        activity = session_activity(self.connection)
        closed = reviewer_page(
            after_sign_in,
            after_sign_in["result"],
            reviewer_session_state(self.connection, session["token"]),
            activity,
        )
        self.assertIn("Current session status:</strong> signed out", closed)
        self.assertIn(f"Last sign-out:</strong> {activity['last_sign_out']}", closed)
        self.assertNotIn("Record reviewer approval", closed)
        unchanged = get_assessment(self.connection, assessment_id)
        assert unchanged is not None
        self.assertEqual(unchanged["result"]["recommendation"], "do-not-proceed")
        self.assertIn("INSUFFICIENT_DEMAND_EVIDENCE", unchanged["result"]["blocking_flags"])
        self.assertEqual(unchanged["result"]["readiness_status"], "internal")
        self.assertFalse(unchanged["human_review_approved"])
        with self.assertRaises(PermissionError):
            approve_assessment(self.connection, BASELINE_ID, session=session)
        self.assertFalse(get_assessment(self.connection, BASELINE_ID)["human_review_approved"])

    def test_http_customer_path_stays_forbidden_and_reviewer_path_approves(self) -> None:
        server = make_server(self.db, port=0)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        host, port = server.server_address
        base = f"http://{host}:{port}"
        opener = urllib.request.build_opener(urllib.request.HTTPRedirectHandler)
        try:
            self._expect_status(
                base + "/assessments",
                b"business_name=Cafe&purpose=startup_feasibility&tier=explore&human_review_approved=true",
                403,
            )
            created = urllib.request.Request(
                base + "/assessments",
                data=b"business_name=Review+Cafe&purpose=startup_feasibility&tier=analyze",
                method="POST",
            )
            with opener.open(created) as response:
                assessment_url = response.geturl().rstrip("/")
            assessment_id = assessment_url.rsplit("/", 1)[-1]
            self._expect_status(
                f"{base}/reviewer/assessments/{assessment_id}/approve",
                b"reviewer_identity=Local+prototype+reviewer&reviewer_gate=local-prototype-reviewer&human_review_approved=true",
                403,
            )
            self._expect_status(
                f"{base}/reviewer/assessments/{assessment_id}/approve",
                b"reviewer_gate=local-prototype-reviewer",
                403,
            )
            self._expect_status(
                base + "/login",
                urllib.parse.urlencode(
                    {
                        "email": REVIEWER_EMAIL,
                        "password": "wrong-pass-1",
                        "next": f"/reviewer/assessments/{assessment_id}",
                    }
                ).encode(),
                403,
            )
            customer_cookie = self._sign_in(
                base,
                f"/reviewer/assessments/{assessment_id}",
                email=CUSTOMER_EMAIL,
                password=CUSTOMER_PASSWORD,
                role="customer",
            )
            self._expect_status_with_cookie(
                f"{base}/reviewer/assessments/{assessment_id}/approve",
                b"",
                customer_cookie,
                403,
                "customer account",
            )
            with urllib.request.urlopen(f"{base}/reviewer/assessments/{assessment_id}") as response:
                unsigned = response.read().decode("utf-8")
            self.assertIn("signed out", unsigned)
            self.assertNotIn("Record reviewer approval", unsigned)
            cookie = self._sign_in(base, f"/reviewer/assessments/{assessment_id}")
            with urllib.request.urlopen(assessment_url + "/audit") as response:
                before_audit = json.loads(response.read().decode("utf-8"))
            self.assertEqual(before_audit["recommendation"]["draft_recommendation"], "do-not-proceed")
            self.assertIn("INSUFFICIENT_DEMAND_EVIDENCE", before_audit["recommendation"]["blocking_flags"])
            self.assertEqual(before_audit["investor_readiness"]["status"], "internal")
            self.assertFalse(before_audit["human_review_approved"])
            sign_in_events = [item for item in before_audit["reviewer_events"] if item["action"] == "sign-in"]
            self.assertTrue(sign_in_events)
            self.assertEqual(sign_in_events[-1]["reviewer_identity"], REVIEWER_EMAIL)
            self.assertEqual(sign_in_events[-1]["authentication_method"], "local-account")
            self.assertTrue(sign_in_events[-1]["recorded_at"])
            self.assertEqual(len(sign_in_events[-1]["session_id"]), 12)
            self.assertNotIn(cookie.split("=", 1)[1], json.dumps(before_audit))
            approved = urllib.request.Request(
                f"{base}/reviewer/assessments/{assessment_id}/approve",
                data=b"",
                method="POST",
                headers={"Cookie": cookie},
            )
            with opener.open(approved) as response:
                page = response.read().decode("utf-8")
            self.assertIn("Not a customer feature", page)
            self.assertIn(f"signed in as {REVIEWER_EMAIL} (local-account, role reviewer)", page)
            self.assertIn("Remaining lifetime:", page)
            self.assertIn("Log out", page)
            self.assertIn("Not a customer feature", page)
            self.assertIn("human_review_approved:</strong> true", page)
            self.assertIn("INSUFFICIENT_DEMAND_EVIDENCE", page)
            self.assertNotIn("Investor readiness:</strong> investor-ready", page)
            with urllib.request.urlopen(assessment_url + "/validate") as response:
                validate = response.read().decode("utf-8")
            self.assertIn("Request review", validate)
            self.assertIn("Human review status:</strong> pending", validate)
            self.assertNotIn("Record reviewer approval", validate)
            with urllib.request.urlopen(assessment_url + "/results") as response:
                results = response.read().decode("utf-8")
            self.assertIn("Human review status:</strong> approved", results)
            self.assertIn("INSUFFICIENT_DEMAND_EVIDENCE:</strong> present", results)
            self.assertIn("Investor readiness:</strong> internal", results)
            with urllib.request.urlopen(assessment_url + "/audit") as response:
                audit = json.loads(response.read().decode("utf-8"))
            self.assertTrue(audit["human_review_approved"])
            self.assertFalse(audit["investor_summary_written"])
            self.assertEqual(audit["investor_readiness"]["status"], "internal")
            self.assertFalse(audit["investor_readiness"]["investor_ready"])
            self.assertIn("INSUFFICIENT_DEMAND_EVIDENCE", audit["recommendation"]["blocking_flags"])
            self.assertEqual(audit["approvals"][0]["assessment_id"], assessment_id)
            self.assertEqual(audit["approvals"][0]["reviewer_identity"], REVIEWER_EMAIL)
            self.assertEqual(audit["approvals"][0]["authentication_method"], "local-account")
            self.assertEqual(
                audit["recommendation"]["draft_recommendation"],
                before_audit["recommendation"]["draft_recommendation"],
            )
            self.assertEqual(
                audit["recommendation"]["blocking_flags"],
                before_audit["recommendation"]["blocking_flags"],
            )
            self.assertEqual(audit["investor_readiness"]["status"], "internal")
            actions = [item["action"] for item in audit["reviewer_events"]]
            self.assertIn("sign-in", actions)
            self.assertIn("approve", actions)
            self.assertNotIn(cookie.split("=", 1)[1], json.dumps(audit))
            with urllib.request.urlopen(base + "/assessments/rugd-intelligence-baseline/audit") as response:
                baseline_audit = json.loads(response.read().decode("utf-8"))
            self.assertFalse(baseline_audit["human_review_approved"])
            self.assertEqual(baseline_audit["approvals"], [])
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=3)

    def test_expired_and_signed_out_sessions_cannot_approve(self) -> None:
        assessment_id = create_assessment(
            self.connection,
            business_name="Lifetime Cafe",
            purpose="startup_feasibility",
            tier="analyze",
        )
        session = self._reviewer_session()
        self.connection.execute(
            "UPDATE reviewer_sessions SET expires_at = ? WHERE token = ?",
            ("2020-01-01T00:00:00+00:00", session_storage_key(session["token"])),
        )
        self.connection.commit()
        with self.assertRaises(PermissionError):
            approve_assessment(self.connection, assessment_id, session=session)
        stored = get_assessment(self.connection, assessment_id)
        assert stored is not None
        self.assertFalse(stored["human_review_approved"])
        expired = reviewer_session_state(self.connection, session["token"])
        expired_page = reviewer_page(stored, None, expired)
        self.assertIn("Authentication state:</strong> expired", expired_page)
        self.assertNotIn("Record reviewer approval", expired_page)
        self.assertIn("Log out", expired_page)
        self.assertIn("Not a customer feature", expired_page)
        close_reviewer_session(self.connection, session["token"])
        with self.assertRaises(PermissionError):
            approve_assessment(self.connection, assessment_id, session=session)
        signed_out = reviewer_session_state(self.connection, session["token"])
        self.assertEqual(signed_out["state"], "signed-out")
        fresh = self._reviewer_session()
        result = approve_assessment(self.connection, assessment_id, session=fresh)
        self.assertTrue(result["human_review_approved"])
        self.assertIn("INSUFFICIENT_DEMAND_EVIDENCE", result["blocking_flags"])
        self.assertEqual(result["readiness_status"], "internal")
        self.assertFalse(result["investor_summary_written"])
        approval = result["audit"]["approvals"][0]
        self.assertEqual(approval["reviewer_identity"], REVIEWER_EMAIL)
        self.assertEqual(approval["authentication_method"], "local-account")
        self.assertTrue(approval["approved_at"])
        with self.assertRaises(PermissionError):
            approve_assessment(self.connection, BASELINE_ID, session=fresh)
        self.assertFalse(get_assessment(self.connection, BASELINE_ID)["human_review_approved"])

        server = make_server(self.db, port=0)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        host, port = server.server_address
        base = f"http://{host}:{port}"
        try:
            self._expect_status(
                base + "/assessments",
                b"business_name=Cafe&human_review_approved=true",
                403,
            )
            cookie = self._sign_in(base, f"/reviewer/assessments/{assessment_id}")
            token = cookie.split("=", 1)[1]
            self.connection.execute(
                "UPDATE reviewer_sessions SET expires_at = ? WHERE token = ?",
                ("2020-01-01T00:00:00+00:00", session_storage_key(token)),
            )
            self.connection.commit()
            with urllib.request.urlopen(
                urllib.request.Request(
                    f"{base}/reviewer/assessments/{assessment_id}",
                    headers={"Cookie": cookie},
                )
            ) as response:
                expired_http = response.read().decode("utf-8")
            self.assertIn("Authentication state:</strong> expired", expired_http)
            self.assertNotIn("Record reviewer approval", expired_http)
            self._expect_status_with_cookie(
                f"{base}/reviewer/assessments/{assessment_id}/approve",
                b"",
                cookie,
                403,
                "expired",
            )
            cleared = self._sign_out(base, cookie, f"/reviewer/assessments/{assessment_id}")
            self.assertIn("Max-Age=0", cleared)
            self._expect_status_with_cookie(
                f"{base}/reviewer/assessments/{assessment_id}/approve",
                b"",
                cookie,
                403,
                "signed out",
            )
            with urllib.request.urlopen(f"{base}/assessments/{assessment_id}/audit") as response:
                trail = json.loads(response.read().decode("utf-8"))
            trail_actions = [item["action"] for item in trail["reviewer_events"]]
            self.assertIn("sign-in", trail_actions)
            self.assertIn("sign-out", trail_actions)
            self.assertIn("INSUFFICIENT_DEMAND_EVIDENCE", trail["recommendation"]["blocking_flags"])
            self.assertEqual(trail["investor_readiness"]["status"], "internal")
            self.assertNotEqual(trail["investor_readiness"]["status"], "investor-ready")
            self.assertNotIn(token, json.dumps(trail))
            self._expect_status_with_cookie(
                f"{base}/reviewer/assessments/{BASELINE_ID}/approve",
                b"",
                self._sign_in(base, f"/reviewer/assessments/{BASELINE_ID}"),
                403,
                "official baseline",
            )
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=3)

    def _reviewer_session(self):
        from app.accounts import bootstrap_reviewer

        bootstrap_reviewer(
            self.connection,
            email=REVIEWER_EMAIL,
            password=REVIEWER_PASSWORD,
        )
        return open_account_session(
            self.connection,
            email=REVIEWER_EMAIL,
            password=REVIEWER_PASSWORD,
        )

    def _sign_in(
        self,
        base: str,
        next_path: str,
        email: str = REVIEWER_EMAIL,
        password: str = REVIEWER_PASSWORD,
        role: str = "reviewer",
    ) -> str:
        if role == "reviewer":
            from app.accounts import bootstrap_reviewer

            bootstrap_reviewer(self.connection, email=email, password=password)
        else:
            self._register(base, email, password, role)
        return self._login(base, next_path, email, password)

    def _register(self, base: str, email: str, password: str, role: str) -> None:
        request = urllib.request.Request(
            base + "/register",
            data=urllib.parse.urlencode(
                {
                    "email": email,
                    "password": password,
                    "password_confirm": password,
                    "role": role,
                }
            ).encode(),
            method="POST",
        )
        try:
            urllib.request.urlopen(request)
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8")
            self.assertEqual(exc.code, 403)
            self.assertIn("already registered", body)

    def _login(self, base: str, next_path: str, email: str, password: str) -> str:
        class NoRedirect(urllib.request.HTTPRedirectHandler):
            def redirect_request(self, req, fp, code, msg, headers, newurl):
                return None

        opener = urllib.request.build_opener(NoRedirect)
        request = urllib.request.Request(
            base + "/login",
            data=urllib.parse.urlencode(
                {"email": email, "password": password, "next": next_path}
            ).encode(),
            method="POST",
        )
        try:
            opener.open(request)
        except urllib.error.HTTPError as exc:
            self.assertEqual(exc.code, 303)
            cookie = exc.headers.get("Set-Cookie") or ""
        else:
            self.fail("sign-in should redirect")
        self.assertTrue(cookie.startswith("rugd_session="))
        self.assertIn("HttpOnly", cookie)
        return cookie.split(";", 1)[0]

    def _sign_out(self, base: str, cookie: str, next_path: str) -> str:
        class NoRedirect(urllib.request.HTTPRedirectHandler):
            def redirect_request(self, req, fp, code, msg, headers, newurl):
                return None

        opener = urllib.request.build_opener(NoRedirect)
        request = urllib.request.Request(
            base + "/reviewer/session/sign-out",
            data=urllib.parse.urlencode({"next": next_path}).encode(),
            method="POST",
            headers={"Cookie": cookie},
        )
        try:
            opener.open(request)
        except urllib.error.HTTPError as exc:
            self.assertEqual(exc.code, 303)
            return exc.headers.get("Set-Cookie") or ""
        self.fail("sign-out should redirect")
        return ""

    def _expect_status_with_cookie(
        self,
        url: str,
        body: bytes,
        cookie: str,
        status: int,
        text: str,
    ) -> None:
        request = urllib.request.Request(url, data=body, method="POST", headers={"Cookie": cookie})
        try:
            urllib.request.urlopen(request)
        except urllib.error.HTTPError as exc:
            self.assertEqual(exc.code, status)
            self.assertIn(text, exc.read().decode("utf-8"))
            return
        self.fail(f"expected HTTP {status}")

    def _expect_status(self, url: str, body: bytes, status: int) -> None:
        request = urllib.request.Request(url, data=body, method="POST")
        try:
            urllib.request.urlopen(request)
        except urllib.error.HTTPError as exc:
            self.assertEqual(exc.code, status)
            return
        self.fail(f"expected HTTP {status}")


if __name__ == "__main__":
    unittest.main()

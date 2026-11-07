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

from app.pages import reviewer_page, validate_page
from app.review import (
    PROTOTYPE_REVIEWER_IDENTITY,
    PROTOTYPE_REVIEWER_PASSPHRASE,
    approve_assessment,
    open_reviewer_session,
)
from app.server import make_server
from app.store import BASELINE_ID, SAMPLE, connect, create_assessment, get_assessment, save_profile, seed

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
        session = open_reviewer_session(
            self.connection,
            reviewer_identity=PROTOTYPE_REVIEWER_IDENTITY,
            reviewer_passphrase=PROTOTYPE_REVIEWER_PASSPHRASE,
        )
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
        self.assertEqual(approval["reviewer_identity"], "Local prototype reviewer")
        self.assertEqual(approval["authentication_method"], "local-session")
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
        self.assertIn("Authentication state:</strong> not signed in", unsigned)
        self.assertNotIn("Record reviewer approval", unsigned)
        reviewer = reviewer_page(stored, stored["result"], session)
        self.assertIn("Not a customer feature", reviewer)
        self.assertIn("not production authentication", reviewer)
        self.assertIn("Authentication state:</strong> signed in as Local prototype reviewer (local-session)", reviewer)
        self.assertIn("Record reviewer approval", reviewer)
        baseline = get_assessment(self.connection, BASELINE_ID)
        assert baseline is not None
        with self.assertRaises(PermissionError):
            approve_assessment(self.connection, BASELINE_ID, session=session)
        self.assertFalse(get_assessment(self.connection, BASELINE_ID)["human_review_approved"])
        self.assertEqual(hashlib.sha256(SAMPLE.read_bytes()).hexdigest(), before)
        self.assertEqual(sorted(path.name for path in OUTPUT.iterdir()), output_before)

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
                base + "/reviewer/session",
                urllib.parse.urlencode(
                    {
                        "reviewer_identity": PROTOTYPE_REVIEWER_IDENTITY,
                        "reviewer_passphrase": "wrong",
                        "next": f"/reviewer/assessments/{assessment_id}",
                    }
                ).encode(),
                403,
            )
            with urllib.request.urlopen(f"{base}/reviewer/assessments/{assessment_id}") as response:
                unsigned = response.read().decode("utf-8")
            self.assertIn("not signed in", unsigned)
            self.assertNotIn("Record reviewer approval", unsigned)
            cookie = self._sign_in(base, f"/reviewer/assessments/{assessment_id}")
            approved = urllib.request.Request(
                f"{base}/reviewer/assessments/{assessment_id}/approve",
                data=b"",
                method="POST",
                headers={"Cookie": cookie},
            )
            with opener.open(approved) as response:
                page = response.read().decode("utf-8")
            self.assertIn("Not a customer feature", page)
            self.assertIn("signed in as Local prototype reviewer (local-session)", page)
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
            self.assertEqual(audit["approvals"][0]["reviewer_identity"], "Local prototype reviewer")
            self.assertEqual(audit["approvals"][0]["authentication_method"], "local-session")
            with urllib.request.urlopen(base + "/assessments/rugd-intelligence-baseline/audit") as response:
                baseline_audit = json.loads(response.read().decode("utf-8"))
            self.assertFalse(baseline_audit["human_review_approved"])
            self.assertEqual(baseline_audit["approvals"], [])
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=3)

    def _sign_in(self, base: str, next_path: str) -> str:
        class NoRedirect(urllib.request.HTTPRedirectHandler):
            def redirect_request(self, req, fp, code, msg, headers, newurl):
                return None

        opener = urllib.request.build_opener(NoRedirect)
        request = urllib.request.Request(
            base + "/reviewer/session",
            data=urllib.parse.urlencode(
                {
                    "reviewer_identity": PROTOTYPE_REVIEWER_IDENTITY,
                    "reviewer_passphrase": PROTOTYPE_REVIEWER_PASSPHRASE,
                    "next": next_path,
                }
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
        self.assertTrue(cookie.startswith("rugd_reviewer="))
        return cookie.split(";", 1)[0]

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

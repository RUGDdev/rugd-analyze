"""The HTML audit page is a read-only view of the existing result and reviewer trail."""

import hashlib
import json
import tempfile
import threading
import unittest
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from app.pages import audit_html_page
from app.accounts import register_account
from app.review import approve_assessment, open_account_session
from app.server import make_server
from app.store import (
    BASELINE_ID,
    SAMPLE,
    connect,
    create_assessment,
    get_assessment,
    list_reviewer_events,
    save_profile,
    seed,
    session_public_id,
)

ROOT = Path(__file__).resolve().parent.parent
OUTPUT = ROOT / "reports" / "output"


class TestHtmlAuditPage(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.db = Path(self.directory.name) / "analyze.sqlite"
        self.connection = connect(self.db)
        seed(self.connection)

    def tearDown(self) -> None:
        self.connection.close()
        self.directory.cleanup()

    def test_approved_audit_page_stays_read_only(self) -> None:
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
        register_account(
            self.connection,
            email="reviewer@pilot.example",
            password="reviewer-pass-1",
            role="reviewer",
        )
        session = open_account_session(
            self.connection,
            email="reviewer@pilot.example",
            password="reviewer-pass-1",
        )
        result = approve_assessment(self.connection, assessment_id, session=session)
        stored = get_assessment(self.connection, assessment_id)
        assert stored is not None
        events = list_reviewer_events(self.connection, assessment_id)
        page = audit_html_page(stored, result, events)
        self.assertIn("sign-in", page)
        self.assertIn("approve", page)
        self.assertIn(session_public_id(session["token"]), page)
        self.assertNotIn(session["token"], page)
        self.assertIn("Audit view", page)
        self.assertIn("Read only", page)
        self.assertIn("Recommendation:</strong> do-not-proceed", page)
        self.assertIn("INSUFFICIENT_DEMAND_EVIDENCE:</strong> present", page)
        self.assertIn("Investor readiness:</strong> internal", page)
        self.assertIn("Human review status:</strong> approved", page)
        self.assertIn("does not by itself mark this assessment investor-ready", page)
        self.assertNotIn("Investor readiness:</strong> investor-ready", page)
        self.assertNotIn("<form", page)
        self.assertNotIn("Record reviewer approval", page)
        self.assertIn("prototype-grade", page)

    def test_http_html_audit_does_not_change_the_assessment(self) -> None:
        before_sample = hashlib.sha256(SAMPLE.read_bytes()).hexdigest()
        output_before = sorted(path.name for path in OUTPUT.iterdir())
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
                data=b"business_name=Audit+Cafe&purpose=startup_feasibility&tier=analyze",
                method="POST",
            )
            with opener.open(created) as response:
                assessment_url = response.geturl().rstrip("/")
            assessment_id = assessment_url.rsplit("/", 1)[-1]
            with urllib.request.urlopen(assessment_url + "/audit/html") as response:
                early = response.read().decode("utf-8")
            self.assertIsNone(get_assessment(self.connection, assessment_id)["result"])
            self.assertIn("Audit view", early)
            self.assertIn("Read only", early)
            self.assertNotIn("<form", early)
            analyzed = urllib.request.Request(
                assessment_url + "/analyze",
                data=b"business_name=Audit+Cafe&purpose=startup_feasibility&tier=analyze",
                method="POST",
            )
            with opener.open(analyzed) as response:
                results = response.read().decode("utf-8")
            stored = get_assessment(self.connection, assessment_id)
            assert stored is not None
            stamp = stored["updated_at"]
            recommendation = stored["result"]["recommendation"]
            flags = list(stored["result"]["blocking_flags"])
            with urllib.request.urlopen(assessment_url + "/audit/html") as response:
                page = response.read().decode("utf-8")
            again = get_assessment(self.connection, assessment_id)
            assert again is not None
            self.assertEqual(again["updated_at"], stamp)
            self.assertEqual(again["result"]["recommendation"], recommendation)
            self.assertEqual(again["result"]["blocking_flags"], flags)
            self.assertFalse(again["human_review_approved"])
            self.assertIn("Recommendation:</strong> do-not-proceed", page)
            self.assertIn("INSUFFICIENT_DEMAND_EVIDENCE:</strong> present", page)
            self.assertIn("Investor readiness:</strong> internal", page)
            self.assertIn("Human review status:</strong> pending", page)
            self.assertIn("placeholder", page)
            self.assertIn("Draft", page)
            self.assertIn("prototype-grade", page)
            self.assertNotIn("Investor readiness:</strong> investor-ready", page)
            self.assertNotIn("<form", page)
            self.assertNotIn("Record reviewer approval", page)
            self.assertIn(f"/assessments/{assessment_id}/audit/html", results)
            with urllib.request.urlopen(assessment_url + "/report") as response:
                report = response.read().decode("utf-8")
                self.assertIn("text/markdown", response.headers.get("Content-Type", ""))
            self.assertIn(f"HTML audit view: /assessments/{assessment_id}/audit/html", report)
            self.assertIn("do-not-proceed", report)
            with urllib.request.urlopen(base + f"/reviewer/assessments/{assessment_id}") as response:
                reviewer = response.read().decode("utf-8")
            self.assertIn(f"/assessments/{assessment_id}/audit/html", reviewer)
            with urllib.request.urlopen(assessment_url + "/audit") as response:
                self.assertEqual(response.headers.get_content_type(), "application/json")
                audit = json.loads(response.read().decode("utf-8"))
            self.assertIn("recommendation", audit)
            self.assertIn("reviewer_events", audit)
            self.assertIn("human_review_approved", audit)
            self.assertIn("investor_readiness", audit)
            self.assertFalse(audit["human_review_approved"])
            self.assertEqual(audit["investor_readiness"]["status"], "internal")
            self.assertIn("INSUFFICIENT_DEMAND_EVIDENCE", audit["recommendation"]["blocking_flags"])
            final = get_assessment(self.connection, assessment_id)
            assert final is not None
            self.assertEqual(final["updated_at"], stamp)
            with urllib.request.urlopen(base + f"/assessments/{BASELINE_ID}/audit/html") as response:
                baseline = response.read().decode("utf-8")
            baseline_record = get_assessment(self.connection, BASELINE_ID)
            assert baseline_record is not None
            self.assertIsNone(baseline_record["result"])
            self.assertFalse(baseline_record["human_review_approved"])
            self.assertIn("Recommendation:</strong> do-not-proceed", baseline)
            self.assertIn("INSUFFICIENT_DEMAND_EVIDENCE:</strong> present", baseline)
            self.assertIn("Investor readiness:</strong> internal", baseline)
            self.assertIn("Human review status:</strong> pending", baseline)
            self.assertIn("Draft", baseline)
            self.assertIn("placeholder", baseline)
            self.assertIn("prototype-grade", baseline)
            self.assertNotIn("Investor readiness:</strong> investor-ready", baseline)
            self.assertNotIn("<form", baseline)
            self.assertNotIn("Record reviewer approval", baseline)
            self._expect_status(assessment_url + "/audit/html", b"", 404)
            self.assertFalse(get_assessment(self.connection, assessment_id)["human_review_approved"])
            self.assertEqual(hashlib.sha256(SAMPLE.read_bytes()).hexdigest(), before_sample)
            self.assertEqual(sorted(path.name for path in OUTPUT.iterdir()), output_before)
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=3)

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

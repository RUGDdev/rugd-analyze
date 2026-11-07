"""Local Analyze app. The 0.1 baseline recommendation stays unchanged."""

import hashlib
import json
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from pathlib import Path

from app.analysis import analyze_record
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
)

ROOT = Path(__file__).resolve().parent.parent
BASELINE_FILE = ROOT / "reports" / "output" / "rugd-intelligence-draft.md"


class TestAnalyzeApp(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.db = Path(self.directory.name) / "analyze.sqlite"
        self.connection = connect(self.db)
        seed(self.connection)

    def tearDown(self) -> None:
        self.connection.close()
        self.directory.cleanup()

    def test_baseline_recommendation_is_preserved(self) -> None:
        before = hashlib.sha256(SAMPLE.read_bytes()).hexdigest()
        record = get_assessment(self.connection, BASELINE_ID)
        assert record is not None
        result = analyze_record(record)
        self.assertEqual(result["recommendation"], "do-not-proceed")
        self.assertIn("INSUFFICIENT_DEMAND_EVIDENCE", result["blocking_flags"])
        self.assertEqual(result["readiness_status"], "internal")
        self.assertEqual(result["human_review_status"], "pending")
        self.assertFalse(result["human_review_approved"])
        self.assertFalse(result["is_final"])
        self.assertIsNone(result["audit"]["recommendation"]["overall_feasibility_score"])
        self.assertEqual(hashlib.sha256(SAMPLE.read_bytes()).hexdigest(), before)
        self.assertIn("do-not-proceed", BASELINE_FILE.read_text(encoding="utf-8"))

    def test_customer_cannot_approve_or_edit_the_baseline(self) -> None:
        with self.assertRaises(PermissionError):
            save_profile(
                self.connection,
                BASELINE_ID,
                {"human_review_approved": True, "business_name": "Changed"},
            )
        record = get_assessment(self.connection, BASELINE_ID)
        assert record is not None
        self.assertFalse(record["human_review_approved"])
        self.assertEqual(record["business_name"], "RUGD Intelligence")

    def test_draft_save_and_tier_change_keep_the_result(self) -> None:
        assessment_id = create_assessment(
            self.connection,
            business_name="Draft Cafe",
            purpose="startup_feasibility",
            tier="explore",
        )
        save_profile(
            self.connection,
            assessment_id,
            {
                "business_name": "Draft Cafe",
                "purpose": "startup_feasibility",
                "tier": "explore",
                "construction_cost": "100000",
                "hypothetical": True,
            },
        )
        saved = get_assessment(self.connection, assessment_id)
        assert saved is not None
        self.assertEqual(saved["profile"]["construction_cost"], "100000")
        result = analyze_record(saved)
        from app.store import save_result

        save_result(self.connection, assessment_id, result.get("intake"), result)
        save_profile(
            self.connection,
            assessment_id,
            {**saved["profile"], "tier": "partner"},
        )
        again = get_assessment(self.connection, assessment_id)
        assert again is not None
        self.assertEqual(again["tier"], "partner")
        self.assertEqual(again["result"]["recommendation"], result["recommendation"])
        self.assertFalse(again["human_review_approved"])

    def test_restaurant_seed_is_hypothetical_and_not_verified(self) -> None:
        record = get_assessment(self.connection, RESTAURANT_ID)
        assert record is not None
        self.assertTrue(record["hypothetical"])
        self.assertEqual(record["profile"]["industry"], "Restaurant")
        self.assertEqual(record["profile"]["construction_cost"], "100000")
        self.assertEqual(record["profile"]["stage"], "Idea")
        result = analyze_record(record)
        self.assertTrue(any("Insufficient" in item for item in result["missing"]))
        self.assertNotEqual(result["recommendation"], "go")

    def test_http_journey_refuses_customer_approval(self) -> None:
        server = make_server(self.db, port=0)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        host, port = server.server_address
        base = f"http://{host}:{port}"
        try:
            with urllib.request.urlopen(base + "/") as response:
                page = response.read().decode("utf-8")
            self.assertIn("RUGD", page)
            self.assertIn("Hypothetical Restaurant Startup", page)
            with urllib.request.urlopen(base + "/market") as response:
                market = response.read().decode("utf-8")
            self.assertIn("Hypothetical demonstration", market)
            request = urllib.request.Request(
                base + "/assessments",
                data=b"business_name=Journey+Cafe&purpose=startup_feasibility&tier=explore&human_review_approved=true",
                method="POST",
            )
            try:
                urllib.request.urlopen(request)
                self.fail("approval field should be refused")
            except urllib.error.HTTPError as exc:
                self.assertEqual(exc.code, 403)
            opener = urllib.request.build_opener(urllib.request.HTTPRedirectHandler)
            created = urllib.request.Request(
                base + "/assessments",
                data=b"business_name=Journey+Cafe&purpose=startup_feasibility&tier=explore",
                method="POST",
            )
            with opener.open(created) as response:
                body = response.read().decode("utf-8")
            self.assertIn("Journey Cafe", body)
            self.assertIn("Save draft", body)
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=3)


if __name__ == "__main__":
    unittest.main()

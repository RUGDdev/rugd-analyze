"""Empty states stay honest, and JSON export omits session secrets."""

import hashlib
import json
import tempfile
import threading
import unittest
import urllib.request
from pathlib import Path

from app.pages import dashboard, results_page
from app.review import open_reviewer_session
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
from app.review import PROTOTYPE_REVIEWER_IDENTITY, PROTOTYPE_REVIEWER_PASSPHRASE

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
        session = open_reviewer_session(
            self.connection,
            reviewer_identity=PROTOTYPE_REVIEWER_IDENTITY,
            reviewer_passphrase=PROTOTYPE_REVIEWER_PASSPHRASE,
        )
        start_reviewer_session(
            self.connection,
            token="second-raw-token",
            reviewer_identity=PROTOTYPE_REVIEWER_IDENTITY,
            authentication_method="local-session",
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

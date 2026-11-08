"""Report and audit downloads repeat the existing views, and the print view keeps status."""

import hashlib
import json
import tempfile
import threading
import unittest
import urllib.request
from pathlib import Path

from app.analysis import analyze_record
from app.server import make_server
from app.store import BASELINE_ID, RESTAURANT_ID, SAMPLE, connect, get_assessment, save_result, seed

ROOT = Path(__file__).resolve().parent.parent
OUTPUT = ROOT / "reports" / "output"


class TestDownloadsAndPrint(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.db = Path(self.directory.name) / "analyze.sqlite"
        self.connection = connect(self.db)
        seed(self.connection)

    def tearDown(self) -> None:
        self.connection.close()
        self.directory.cleanup()

    def test_downloads_match_views_and_print_keeps_sections(self) -> None:
        before = hashlib.sha256(SAMPLE.read_bytes()).hexdigest()
        output_before = sorted(path.name for path in OUTPUT.iterdir())
        record = get_assessment(self.connection, RESTAURANT_ID)
        assert record is not None
        result = analyze_record(record)
        save_result(self.connection, RESTAURANT_ID, result.get("intake"), result)
        stored = get_assessment(self.connection, RESTAURANT_ID)
        assert stored is not None
        stamp = stored["updated_at"]
        server = make_server(self.db, port=0)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        host, port = server.server_address
        base = f"http://{host}:{port}/assessments/{RESTAURANT_ID}"
        try:
            with urllib.request.urlopen(base + "/report") as response:
                report = response.read()
                self.assertIn("text/markdown", response.headers.get("Content-Type", ""))
                self.assertIsNone(response.headers.get("Content-Disposition"))
            with urllib.request.urlopen(base + "/report/download") as response:
                downloaded = response.read()
                disposition = response.headers.get("Content-Disposition", "")
                self.assertIn("text/markdown", response.headers.get("Content-Type", ""))
            self.assertEqual(downloaded, report)
            self.assertIn("attachment;", disposition)
            self.assertIn("Hypothetical-Restaurant-Startup-", disposition)
            self.assertRegex(disposition, r"\d{4}-\d{2}-\d{2}-report\.md")
            with urllib.request.urlopen(base + "/audit") as response:
                audit_bytes = response.read()
                self.assertEqual(response.headers.get_content_type(), "application/json")
            with urllib.request.urlopen(base + "/audit/download") as response:
                audit_download = response.read()
                audit_disposition = response.headers.get("Content-Disposition", "")
                self.assertEqual(response.headers.get_content_type(), "application/json")
            self.assertEqual(audit_download, audit_bytes)
            self.assertEqual(json.loads(audit_download)["recommendation"]["draft_recommendation"], "do-not-proceed")
            self.assertIn("attachment;", audit_disposition)
            self.assertRegex(audit_disposition, r"Hypothetical-Restaurant-Startup-\d{4}-\d{2}-\d{2}-audit\.json")
            with urllib.request.urlopen(base + "/results") as response:
                results = response.read().decode("utf-8")
            self.assertIn("Download Markdown report", results)
            self.assertIn("Download JSON audit", results)
            with urllib.request.urlopen(base + "/audit/print") as response:
                printed = response.read().decode("utf-8")
                self.assertIn("text/html", response.headers.get("Content-Type", ""))
            self.assertIn('class="print-view"', printed)
            self.assertIn("@media print", printed)
            self.assertIn("Recommendation:</strong> do-not-proceed", printed)
            self.assertIn("INSUFFICIENT_DEMAND_EVIDENCE:</strong> present", printed)
            self.assertIn("Investor readiness:</strong> internal", printed)
            self.assertIn("Human review status:</strong> pending", printed)
            self.assertIn("Reviewer events", printed)
            self.assertIn("Limitations", printed)
            self.assertIn("Demonstration data is not real market research", printed)
            self.assertIn('class="limitations"', printed)
            self.assertNotIn(".limitations { display: none", printed)
            self.assertNotIn("<form", printed)
            self.assertNotIn("Investor readiness:</strong> investor-ready", printed)
            again = get_assessment(self.connection, RESTAURANT_ID)
            assert again is not None
            self.assertEqual(again["updated_at"], stamp)
            self.assertEqual(again["result"]["recommendation"], "do-not-proceed")
            self.assertFalse(again["human_review_approved"])
            with urllib.request.urlopen(f"http://{host}:{port}/assessments/{BASELINE_ID}/audit/print") as response:
                baseline_print = response.read().decode("utf-8")
            self.assertIn("Official baseline", baseline_print)
            self.assertIn("INSUFFICIENT_DEMAND_EVIDENCE:</strong> present", baseline_print)
            self.assertIsNone(get_assessment(self.connection, BASELINE_ID)["result"])
            self.assertFalse(get_assessment(self.connection, BASELINE_ID)["human_review_approved"])
            self.assertEqual(hashlib.sha256(SAMPLE.read_bytes()).hexdigest(), before)
            self.assertEqual(sorted(path.name for path in OUTPUT.iterdir()), output_before)
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=3)


if __name__ == "__main__":
    unittest.main()

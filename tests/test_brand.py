"""The customer shell is branded and still shows the baseline safeguards."""

import hashlib
import tempfile
import threading
import unittest
import urllib.request
from pathlib import Path

from app.analysis import analyze_record
from app.pages import (
    audit_html_page,
    dashboard,
    market_page,
    market_pulse_page,
    results_page,
)
from app.server import make_server
from app.store import BASELINE_ID, SAMPLE, connect, get_assessment, seed

ROOT = Path(__file__).resolve().parent.parent
LOGO = ROOT / "app" / "static" / "rugd-logo.png"
NOTE = "This screen does not grant investor-ready status."
NAV_LABELS = (
    "Dashboard",
    "Explore",
    "Analyze",
    "Validate (demonstration)",
    "Partner (demonstration)",
    "My Assessments",
    "Market Intelligence (demonstration)",
    "Reports",
    "Settings",
)


class TestBrandShell(unittest.TestCase):
    def test_sidebar_pages_keep_warnings_and_the_baseline(self) -> None:
        before = hashlib.sha256(SAMPLE.read_bytes()).hexdigest()
        self.assertTrue(LOGO.is_file())
        self.assertEqual(LOGO.read_bytes()[:8], b"\x89PNG\r\n\x1a\n")
        directory = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        connection = connect(Path(directory.name) / "analyze.sqlite")
        try:
            seed(connection)
            baseline = get_assessment(connection, BASELINE_ID)
            assert baseline is not None
            result = analyze_record(baseline)
            pages = {
                "dashboard": dashboard([baseline]),
                "results": results_page(baseline, result),
                "market": market_page(),
                "pulse": market_pulse_page(),
                "audit": audit_html_page(baseline, result),
            }
            for name, page in pages.items():
                self.assertIn('class="sidebar"', page, name)
                self.assertIn('src="/static/rugd-logo.png"', page, name)
                self.assertIn('alt="RUGD Intelligence"', page, name)
                self.assertIn(NOTE, page, name)
                self.assertIn("#263746", page, name)
                self.assertIn("#A88958", page, name)
                self.assertIn("#F5F2EB", page, name)
                for label in NAV_LABELS:
                    self.assertIn(label, page, name)
                self.assertNotIn("Investor readiness:</strong> investor-ready", page, name)
                self.assertNotIn("Monitoring active: true", page, name)
            self.assertIn('href="/" class="active"', pages["dashboard"])
            self.assertIn('href="/analyze" class="active"', pages["results"])
            self.assertIn('href="/market" class="active"', pages["market"])
            self.assertIn('href="/market-pulse" class="active"', pages["pulse"])
            self.assertIn('href="/reports" class="active"', pages["audit"])
            self.assertIn("Recommendation:</strong> do-not-proceed", pages["results"])
            self.assertIn("INSUFFICIENT_DEMAND_EVIDENCE", pages["results"])
            self.assertIn("Investor readiness:</strong> internal", pages["results"])
            self.assertIn("human_review_approved:</strong> false", pages["results"])
            self.assertEqual(result["recommendation"], "do-not-proceed")
            self.assertIn("INSUFFICIENT_DEMAND_EVIDENCE", result["blocking_flags"])
            self.assertEqual(result["readiness_status"], "internal")
            self.assertFalse(result["human_review_approved"])
            self.assertEqual(hashlib.sha256(SAMPLE.read_bytes()).hexdigest(), before)
        finally:
            connection.close()
            directory.cleanup()

    def test_logo_route_does_not_change_the_baseline(self) -> None:
        before = hashlib.sha256(SAMPLE.read_bytes()).hexdigest()
        directory = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        db = Path(directory.name) / "analyze.sqlite"
        connection = connect(db)
        seed(connection)
        server = make_server(db, port=0)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        host, port = server.server_address
        try:
            with urllib.request.urlopen(f"http://{host}:{port}/static/rugd-logo.png") as response:
                payload = response.read()
                content_type = response.headers.get("Content-Type", "")
            self.assertEqual(content_type, "image/png")
            self.assertEqual(payload[:8], b"\x89PNG\r\n\x1a\n")
            with urllib.request.urlopen(f"http://{host}:{port}/") as response:
                page = response.read().decode("utf-8")
            self.assertIn('class="sidebar"', page)
            self.assertIn(NOTE, page)
            baseline = get_assessment(connection, BASELINE_ID)
            assert baseline is not None
            self.assertFalse(baseline["human_review_approved"])
            self.assertIsNone(baseline["result"])
            self.assertEqual(hashlib.sha256(SAMPLE.read_bytes()).hexdigest(), before)
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=3)
            connection.close()
            directory.cleanup()

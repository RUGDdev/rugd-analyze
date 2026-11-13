"""Market Pulse is a labeled demonstration and does not change engine flags."""

import copy
import hashlib
import tempfile
import threading
import unittest
import urllib.request
from pathlib import Path

from app.analysis import analyze_record
from app.durable_value import LABEL
from app.market_pulse import PULSE_LABEL, QUESTIONS, market_pulse
from app.pages import market_pulse_page, partner_page
from app.server import make_server
from app.store import BASELINE_ID, SAMPLE, connect, get_assessment, seed

ROOT = Path(__file__).resolve().parent.parent
DRAFT_REPORT = ROOT / "reports" / "output" / "rugd-intelligence-draft.md"


class TestMarketPulse(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.db = Path(self.directory.name) / "analyze.sqlite"
        self.connection = connect(self.db)
        seed(self.connection)

    def tearDown(self) -> None:
        self.connection.close()
        self.directory.cleanup()

    def test_demonstration_cannot_be_live_and_cannot_change_flags(self) -> None:
        sample_before = hashlib.sha256(SAMPLE.read_bytes()).hexdigest()
        report_before = hashlib.sha256(DRAFT_REPORT.read_bytes()).hexdigest()
        baseline = get_assessment(self.connection, BASELINE_ID)
        assert baseline is not None
        before = analyze_record(baseline)
        snapshot = copy.deepcopy(before)
        pulse = market_pulse()
        page = market_pulse_page()
        partner = partner_page()
        self.assertEqual(before, snapshot)
        self.assertEqual(len(QUESTIONS), 8)
        self.assertEqual(len(pulse["questions"]), 8)
        self.assertEqual(pulse["label"], PULSE_LABEL)
        self.assertFalse(pulse["monitoring_active"])
        self.assertFalse(pulse["live_feed_connected"])
        self.assertFalse(pulse["authoritative"])
        self.assertEqual(pulse["scheduled_jobs"], [])
        self.assertEqual(pulse["connectors"], [])
        self.assertEqual(pulse["notifications"], [])
        self.assertNotIn("score", pulse)
        sides = {card["side"] for card in pulse["cards"]}
        self.assertEqual(sides, {"internal", "external"})
        titles = [card["title"] for card in pulse["cards"]]
        self.assertIn("Revenue trend", titles)
        self.assertIn("Labor", titles)
        self.assertIn("Local demographics", titles)
        for card in pulse["cards"]:
            self.assertEqual(card["label"], PULSE_LABEL)
            self.assertFalse(card["monitoring_active"])
            self.assertIsNone(card["connector"])
            self.assertFalse(card["scheduled"])
            self.assertIsNone(card["notification"])
            self.assertTrue(card["pillar_labels"])
            self.assertEqual(card["pillar_label_note"], LABEL)
            self.assertNotIn("score", card)
        for question in QUESTIONS:
            self.assertTrue(question.endswith("?"))
            self.assertIn(question, page)
        for text in (page, partner):
            self.assertIn(PULSE_LABEL, text)
            self.assertIn("Monitoring active: false", text)
            self.assertIn("Live feed connected: false", text)
            self.assertIn("Scheduled jobs: none", text)
            self.assertIn("Connectors: none", text)
            self.assertIn("Notifications: none", text)
            self.assertIn("Educational pillar label:", text)
            self.assertIn(LABEL, text)
            self.assertIn("Static template.", text)
            self.assertIn("do not lift a serious concern", text)
            self.assertNotIn("Monitoring active: true", text)
            self.assertNotIn("Live feed connected: true", text)
        after = analyze_record(get_assessment(self.connection, BASELINE_ID))
        self.assertEqual(after["recommendation"], before["recommendation"])
        self.assertEqual(after["blocking_flags"], before["blocking_flags"])
        self.assertEqual(after["readiness_status"], before["readiness_status"])
        self.assertFalse(after["human_review_approved"])
        self.assertEqual(after["recommendation"], "do-not-proceed")
        self.assertIn("INSUFFICIENT_DEMAND_EVIDENCE", after["blocking_flags"])
        self.assertEqual(hashlib.sha256(SAMPLE.read_bytes()).hexdigest(), sample_before)
        self.assertEqual(hashlib.sha256(DRAFT_REPORT.read_bytes()).hexdigest(), report_before)

    def test_http_query_cannot_turn_monitoring_on(self) -> None:
        sample_before = hashlib.sha256(SAMPLE.read_bytes()).hexdigest()
        baseline = get_assessment(self.connection, BASELINE_ID)
        assert baseline is not None
        before = analyze_record(baseline)
        server = make_server(self.db, port=0)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        host, port = server.server_address
        try:
            with urllib.request.urlopen(
                f"http://{host}:{port}/market-pulse?monitoring_active=true&notify=true"
            ) as response:
                page = response.read().decode("utf-8")
            self.assertIn(PULSE_LABEL, page)
            self.assertIn("Monitoring active: false", page)
            self.assertIn("Notifications: none", page)
            self.assertNotIn("Monitoring active: true", page)
            after = analyze_record(get_assessment(self.connection, BASELINE_ID))
            self.assertEqual(after["blocking_flags"], before["blocking_flags"])
            self.assertEqual(after["recommendation"], "do-not-proceed")
            self.assertFalse(after["human_review_approved"])
            self.assertEqual(hashlib.sha256(SAMPLE.read_bytes()).hexdigest(), sample_before)
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=3)

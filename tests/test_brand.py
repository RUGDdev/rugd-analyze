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
    forgot_password_page,
    market_page,
    market_pulse_page,
    new_assessment_page,
    results_page,
    settings_page,
    shared_assessment_page,
    verification_banner,
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
    "Research",
    "Reports",
    "Business plan",
    "Pitch deck",
    "Adviser",
    "Action Center",
    "History",
    "Settings",
)
NAV_TIPS = (
    ('href="/"', "Dashboard", "See saved drafts and the next recommended step."),
    ('href="/explore"', "Explore", "Start or continue an intake and save a draft."),
    ('href="/analyze"', "Analyze", "See what RUGD found for a saved draft."),
    (
        'href="/validate"',
        "Validate (demonstration)",
        "Request a human review in this demonstration. It cannot approve an assessment.",
    ),
    (
        'href="/partner"',
        "Partner (demonstration)",
        "Open the partner dashboard. Monitoring is not running.",
    ),
    ('href="/assessments"', "My Assessments", "Open, export, or start one of your drafts."),
    (
        'href="/market"',
        "Market Intelligence (demonstration)",
        "Read a market snapshot for a place and an industry.",
    ),
    (
        'href="/market-pulse"',
        "Market Pulse (demonstration)",
        "See example monitoring cards. Monitoring is not active.",
    ),
    (
        'href="/intelligence"',
        "Research",
        "Save evidence and developments for a business you can open. This is not a live feed.",
    ),
    ('href="/reports"', "Reports", "Generate a report from a saved assessment and open it later."),
    ('href="/plans"', "Business plan", "Write a plan from a saved assessment and export it."),
    ('href="/decks"', "Pitch deck", "Build a presentation from a saved business plan and export it."),
    ('href="/adviser"', "Adviser", "Ask about a saved assessment. A suggestion is stored only after you approve it."),
    ('href="/actions"', "Action Center", "Save follow-up items for an assessment you can change."),
    ('href="/history"', "History", "See saved assessments, reports, and action status."),
    ('href="/settings"', "Settings", "Update this local account and its email preferences."),
    ('href="/login"', "Login", "Sign in with a local email and password."),
    ('href="/register"', "Register", "Create a local customer account."),
    ('href="/logout"', "Log out", "End this local session."),
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

    def test_new_surfaces_use_the_sidebar_and_brand_cards(self) -> None:
        home = dashboard([])
        self.assertIn("Welcome to RUGD Intelligence", home)
        self.assertIn("No feasibility score is calculated.", home)
        self.assertIn('href="/login"', home)
        self.assertIn('href="/register"', home)
        signed_home = dashboard([], signed_in=True, viewer_id="brand-reader")
        self.assertIn("preliminary business evaluation", signed_home)
        self.assertIn("read-only share", signed_home)
        self.assertIn("No feasibility score is calculated.", signed_home)
        self.assertIn('class="sidebar"', home)
        noticed = home.replace("<main>", "<main>\n" + verification_banner(), 1)
        self.assertLess(noticed.index('class="sidebar"'), noticed.index('id="email-unverified"'))
        self.assertIn("Your email is not verified.", noticed)
        self.assertIn('class="banner"', noticed)
        fresh = new_assessment_page()
        shared = shared_assessment_page(
            {
                "id": "polish-draft",
                "business_name": "Polish Cafe",
                "tier": "explore",
                "read_only": False,
                "pilot_label": "Customer draft. Not a completed assessment.",
                "profile": {},
            },
            {"engine_ran": False},
        )
        reset = forgot_password_page()
        preferences = settings_page()
        for name, page in {
            "new": fresh,
            "share": shared,
            "reset": reset,
            "preferences": preferences,
        }.items():
            self.assertIn('class="sidebar"', page, name)
            self.assertIn('src="/static/rugd-logo.png"', page, name)
            self.assertIn("#263746", page, name)
            self.assertIn("#A88958", page, name)
            self.assertIn(NOTE, page, name)
        self.assertIn('class="card"', fresh)
        self.assertIn('class="card"', preferences)
        self.assertIn("Email preferences", preferences)
        self.assertIn("Sign in with a local account to store which notices this account receives.", preferences)
        self.assertIn("Is this a startup idea or an existing or expanding business?", fresh)
        self.assertIn("Read-only share.", shared)
        self.assertIn("The preliminary business evaluation is shown after Analyze has been run.", shared)
        self.assertIn('class="bar"', results_page(
            {
                "id": "rugd-intelligence-baseline",
                "business_name": "RUGD Intelligence",
                "tier": "analyze",
                "read_only": True,
                "pilot_label": "Official baseline. Not a completed customer study.",
                "human_review_approved": False,
            },
            {
                "engine_ran": True,
                "model_version": "0.1-pilot",
                "recommendation": "do-not-proceed",
                "blocking_flags": ["INSUFFICIENT_DEMAND_EVIDENCE"],
                "gap_flags": [],
                "missing": [],
                "human_review_approved": False,
                "human_review_status": "pending",
                "readiness_status": "internal",
                "financial": None,
                "projection": None,
                "projection_text": "",
                "demand": {"status": "uncleared"},
                "score_line": "Not calculated — methodology pending approval.",
            },
        ))

    def test_sidebar_hover_explains_each_section(self) -> None:
        page = dashboard([])
        self.assertIn("nav a:hover .nav-tip", page)
        self.assertIn("border-left: 3px solid var(--bronze)", page)
        for href, label, tip in NAV_TIPS:
            self.assertIn(href, page)
            self.assertIn(f"{label}<span class=\"nav-tip\">{tip}</span>", page)

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

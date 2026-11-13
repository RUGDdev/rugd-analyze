"""Industry guidance names a method and does not invent a benchmark."""

from __future__ import annotations

import json
import tempfile
import threading
import unittest
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from app.accounts import register_account
from app.guidance import BENCHMARK_NOTE, family_for, illustrative_math, recommendation
from app.pages import assessment_form
from app.server import make_server
from app.store import connect, get_assessment, seed, set_email_verified


def _draft(industry: str) -> dict:
    return {
        "id": "guide-1",
        "business_name": "Guide Draft",
        "tier": "explore",
        "owner_user_id": "guide-reader",
        "read_only": False,
        "hypothetical": False,
        "pilot_label": "Customer draft. Not a completed assessment.",
        "purpose": "startup_feasibility",
        "created_at": "2026-11-12",
        "profile": {
            "business_name": "Guide Draft",
            "purpose": "startup_feasibility",
            "tier": "explore",
            "venture_path": "startup",
            "industry": industry,
        },
        "result": None,
        "human_review_approved": False,
    }


class TestIndustryGuidance(unittest.TestCase):
    def test_restaurant_and_software_use_different_methods(self) -> None:
        cafe = recommendation({"industry": "Neighborhood coffee shop"})
        software = recommendation({"industry": "Software subscription"})
        self.assertEqual(cafe["family"], "hospitality")
        self.assertEqual(cafe["recommended_id"], "covers")
        self.assertIn("seats", cafe["method"]["formula"])
        self.assertEqual(software["family"], "software")
        self.assertEqual(software["recommended_id"], "subscription")
        self.assertNotEqual(cafe["recommended_name"], software["recommended_name"])
        self.assertEqual(cafe["benchmark_note"], BENCHMARK_NOTE)
        self.assertNotIn("%", BENCHMARK_NOTE)
        self.assertIsNone(illustrative_math({"industry": "cafe"}, "covers"))

    def test_services_math_uses_only_entered_assumptions(self) -> None:
        self.assertEqual(family_for("Accounting firm"), "services")
        guide = recommendation(
            {
                "industry": "Accounting firm",
                "forecast_people": "2",
                "forecast_hours": "80",
                "forecast_rate": "150",
            }
        )
        self.assertEqual(guide["recommended_id"], "billable")
        math = guide["math"]
        assert math is not None
        self.assertEqual(math["amount"], 24000)
        self.assertEqual(math["kind"], "illustrative_example")
        self.assertIn("2 × 80 × 150 = 24000", math["lines"][0])
        self.assertIsNone(guide["math"] if False else illustrative_math({"forecast_people": "2"}, "billable"))

    def test_seat_formula_matches_the_existing_engine(self) -> None:
        math = illustrative_math(
            {
                "seats": "10",
                "average_ticket": "20",
                "weekday_occupancy": "0.5",
                "weekend_occupancy": "0.5",
                "operating_days": "300",
                "downside_multiplier": "0.8",
            },
            "covers",
        )
        assert math is not None
        self.assertIn("30000", math["lines"][0])
        self.assertIn("24000", str(math["downside"]))
        self.assertIsNone(math["amount"])

    def test_placeholder_name_starts_blank_and_named_draft_keeps_its_name(self) -> None:
        fresh = _draft("")
        fresh["profile"]["business_name"] = "New draft"
        blank = assessment_form(fresh)
        self.assertIn('id="business_name" name="business_name" value=""', blank)
        self.assertIn('data-start="name"', blank)
        named = _draft("Restaurant")
        named["profile"]["business_name"] = "Harbor Light Cafe"
        page = assessment_form(named)
        self.assertIn('name="business_name" value="Harbor Light Cafe"', page)

    def test_intake_shows_the_guided_workspace(self) -> None:
        page = assessment_form(_draft("Neighborhood restaurant"))
        self.assertIn('id="guided-workspace"', page)
        self.assertIn("Save &amp; Continue", page)
        self.assertIn("What should we call your business?", page)
        self.assertIn("Let&#x27;s start with a name. You can change it later.", page)
        self.assertIn('id="side-stage"', page)
        self.assertIn('id="guided-progress-slot"', page)
        self.assertIn('id="name-seed"', page)
        self.assertNotIn("You are the RUGD analyst", page)
        self.assertNotIn("ANALYST_PROVIDER", page)
        self.assertIn("Built-in adviser. No outside AI service was used.", page)
        self.assertIn("Covers and average check", page)
        self.assertIn(BENCHMARK_NOTE, page)
        self.assertIn('id="suggestion-note"', page)
        software = assessment_form(_draft("Software subscription"))
        paragraph = software.split('id="forecast-recommended"', 1)[1].split("</p>", 1)[0]
        self.assertIn("Paying customers and monthly price", paragraph)
        self.assertNotIn("Covers", paragraph)


class TestGuidedSave(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.database = Path(self.directory.name) / "analyze.sqlite"
        self.connection = connect(self.database)
        seed(self.connection)
        self.server = make_server(self.database, port=0)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base = f"http://127.0.0.1:{self.server.server_address[1]}"

    def tearDown(self) -> None:
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=5)
        self.connection.close()
        self.directory.cleanup()

    def test_save_stays_on_the_draft_and_keeps_a_bad_entry(self) -> None:
        user = register_account(self.connection, email="guide@pilot.example", password="session-pass-1")
        set_email_verified(self.connection, user["id"])
        cookie = self._login()
        created = self._post(
            "/assessments",
            {"business_name": "Guide Cafe", "venture_path": "startup", "purpose": "startup_feasibility"},
            cookie,
        )
        assessment_id = created[2]["Location"].rstrip("/").rsplit("/", 1)[-1]
        saved = self._post(
            f"/assessments/{assessment_id}/save",
            {
                "guided_save": "1",
                "business_name": "Guide Cafe",
                "concept": "A fictional cafe used to test guided save.",
                "industry": "Restaurant",
                "forecast_choice": "recommended",
            },
            cookie,
        )
        self.assertEqual(saved[0], 200)
        payload = json.loads(saved[1])
        self.assertTrue(payload["saved"])
        self.assertIn("Covers and average check", payload["forecast_html"])
        record = get_assessment(self.connection, assessment_id)
        assert record is not None
        self.assertEqual(record["profile"]["concept"], "A fictional cafe used to test guided save.")
        self.assertNotIn("guided_save", record["profile"])
        refused = self._post(
            f"/assessments/{assessment_id}/save",
            {"guided_save": "1", "business_name": "Guide Cafe", "gross_margin_pct": "55", "concept": "Kept"},
            cookie,
        )
        self.assertEqual(refused[0], 400)
        self.assertIn("Gross margin", refused[1])
        again = get_assessment(self.connection, assessment_id)
        assert again is not None
        self.assertEqual(again["profile"]["concept"], "A fictional cafe used to test guided save.")
        self.assertFalse(again["human_review_approved"])

    def _login(self) -> str:
        _status, _body, headers = self._open(
            "/login",
            urllib.parse.urlencode({"email": "guide@pilot.example", "password": "session-pass-1"}).encode(),
            {},
        )
        return (headers.get("Set-Cookie") or "").split(";", 1)[0]

    def _post(self, path: str, form: dict[str, str], cookie: str) -> tuple[int, str, dict[str, str]]:
        return self._open(path, urllib.parse.urlencode(form).encode(), {"Cookie": cookie})

    def _open(self, path: str, data: bytes, headers: dict[str, str]) -> tuple[int, str, dict[str, str]]:
        class NoRedirect(urllib.request.HTTPRedirectHandler):
            def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: ARG002
                try:
                    fp.close()
                except Exception:
                    pass
                return None

        request = urllib.request.Request(self.base + path, data=data, headers=headers, method="POST")
        try:
            response = urllib.request.build_opener(NoRedirect).open(request)
        except urllib.error.HTTPError as exc:
            response = exc
        try:
            status = response.status if hasattr(response, "status") else response.code
            body = response.read().decode("utf-8", "replace")
            return status, body, dict(response.headers)
        finally:
            response.close()

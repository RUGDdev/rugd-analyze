"""Contextual help on every financial input, and the operating-day planner."""

from __future__ import annotations

import json
import re
import tempfile
import threading
import unittest
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from app.accounts import register_account
from app.field_help import (
    DAYS,
    estimate_text,
    has_help,
    help_html,
    help_keys,
    operating_estimate,
    parse_schedule,
    schedule_html,
    section_intro,
)
from app.pages import assessment_form
from app.server import make_server
from app.store import connect, get_assessment, seed, set_email_verified

STARTUP_FIELDS = (
    "construction_cost",
    "seats",
    "average_ticket",
    "weekday_occupancy",
    "weekend_occupancy",
    "operating_days",
    "contribution_margin",
    "equipment",
    "soft_costs",
    "preopening_working_capital",
    "contingency_pct",
    "debt_share",
    "annual_interest_rate",
    "amortization_years",
    "annual_fixed_costs",
    "downside_multiplier",
)
MONTHLY_FIELDS = (
    "initial_capital",
    "monthly_fixed_costs",
    "gross_margin_pct",
    "projected_monthly_revenue_base",
)
WORKSHEET_FIELDS = (
    "forecast_people",
    "forecast_hours",
    "forecast_rate",
    "forecast_clients",
    "forecast_fee",
    "forecast_transactions",
    "forecast_average_sale",
    "forecast_customers",
    "forecast_monthly_price",
    "forecast_visits",
)
INDUSTRIES = (
    "Neighborhood restaurant",
    "Retail shop",
    "Software subscription",
    "Accounting firm",
    "Dental clinic",
    "Something unusual",
)


def _draft(industry: str, path: str = "startup", **profile: str) -> dict:
    base = {
        "business_name": "Help Draft",
        "purpose": "startup_feasibility",
        "tier": "explore",
        "venture_path": path,
        "industry": industry,
    }
    base.update(profile)
    return {
        "id": "help-1",
        "business_name": "Help Draft",
        "tier": "explore",
        "owner_user_id": "help-reader",
        "read_only": False,
        "hypothetical": False,
        "pilot_label": "Customer draft. Not a completed assessment.",
        "purpose": "startup_feasibility",
        "created_at": "2026-11-12",
        "profile": base,
        "result": None,
        "human_review_approved": False,
    }


class TestHelpOnEveryFinancialField(unittest.TestCase):
    def test_every_startup_monthly_and_worksheet_field_has_help(self) -> None:
        for industry in INDUSTRIES:
            page = assessment_form(_draft(industry))
            for key in STARTUP_FIELDS + MONTHLY_FIELDS + WORKSHEET_FIELDS:
                with self.subTest(industry=industry, key=key):
                    self.assertIn(f'id="help-{key}"', page)
                    self.assertRegex(page, rf'aria-label="Help: [^"]+"[^>]*>|aria-label="Help: ')
                    self.assertIn(f'<label for="{key}"', page)

    def test_existing_business_path_and_measured_checkbox(self) -> None:
        page = assessment_form(_draft("Neighborhood restaurant", path="existing"))
        for key in MONTHLY_FIELDS + ("inputs_are_measured",):
            with self.subTest(key=key):
                self.assertIn(f'id="help-{key}"', page)

    def test_help_and_field_ids_are_unique(self) -> None:
        page = assessment_form(_draft("Neighborhood restaurant"))
        ids = re.findall(r'\bid="([^"]+)"', page)
        duplicates = sorted({value for value in ids if ids.count(value) > 1})
        self.assertEqual(duplicates, [])

    def test_verified_revenue_has_help(self) -> None:
        page = assessment_form(_draft("Neighborhood restaurant"))
        self.assertIn('id="help-verified_revenue_trailing_12m"', page)
        self.assertIn('id="verified_revenue_trailing_12m"', page)

    def test_catalog_has_no_field_that_the_page_omits(self) -> None:
        page = assessment_form(_draft("Neighborhood restaurant", path="existing"))
        startup = assessment_form(_draft("Neighborhood restaurant"))
        for key in help_keys():
            with self.subTest(key=key):
                self.assertTrue(f'id="help-{key}"' in page or f'id="help-{key}"' in startup)

    def test_each_help_has_every_required_part(self) -> None:
        for key in help_keys():
            for industry in INDUSTRIES:
                body = help_html(key, "Label", {"industry": industry})
                with self.subTest(key=key, industry=industry):
                    self.assertIn("What it means.", body)
                    self.assertIn("Why it matters.", body)
                    self.assertIn("Example.", body)
                    self.assertIn("How to estimate it", body)
                    self.assertIn("Common mistakes", body)
                    self.assertIn("Benchmarks.", body)
                    self.assertIn("Illustration only", body)
                    self.assertIn('aria-label="Help: Label"', body)
                    self.assertIn("<details", body)

    def test_help_is_optional_native_and_keyboard_reachable(self) -> None:
        body = help_html("seats", "Seats", {"industry": "Restaurant"})
        self.assertTrue(body.startswith("<details"))
        self.assertNotIn(" open", body.split(">", 1)[0])
        self.assertIn("<summary", body)
        self.assertNotIn("tabindex=\"-1\"", body)
        self.assertNotIn("required", body)

    def test_help_never_invents_a_benchmark_or_source(self) -> None:
        for key in help_keys():
            for industry in INDUSTRIES:
                body = help_html(key, "Label", {"industry": industry})
                text = re.sub(r"<[^>]+>", " ", body)
                with self.subTest(key=key, industry=industry):
                    self.assertNotRegex(text, r"(?i)industry average (is|of)|typical(ly)? (is|are) \d|according to")
                    self.assertNotRegex(text, r"(?i)\b(IBISWorld|NRA|National Restaurant Association|RMA|BLS|Census)\b")
                    self.assertNotIn("http", text)
                    benchmark = text.split("Benchmarks.", 1)[1]
                    self.assertNotRegex(benchmark.split("Illustration", 1)[0], r"\d+(\.\d+)?\s*%")

    def test_restaurant_help_uses_restaurant_language(self) -> None:
        profile = {"industry": "Neighborhood restaurant"}
        seats = help_html("seats", "Seats", profile)
        self.assertIn("cover", seats.lower())
        self.assertIn("one cover per occupied seat", seats)
        self.assertIn("known limit", seats)
        self.assertIn("proposed for RUGD review", seats)
        ticket = help_html("average_ticket", "Average ticket", profile)
        self.assertIn("per cover", ticket.lower())
        margin = help_html("contribution_margin", "Contribution margin", profile)
        self.assertIn("food", margin.lower())
        software = help_html("contribution_margin", "Contribution margin", {"industry": "Software subscription"})
        self.assertNotEqual(margin, software)

    def test_engine_placeholders_are_disclosed(self) -> None:
        for key, number in (
            ("contingency_pct", "0.10"),
            ("debt_share", "0.70"),
            ("annual_interest_rate", "0.08"),
            ("amortization_years", "20"),
            ("downside_multiplier", "0.6"),
        ):
            with self.subTest(key=key):
                body = help_html(key, "Label", {})
                self.assertIn(number, body)
                self.assertIn("placeholder", body.lower())
                self.assertRegex(body.lower(), r"not (an? )?(industry|market|advice|lender)")

    def test_from_your_answers_uses_only_entered_numbers(self) -> None:
        empty = help_html("contribution_margin", "Margin", {"industry": "Restaurant"})
        self.assertNotIn("From your answers", empty)
        partial = help_html("contribution_margin", "Margin", {"industry": "Restaurant", "contribution_margin": "0.5"})
        self.assertNotIn("From your answers", partial)
        filled = help_html(
            "contribution_margin",
            "Margin",
            {
                "industry": "Restaurant",
                "seats": "10",
                "average_ticket": "20",
                "weekday_occupancy": "0.5",
                "weekend_occupancy": "0.5",
                "operating_days": "300",
                "contribution_margin": "0.5",
            },
        )
        self.assertIn("From your answers", filled)
        self.assertIn("30,000", filled)
        self.assertIn("15,000", filled)
        self.assertIn("not a forecast", filled)


class TestSectionIntros(unittest.TestCase):
    def test_intros_render_on_the_intake_in_plain_language(self) -> None:
        page = assessment_form(_draft("Neighborhood restaurant"))
        for section in ("opening", "sales", "margin", "worksheet", "monthly"):
            with self.subTest(section=section):
                self.assertIn(f'data-section="{section}"', page)
        self.assertIn('data-section="forecast"', page)
        for section in ("opening", "sales", "margin", "worksheet", "monthly", "forecast"):
            text = section_intro(section, {"industry": "Neighborhood restaurant"})
            self.assertNotRegex(text, r"(?i)engine|dscr|human_review|recommend_against")

    def test_intro_changes_with_industry(self) -> None:
        cafe = section_intro("sales", {"industry": "Neighborhood restaurant"})
        saas = section_intro("sales", {"industry": "Software subscription"})
        self.assertNotEqual(cafe, saas)


class TestOperatingSchedule(unittest.TestCase):
    def test_arithmetic_is_transparent(self) -> None:
        weekdays = ["mon", "tue", "wed", "thu", "fri"]
        estimate = operating_estimate(weekdays, None)
        self.assertEqual(estimate["annual_days"], 260)
        self.assertEqual(estimate["monthly_days"], 21.7)
        self.assertTrue(estimate["weeks_assumed"])
        six = operating_estimate(["mon", "tue", "wed", "thu", "fri", "sat"], 50)
        self.assertEqual(six["annual_days"], 300)
        self.assertEqual(six["monthly_days"], 25)
        self.assertFalse(six["weeks_assumed"])

    def test_estimate_text_labels_assumptions_and_the_weekend_weighting(self) -> None:
        text = estimate_text({"operating_schedule": "mon,tue,wed,thu,fri"})
        self.assertIn("5 days a week × 52 weeks = 260", text)
        self.assertIn("about 21.7 operating days a month", text)
        self.assertIn("52 is assumed", text)
        self.assertIn("5/7", text)
        self.assertIn("2/7", text)
        balanced = estimate_text({"operating_schedule": "mon,tue,wed,thu,fri,sat,sun", "operating_weeks": "52"})
        self.assertNotIn("5/7", balanced)
        self.assertNotIn("assumed", balanced)
        self.assertIn("= 364 operating days", balanced)

    def test_empty_and_invalid_inputs_do_not_guess(self) -> None:
        self.assertIn("Pick the days", estimate_text({}))
        self.assertIn("between 1 and 52", estimate_text({"operating_schedule": "mon", "operating_weeks": "80"}))
        self.assertEqual(parse_schedule("sun, MON, funday, mon"), ["mon", "sun"])

    def test_saved_operating_days_is_never_reinterpreted(self) -> None:
        profile = {"operating_days": "312", "operating_schedule": "mon,tue,wed,thu,fri"}
        text = estimate_text(profile)
        self.assertIn("operating days entry is 312", text)
        self.assertIn("until you choose Use", text)
        page = assessment_form(_draft("Neighborhood restaurant", operating_days="312"))
        self.assertIn('id="operating_days" name="operating_days" value="312"', page)
        unchecked = schedule_html({"operating_days": "312"}, "")
        self.assertNotIn(" checked", unchecked)
        for code, _label in DAYS:
            self.assertIn(f'data-day="{code}"', unchecked)

    def test_selector_is_a_group_of_seven_labelled_checkboxes(self) -> None:
        page = assessment_form(_draft("Neighborhood restaurant", operating_schedule="mon,sat", operating_weeks="48"))
        block = page.split('id="operating-schedule"', 1)[1].split("</section>", 1)[0]
        self.assertEqual(len(re.findall(r'type="checkbox" data-day=', block)), 7)
        self.assertEqual(len(re.findall(r" checked", block)), 2)
        self.assertIn('aria-label="Days open each week"', block)
        self.assertIn('value="48"', block)
        self.assertIn('aria-live="polite"', block)
        self.assertIn('id="schedule-use"', block)
        self.assertIn("The operating days field does not change until you choose Use.", block)

    def test_locked_page_has_no_use_button(self) -> None:
        self.assertNotIn("schedule-use", schedule_html({"operating_schedule": "mon"}, "disabled"))


class TestScheduleSaves(unittest.TestCase):
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

    def test_schedule_persists_and_changes_no_result_or_approval(self) -> None:
        user = register_account(self.connection, email="help@pilot.example", password="session-pass-1")
        set_email_verified(self.connection, user["id"])
        _s, _b, headers = self._open(
            "/login",
            urllib.parse.urlencode({"email": "help@pilot.example", "password": "session-pass-1"}).encode(),
            {},
        )
        cookie = (headers.get("Set-Cookie") or "").split(";", 1)[0]
        created = self._open(
            "/assessments",
            urllib.parse.urlencode(
                {"business_name": "Help Cafe", "venture_path": "startup", "purpose": "startup_feasibility"}
            ).encode(),
            {"Cookie": cookie},
        )
        assessment_id = created[2]["Location"].rstrip("/").rsplit("/", 1)[-1]
        status, body, _h = self._open(
            f"/assessments/{assessment_id}/save",
            urllib.parse.urlencode(
                {
                    "guided_save": "1",
                    "business_name": "Help Cafe",
                    "industry": "Restaurant",
                    "operating_days": "300",
                    "operating_schedule": "mon,tue,wed,thu,fri,sat",
                    "operating_weeks": "50",
                }
            ).encode(),
            {"Cookie": cookie},
        )
        self.assertEqual(status, 200)
        self.assertTrue(json.loads(body)["saved"])
        forged = self._open(
            f"/assessments/{assessment_id}/save",
            urllib.parse.urlencode(
                {"guided_save": "1", "business_name": "Help Cafe", "human_review_approved": "true"}
            ).encode(),
            {"Cookie": cookie},
        )
        self.assertEqual(forged[0], 403)
        record = get_assessment(self.connection, assessment_id)
        assert record is not None
        self.assertEqual(record["profile"]["operating_schedule"], "mon,tue,wed,thu,fri,sat")
        self.assertEqual(record["profile"]["operating_weeks"], "50")
        self.assertEqual(record["profile"]["operating_days"], "300")
        self.assertFalse(record["human_review_approved"])
        self.assertIsNone(record["result"])
        page = urllib.request.build_opener().open(
            urllib.request.Request(f"{self.base}/assessments/{assessment_id}", headers={"Cookie": cookie})
        ).read().decode("utf-8")
        self.assertIn('value="50"', page)
        self.assertIn("6 days a week × 50 weeks = 300", page)

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
            return status, response.read().decode("utf-8", "replace"), dict(response.headers)
        finally:
            response.close()


class TestRevenueFormulaUnchanged(unittest.TestCase):
    def test_seat_formula_still_matches_documented_behavior(self) -> None:
        from engine.financial import seat_occupancy_revenue

        revenue = seat_occupancy_revenue(
            seats=10,
            weekday_occupancy=0.5,
            weekend_occupancy=0.5,
            average_ticket=20,
            operating_days=300,
        ).revenue
        self.assertEqual(revenue, 30000)
        blended = seat_occupancy_revenue(
            seats=10,
            weekday_occupancy=0.6,
            weekend_occupancy=0.9,
            average_ticket=20,
            operating_days=364,
        ).revenue
        self.assertAlmostEqual(blended, 10 * ((0.6 * 5 + 0.9 * 2) / 7) * 20 * 364, places=1)
        self.assertTrue(has_help("seats"))


if __name__ == "__main__":
    unittest.main()

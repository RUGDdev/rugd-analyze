"""The Analyze results dashboard: formatting, honest status, grounded recommendations, navigation."""

from __future__ import annotations

import re
import unittest

from app import display
from app.store import BASELINE_ID
from tests.test_advisory_server import PROFILE, AdvisoryServerCase

SECTION_IDS = ("overview", "key-numbers", "benchmarks", "revenue-model", "scenarios", "recommendations")


class TestDisplayFormatting(unittest.TestCase):
    def test_money_percent_and_multiple_follow_one_style(self) -> None:
        self.assertEqual(display.money(2537206), "$2,537,206")
        self.assertEqual(display.money(365000), "$365,000")
        self.assertEqual(display.money(-125000), "-$125,000")
        self.assertEqual(display.money(0), "$0")
        self.assertEqual(display.money(22, cents=True), "$22.00")
        self.assertEqual(display.percent(0.55), "55%")
        self.assertEqual(display.percent(0.08, 1), "8.0%")
        self.assertEqual(display.multiple(1.25), "1.25×")
        self.assertEqual(display.multiple(-0.69), "-0.69×")

    def test_rounding_is_half_up_and_never_makes_negative_zero(self) -> None:
        self.assertEqual(display.money(2.5), "$3")
        self.assertEqual(display.money(-0.4), "$0")
        self.assertEqual(display.multiple(1.005), "1.01×")

    def test_missing_is_words_and_zero_is_zero(self) -> None:
        for blank in (None, "", "  ", "n/a", float("nan"), True):
            self.assertEqual(display.money(blank), "Not provided")
            self.assertEqual(display.percent(blank), "Not provided")
            self.assertEqual(display.multiple(blank), "Not calculated")
        self.assertEqual(display.money(0), "$0")
        self.assertEqual(display.money("0"), "$0")
        self.assertEqual(display.percent(0), "0%")
        self.assertEqual(display.multiple(0), "0.00×")

    def test_chip_states_are_distinct(self) -> None:
        self.assertIn("Calculated", display.chip("calculated"))
        self.assertIn("Your estimate", display.chip("estimated"))
        self.assertIn("Missing", display.chip("missing"))
        self.assertEqual(display.state_from_engine("calculated by the deterministic engine"), "calculated")
        self.assertEqual(display.state_from_engine("user-supplied assumption"), "estimated")


class TestAnalyzeDashboard(AdvisoryServerCase):
    def analyzed(self, cookie: str, profile: dict | None = None) -> tuple[str, str]:
        assessment_id = self.new_draft(cookie, profile)
        status, body, headers = self.request(f"/assessments/{assessment_id}/analyze", {}, cookie)
        if status in (301, 302, 303):
            body = self.request(headers["Location"], None, cookie)[1]
        return assessment_id, body

    def test_every_section_has_a_working_tab_and_a_panel(self) -> None:
        cookie = self.sign_in("owner@pilot.example")
        _aid, body = self.analyzed(cookie)
        for key in SECTION_IDS:
            self.assertIn(f'href="#{key}"', body, key)
            self.assertIn(f'data-tab="{key}"', body, key)
            self.assertIn(f'id="{key}"', body, key)
        # Without scripting every panel is in the page, so nothing is hidden from a reader.
        self.assertIn("js-dash", body)
        self.assertIn("hashchange", body)

    def test_status_uses_labels_not_a_made_up_score(self) -> None:
        cookie = self.sign_in("owner@pilot.example")
        _aid, body = self.analyzed(cookie)
        for text in ("Customer evidence needed", "Waiting for an authorized review", "Not enough evidence of customer demand", "INSUFFICIENT_DEMAND_EVIDENCE", "Not calculated — methodology pending approval."):
            self.assertIn(text, body)
        self.assertIsNone(re.search(r"readiness[^<]{0,40}\d+\s?%", body, re.I))
        self.assertNotIn('name="human_review_approved"', body)
        self.assertNotIn('name="human_review_status"', body)
        self.assertIn("do-not-proceed", body)

    def test_numbers_are_formatted_and_missing_is_not_zero(self) -> None:
        cookie = self.sign_in("owner@pilot.example")
        _aid, body = self.analyzed(cookie)
        self.assertIn("$2,387,000", body)
        self.assertIn("-0.69×", body)
        self.assertIn("$167,713", body)
        self.assertIn("8.0%", body)
        self.assertIn("Starting number, not yours", body)
        self.assertIsNone(re.search(r"\$\d{4,}(?!,)", body), "currency must carry thousands separators")
        sparse = dict(PROFILE, average_ticket="", weekday_occupancy="", weekend_occupancy="")
        _aid2, page = self.analyzed(cookie, sparse)
        revenue = page.split('id="revenue-model"')[1].split('id="scenarios"')[0]
        self.assertIn("Not provided", revenue)
        self.assertNotIn("Average ticket</td><td>$0", revenue)

    def test_benchmarks_say_none_verified_and_never_invent_a_range(self) -> None:
        cookie = self.sign_in("owner@pilot.example")
        _aid, body = self.analyzed(cookie)
        panel = body.split('id="benchmarks"')[1].split('id="revenue-model"')[0]
        self.assertIn("No verified benchmark available", panel)
        self.assertIn("secondary industry benchmark", panel)
        self.assertIn("It is not a target", panel)
        self.assertIn(f"/assessments/{_aid}/benchmarks", panel)
        other = dict(PROFILE, industry="Software subscription", market="Huntsville, Alabama", service_style="")
        aid2, page = self.analyzed(cookie, other)
        panel2 = page.split('id="benchmarks"')[1].split('id="revenue-model"')[0]
        self.assertIn("No verified benchmark available", panel2)
        self.assertIn("does not estimate one", panel2)
        self.assertIn(f"/assessments/{aid2}/intelligence", panel2)

    def test_recommendations_are_grounded_linked_and_make_no_pass_claim(self) -> None:
        cookie = self.sign_in("owner@pilot.example")
        aid, body = self.analyzed(cookie)
        panel = body.split('id="recommendations"')[1]
        self.assertIn("Show that customers will buy", panel)
        self.assertIn("Make the business earn more than it costs first", panel)
        self.assertIn(f"/assessments/{aid}/improve?target=1&amp;preset=", panel.replace("&preset=", "&amp;preset="))
        self.assertIn(f"/assessments/{aid}/revenue-worksheet", panel)
        self.assertIn("#evidence-checklist-", panel)
        lowered = panel.lower()
        for claim in ("will pass", "you will pass", "guarantee", "investor-ready result"):
            self.assertNotIn(claim, lowered)
        self.assertIn("not an official pass", lowered)
        self.assertNotIn("Increase available capital", panel, "more capital cannot fix negative operating cash flow")

    def test_saved_scenarios_and_benchmark_records_appear_and_stay_intact(self) -> None:
        cookie = self.sign_in("owner@pilot.example")
        aid = self.new_draft(cookie)
        saved = self.request(f"/assessments/{aid}/improve", {"op": "save", "name": "Smaller room", "ov_seats": "45", "scale_with_size": "on", "target": "1"}, cookie)
        self.assertIn(saved[0], (200, 302, 303))
        self.request(
            f"/assessments/{aid}/benchmarks",
            {"op": "save", "metric_key": "average_check", "value": "24.50", "source_name": "Lender guide, Shoals edition", "source_url": "https://example.org/guide", "published_on": "2024", "geography": "Colbert County, Alabama", "scale": "50 to 80 seats"},
            cookie,
        )
        status, body, headers = self.request(f"/assessments/{aid}/analyze", {}, cookie)
        if status in (301, 302, 303):
            body = self.request(headers["Location"], None, cookie)[1]
        scenarios = body.split('id="scenarios"')[1].split('id="recommendations"')[0]
        self.assertIn("Smaller room", scenarios)
        self.assertIn("not approved", scenarios)
        benchmarks = body.split('id="benchmarks"')[1].split('id="revenue-model"')[0]
        self.assertIn("Lender guide, Shoals edition", benchmarks)
        self.assertIn("customer-recorded", benchmarks)
        self.assertIn("No verified benchmark available", benchmarks, "a customer record is not verification")
        # The saved scenario is still on its own page, unchanged.
        page = self.request(f"/assessments/{aid}/improve", None, cookie)[1]
        self.assertIn("Smaller room", page)
        self.assertIn(f"/assessments/{aid}/results#scenarios", page)

    def test_other_accounts_cannot_see_the_dashboard_or_its_records(self) -> None:
        owner = self.sign_in("owner@pilot.example")
        other = self.sign_in("other@pilot.example")
        aid = self.new_draft(owner)
        self.request(f"/assessments/{aid}/improve", {"op": "save", "name": "Private plan", "ov_seats": "45", "scale_with_size": "on", "target": "1"}, owner)
        self.request(f"/assessments/{aid}/analyze", {}, owner)
        status, body, _h = self.request(f"/assessments/{aid}/results", None, other)
        self.assertIn(status, (302, 303, 403, 404))
        self.assertNotIn("Private plan", body)
        self.assertNotIn("analyze-dashboard", body)

    def test_viewing_the_dashboard_never_changes_the_official_result(self) -> None:
        cookie = self.sign_in("owner@pilot.example")
        aid, _body = self.analyzed(cookie)
        before = self.record(aid)
        for _ in range(2):
            self.request(f"/assessments/{aid}/results", None, cookie)
        after = self.record(aid)
        self.assertEqual(before["result"], after["result"])
        self.assertFalse(after["human_review_approved"])
        flags = [flag["code"] if isinstance(flag, dict) else flag for flag in after["result"]["blocking_flags"]]
        self.assertIn("INSUFFICIENT_DEMAND_EVIDENCE", flags)
        self.assertEqual(after["result"]["recommendation"], "do-not-proceed")

    def test_official_baseline_is_unchanged_after_dashboard_use(self) -> None:
        cookie = self.sign_in("owner@pilot.example")
        status, body, _h = self.request(f"/assessments/{BASELINE_ID}/results", None, cookie)
        self.assertEqual(status, 200)
        self.assertIn("do-not-proceed", body)
        self.assertIn("INSUFFICIENT_DEMAND_EVIDENCE", body)
        self.assertFalse(self.record(BASELINE_ID)["human_review_approved"])


if __name__ == "__main__":
    unittest.main()

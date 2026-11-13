"""The shared page design: one header, one workspace row, one money style, on every workspace."""

from __future__ import annotations

import re
import unittest

from app import display, ui
from tests.test_advisory_server import AdvisoryServerCase

WORKSPACE_PATHS = {
    "explore": "",
    "research": "/intelligence",
    "analyze": "/results",
    "improve": "/improve",
    "plan": "/plans",
    "deck": "/decks",
    "reports": "/reports",
    "adviser": "/advice",
    "actions": "/actions",
    "pulse": "/pulse",
}


class TestSharedComponents(unittest.TestCase):
    def test_workspace_nav_marks_only_the_current_workspace(self) -> None:
        html = ui.workspace_nav("abc", "plan")
        self.assertEqual(html.count('aria-current="page"'), 1)
        self.assertRegex(html, r'<a href="/assessments/abc/plans" aria-current="page" class="on">Business plan</a>')
        self.assertIn('id="journey-nav"', html)
        for key in WORKSPACE_PATHS:
            self.assertIn(f'href="/assessments/abc{WORKSPACE_PATHS[key]}"', html)
        self.assertEqual(ui.workspace_nav("abc", "").count("aria-current"), 0)

    def test_when_writes_a_stored_timestamp_in_everyday_words(self) -> None:
        html = ui.when("2026-11-13T13:32:08+00:00")
        self.assertIn("Nov 13, 2026, 13:32 UTC", html)
        self.assertIn('datetime="2026-11-13T13:32:08+00:00"', html)
        self.assertEqual(ui.when(""), "not recorded")
        self.assertEqual(ui.when("not a date"), "not a date")

    def test_page_header_has_one_h1_and_escapes_text(self) -> None:
        html = ui.page_header("<b>Title</b>", subtitle="Line", chips=(ui.pill("Chip"),))
        self.assertEqual(html.count("<h1"), 1)
        self.assertNotIn("<b>Title</b>", html)
        self.assertIn("Chip", html)

    def test_item_card_links_the_title_and_keeps_body_markup(self) -> None:
        html = ui.item_card("Saved <thing>", href="/x", meta="meta", body="<ul><li>one</li></ul>")
        self.assertIn('<a href="/x">Saved &lt;thing&gt;</a>', html)
        self.assertIn("<li>one</li>", html)

    def test_figures_are_written_the_way_a_person_reads_them(self) -> None:
        self.assertEqual(display.figure("base_monthly_cash_flow", 5360.0), "$5,360")
        self.assertEqual(display.figure("downside_monthly_cash_flow", -1584.0), "-$1,584")
        self.assertEqual(display.figure("break_even_monthly_revenue", 19354.84), "$19,354.84")
        self.assertEqual(display.figure("months_to_break_even_base", 33.6), "33.6 months")
        self.assertEqual(display.figure("gross_margin_pct", 0.62), "62%")
        self.assertEqual(display.figure("downside_multiplier", 0.6), "0.6×")
        self.assertEqual(display.figure("dscr", 1.25), "1.25×")
        self.assertEqual(display.figure("base_monthly_cash_flow", None), "Not calculated")
        self.assertEqual(display.dollars(100.0), "$100")
        self.assertEqual(display.dollars(0), "$0")


class TestWorkspacePages(AdvisoryServerCase):
    def analyzed(self, cookie: str) -> str:
        assessment_id = self.new_draft(cookie)
        status, _body, headers = self.request(f"/assessments/{assessment_id}/analyze", {}, cookie)
        self.assertIn(status, (200, 301, 302, 303))
        return assessment_id

    def get(self, path: str, cookie: str) -> str:
        status, body, _headers = self.request(path, None, cookie)
        self.assertEqual(status, 200, path)
        return body

    def test_every_workspace_page_has_one_h1_and_the_workspace_row_with_its_own_tab_marked(self) -> None:
        cookie = self.sign_in("owner@pilot.example")
        aid = self.analyzed(cookie)
        for key, suffix in WORKSPACE_PATHS.items():
            page = self.get(f"/assessments/{aid}{suffix}", cookie)
            self.assertEqual(len(re.findall(r"<h1[ >]", page)), 1, f"{key}: exactly one page title")
            self.assertIn('id="journey-nav"', page, key)
            current = re.findall(r'<a href="([^"]+)" aria-current="page" class="on">', page)
            self.assertEqual(current, [f"/assessments/{aid}{suffix}"], f"{key}: its own tab is marked current")

    def test_every_section_list_page_has_one_h1_and_no_signed_out_data(self) -> None:
        cookie = self.sign_in("owner@pilot.example")
        self.analyzed(cookie)
        for path in (
            "/", "/assessments", "/explore", "/analyze", "/intelligence", "/reports", "/plans", "/decks",
            "/adviser", "/actions", "/history", "/market-pulse", "/assessments/new",
        ):
            page = self.get(path, cookie)
            self.assertEqual(len(re.findall(r"<h1[ >]", page)), 1, f"{path}: exactly one page title")
            self.assertNotIn('name="human_review_approved"', page, path)
            self.assertNotIn('name="human_review_status"', page, path)

    def test_saved_report_plan_and_deck_show_dollars_and_dates_in_plain_form(self) -> None:
        cookie = self.sign_in("owner@pilot.example")
        aid = self.analyzed(cookie)
        for path, listing in (
            (f"/assessments/{aid}/reports", "reports"),
            (f"/assessments/{aid}/plans", "plans"),
        ):
            self.request(path, {}, cookie)
            page = self.get(path, cookie)
            link = re.findall(rf'href="(/assessments/{aid}/{listing}/[0-9a-f-]{{36}})"', page)
            self.assertTrue(link, listing)
            saved = self.get(link[0], cookie)
            self.assertRegex(saved, r"\$\d")
            self.assertIsNone(re.search(r"_cash_flow: -?\d+\.\d\. ", saved), "no raw engine number in the text")
            self.assertIsNone(re.search(r"\$\d{4,}(?!,)", saved), "currency carries thousands separators")
            self.assertIn("<time", saved)
        plans = self.get(f"/assessments/{aid}/plans", cookie)
        plan_id = re.findall(r"/plans/([0-9a-f-]{36})", plans)[0]
        self.request(f"/assessments/{aid}/decks", {"plan_id": plan_id, "audience": "investor"}, cookie)
        decks = self.get(f"/assessments/{aid}/decks", cookie)
        deck_link = re.findall(rf'href="(/assessments/{aid}/decks/[0-9a-f-]{{36}})"', decks)
        self.assertTrue(deck_link)
        deck = self.get(deck_link[0], cookie)
        self.assertRegex(deck, r"\$\d")
        self.assertNotIn("Saved 20", deck.replace("<time", ""), "timestamps are not shown as raw ISO text")

    def test_official_baseline_is_unchanged_by_the_new_pages(self) -> None:
        cookie = self.sign_in("owner@pilot.example")
        page = self.get("/", cookie)
        self.assertNotIn("investor-ready</strong>", page)
        status, body, _headers = self.request("/audit", None, cookie)
        self.assertIn(status, (200, 302, 303, 403, 404))
        self.assertNotIn("human_review_approved: true", body)


if __name__ == "__main__":
    unittest.main()

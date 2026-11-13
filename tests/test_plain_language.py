"""Plain business wording on customer pages. Codes and results stay as stored."""

from __future__ import annotations

import json
import re
import unittest

from app import display, wording
from tests.test_advisory_server import AdvisoryServerCase


def _visible(page: str) -> str:
    """The text a customer reads without opening a Technical reference."""
    page = re.sub(r'(?is)<details class="[^"]*techref[^"]*".*?</details>', "", page)
    page = re.sub(r"(?is)<(script|style).*?</\1>", "", page)
    page = re.sub(r"(?s)<[^>]+>", " ", page)
    return re.sub(r"\s+", " ", page)


class TestWordingLayer(unittest.TestCase):
    def test_required_plain_terms(self) -> None:
        self.assertEqual(wording.gate_label("Blocked"), "Important information still needed")
        self.assertEqual(wording.band_label("Blocked"), "Assessment not yet ready")
        self.assertEqual(wording.title_of("INSUFFICIENT_DEMAND_EVIDENCE"), "Not enough evidence of customer demand")
        self.assertEqual(wording.PRELIMINARY, "Preliminary business evaluation")
        self.assertIn("Documented sales from an existing business", wording.field_label("revenue_trailing_12m"))

    def test_unknown_codes_still_get_readable_words(self) -> None:
        self.assertEqual(wording.gate_label("Something New"), "Something New")
        self.assertNotIn("_", wording.title_of("SOME_NEW_FLAG"))

    def test_every_finding_says_what_why_and_what_next(self) -> None:
        for code, item in wording.FINDINGS.items():
            with self.subTest(code=code):
                self.assertTrue(item.title and item.found and item.matters and item.todo)
                self.assertNotIn(code, item.title + item.found + item.matters + item.todo)
                self.assertTrue(item.links, "each finding names a place to go")

    def test_saved_text_is_translated_for_display_only(self) -> None:
        raw = "startup_base_dscr: -$0.69. Startup base DSCR. Copied from the stored projection."
        shown = wording.humanize_lines(raw)
        self.assertEqual(shown, "Loan coverage, typical year: -0.69×.")
        self.assertIn("startup_base_dscr", raw)  # the stored line is untouched
        self.assertEqual(wording.humanize_lines("human_review_approved: false"), "Authorized review approved: No")
        self.assertIn("Not enough evidence of customer demand", wording.humanize_lines("Open: INSUFFICIENT_DEMAND_EVIDENCE"))

    def test_coverage_ratios_are_not_shown_as_dollars(self) -> None:
        self.assertEqual(display.figure("startup_base_dscr", -0.6948), "-0.69×")
        self.assertEqual(display.figure("startup_downside_dscr", 1.25), "1.25×")

    def test_help_control_answers_three_questions(self) -> None:
        for key in wording.EXPLANATIONS:
            with self.subTest(key=key):
                html = wording.explain(key, "abc")
                for part in ("What it means.", "Why it matters.", "What to do."):
                    self.assertIn(part, html)
        self.assertIn('href="/assessments/abc/intelligence"', wording.explain("demand_evidence", "abc"))


class TestPlainPages(AdvisoryServerCase):
    def _analyzed(self) -> tuple[str, str]:
        cookie = self.sign_in("plain@pilot.example")
        aid = self.new_draft(cookie)
        self.request(f"/assessments/{aid}/analyze", {}, cookie)
        return cookie, aid

    def test_major_pages_use_plain_words_and_hide_codes(self) -> None:
        cookie, aid = self._analyzed()
        pages = {
            "dashboard": "/",
            "explore": f"/assessments/{aid}",
            "results": f"/assessments/{aid}/results",
            "improve": f"/assessments/{aid}/improve",
            "actions": f"/assessments/{aid}/actions",
        }
        for name, path in pages.items():
            status, body, _ = self.request(path, None, cookie)
            self.assertEqual(status, 200, name)
            text = _visible(body)
            with self.subTest(page=name):
                for jargon in ("INSUFFICIENT_DEMAND_EVIDENCE", "FINANCIAL_INPUTS_NOT_MEASURED", "UNEVALUATED_OPERATOR_CAPACITY", "Gate Blocked", "Band Blocked"):
                    self.assertNotIn(jargon, text)
        results = _visible(self.request(pages["results"], None, cookie)[1])
        self.assertIn("Not enough evidence of customer demand", results)
        self.assertIn("Important information still needed", results)
        self.assertIn("Assessment not yet ready", results)
        self.assertIn("Preliminary business evaluation", results)

    def test_blocking_finding_explains_what_why_and_where_to_go(self) -> None:
        cookie, aid = self._analyzed()
        body = self.request(f"/assessments/{aid}/results", None, cookie)[1]
        text = _visible(body)
        for label in ("What RUGD found", "Why it matters", "What you can do"):
            self.assertIn(label, text)
        self.assertIn(f'href="/assessments/{aid}/intelligence"', body)

    def test_next_step_links_open(self) -> None:
        cookie, aid = self._analyzed()
        seen: set[str] = set()
        for page in (f"/assessments/{aid}/results", f"/assessments/{aid}/improve", f"/assessments/{aid}"):
            body = self.request(page, None, cookie)[1]
            for href in re.findall(r'href="(/assessments/' + re.escape(aid) + r'[^"#]*)', body):
                seen.add(href)
        self.assertTrue(seen)
        wanted = {f"/assessments/{aid}/intelligence", f"/assessments/{aid}/improve", f"/assessments/{aid}/revenue-worksheet"}
        self.assertTrue(wanted & seen)
        for href in sorted(seen):
            if href.endswith(("/export", "/delete")) or "/print" in href:
                continue
            status = self.request(href, None, cookie)[0]
            with self.subTest(href=href):
                self.assertIn(status, (200, 303), href)

    def test_help_controls_appear_with_their_three_parts(self) -> None:
        cookie, aid = self._analyzed()
        for path in (f"/assessments/{aid}/results", f"/assessments/{aid}/improve", f"/assessments/{aid}/benchmarks"):
            body = self.request(path, None, cookie)[1]
            with self.subTest(path=path):
                self.assertIn('class="dh"', body)
                self.assertIn("What it means.", body)
                self.assertIn("Why it matters.", body)
                self.assertIn("What to do.", body)

    def test_codes_stay_in_the_data_and_the_technical_reference(self) -> None:
        cookie, aid = self._analyzed()
        stored_before = json.dumps(self.record(aid)["result"], sort_keys=True)
        body = self.request(f"/assessments/{aid}/results", None, cookie)[1]
        self.assertIn("INSUFFICIENT_DEMAND_EVIDENCE", body)  # kept, collapsed
        self.assertIn('data-gate="Blocked"', body)
        self.assertRegex(body, r'(?is)<details class="[^"]*techref[^"]*".*?INSUFFICIENT_DEMAND_EVIDENCE')
        for path in ("", "/results", "/improve", "/actions", "/advice"):
            self.request(f"/assessments/{aid}{path}", None, cookie)
        record = self.record(aid)
        self.assertEqual(json.dumps(record["result"], sort_keys=True), stored_before)
        self.assertIn("INSUFFICIENT_DEMAND_EVIDENCE", record["result"]["blocking_flags"])
        self.assertEqual(record["result"]["recommendation"], "do-not-proceed")
        self.assertEqual(record["result"]["readiness_status"], "internal")
        self.assertFalse(record["human_review_approved"])

    def test_no_customer_control_can_approve_a_review(self) -> None:
        cookie, aid = self._analyzed()
        for path in ("/", f"/assessments/{aid}", f"/assessments/{aid}/results", f"/assessments/{aid}/improve", "/validate"):
            body = self.request(path, None, cookie)[1]
            self.assertNotRegex(body, r'name="human_review_approved"', path)

    def test_a_blocked_assessment_stays_blocked_after_adding_notes(self) -> None:
        cookie, aid = self._analyzed()
        self.request(f"/assessments/{aid}/checklist", {"return_to": "results", "known_market-demand": "1", "check_market-demand": "1"}, cookie)
        record = self.record(aid)
        self.assertIn("INSUFFICIENT_DEMAND_EVIDENCE", record["result"]["blocking_flags"])
        self.assertEqual(record["result"]["recommendation"], "do-not-proceed")
        text = _visible(self.request(f"/assessments/{aid}/results", None, cookie)[1])
        self.assertIn("Not enough evidence of customer demand", text)

    def test_saved_plan_and_report_use_plain_labels(self) -> None:
        cookie, aid = self._analyzed()
        self.request(f"/assessments/{aid}/reports", {}, cookie)
        self.request(f"/assessments/{aid}/plans", {}, cookie)
        for kind in ("reports", "plans"):
            listing = self.request(f"/assessments/{aid}/{kind}", None, cookie)[1]
            found = re.findall(rf"/assessments/{aid}/{kind}/[0-9a-f-]{{36}}", listing)
            self.assertTrue(found, kind)
            page = self.request(found[0], None, cookie)[1]
            text = _visible(page)
            with self.subTest(kind=kind):
                self.assertNotIn("base_monthly_cash_flow", text)
                self.assertNotIn("human_review_approved", text)
                self.assertNotIn("startup_base_dscr", text)


if __name__ == "__main__":
    unittest.main()

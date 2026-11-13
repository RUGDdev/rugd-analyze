"""Editable assumptions, preview, approval, funding gap, and result history.

The calculation under test is the one Analyze uses. These tests check that the new
workspace never writes an official result, never sets human review, and never turns
a blank into a zero.
"""

from __future__ import annotations

import json
import re
import unittest

from app import assumptions as asm
from app.analysis import analyze_record
from app.store import BASELINE_ID, RESTAURANT_ID, get_assessment, list_official_results
from tests.test_advisory_server import PROFILE, AdvisoryServerCase

EXAMPLE = {"a_equipment": "365000", "a_soft_costs": "225000", "a_preopening_working_capital": "200000"}
HYPOTHETICAL = {"b_equipment": "hypothetical", "b_soft_costs": "hypothetical", "b_preopening_working_capital": "hypothetical"}
BARE = {key: value for key, value in PROFILE.items() if key not in {"equipment", "soft_costs"}}


def _stamp(page: str) -> str:
    match = re.search(r'name="base" value="([0-9a-f]+)"', page)
    assert match, "no base stamp on the page"
    return match.group(1)


class TestAssumptionLogic(unittest.TestCase):
    def test_missing_zero_and_entered_are_three_different_states(self) -> None:
        profile = {"equipment": "", "soft_costs": "0", "construction_cost": "1800000", "contingency_pct": "0.10", "available_cash": ""}
        self.assertEqual(asm.field_status(profile, "equipment")["state"], "missing")
        self.assertIn("counts it as $0", asm.field_status(profile, "equipment")["text"])
        self.assertEqual(asm.field_status(profile, "soft_costs")["state"], "zero")
        self.assertIn("on purpose", asm.field_status(profile, "soft_costs")["text"])
        self.assertEqual(asm.field_status(profile, "construction_cost")["state"], "estimated")
        # Equal to the built-in default: shown as a starting number, not as the customer's own figure.
        self.assertEqual(asm.field_status(profile, "contingency_pct")["state"], "placeholder")
        cash = asm.field_status(profile, "available_cash")
        self.assertEqual(cash["state"], "missing")
        self.assertIn("not treated as $0", cash["text"])

    def test_a_zero_downside_multiplier_names_the_monthly_view_quirk(self) -> None:
        text = asm.field_status({"downside_multiplier": "0"}, "downside_multiplier")["text"]
        self.assertIn("monthly view treats 0 as not entered", text)

    def test_preview_uses_the_same_calculation_as_analyze(self) -> None:
        for profile in (dict(PROFILE), dict(PROFILE, equipment="365000", soft_costs="225000", preopening_working_capital="200000")):
            record = {"id": "x", "profile": profile, "business_name": "t", "purpose": "startup_feasibility", "tier": "explore",
                      "read_only": False, "hypothetical": True, "intake": None, "result": None, "human_review_approved": False}
            official = analyze_record(record)
            self.assertEqual(asm.official_measures(official), asm.run(profile)["measures"])

    def test_hypothetical_example_changes_the_total_by_the_arithmetic(self) -> None:
        base = asm.run(PROFILE)["measures"]["total_project_cost"]
        proposal = asm.read_proposal(PROFILE, {**EXAMPLE}, {})
        after = asm.run(proposal["profile"])["measures"]["total_project_cost"]
        # (365000-250000 + 225000-120000 + 200000) x 1.10 default contingency
        self.assertAlmostEqual(after - base, 420000 * 1.10, places=2)

    def test_reading_a_form(self) -> None:
        proposal = asm.read_proposal(PROFILE, {"a_equipment": "$365,000", "a_soft_costs": "120000", "a_seats": "abc", "a_debt_share": "1.5",
                                                "a_average_ticket": "-3", "a_construction_cost": "", "a_annual_fixed_costs": ""}, {})
        self.assertEqual([item["field"] for item in proposal["changes"]], ["equipment", "annual_fixed_costs"])
        self.assertEqual(proposal["profile"]["equipment"], "365000")
        self.assertEqual(proposal["profile"]["annual_fixed_costs"], "")
        self.assertEqual(proposal["profile"]["soft_costs"], PROFILE["soft_costs"])
        self.assertEqual(set(proposal["errors"]), {"seats", "debt_share", "average_ticket", "construction_cost"})
        self.assertEqual(proposal["profile"]["construction_cost"], PROFILE["construction_cost"])
        # The saved profile object is never edited in place.
        self.assertEqual(PROFILE["equipment"], "250000")

    def test_only_the_listed_assumptions_can_change(self) -> None:
        proposal = asm.read_proposal(PROFILE, {"a_human_review_approved": "true", "a_total_project_cost": "1", "human_review_approved": "true",
                                                "a_business_name": "X"}, {})
        self.assertEqual(proposal["changes"], [])
        self.assertEqual(proposal["profile"], PROFILE)

    def test_zero_is_a_change_from_blank(self) -> None:
        proposal = asm.read_proposal(PROFILE, {"a_preopening_working_capital": "0"}, {})
        self.assertEqual([(item["field"], item["to"]) for item in proposal["changes"]], [("preopening_working_capital", "0")])
        self.assertEqual(asm.field_status(proposal["profile"], "preopening_working_capital")["state"], "zero")

    def test_funding_gap_arithmetic(self) -> None:
        values = {"total_project_cost": 1000.0, "debt": 700.0, "equity": 300.0}
        self.assertEqual(asm.funding_gap(values, 100.0)["remaining"], 200.0)
        covered = asm.funding_gap(values, 450.0)
        self.assertEqual((covered["remaining"], covered["left_over"]), (0.0, 150.0))
        missing = asm.funding_gap(values, None)
        self.assertIsNone(missing["remaining"])
        self.assertIsNone(missing["cash"])
        self.assertFalse(asm.funding_gap({}, 5.0)["calculated"])

    def test_example_is_for_restaurants_and_blank_lines_only(self) -> None:
        self.assertEqual(asm.example_for(BARE), {"equipment": "365000", "soft_costs": "225000", "preopening_working_capital": "200000"})
        self.assertEqual(asm.example_for(PROFILE), {"preopening_working_capital": "200000"})
        self.assertEqual(asm.example_for(dict(BARE, industry="Software subscription")), {})
        self.assertIn("not industry standards", asm.EXAMPLE_NOTE)

    def test_basis_follows_the_value_it_labeled(self) -> None:
        basis = {"equipment": {"basis": "hypothetical", "value": "365000", "at": ""}}
        self.assertEqual(asm.stored_basis(basis, {"equipment": "365000"}, "equipment"), "hypothetical")
        self.assertEqual(asm.stored_basis(basis, {"equipment": "365000.0"}, "equipment"), "hypothetical")
        self.assertEqual(asm.stored_basis(basis, {"equipment": "300000"}, "equipment"), "")
        self.assertEqual(asm.stored_basis(basis, {"equipment": ""}, "equipment"), "")


class TestAssumptionPages(AdvisoryServerCase):
    def analyzed(self, cookie: str, profile: dict | None = None) -> str:
        assessment_id = self.new_draft(cookie, profile)
        self.assertEqual(self.request(f"/assessments/{assessment_id}/analyze", {}, cookie)[0], 303)
        return assessment_id

    def stored_result(self, assessment_id: str) -> str:
        return self.connection.execute("SELECT result_json FROM assessments WHERE id = ?", (assessment_id,)).fetchone()[0]

    def records(self, kind: str) -> int:
        return self.connection.execute("SELECT COUNT(*) FROM advisory_records WHERE kind = ?", (kind,)).fetchone()[0]

    def test_the_page_edits_assumptions_and_never_calculated_outputs(self) -> None:
        cookie = self.sign_in("owner@pilot.example")
        assessment_id = self.analyzed(cookie)
        status, page, _h = self.request(f"/assessments/{assessment_id}/assumptions", None, cookie)
        self.assertEqual(status, 200)
        for key in asm.EDITABLE:
            self.assertIn(f'name="a_{key}"', page, key)
            self.assertIn(f'name="b_{key}"', page, key)
            self.assertIn(f'data-help="{key}"', page, key)
        for output in ("total_project_cost", "debt", "equity", "annual_debt_service", "base_dscr", "downside_dscr", "break_even_revenue"):
            self.assertNotIn(f'name="a_{output}"', page, output)
        for words in ("Official assessment", "Working draft", "Proposed", "Preview"):
            self.assertIn(f"<b>{words}</b>", page)
        self.assertIn(f"/assessments/{assessment_id}/benchmarks", page)
        self.assertIn(f"/assessments/{assessment_id}/improve", page)
        self.assertIn("A sourced benchmark is a figure with a named source", page)
        self.assertNotIn("Review and approve", page)

    def test_preview_shows_before_and_after_and_saves_nothing(self) -> None:
        cookie = self.sign_in("owner@pilot.example")
        assessment_id = self.analyzed(cookie)
        before = self.stored_result(assessment_id)
        profile_before = self.record(assessment_id)["profile"]
        status, page, _h = self.request(f"/assessments/{assessment_id}/assumptions", {"op": "calculate", **EXAMPLE, **HYPOTHETICAL}, cookie)
        self.assertEqual(status, 200)
        self.assertIn("$2,387,000", page)  # official and working draft
        self.assertIn("$2,849,000", page)  # proposed preview
        self.assertIn("+$462,000", page)
        self.assertIn("Not saved", page)
        self.assertIn("Review and approve", page)
        self.assertEqual(self.record(assessment_id)["profile"], profile_before)
        self.assertEqual(self.stored_result(assessment_id), before)
        for kind in ("assumption_change", "assumption_basis"):
            self.assertEqual(self.records(kind), 0)
        self.assertEqual(self.connection.execute("SELECT COUNT(*) FROM official_results WHERE assessment_id = ?", (assessment_id,)).fetchone()[0], 1)

    def test_the_live_preview_fragment_is_only_the_panel(self) -> None:
        cookie = self.sign_in("owner@pilot.example")
        assessment_id = self.new_draft(cookie)
        status, fragment, headers = self.request(
            f"/assessments/{assessment_id}/assumptions", {"op": "calculate", "fragment": "1", **EXAMPLE}, cookie
        )
        self.assertEqual(status, 200)
        self.assertIn("text/html", headers["Content-Type"])
        self.assertNotIn("<html", fragment)
        self.assertIn('id="preview-card"', fragment)
        self.assertIn("$2,849,000", fragment)
        self.assertEqual(self.record(assessment_id)["profile"]["equipment"], "250000")

    def test_saving_needs_approval_and_changes_only_the_working_draft(self) -> None:
        cookie = self.sign_in("owner@pilot.example")
        assessment_id = self.analyzed(cookie)
        before = self.stored_result(assessment_id)
        stamp = _stamp(self.request(f"/assessments/{assessment_id}/assumptions", None, cookie)[1])
        data = {"op": "apply", "base": stamp, **EXAMPLE, **HYPOTHETICAL}
        status, page, _h = self.request(f"/assessments/{assessment_id}/assumptions", data, cookie)
        self.assertEqual(status, 400)
        self.assertIn("Tick the box to approve", page)
        self.assertEqual(self.record(assessment_id)["profile"]["equipment"], "250000")
        self.assertEqual(self.records("assumption_change"), 0)

        # A customer control can never set human review: the request is refused outright.
        refused = self.request(f"/assessments/{assessment_id}/assumptions", {**data, "confirm": "yes", "human_review_approved": "true"}, cookie)
        self.assertEqual(refused[0], 403)
        self.assertEqual(self.record(assessment_id)["profile"]["equipment"], "250000")
        status, page, _h = self.request(
            f"/assessments/{assessment_id}/assumptions", {**data, "confirm": "yes", "a_human_review_approved": "true"}, cookie
        )
        self.assertEqual(status, 200)
        self.assertIn("Saved 3 changes to your working draft", page)
        saved = self.record(assessment_id)
        self.assertEqual(
            (saved["profile"]["equipment"], saved["profile"]["soft_costs"], saved["profile"]["preopening_working_capital"]),
            ("365000", "225000", "200000"),
        )
        raw = json.loads(self.connection.execute("SELECT profile_json FROM assessments WHERE id = ?", (assessment_id,)).fetchone()[0])
        self.assertIs(raw["human_review_approved"], False)
        self.assertFalse(saved["human_review_approved"])
        # The official result, its flags, and its review status are exactly as they were.
        self.assertEqual(self.stored_result(assessment_id), before)
        official = saved["result"]
        self.assertIn("INSUFFICIENT_DEMAND_EVIDENCE", official["blocking_flags"])
        self.assertEqual(official["readiness_status"], "internal")
        self.assertEqual(official["recommendation"], "do-not-proceed")
        # History and labels were recorded, with an audit event.
        self.assertEqual(self.records("assumption_change"), 1)
        basis = json.loads(self.connection.execute("SELECT payload_json FROM advisory_records WHERE kind = 'assumption_basis'").fetchone()[0])
        self.assertEqual(basis["fields"]["equipment"]["basis"], "hypothetical")
        self.assertEqual(basis["fields"]["equipment"]["value"], "365000")
        audit = [row["action"] for row in self.connection.execute("SELECT action FROM audit_events WHERE assessment_id = ?", (assessment_id,))]
        self.assertIn("assumptions_saved", audit)
        self.assertIn("Hypothetical values in your draft", page)
        self.assertIn("Equipment: $250,000 to $365,000 (Hypothetical)", page)

    def test_key_numbers_keeps_describing_the_official_run_until_a_new_assessment(self) -> None:
        cookie = self.sign_in("owner@pilot.example")
        assessment_id = self.analyzed(cookie)
        stamp = _stamp(self.request(f"/assessments/{assessment_id}/assumptions", None, cookie)[1])
        self.request(f"/assessments/{assessment_id}/assumptions", {"op": "apply", "base": stamp, "confirm": "yes", **EXAMPLE, **HYPOTHETICAL}, cookie)
        page = self.request(f"/assessments/{assessment_id}/results", None, cookie)[1]
        self.assertIn("Your working draft is different from the official assessment", page)
        self.assertIn("$2,387,000", page)
        self.assertNotIn("$2,849,000", page)
        # The draft's hypothetical labels do not relabel the official figures, which used other values.
        uses = page.split("<h3>Uses of money", 1)[1].split("<h3>Sources and financing", 1)[0]
        self.assertNotIn("dchip-hypothetical", uses)
        # Running a new assessment is an explicit action, and the earlier result is kept.
        self.assertEqual(self.request(f"/assessments/{assessment_id}/analyze", {}, cookie)[0], 303)
        page = self.request(f"/assessments/{assessment_id}/results", None, cookie)[1]
        self.assertNotIn("Your working draft is different from the official assessment", page)
        self.assertIn("$2,849,000", page)
        uses = page.split("<h3>Uses of money", 1)[1].split("<h3>Sources and financing", 1)[0]
        self.assertIn("dchip-hypothetical", uses)
        history = list_official_results(self.connection, assessment_id)
        self.assertEqual(len(history), 2)
        self.assertIsNone(history[0]["superseded_at"])
        self.assertIsNotNone(history[1]["superseded_at"])
        self.assertEqual(history[1]["result"]["projection"]["sources_and_uses"]["uses"]["total_project_cost"]["amount"], 2387000.0)
        self.assertEqual(history[0]["result"]["projection"]["sources_and_uses"]["uses"]["total_project_cost"]["amount"], 2849000.0)
        assumptions = self.request(f"/assessments/{assessment_id}/assumptions", None, cookie)[1]
        self.assertIn("Current official result", assumptions)
        self.assertIn("Previous official result", assumptions)
        self.assertIn("$2,387,000", assumptions)

    def test_an_older_result_with_no_history_is_kept_when_replaced(self) -> None:
        cookie = self.sign_in("owner@pilot.example")
        assessment_id = self.analyzed(cookie)
        self.connection.execute("DELETE FROM official_results")
        self.connection.commit()
        original = self.stored_result(assessment_id)
        self.assertEqual(self.request(f"/assessments/{assessment_id}/analyze", {}, cookie)[0], 303)
        history = list_official_results(self.connection, assessment_id)
        self.assertEqual(len(history), 2)
        self.assertIsNone(history[1]["saved_at"])
        self.assertEqual(json.dumps(history[1]["result"]), json.dumps(json.loads(original)))

    def test_a_draft_that_changed_after_the_page_opened_is_not_overwritten(self) -> None:
        cookie = self.sign_in("owner@pilot.example")
        assessment_id = self.new_draft(cookie)
        old = _stamp(self.request(f"/assessments/{assessment_id}/assumptions", None, cookie)[1])
        self.request(f"/assessments/{assessment_id}/assumptions", {"op": "apply", "base": old, "confirm": "yes", "a_seats": "70"}, cookie)
        self.assertEqual(self.record(assessment_id)["profile"]["seats"], "70")
        status, page, _h = self.request(
            f"/assessments/{assessment_id}/assumptions", {"op": "apply", "base": old, "confirm": "yes", "a_seats": "80"}, cookie
        )
        self.assertEqual(status, 409)
        self.assertIn("Your draft changed after this page was opened", page)
        self.assertEqual(self.record(assessment_id)["profile"]["seats"], "70")

    def test_blank_and_zero_are_shown_and_saved_differently(self) -> None:
        cookie = self.sign_in("owner@pilot.example")
        assessment_id = self.analyzed(cookie)
        page = self.request(f"/assessments/{assessment_id}/assumptions", None, cookie)[1]
        self.assertIn("Not entered. The calculation counts it as $0", page)
        key_numbers = self.request(f"/assessments/{assessment_id}/results", None, cookie)[1]
        self.assertIn("Not entered, counted as $0", key_numbers)
        self.assertNotIn("Pre-opening working capital</th><td class=num>$0 <span class=\"dchip dchip-zero\"", key_numbers)
        # Typing 0 is a deliberate value, not a blank.
        stamp = _stamp(page)
        data = {"op": "apply", "base": stamp, "confirm": "yes", "a_preopening_working_capital": "0"}
        status, saved, _h = self.request(f"/assessments/{assessment_id}/assumptions", data, cookie)
        self.assertEqual(status, 200)
        self.assertEqual(self.record(assessment_id)["profile"]["preopening_working_capital"], "0")
        self.assertIn("Entered as 0 on purpose", saved)
        self.request(f"/assessments/{assessment_id}/analyze", {}, cookie)
        key_numbers = self.request(f"/assessments/{assessment_id}/results", None, cookie)[1]
        self.assertIn("Entered as zero", key_numbers)
        self.assertNotIn("Not entered, counted as $0", key_numbers)

    def test_an_optional_line_can_go_back_to_not_entered_but_a_needed_one_cannot(self) -> None:
        cookie = self.sign_in("owner@pilot.example")
        assessment_id = self.new_draft(cookie)
        stamp = _stamp(self.request(f"/assessments/{assessment_id}/assumptions", None, cookie)[1])
        status, page, _h = self.request(
            f"/assessments/{assessment_id}/assumptions", {"op": "apply", "base": stamp, "confirm": "yes", "a_construction_cost": "", "a_seats": "61"}, cookie
        )
        self.assertEqual(status, 400)
        self.assertIn("cannot be cleared", page)
        self.assertEqual(self.record(assessment_id)["profile"]["construction_cost"], "1800000")
        self.assertEqual(self.record(assessment_id)["profile"]["seats"], "60")
        status, _page, _h = self.request(
            f"/assessments/{assessment_id}/assumptions", {"op": "apply", "base": stamp, "confirm": "yes", "a_equipment": ""}, cookie
        )
        self.assertEqual(status, 200)
        self.assertEqual(self.record(assessment_id)["profile"]["equipment"], "")

    def test_bad_entries_are_reported_escaped_and_never_saved(self) -> None:
        cookie = self.sign_in("owner@pilot.example")
        assessment_id = self.new_draft(cookie)
        stamp = _stamp(self.request(f"/assessments/{assessment_id}/assumptions", None, cookie)[1])
        data = {"op": "apply", "base": stamp, "confirm": "yes", "a_debt_share": "1.5", "a_seats": "<script>alert(1)</script>",
                "a_average_ticket": "-3", "a_equipment": "1e99", "a_operating_days": "400", "a_amortization_years": "7.5"}
        status, page, _h = self.request(f"/assessments/{assessment_id}/assumptions", data, cookie)
        self.assertEqual(status, 400)
        self.assertNotIn("<script>alert(1)</script>", page)
        self.assertIn("&lt;script&gt;alert(1)&lt;/script&gt;", page)
        for message in ("Debt share must be from 0 to 1", "Seats must be a number", "Average ticket cannot be negative", "Equipment is too large",
                        "Operating days (per year) must be above 0 and at most 366", "Repayment term (years) must be a whole number"):
            self.assertIn(message, page)
        self.assertEqual(self.record(assessment_id)["profile"]["seats"], "60")
        self.assertEqual(self.records("assumption_change"), 0)

    def test_funding_gap_distinguishes_cash_from_equity(self) -> None:
        cookie = self.sign_in("owner@pilot.example")
        assessment_id = self.new_draft(cookie)
        page = self.request(f"/assessments/{assessment_id}/assumptions", None, cookie)[1]
        self.assertIn("Remaining funding requirement", page)
        self.assertIn("$716,100", page)  # equity
        self.assertIn("$566,100", page)  # equity less the $150,000 cash in the draft
        covered = self.request(f"/assessments/{assessment_id}/assumptions", {"op": "calculate", "a_available_cash": "800000"}, cookie)[1]
        self.assertIn("None. Your cash covers the equity, with $83,900 to spare.", covered)
        blank = self.request(f"/assessments/{assessment_id}/assumptions", {"op": "calculate", "a_available_cash": ""}, cookie)[1]
        self.assertIn("Not calculated. Enter the cash you can put in.", blank)
        self.assertIn("Not entered", blank)
        self.assertEqual(self.record(assessment_id)["profile"]["available_cash"], "150000")

    def test_key_numbers_gets_edit_links_and_a_funding_gap(self) -> None:
        cookie = self.sign_in("owner@pilot.example")
        assessment_id = self.analyzed(cookie)
        page = self.request(f"/assessments/{assessment_id}/results", None, cookie)[1]
        for section in ("project-costs", "financing", "revenue", "operating", "monthly"):
            self.assertIn(f'data-edit-assumptions="{section}"', page, section)
            self.assertIn(f"/assessments/{assessment_id}/assumptions#{section}", page)
        self.assertIn('id="planning-strip"', page)
        self.assertIn('id="funding-gap"', page)
        gap = page.split('id="funding-gap"', 1)[1].split("</div>", 2)[0]
        for words in ("Total project cost", "Proposed debt financing", "Equity required", "Your available cash", "Remaining funding requirement"):
            self.assertIn(words, gap)
        self.assertIn("$566,100", gap)
        self.assertNotIn("name=\"a_", page)

    def test_the_restaurant_example_fills_the_form_and_saves_nothing(self) -> None:
        cookie = self.sign_in("owner@pilot.example")
        assessment_id = self.new_draft(cookie, BARE)
        profile_before = self.record(assessment_id)["profile"]
        page = self.request(f"/assessments/{assessment_id}/assumptions", None, cookie)[1]
        self.assertIn('value="example"', page)
        status, filled, _h = self.request(f"/assessments/{assessment_id}/assumptions", {"op": "example"}, cookie)
        self.assertEqual(status, 200)
        for key, value in {"equipment": "365000", "soft_costs": "225000", "preopening_working_capital": "200000"}.items():
            self.assertRegex(filled, rf'id="a_{key}" name="a_{key}"[^>]*value="{value}"')
            self.assertRegex(filled, rf'<select id="b_{key}" name="b_{key}"[^>]*>.*?<option value="hypothetical" selected>')
        self.assertIn("Nothing was saved", filled)
        self.assertIn("not industry standards", filled)
        self.assertEqual(self.record(assessment_id)["profile"], profile_before)
        self.assertEqual(self.records("assumption_basis"), 0)
        # A value the customer already typed is not overwritten by the example.
        typed = self.request(f"/assessments/{assessment_id}/assumptions", {"op": "example", "a_equipment": "300000"}, cookie)[1]
        self.assertRegex(typed, r'id="a_equipment" name="a_equipment"[^>]*value="300000"')
        # Other industries get no restaurant example.
        software = self.new_draft(cookie, dict(BARE, industry="Software subscription"))
        self.assertNotIn('value="example"', self.request(f"/assessments/{software}/assumptions", None, cookie)[1])

    def test_money_and_ratios_are_formatted_for_people(self) -> None:
        cookie = self.sign_in("owner@pilot.example")
        assessment_id = self.analyzed(cookie)
        page = self.request(f"/assessments/{assessment_id}/assumptions", {"op": "calculate", **EXAMPLE}, cookie)[1]
        visible = re.sub(r"<[^>]+>", " ", page.split('id="preview-card"', 1)[1].split("Run a new assessment", 1)[0])
        self.assertIn("$2,849,000", visible)
        self.assertIn("$200,173.44", visible)
        self.assertRegex(visible, r"-?\d\.\d\d×")
        self.assertNotRegex(visible, r"\d{7,}\.0\b")
        self.assertNotIn("nan", visible.lower().replace("financing", ""))
        self.assertNotIn("None ", visible.replace("None. Your cash", ""))

    def test_layout_adapts_to_small_screens(self) -> None:
        cookie = self.sign_in("owner@pilot.example")
        assessment_id = self.new_draft(cookie)
        page = self.request(f"/assessments/{assessment_id}/assumptions", None, cookie)[1]
        self.assertIn('name="viewport"', page)
        self.assertRegex(page, r"@media \(max-width: 800px\)\s*\{\s*\.asm \.asm-row \{ grid-template-columns: 1fr; \}")
        self.assertIn("overflow-x: auto", page)  # the shared table wrapper scrolls instead of overflowing

    def test_one_account_cannot_read_or_change_another_accounts_assumptions(self) -> None:
        owner = self.sign_in("owner@pilot.example")
        other = self.sign_in("other@pilot.example")
        assessment_id = self.analyzed(owner)
        stamp = _stamp(self.request(f"/assessments/{assessment_id}/assumptions", None, owner)[1])
        self.request(f"/assessments/{assessment_id}/assumptions", {"op": "apply", "base": stamp, "confirm": "yes", **EXAMPLE, **HYPOTHETICAL}, owner)
        before = json.dumps(self.record(assessment_id), sort_keys=True, default=str)
        attempts = (
            None,
            {"op": "calculate", **EXAMPLE},
            {"op": "calculate", "fragment": "1", **EXAMPLE},
            {"op": "example"},
            {"op": "apply", "base": stamp, "confirm": "yes", "a_seats": "10"},
        )
        for data in attempts:
            status, page, _h = self.request(f"/assessments/{assessment_id}/assumptions", data, other)
            self.assertIn(status, (403, 404), data)
            self.assertNotIn("Riverside Table", page)
            self.assertNotIn("$2,849,000", page)
            self.assertNotIn("Hypothetical", page)
        self.assertIn(self.request(f"/assessments/{assessment_id}/assumptions")[0], (302, 303, 401, 403, 404))
        self.assertEqual(json.dumps(self.record(assessment_id), sort_keys=True, default=str), before)
        self.assertEqual(self.records("assumption_change"), 1)

    def test_a_reader_may_preview_a_shared_record_but_not_save(self) -> None:
        reader = self.sign_in("reader@pilot.example")
        status, page, _h = self.request(f"/assessments/{RESTAURANT_ID}/assumptions", None, reader)
        self.assertEqual(status, 200)
        self.assertIn("Preview only.", page)
        self.assertNotIn('value="example"', page)
        self.assertNotIn("Run a new assessment with my working draft", page)
        self.assertEqual(self.request(f"/assessments/{RESTAURANT_ID}/assumptions", {"op": "calculate", "a_seats": "10"}, reader)[0], 200)
        for data in ({"op": "apply", "confirm": "yes", "a_seats": "10"}, {"op": "example"}):
            self.assertEqual(self.request(f"/assessments/{RESTAURANT_ID}/assumptions", data, reader)[0], 403)

    def test_existing_restaurant_assessment_previews_with_the_official_numbers(self) -> None:
        reader = self.sign_in("reader@pilot.example")
        record = get_assessment(self.connection, RESTAURANT_ID)
        before = json.dumps(record, sort_keys=True, default=str)
        profile = record["profile"]
        self.assertEqual(asm.run(profile)["measures"].get("total_project_cost"), asm.official_measures(analyze_record(record)).get("total_project_cost"))
        page = self.request(f"/assessments/{RESTAURANT_ID}/assumptions", {"op": "calculate"}, reader)[1]
        self.assertIn("Before and after", page)
        self.assertEqual(json.dumps(get_assessment(self.connection, RESTAURANT_ID), sort_keys=True, default=str), before)

    def test_official_baseline_is_untouched(self) -> None:
        cookie = self.sign_in("owner@pilot.example")
        before = json.dumps(get_assessment(self.connection, BASELINE_ID), sort_keys=True, default=str)
        self.assertEqual(self.request(f"/assessments/{BASELINE_ID}/assumptions", None, cookie)[0], 200)
        self.assertEqual(self.request(f"/assessments/{BASELINE_ID}/assumptions", {"op": "calculate", "a_seats": "10"}, cookie)[0], 200)
        for data in ({"op": "apply", "confirm": "yes", "a_seats": "10"}, {"op": "example"}):
            self.assertEqual(self.request(f"/assessments/{BASELINE_ID}/assumptions", data, cookie)[0], 403)
        self.assertEqual(json.dumps(get_assessment(self.connection, BASELINE_ID), sort_keys=True, default=str), before)
        baseline = get_assessment(self.connection, BASELINE_ID)
        official = analyze_record(baseline)
        self.assertIn("INSUFFICIENT_DEMAND_EVIDENCE", official["blocking_flags"])
        self.assertEqual(official["readiness_status"], "internal")
        self.assertEqual(official["recommendation"], "do-not-proceed")
        self.assertFalse(official["human_review_approved"])
        self.assertEqual(self.connection.execute("SELECT COUNT(*) FROM official_results WHERE assessment_id = ?", (BASELINE_ID,)).fetchone()[0], 0)


if __name__ == "__main__":
    unittest.main()

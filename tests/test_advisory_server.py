"""Benchmarks, suggestions, the revenue worksheet, and scenarios through the running server."""

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
from app.analysis import analyze_record
from app.server import make_server
from app.store import BASELINE_ID, RESTAURANT_ID, connect, get_assessment, seed, set_email_verified

PROFILE = {
    "business_name": "Riverside Table",
    "industry": "Restaurant",
    "market": "Colbert County, Alabama",
    "service_style": "full_service",
    "seats": "60",
    "average_ticket": "22",
    "weekday_occupancy": "0.40",
    "weekend_occupancy": "0.65",
    "operating_days": "340",
    "construction_cost": "1800000",
    "equipment": "250000",
    "soft_costs": "120000",
    "contribution_margin": "0.30",
    "annual_fixed_costs": "180000",
    "available_cash": "150000",
    "initial_capital": "180000",
    "monthly_fixed_costs": "12000",
    "gross_margin_pct": "0.62",
    "projected_monthly_revenue_base": "28000",
}


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: ARG002
        try:
            fp.close()
        except Exception:
            pass
        return None


class AdvisoryServerCase(unittest.TestCase):
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

    def request(self, path: str, data: dict | None = None, cookie: str = "") -> tuple[int, str, dict]:
        body = None if data is None else urllib.parse.urlencode(data).encode()
        headers = {"Cookie": cookie} if cookie else {}
        request = urllib.request.Request(self.base + path, data=body, headers=headers, method="GET" if data is None else "POST")
        try:
            response = urllib.request.build_opener(_NoRedirect).open(request)
        except urllib.error.HTTPError as exc:
            response = exc
        try:
            status = response.status if hasattr(response, "status") else response.code
            return status, response.read().decode("utf-8", "replace"), dict(response.headers)
        finally:
            response.close()

    def sign_in(self, email: str) -> str:
        user = register_account(self.connection, email=email, password="session-pass-1")
        set_email_verified(self.connection, user["id"])
        _s, _b, headers = self.request("/login", {"email": email, "password": "session-pass-1"})
        return (headers.get("Set-Cookie") or "").split(";", 1)[0]

    def new_draft(self, cookie: str, profile: dict | None = None) -> str:
        created = self.request(
            "/assessments",
            {"business_name": "Riverside Table", "venture_path": "startup", "purpose": "startup_feasibility"},
            cookie,
        )
        assessment_id = created[2]["Location"].rstrip("/").rsplit("/", 1)[-1]
        saved = self.request(
            f"/assessments/{assessment_id}/save",
            {"guided_save": "1", "inputs_are_measured": "", **(profile or PROFILE)},
            cookie,
        )
        self.assertEqual(saved[0], 200, saved[1])
        return assessment_id

    def record(self, assessment_id: str) -> dict:
        record = get_assessment(self.connection, assessment_id)
        assert record is not None
        return record


class TestPagesAndIntake(AdvisoryServerCase):
    def test_guided_save_returns_suggestion_cards_for_the_fields(self) -> None:
        cookie = self.sign_in("owner@pilot.example")
        assessment_id = self.new_draft(cookie)
        status, body, _h = self.request(
            f"/assessments/{assessment_id}/save", {"guided_save": "1", **PROFILE}, cookie
        )
        payload = json.loads(body)
        self.assertTrue(payload["saved"])
        advice = payload["advice"]
        self.assertIn("No average-check benchmark for Colbert County, Alabama", advice["average_ticket"])
        self.assertIn("Debt share from your cash", advice["debt_share"])
        self.assertIn('data-act="dismiss"', advice["average_ticket"])
        page = self.request(f"/assessments/{assessment_id}", None, cookie)[1]
        self.assertIn('data-advice-for="debt_share"', page)
        self.assertIn("Venue and cash (optional)", page)
        self.assertIn('id="help-available_cash"', page)
        self.assertIn("Source and reasoning", page)
        self.assertIn("/improve", page)

    def test_new_fields_save_and_do_not_set_review_status(self) -> None:
        cookie = self.sign_in("owner@pilot.example")
        assessment_id = self.new_draft(cookie, dict(PROFILE, venue_sqft="3200", construction_scope="renovation", staff_fte="9", avg_hourly_wage="17"))
        record = self.record(assessment_id)
        self.assertEqual(record["profile"]["venue_sqft"], "3200")
        self.assertEqual(record["profile"]["construction_scope"], "renovation")
        self.assertFalse(record["human_review_approved"])
        self.assertIsNone(record["result"])

    def test_forged_review_approval_is_rejected_on_every_new_route(self) -> None:
        cookie = self.sign_in("owner@pilot.example")
        assessment_id = self.new_draft(cookie)
        for path in ("improve", "benchmarks", "revenue-worksheet", "suggestions"):
            status, _b, _h = self.request(f"/assessments/{assessment_id}/{path}", {"op": "save", "human_review_approved": "true"}, cookie)
            self.assertEqual(status, 403, path)
        self.assertFalse(self.record(assessment_id)["human_review_approved"])

    def test_results_page_links_to_improvement_planner_after_analyze(self) -> None:
        cookie = self.sign_in("owner@pilot.example")
        assessment_id = self.new_draft(cookie)
        status, body, headers = self.request(f"/assessments/{assessment_id}/analyze", {}, cookie)
        if status in (301, 302, 303):
            body = self.request(headers["Location"], None, cookie)[1]
        self.assertIn('id="analyze-dashboard"', body)
        self.assertIn(f"/assessments/{assessment_id}/improve", body)
        self.assertIn(f"/assessments/{assessment_id}/benchmarks", body)

    def test_nonrestaurant_benchmark_page_says_nothing_is_loaded(self) -> None:
        cookie = self.sign_in("owner@pilot.example")
        assessment_id = self.new_draft(cookie, dict(PROFILE, industry="Software subscription", market="Huntsville, Alabama", service_style=""))
        page = self.request(f"/assessments/{assessment_id}/benchmarks", None, cookie)[1]
        self.assertIn("No benchmark is loaded for Software subscription", page)
        self.assertIn("RUGD does not estimate one", page)
        self.assertIn("Record a figure or build your own assumption", page)
        self.assertNotIn("National Restaurant Association's annual survey", page.split("<h2>Stored figures</h2>")[1].split("<h2>Not loaded</h2>")[0])

    def test_restaurant_benchmark_page_shows_properties_flags_and_the_conflict(self) -> None:
        cookie = self.sign_in("owner@pilot.example")
        assessment_id = self.new_draft(cookie, dict(PROFILE, service_style=""))
        page = self.request(f"/assessments/{assessment_id}/benchmarks", None, cookie)[1]
        for text in (
            "secondary industry benchmark",
            "National median. Not specific to Colbert County, Alabama.",
            "Full-service food and beverage cost: not loaded",
            "30% of sales versus 32.0% of sales",
            "Not loaded:",
            "Average check per cover",
            "A benchmark is context. It is not a target",
            "Where to look",
            "bls.gov/oes",
            "Service style is not set",
        ):
            self.assertIn(text, page)


class TestSuggestionDecisions(AdvisoryServerCase):
    def test_dismissal_persists_and_never_edits_the_draft(self) -> None:
        cookie = self.sign_in("owner@pilot.example")
        assessment_id = self.new_draft(cookie)
        before = dict(self.record(assessment_id)["profile"])
        status, body, _h = self.request(
            f"/assessments/{assessment_id}/suggestions",
            {"card": "average_ticket:none", "status": "dismissed", "value": ""},
            cookie,
        )
        self.assertEqual(status, 200)
        advice = json.loads(body)["advice"]
        self.assertNotIn('data-card="average_ticket:none" data-field="average_ticket" data-value=""', advice["average_ticket"])
        self.assertIn("1 dismissed", advice["average_ticket"])
        self.assertEqual(self.record(assessment_id)["profile"], before)
        page = self.request(f"/assessments/{assessment_id}", None, cookie)[1]
        self.assertIn("1 dismissed", page)
        restored = json.loads(
            self.request(f"/assessments/{assessment_id}/suggestions", {"card": "average_ticket:none", "status": "active"}, cookie)[1]
        )["advice"]
        self.assertNotIn("1 dismissed", restored["average_ticket"])
        self.assertIn("No average-check benchmark", restored["average_ticket"])

    def test_accepting_records_the_choice_but_the_value_is_the_customers_to_enter(self) -> None:
        cookie = self.sign_in("owner@pilot.example")
        assessment_id = self.new_draft(cookie)
        before = dict(self.record(assessment_id)["profile"])
        self.request(f"/assessments/{assessment_id}/suggestions", {"card": "debt_share:cash", "status": "accepted", "value": "0.93"}, cookie)
        advice = json.loads(self.request(f"/assessments/{assessment_id}/save", {"guided_save": "1", **PROFILE}, cookie)[1])["advice"]
        self.assertIn("You used this suggestion.", advice["debt_share"])
        self.assertEqual(self.record(assessment_id)["profile"], before)
        self.assertEqual(self.record(assessment_id)["profile"]["debt_share"], "0.70")

    def test_bad_card_or_status_is_refused(self) -> None:
        cookie = self.sign_in("owner@pilot.example")
        assessment_id = self.new_draft(cookie)
        for data in (
            {"card": "<script>:x", "status": "dismissed"},
            {"card": "average_ticket:none", "status": "approved"},
            {"card": "", "status": "dismissed"},
        ):
            self.assertEqual(self.request(f"/assessments/{assessment_id}/suggestions", data, cookie)[0], 400)

    def test_decisions_are_isolated_between_accounts(self) -> None:
        owner = self.sign_in("owner@pilot.example")
        other = self.sign_in("other@pilot.example")
        assessment_id = self.new_draft(owner)
        self.request(f"/assessments/{assessment_id}/suggestions", {"card": "average_ticket:none", "status": "dismissed"}, owner)
        self.assertEqual(self.request(f"/assessments/{assessment_id}/suggestions", {"card": "x:y", "status": "dismissed"}, other)[0], 403)
        other_draft = self.new_draft(other)
        page = self.request(f"/assessments/{other_draft}", None, other)[1]
        self.assertNotIn("1 dismissed", page)


class TestBenchmarkEntries(AdvisoryServerCase):
    def test_save_shows_as_customer_recorded_and_unverified_then_removes(self) -> None:
        cookie = self.sign_in("owner@pilot.example")
        assessment_id = self.new_draft(cookie)
        status, page, _h = self.request(
            f"/assessments/{assessment_id}/benchmarks",
            {
                "op": "save",
                "metric_key": "average_check",
                "value": "24.50",
                "source_name": "Lender guide, Shoals edition",
                "source_url": "https://example.org/guide",
                "published_on": "2019",
                "geography": "Colbert County, Alabama",
                "scale": "50 to 80 seats",
            },
            cookie,
        )
        self.assertEqual(status, 200)
        self.assertIn("customer-recorded, unverified", page)
        self.assertIn("Stale, older than two years", page)
        self.assertIn("Lender guide, Shoals edition", page)
        self.assertIn("RUGD has not verified it", page)
        cards = json.loads(self.request(f"/assessments/{assessment_id}/save", {"guided_save": "1", **PROFILE}, cookie)[1])["advice"]
        self.assertIn("24.5", cards["average_ticket"])
        self.assertIn('data-value="24.5"', cards["average_ticket"])
        stored = self.connection.execute("SELECT id FROM advisory_records WHERE kind = 'benchmark_entry'").fetchone()
        status, page, _h = self.request(f"/assessments/{assessment_id}/benchmarks", {"op": "delete", "entry_id": stored["id"]}, cookie)
        self.assertEqual(status, 200)
        self.assertIn("The figure was removed.", page)
        self.assertIsNone(self.connection.execute("SELECT id FROM advisory_records WHERE kind = 'benchmark_entry'").fetchone())

    def test_a_figure_without_a_source_is_rejected(self) -> None:
        cookie = self.sign_in("owner@pilot.example")
        assessment_id = self.new_draft(cookie)
        status, page, _h = self.request(
            f"/assessments/{assessment_id}/benchmarks",
            {"op": "save", "metric_key": "average_check", "value": "24", "source_name": ""},
            cookie,
        )
        self.assertEqual(status, 400)
        self.assertIn("Name the source", page)
        self.assertIsNone(self.connection.execute("SELECT id FROM advisory_records").fetchone())

    def test_one_account_cannot_read_or_delete_another_accounts_figure(self) -> None:
        owner = self.sign_in("owner@pilot.example")
        other = self.sign_in("other@pilot.example")
        assessment_id = self.new_draft(owner)
        self.request(
            f"/assessments/{assessment_id}/benchmarks",
            {"op": "save", "metric_key": "average_check", "value": "24", "source_name": "Private note"},
            owner,
        )
        self.assertIn(self.request(f"/assessments/{assessment_id}/benchmarks", None, other)[0], (403, 404))
        stored = self.connection.execute("SELECT id FROM advisory_records").fetchone()
        self.assertIn(
            self.request(f"/assessments/{assessment_id}/benchmarks", {"op": "delete", "entry_id": stored["id"]}, other)[0], (403, 404)
        )
        self.assertIsNotNone(self.connection.execute("SELECT id FROM advisory_records").fetchone())


class TestScenarios(AdvisoryServerCase):
    def analyzed(self, cookie: str) -> tuple[str, dict]:
        assessment_id = self.new_draft(cookie)
        status, _b, _h = self.request(f"/assessments/{assessment_id}/analyze", dict(PROFILE), cookie)
        self.assertEqual(status, 303)
        record = self.record(assessment_id)
        self.assertTrue(record["result"]["engine_ran"])
        return assessment_id, json.loads(json.dumps(record["result"], sort_keys=True))

    def test_improve_page_explains_gaps_and_alternatives_for_the_high_cost_restaurant(self) -> None:
        cookie = self.sign_in("owner@pilot.example")
        assessment_id, _official = self.analyzed(cookie)
        page = self.request(f"/assessments/{assessment_id}/improve", None, cookie)[1]
        for text in (
            "not approved",
            "What the official result says",
            "INSUFFICIENT_DEMAND_EVIDENCE",
            "Funding and cash-flow gaps",
            "Funding needed from you",
            "Gap against the cash you entered",
            "Put in the cash the project needs",
            "Lower the build cost",
            "Build a smaller venue",
            "Ask for a longer repayment term",
            "Official result, unchanged by this page",
        ):
            self.assertIn(text, page)

    def test_calculate_does_not_save_anything(self) -> None:
        cookie = self.sign_in("owner@pilot.example")
        assessment_id, official = self.analyzed(cookie)
        before = dict(self.record(assessment_id)["profile"])
        status, page, _h = self.request(
            f"/assessments/{assessment_id}/improve",
            {"op": "calculate", "ov_seats": "45", "scale_with_size": "on"},
            cookie,
        )
        self.assertEqual(status, 200)
        self.assertIn("Draft result", page)
        self.assertIn("Recalculated from supported relationships", page)
        self.assertIn("Needs your verification", page)
        self.assertEqual(self.record(assessment_id)["profile"], before)
        self.assertIsNone(self.connection.execute("SELECT id FROM advisory_records WHERE kind = 'scenario'").fetchone())
        self.assertEqual(json.loads(json.dumps(self.record(assessment_id)["result"], sort_keys=True)), official)

    def test_save_compare_persist_and_apply_with_explicit_approval(self) -> None:
        cookie = self.sign_in("owner@pilot.example")
        assessment_id, official = self.analyzed(cookie)
        status, page, _h = self.request(
            f"/assessments/{assessment_id}/improve",
            {"op": "save", "name": "Smaller room", "ov_seats": "45", "scale_with_size": "on", "target": "1"},
            cookie,
        )
        self.assertEqual(status, 200, page[:300])
        self.assertIn("Saved as a separate scenario", page)
        self.assertIn("Smaller room", page)
        self.assertIn("Saved scenarios side by side", page)
        self.assertIn("<svg", page)
        status, page, _h = self.request(
            f"/assessments/{assessment_id}/improve",
            {"op": "save", "name": "Owner cash", "cash_contribution": "900000", "derive_debt_from_cash": "on"},
            cookie,
        )
        self.assertEqual(status, 200)
        self.assertIn("Owner cash", page)
        again = self.request(f"/assessments/{assessment_id}/improve", None, cookie)[1]
        self.assertIn("Smaller room", again)
        self.assertIn("Owner cash", again)
        # Saving changed nothing in the draft or the official result.
        self.assertEqual(self.record(assessment_id)["profile"]["seats"], "60")
        self.assertEqual(json.loads(json.dumps(self.record(assessment_id)["result"], sort_keys=True)), official)
        stored = self.connection.execute(
            "SELECT id FROM advisory_records WHERE kind = 'scenario' AND title = 'Smaller room'"
        ).fetchone()
        # Without the confirmation box, nothing is applied.
        status, page, _h = self.request(
            f"/assessments/{assessment_id}/improve", {"op": "apply", "scenario_id": stored["id"]}, cookie
        )
        self.assertEqual(status, 400)
        self.assertIn("Nothing was changed", page)
        self.assertEqual(self.record(assessment_id)["profile"]["seats"], "60")
        # With it, only the scenario's fields change and the previous values are recorded.
        status, page, _h = self.request(
            f"/assessments/{assessment_id}/improve",
            {"op": "apply", "scenario_id": stored["id"], "confirm": "yes"},
            cookie,
        )
        self.assertEqual(status, 200)
        self.assertIn("The official result, flags, and review status are unchanged", page)
        record = self.record(assessment_id)
        self.assertEqual(record["profile"]["seats"], "45")
        self.assertEqual(record["profile"]["construction_cost"], "1350000")
        self.assertEqual(record["profile"]["average_ticket"], "22")
        self.assertEqual(record["profile"]["annual_fixed_costs"], "180000")
        self.assertFalse(record["human_review_approved"])
        self.assertEqual(json.loads(json.dumps(record["result"], sort_keys=True)), official)
        self.assertIn("Applied", page)
        payload = json.loads(
            self.connection.execute("SELECT payload_json FROM advisory_records WHERE id = ?", (stored["id"],)).fetchone()[0]
        )
        self.assertEqual({item["field"] for item in payload["applied"][0]["changes"]}, {"seats", "construction_cost", "equipment", "soft_costs"})
        self.assertEqual({item["from"] for item in payload["applied"][0]["changes"] if item["field"] == "seats"}, {"60"})
        audit = self.connection.execute("SELECT action FROM audit_events WHERE action LIKE 'scenario_%'").fetchall()
        self.assertEqual({row["action"] for row in audit}, {"scenario_saved", "scenario_applied"})

    def test_saving_requires_a_change_and_valid_numbers(self) -> None:
        cookie = self.sign_in("owner@pilot.example")
        assessment_id = self.new_draft(cookie)
        for data, fragment in (
            ({"op": "save", "name": "Nothing"}, "Change at least one number"),
            ({"op": "save", "ov_seats": "abc"}, "must be a number"),
            ({"op": "save", "ov_weekday_occupancy": "1.5"}, "0 to 1"),
        ):
            status, page, _h = self.request(f"/assessments/{assessment_id}/improve", data, cookie)
            self.assertEqual(status, 400)
            self.assertIn(fragment, page)
        self.assertIsNone(self.connection.execute("SELECT id FROM advisory_records").fetchone())

    def test_preset_link_prefills_the_draft_scenario_and_calculates(self) -> None:
        cookie = self.sign_in("owner@pilot.example")
        assessment_id = self.new_draft(cookie)
        status, page, _h = self.request(f"/assessments/{assessment_id}/improve?preset=smaller_venue", None, cookie)
        self.assertEqual(status, 200)
        self.assertIn('name="ov_seats" value="45"', page)
        self.assertIn("Draft result", page)

    def test_a_smaller_restaurant_with_different_staffing_and_revenue(self) -> None:
        cookie = self.sign_in("owner@pilot.example")
        small = {
            "business_name": "Corner Cafe",
            "industry": "Cafe",
            "market": "Florence, Alabama",
            "service_style": "limited_service",
            "seats": "24",
            "average_ticket": "14",
            "weekday_occupancy": "0.55",
            "weekend_occupancy": "0.80",
            "operating_days": "350",
            "construction_cost": "140000",
            "equipment": "60000",
            "soft_costs": "15000",
            "contribution_margin": "0.55",
            "annual_fixed_costs": "60000",
            "available_cash": "60000",
            "staff_fte": "4",
            "avg_hourly_wage": "16",
        }
        assessment_id = self.new_draft(cookie, small)
        page = self.request(f"/assessments/{assessment_id}/improve", None, cookie)[1]
        self.assertIn("Where your working numbers stand", page)
        advice = json.loads(self.request(f"/assessments/{assessment_id}/save", {"guided_save": "1", **small}, cookie)[1])["advice"]
        self.assertIn("Staffing check", advice["annual_fixed_costs"])
        self.assertIn("4 full-time equivalents × 16 per hour × 2,080 hours = 133,120", advice["annual_fixed_costs"])

    def test_cross_account_isolation_for_scenarios(self) -> None:
        owner = self.sign_in("owner@pilot.example")
        other = self.sign_in("other@pilot.example")
        assessment_id = self.new_draft(owner)
        self.request(f"/assessments/{assessment_id}/improve", {"op": "save", "name": "Private plan", "ov_seats": "40"}, owner)
        stored = self.connection.execute("SELECT id FROM advisory_records WHERE kind = 'scenario'").fetchone()
        for data in (
            None,
            {"op": "save", "name": "Mine now", "ov_seats": "30"},
            {"op": "delete", "scenario_id": stored["id"]},
            {"op": "apply", "scenario_id": stored["id"], "confirm": "yes"},
        ):
            status, page, _h = self.request(f"/assessments/{assessment_id}/improve", data, other)
            self.assertIn(status, (403, 404))
            self.assertNotIn("Private plan", page)
        self.assertEqual(self.connection.execute("SELECT COUNT(*) FROM advisory_records WHERE kind = 'scenario'").fetchone()[0], 1)
        self.assertEqual(self.record(assessment_id)["profile"]["seats"], "60")
        # An anonymous visitor gets nothing either.
        self.assertIn(self.request(f"/assessments/{assessment_id}/improve")[0], (302, 303, 401, 403, 404))

    def test_a_reader_may_calculate_but_not_save_or_apply(self) -> None:
        owner = self.sign_in("owner@pilot.example")
        reader = self.sign_in("reader@pilot.example")
        status, page, _h = self.request(f"/assessments/{RESTAURANT_ID}/improve", {"op": "calculate", "ov_seats": "10"}, reader)
        self.assertEqual(status, 200)
        self.assertIn("not approved", page)
        for data in ({"op": "save", "ov_seats": "10"}, {"op": "apply", "scenario_id": "x", "confirm": "yes"}):
            self.assertEqual(self.request(f"/assessments/{RESTAURANT_ID}/improve", data, reader)[0], 403)
        del owner

    def test_official_baseline_is_preserved(self) -> None:
        cookie = self.sign_in("owner@pilot.example")
        before = json.dumps(get_assessment(self.connection, BASELINE_ID), sort_keys=True, default=str)
        page = self.request(f"/assessments/{BASELINE_ID}/improve", None, cookie)[1]
        self.assertIn("INSUFFICIENT_DEMAND_EVIDENCE", page)
        self.assertIn("do-not-proceed", page)
        self.assertIn("internal", page)
        self.assertIn("Scenarios need the startup numbers", page)
        for path in ("improve", "benchmarks", "revenue-worksheet"):
            self.assertEqual(self.request(f"/assessments/{BASELINE_ID}/{path}", {"op": "save", "ov_seats": "10"}, cookie)[0], 403)
        self.assertEqual(self.request(f"/assessments/{BASELINE_ID}/suggestions", {"card": "a:b", "status": "dismissed"}, cookie)[0], 403)
        self.assertEqual(self.request(f"/assessments/{BASELINE_ID}/benchmarks", None, cookie)[0], 200)
        self.assertEqual(self.request(f"/assessments/{BASELINE_ID}/revenue-worksheet", None, cookie)[0], 200)
        after = json.dumps(get_assessment(self.connection, BASELINE_ID), sort_keys=True, default=str)
        self.assertEqual(before, after)
        baseline = get_assessment(self.connection, BASELINE_ID)
        self.assertFalse(baseline["human_review_approved"])
        self.assertIsNone(baseline["result"])
        official = analyze_record(baseline)
        self.assertIn("INSUFFICIENT_DEMAND_EVIDENCE", official["blocking_flags"])
        self.assertEqual(official["readiness_status"], "internal")
        self.assertEqual(official["recommendation"], "do-not-proceed")
        self.assertFalse(official["human_review_approved"])


class TestRevenueWorksheetPage(AdvisoryServerCase):
    FORM = {
        "seats": "50",
        "operating_weeks": "50",
        "day_mon": "1",
        "day_tue": "1",
        "day_wed": "1",
        "day_thu": "1",
        "day_fri": "1",
        "day_sat": "1",
        "period_1_name": "Dinner",
        "period_1_turns": "1.5",
        "period_1_util_weekday": "0.6",
        "period_1_util_weekend": "0.8",
        "period_1_ticket": "20",
        "stream_1_name": "Catering",
        "stream_1_annual": "30000",
    }

    def test_calculate_shows_the_calculation_and_compares_with_the_official_formula(self) -> None:
        cookie = self.sign_in("owner@pilot.example")
        assessment_id = self.new_draft(cookie, dict(PROFILE, seats="50", average_ticket="20", weekday_occupancy="0.6", weekend_occupancy="0.8", operating_days="300"))
        status, page, _h = self.request(f"/assessments/{assessment_id}/revenue-worksheet", dict(self.FORM, op="calculate"), cookie)
        self.assertEqual(status, 200)
        self.assertIn("Proposed.", page)
        self.assertIn("50 seats × 1.5 turns × 0.6 utilization × 20.00 check × 250 weekday days", page)
        self.assertIn("315,000", page)
        self.assertIn("Compared with the official calculation", page)
        self.assertIn("Use the days you are actually open", page)
        self.assertIn("The official result is not changed by this page", page)
        self.assertIsNone(self.record(assessment_id)["result"])

    def test_save_then_apply_needs_confirmation_and_records_the_previous_value(self) -> None:
        cookie = self.sign_in("owner@pilot.example")
        assessment_id, official = TestScenarios.analyzed(self, cookie)
        status, page, _h = self.request(f"/assessments/{assessment_id}/revenue-worksheet", dict(self.FORM, op="save"), cookie)
        self.assertEqual(status, 200)
        self.assertIn("Saved as a proposed worksheet", page)
        reopened = self.request(f"/assessments/{assessment_id}/revenue-worksheet", None, cookie)[1]
        self.assertIn('value="Dinner"', reopened)
        self.assertEqual(self.record(assessment_id)["profile"]["projected_monthly_revenue_base"], "28000")
        status, page, _h = self.request(f"/assessments/{assessment_id}/revenue-worksheet", dict(self.FORM, op="apply"), cookie)
        self.assertEqual(status, 400)
        self.assertEqual(self.record(assessment_id)["profile"]["projected_monthly_revenue_base"], "28000")
        status, page, _h = self.request(
            f"/assessments/{assessment_id}/revenue-worksheet", dict(self.FORM, op="apply", confirm="yes"), cookie
        )
        self.assertEqual(status, 200)
        self.assertIn("The previous value was 28000", page)
        record = self.record(assessment_id)
        self.assertEqual(record["profile"]["projected_monthly_revenue_base"], "26250.00")
        self.assertEqual(json.loads(json.dumps(record["result"], sort_keys=True)), official)
        self.assertFalse(record["human_review_approved"])

    def test_invalid_worksheet_is_not_saved(self) -> None:
        cookie = self.sign_in("owner@pilot.example")
        assessment_id = self.new_draft(cookie)
        status, page, _h = self.request(
            f"/assessments/{assessment_id}/revenue-worksheet", dict(self.FORM, op="save", period_1_util_weekday="2"), cookie
        )
        self.assertEqual(status, 400)
        self.assertIn("utilization must be from 0 to 1", page)
        self.assertIsNone(self.connection.execute("SELECT id FROM advisory_records").fetchone())

    def test_worksheet_is_private_to_its_owner(self) -> None:
        owner = self.sign_in("owner@pilot.example")
        other = self.sign_in("other@pilot.example")
        assessment_id = self.new_draft(owner)
        self.request(f"/assessments/{assessment_id}/revenue-worksheet", dict(self.FORM, op="save"), owner)
        status, page, _h = self.request(f"/assessments/{assessment_id}/revenue-worksheet", None, other)
        self.assertIn(status, (403, 404))
        self.assertNotIn("Dinner", page)
        self.assertEqual(self.request(f"/assessments/{assessment_id}/revenue-worksheet", dict(self.FORM, op="save"), other)[0], 403)


if __name__ == "__main__":
    unittest.main()

"""Benchmarks, suggestions, the revenue worksheet, and improvement scenarios, without a server."""

from __future__ import annotations

import unittest

from app import advisory, benchmarks, improve
from app import revenue_worksheet as rw
from engine.financial import seat_occupancy_revenue
from engine.startup_projection import project_startup

REQUIRED_RECORD_KEYS = {
    "industry",
    "subsector",
    "business_model",
    "geography",
    "scale",
    "metric",
    "unit",
    "value",
    "source",
    "published",
    "period",
    "retrieved",
    "methodology",
    "limitations",
    "confidence",
    "applicability",
}

HIGH_COST = {
    "industry": "Restaurant",
    "market": "Colbert County, Alabama",
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
}
SMALL = {
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
SOLVABLE = {
    "industry": "Restaurant",
    "market": "Colbert County, Alabama",
    "seats": "80",
    "average_ticket": "30",
    "weekday_occupancy": "0.6",
    "weekend_occupancy": "0.8",
    "operating_days": "340",
    "construction_cost": "1600000",
    "contribution_margin": "0.6",
    "annual_fixed_costs": "100000",
    "available_cash": "100000",
}
SOFTWARE = {
    "industry": "Software subscription",
    "market": "Huntsville, Alabama",
    "seats": "10",
    "average_ticket": "49",
    "weekday_occupancy": "0.5",
    "weekend_occupancy": "0.2",
    "operating_days": "300",
    "construction_cost": "30000",
    "contribution_margin": "0.8",
}


def _entry(metric_key: str, value: float, **extra: str) -> dict:
    spec = benchmarks.METRICS[metric_key]
    payload = {
        "metric_key": metric_key,
        "metric": spec["label"],
        "unit": spec["unit"],
        "kind": spec["kind"],
        "value": value,
        "source": extra.get("source", "A local lender's guide"),
        "source_url": extra.get("source_url", ""),
        "published": extra.get("published", "2026"),
        "retrieved": extra.get("retrieved", "2026-11-01"),
        "geography": extra.get("geography", "Colbert County, Alabama"),
        "scale": "Not stated",
        "notes": "",
        "confidence": "low",
    }
    return {"id": extra.get("id", f"e-{metric_key}-{value}"), "payload": payload}


class TestBenchmarkRecords(unittest.TestCase):
    def test_restaurant_records_carry_every_required_property(self) -> None:
        context = benchmarks.match(HIGH_COST)
        self.assertGreater(len(context["records"]), 0)
        for record in context["records"]:
            with self.subTest(record=record["id"]):
                self.assertTrue(REQUIRED_RECORD_KEYS <= set(record))
                self.assertEqual(record["status"], benchmarks.STATUS_SECONDARY)
                self.assertIn("Not specific to Colbert County, Alabama", " ".join(record["applicability"]))
                self.assertTrue(record["limitations"])

    def test_nonrestaurant_has_no_stored_figures_and_says_so(self) -> None:
        context = benchmarks.match(SOFTWARE)
        self.assertEqual(context["records"], [])
        self.assertTrue(context["missing"])
        self.assertEqual(context["unresolved"], [])
        self.assertIn("not a target", context["caveat"].lower())

    def test_conflict_on_full_service_food_cost_is_listed_not_resolved(self) -> None:
        items = benchmarks.unresolved()
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["candidates"], ["30% of sales", "32.0% of sales"])
        context = benchmarks.match({"industry": "Restaurant", "service_style": "full_service"})
        self.assertTrue(context["unresolved"])
        self.assertNotIn("food_cost_pct", {r.get("metric_key") for r in context["records"]})
        limited = benchmarks.match({"industry": "Restaurant", "service_style": "limited_service"})
        self.assertEqual(limited["unresolved"], [])

    def test_style_filters_stored_records(self) -> None:
        full = benchmarks.match({"industry": "Restaurant", "service_style": "full_service"})["records"]
        limited = benchmarks.match({"industry": "Restaurant", "service_style": "limited_service"})["records"]
        self.assertTrue(all(item["style"] == "full_service" for item in full))
        self.assertTrue(all(item["style"] == "limited_service" for item in limited))

    def test_stale_undated_and_conflicting_customer_figures_are_flagged(self) -> None:
        entries = [
            _entry("food_cost_pct", 0.25, id="a", published="2019"),
            _entry("food_cost_pct", 0.36, id="b", published="2026"),
            _entry("average_check", 21.0, id="c", published=""),
        ]
        records = benchmarks.match(HIGH_COST, entries, today=__import__("datetime").date(2026, 11, 12))["records"]
        by_id = {r["id"]: r for r in records}
        self.assertTrue(by_id["entry:a"]["stale"])
        self.assertFalse(by_id["entry:b"]["stale"])
        self.assertTrue(by_id["entry:a"]["conflict"])
        self.assertTrue(by_id["entry:b"]["conflict"])
        self.assertTrue(by_id["entry:c"]["undated"])
        self.assertFalse(by_id["entry:c"]["conflict"])
        # A conflict is never averaged away: the latest recorded figure is returned as it is.
        picked = benchmarks.best_entry(records, "food_cost_pct")
        self.assertIn(picked["value"], (0.25, 0.36))

    def test_secondary_benchmark_is_never_a_verified_status(self) -> None:
        for record in benchmarks.registry():
            self.assertNotIn("verified", record["status"].replace("unverified", ""))
            self.assertEqual(record["retrieved"], "")

    def test_entry_validation(self) -> None:
        good, reason = benchmarks.prepare_entry(
            {"metric_key": "food_cost_pct", "value": "31.5", "source_name": "Lender guide", "published_on": "2025"}
        )
        self.assertEqual(reason, "")
        self.assertAlmostEqual(good["value"], 0.315)
        for form, fragment in (
            ({"metric_key": "food_cost_pct", "value": "31", "source_name": ""}, "Name the source"),
            ({"metric_key": "food_cost_pct", "value": "abc", "source_name": "x"}, "number"),
            ({"metric_key": "food_cost_pct", "value": "140", "source_name": "x"}, "percent"),
            ({"metric_key": "average_check", "value": "20", "source_name": "x", "source_url": "javascript:alert(1)"}, "http"),
            ({"metric_key": "average_check", "value": "20", "source_name": "x", "published_on": "last year"}, "YYYY"),
            ({"metric_key": "nope", "value": "20", "source_name": "x"}, "Choose"),
        ):
            with self.subTest(form=form):
                entry, why = benchmarks.prepare_entry(form)
                self.assertIsNone(entry)
                self.assertIn(fragment, why)


class TestSuggestionCards(unittest.TestCase):
    def cards(self, profile: dict, entries: list | None = None) -> dict:
        return advisory.build_cards(profile, entries or [], "a-1")

    def test_no_benchmark_means_no_invented_value(self) -> None:
        cards = self.cards(HIGH_COST)
        ticket = cards["average_ticket"][0]
        self.assertEqual(ticket["value"], "")
        self.assertIn("No average-check figure is loaded", ticket["source"])
        for field in ("contingency_pct", "annual_interest_rate"):
            for card in cards.get(field, []):
                self.assertEqual(card["value"], "")

    def test_recorded_average_check_becomes_a_suggestion_with_its_source(self) -> None:
        cards = self.cards(HIGH_COST, [_entry("average_check", 21.5)])
        card = cards["average_ticket"][0]
        self.assertEqual(card["value"], "21.5")
        self.assertIn("A local lender's guide", card["source"])
        self.assertIn("RUGD has not checked it", card["source"])

    def test_seats_from_floor_area_needs_both_a_size_and_a_recorded_rate(self) -> None:
        profile = dict(HIGH_COST, venue_sqft="3000")
        with_rate = self.cards(profile, [_entry("sqft_per_seat", 15.0)])["seats"][0]
        self.assertEqual(with_rate["value"], "200")
        without = self.cards(profile)["seats"][0]
        self.assertEqual(without["value"], "")
        self.assertIn("50.0 sq ft per seat", without["text"])

    def test_margin_value_only_when_all_three_cost_shares_are_recorded(self) -> None:
        partial = self.cards(HIGH_COST, [_entry("food_cost_pct", 0.30)])["contribution_margin"][0]
        self.assertEqual(partial["value"], "")
        full = self.cards(
            HIGH_COST,
            [_entry("food_cost_pct", 0.30), _entry("labor_pct", 0.20), _entry("other_variable_pct", 0.05)],
        )["contribution_margin"][0]
        self.assertEqual(full["value"], "0.45")
        self.assertEqual(full["widget"], "margin")

    def test_secondary_median_is_context_only_never_a_margin_value(self) -> None:
        card = self.cards(dict(HIGH_COST, service_style="limited_service"))["contribution_margin"][0]
        self.assertEqual(card["value"], "")
        self.assertIn("For context only", card["source"])

    def test_debt_share_from_cash_shows_its_arithmetic(self) -> None:
        card = self.cards(HIGH_COST)["debt_share"][0]
        self.assertEqual(card["id"], "debt_share:cash")
        total = (1800000 + 250000 + 120000) * 1.10
        self.assertAlmostEqual(float(card["value"]), round(1 - 150000 / total, 4))
        self.assertTrue(card["calc"])

    def test_staffing_check_is_arithmetic_with_no_value(self) -> None:
        card = self.cards(SMALL)["annual_fixed_costs"][0]
        self.assertEqual(card["value"], "")
        self.assertIn("4 full-time equivalents × 16 per hour × 2,080 hours = 133,120", card["calc"][0])

    def test_nonrestaurant_gets_generic_cards_and_no_restaurant_ones(self) -> None:
        cards = self.cards(SOFTWARE)
        self.assertNotIn("service_style", cards)
        self.assertNotIn("seats", cards)
        self.assertIn("average_ticket", cards)
        self.assertIn("No average-check figure is loaded for Software subscription", cards["average_ticket"][0]["source"])
        self.assertEqual(cards["contribution_margin"][0]["widget_data"]["labels"].split("|")[0], "Cost of goods or direct delivery")

    def test_dismissed_cards_move_to_the_dismissed_list(self) -> None:
        cards = self.cards(HIGH_COST)["average_ticket"]
        shown, dismissed = advisory.split(cards, {"average_ticket:none": {"status": "dismissed"}})
        self.assertEqual(shown, [])
        self.assertEqual(len(dismissed), 1)
        html = advisory.slot_html("average_ticket", cards, {"average_ticket:none": {"status": "dismissed"}}, HIGH_COST, True)
        self.assertIn("1 dismissed", html)
        self.assertIn('data-act="restore"', html)
        self.assertNotIn('class="advice-card"', html)

    def test_read_only_cards_have_no_action_buttons(self) -> None:
        html = advisory.slot_html("average_ticket", self.cards(HIGH_COST, [_entry("average_check", 21.5)])["average_ticket"], {}, HIGH_COST, False)
        self.assertIn("advice-card", html)
        self.assertNotIn("advice-btn", html)


class TestEngineIsUntouched(unittest.TestCase):
    def test_evaluate_matches_project_startup_exactly(self) -> None:
        base = improve.base_inputs(HIGH_COST)
        metrics, error = improve.evaluate(base["inputs"])
        self.assertEqual(error, "")
        values = base["inputs"]
        direct = project_startup(
            values["construction_cost"],
            values["seats"],
            values["average_ticket"],
            values["weekday_occupancy"],
            values["weekend_occupancy"],
            values["operating_days"],
            values["contribution_margin"],
            equipment=values["equipment"],
            soft_costs=values["soft_costs"],
            preopening_working_capital=values["preopening_working_capital"],
            contingency_pct=values["contingency_pct"],
            debt_share=values["debt_share"],
            annual_interest_rate=values["annual_interest_rate"],
            amortization_years=int(values["amortization_years"]),
            annual_fixed_costs=values["annual_fixed_costs"],
            downside_multiplier=values["downside_multiplier"],
        ).to_dict()
        self.assertEqual(metrics["total_project_cost"], direct["sources_and_uses"]["uses"]["total_project_cost"]["amount"])
        self.assertEqual(metrics["annual_debt_service"], direct["sources_and_uses"]["sources"]["annual_debt_service"])
        self.assertEqual(metrics["base_dscr"], direct["views"]["base"]["dscr"])
        self.assertEqual(metrics["downside_dscr"], direct["views"]["downside"]["dscr"])
        self.assertEqual(metrics["break_even_revenue"], direct["views"]["break_even"]["revenue"])

    def test_scoring_constants_and_flags_are_unchanged(self) -> None:
        from scoring import rules

        self.assertEqual(rules.DEFAULT_DOWNSIDE_DSCR_MINIMUM, 1.00)
        self.assertEqual(rules.LENDER_DOWNSIDE_DSCR_MINIMUM, 1.25)
        self.assertIn("INSUFFICIENT_DEMAND_EVIDENCE", rules.RECOMMEND_AGAINST_FLAGS)

    def test_improve_module_never_imports_scoring_writers(self) -> None:
        with open(improve.__file__, encoding="utf-8") as handle:
            source = handle.read()
        for forbidden in ("human_review_approved", "analyze_record", "save_profile", "run_assessment"):
            self.assertNotIn(forbidden, source)


class TestImprovementScenarios(unittest.TestCase):
    def test_high_construction_cost_and_limited_cash_shows_a_funding_gap(self) -> None:
        base = improve.base_inputs(HIGH_COST)
        self.assertEqual(base["missing"], [])
        metrics, _ = improve.evaluate(base["inputs"])
        self.assertLess(metrics["base_cash_flow"], 0)
        gap = improve.gap(base["inputs"], metrics, base["cash"], 1.0)
        self.assertEqual(gap["downside"]["debt_capacity"], 0.0)
        self.assertEqual(gap["downside"]["owner_funding_needed"], metrics["total_project_cost"])
        self.assertAlmostEqual(gap["downside"]["gap_vs_cash"], metrics["total_project_cost"] - 150000)
        self.assertFalse(gap["meets_target"]["downside"])
        findings = improve.financial_findings(metrics, 1.0)
        self.assertTrue(any("zero or negative" in line for line in findings))
        ids = [item["id"] for item in improve.presets(base["inputs"], metrics, base["cash"], 1.0, 0.25)]
        self.assertIn("owner_cash", ids)
        self.assertIn("lower_build", ids)
        self.assertIn("smaller_venue", ids)

    def test_unreachable_targets_are_reported_as_not_solved(self) -> None:
        base = improve.base_inputs(HIGH_COST)
        metrics, _ = improve.evaluate(base["inputs"])
        presets = {item["id"]: item for item in improve.presets(base["inputs"], metrics, base["cash"], 1.0, 0.25)}
        self.assertFalse(presets["lower_build"]["solved"])
        self.assertIn("does not reach", presets["lower_build"]["basis"])
        self.assertFalse(presets["lower_fixed"]["solved"])
        self.assertIn("Cost cuts alone are not enough", presets["lower_fixed"]["basis"])

    def test_a_solved_build_cost_really_reaches_the_target(self) -> None:
        base = improve.base_inputs(SOLVABLE)
        metrics, _ = improve.evaluate(base["inputs"])
        self.assertLess(metrics["downside_dscr"], 1.0)
        presets = {item["id"]: item for item in improve.presets(base["inputs"], metrics, base["cash"], 1.0, 0.25)}
        solved = presets["lower_build"]
        self.assertTrue(solved["solved"])
        scenario = improve.build_scenario(base, {"overrides": solved["overrides"], "cash": base["cash"], "cash_changed": False, "scale_with_size": False, "derive_debt_from_cash": False})
        self.assertGreaterEqual(scenario["metrics"]["downside_dscr"], 1.0)
        self.assertLess(solved["overrides"]["construction_cost"], base["inputs"]["construction_cost"])

    def test_every_solved_preset_reaches_the_target_when_applied(self) -> None:
        base = improve.base_inputs(SOLVABLE)
        metrics, _ = improve.evaluate(base["inputs"])
        presets = improve.presets(base["inputs"], metrics, base["cash"], 1.0, 0.25)
        solved = [item for item in presets if item["solved"] and item["overrides"]]
        self.assertTrue({"lower_build", "higher_ticket"} <= {item["id"] for item in solved})
        for item in solved:
            with self.subTest(preset=item["id"]):
                scenario = improve.build_scenario(
                    base,
                    {"overrides": item["overrides"], "cash": base["cash"], "cash_changed": False, "scale_with_size": item["scale"], "derive_debt_from_cash": False},
                )
                self.assertGreaterEqual(scenario["metrics"]["downside_dscr"], 1.0)

    def test_smaller_restaurant_scales_costs_with_seats_and_leaves_fixed_costs(self) -> None:
        base = improve.base_inputs(SMALL)
        spec, errors = improve.parse_scenario({"ov_seats": "18", "scale_with_size": "on"}, base)
        self.assertEqual(errors, [])
        scenario = improve.build_scenario(base, spec, name="Smaller")
        self.assertEqual(scenario["inputs"]["seats"], 18.0)
        self.assertEqual(scenario["inputs"]["construction_cost"], 105000.0)
        self.assertEqual(scenario["inputs"]["equipment"], 45000.0)
        self.assertEqual(scenario["inputs"]["annual_fixed_costs"], 60000.0)
        fields = {item["field"] for item in scenario["dependent"]}
        self.assertEqual(fields, {"construction_cost", "equipment", "soft_costs"})
        self.assertTrue(all("Assumes the same cost per seat" in item["relationship"] for item in scenario["dependent"]))
        needs = {item["field"] for item in scenario["needs"]}
        self.assertIn("Seats", needs)
        self.assertIn("Construction cost", needs)

    def test_explicit_override_wins_over_a_derived_value(self) -> None:
        base = improve.base_inputs(SMALL)
        spec, _ = improve.parse_scenario({"ov_seats": "18", "ov_construction_cost": "120000", "scale_with_size": "on"}, base)
        scenario = improve.build_scenario(base, spec)
        self.assertEqual(scenario["inputs"]["construction_cost"], 120000.0)
        self.assertNotIn("construction_cost", {item["field"] for item in scenario["dependent"]})

    def test_debt_share_follows_cash_when_asked(self) -> None:
        base = improve.base_inputs(SMALL)
        spec, _ = improve.parse_scenario({"cash_contribution": "107500", "derive_debt_from_cash": "on"}, base)
        scenario = improve.build_scenario(base, spec)
        total = (140000 + 60000 + 15000) * 1.10
        self.assertAlmostEqual(scenario["inputs"]["debt_share"], round(1 - 107500 / total, 4))
        self.assertIn("available_cash", scenario["changed"])
        self.assertEqual(scenario["dependent"][0]["field"], "debt_share")

    def test_invalid_input_is_reported_not_guessed(self) -> None:
        base = improve.base_inputs(SMALL)
        for form, fragment in (
            ({"ov_seats": "twelve"}, "must be a number"),
            ({"ov_weekday_occupancy": "1.4"}, "0 to 1"),
            ({"ov_seats": "10.5"}, "whole number"),
            ({"ov_construction_cost": "-5"}, "negative"),
            ({"cash_contribution": "-1"}, "zero or more"),
        ):
            with self.subTest(form=form):
                spec, errors = improve.parse_scenario(form, base)
                self.assertTrue(any(fragment in item for item in errors), errors)

    def test_nonrestaurant_scenarios_use_the_same_engine(self) -> None:
        base = improve.base_inputs(SOFTWARE)
        self.assertEqual(base["missing"], [])
        metrics, error = improve.evaluate(base["inputs"])
        self.assertEqual(error, "")
        presets = improve.presets(base["inputs"], metrics, base["cash"], 1.0, 0.25)
        self.assertTrue(presets)
        self.assertEqual(benchmarks.match(SOFTWARE)["records"], [])

    def test_incomplete_startup_inputs_are_named(self) -> None:
        base = improve.base_inputs({"industry": "Restaurant", "seats": "20"})
        self.assertIn("construction_cost", base["missing"])
        _b, scenario, errors = improve.scenario_from_form({"industry": "Restaurant", "seats": "20"}, {})
        self.assertIsNone(scenario)
        self.assertEqual(errors, [])

    def test_placeholders_are_disclosed_and_listed_for_verification(self) -> None:
        base = improve.base_inputs(SMALL)
        self.assertIn("debt_share", base["placeholders"])
        spec, _ = improve.parse_scenario({"ov_average_ticket": "16"}, base)
        scenario = improve.build_scenario(base, spec)
        text = " ".join(item["verify"] for item in scenario["needs"])
        self.assertIn("starting number from RUGD", text)
        self.assertIn("menu prices", text)

    def test_apply_touches_only_scenario_fields_and_records_the_previous_value(self) -> None:
        base = improve.base_inputs(SMALL)
        spec, _ = improve.parse_scenario({"ov_seats": "18", "scale_with_size": "on"}, base)
        scenario = improve.build_scenario(base, spec, name="Smaller")
        stored = {"id": "s1", "payload": improve.payload_for_save(scenario, "Smaller", ""), "created_at": "now"}
        rebuilt = improve.recompute(stored)
        profile = dict(SMALL, human_review_approved=False, business_name="Cafe")
        updated, changes = improve.apply_to_profile(profile, rebuilt)
        self.assertEqual({item["field"] for item in changes}, {"seats", "construction_cost", "equipment", "soft_costs"})
        self.assertEqual(updated["seats"], "18")
        self.assertEqual(updated["construction_cost"], "105000")
        self.assertEqual({item["from"] for item in changes if item["field"] == "seats"}, {"24"})
        for key in ("business_name", "average_ticket", "annual_fixed_costs", "human_review_approved", "industry"):
            self.assertEqual(updated[key], profile[key])
        again, none = improve.apply_to_profile(updated, rebuilt)
        self.assertEqual(none, [])
        self.assertEqual(again, updated)

    def test_saved_scenario_recomputes_from_saved_inputs_only(self) -> None:
        base = improve.base_inputs(SMALL)
        spec, _ = improve.parse_scenario({"ov_average_ticket": "16"}, base)
        scenario = improve.build_scenario(base, spec, name="Higher ticket")
        stored = {"id": "s2", "payload": improve.payload_for_save(scenario, "Higher ticket", "")}
        rebuilt = improve.recompute(stored)
        self.assertEqual(rebuilt["metrics"], scenario["metrics"])
        broken = improve.recompute({"id": "s3", "payload": {"inputs": {"seats": 5}}})
        self.assertIsNone(broken["metrics"])

    def test_the_not_approved_statement_is_present(self) -> None:
        self.assertIn("not approved", improve.NOT_APPROVED)
        self.assertIn("does not change the official result", improve.NOT_APPROVED)

    def test_official_issues_split_evidence_from_financial(self) -> None:
        result = {
            "engine_ran": True,
            "recommendation": "do-not-proceed",
            "blocking_flags": ["INSUFFICIENT_DEMAND_EVIDENCE", "NEGATIVE_OR_MARGINAL_CASH_FLOW"],
            "gap_flags": ["UNEVALUATED_OPERATOR_CAPACITY"],
            "readiness_status": "internal",
            "human_review_status": "pending",
        }
        explained = improve.explain_official({"result": result})
        evidence = {item["flag"] for item in explained["evidence"]}
        financial = {item["flag"] for item in explained["financial"]}
        self.assertEqual(evidence, {"INSUFFICIENT_DEMAND_EVIDENCE", "UNEVALUATED_OPERATOR_CAPACITY"})
        self.assertEqual(financial, {"NEGATIVE_OR_MARGINAL_CASH_FLOW"})
        self.assertFalse(improve.explain_official({"result": None})["ran"])


class TestRevenueWorksheet(unittest.TestCase):
    FORM = {
        "seats": "50",
        "operating_schedule": "mon,tue,wed,thu,fri,sat",
        "operating_weeks": "50",
        "period_1_name": "Dinner",
        "period_1_turns": "1.5",
        "period_1_util_weekday": "0.6",
        "period_1_util_weekend": "0.8",
        "period_1_ticket": "20",
    }

    def test_calculation_is_transparent_and_exact(self) -> None:
        worksheet, errors = rw.parse(self.FORM)
        self.assertEqual(errors, [])
        calc = rw.calculate(worksheet)
        self.assertEqual(calc["weekday_days"], 250)
        self.assertEqual(calc["weekend_days"], 50)
        self.assertEqual(calc["core_revenue"], 285000.0)
        self.assertEqual(len(calc["lines"]), 2)
        self.assertIn("50 seats × 1.5 turns × 0.6 utilization × 20.00 check × 250 weekday days", calc["lines"][0]["formula"])
        self.assertEqual(calc["total_revenue"], 285000.0)
        self.assertEqual(calc["monthly_revenue"], round(285000 / 12, 2))

    def test_other_streams_add_and_empty_inputs_calculate_nothing(self) -> None:
        form = dict(self.FORM, stream_1_name="Catering", stream_1_annual="30000")
        calc = rw.calculate(rw.parse(form)[0])
        self.assertEqual(calc["other_revenue"], 30000.0)
        self.assertEqual(calc["total_revenue"], 315000.0)
        self.assertIsNone(rw.calculate(rw.parse({})[0]))
        self.assertIn("seats", rw.missing(rw.parse({})[0]))

    def test_bad_values_are_errors(self) -> None:
        _w, errors = rw.parse(dict(self.FORM, period_1_util_weekday="1.5", period_1_turns="0"))
        self.assertEqual(len(errors), 2)
        _w, errors = rw.parse(dict(self.FORM, seats="1.5"))
        self.assertTrue(errors)

    def test_comparison_uses_the_unchanged_official_formula(self) -> None:
        profile = {
            "seats": "50",
            "average_ticket": "20",
            "weekday_occupancy": "0.6",
            "weekend_occupancy": "0.8",
            "operating_days": "300",
            "contribution_margin": "0.4",
            "annual_fixed_costs": "20000",
        }
        worksheet, _ = rw.parse(self.FORM)
        calc = rw.calculate(worksheet)
        comparison = rw.compare(worksheet, calc, profile)
        expected = seat_occupancy_revenue(50, 20, 0.6, 0.8, 300).revenue
        self.assertEqual(comparison["official"], expected)
        self.assertEqual(comparison["difference"], round(calc["total_revenue"] - expected, 2))
        self.assertFalse(comparison["beyond_official_cap"])
        self.assertEqual(comparison["cash_flow"]["official"], round(expected * 0.4 - 20000, 2))
        self.assertEqual(comparison["steps"][0]["value"], expected)
        self.assertEqual(comparison["steps"][-1]["value"], calc["total_revenue"])

    def test_turns_above_one_are_flagged_as_beyond_the_official_cap(self) -> None:
        worksheet, _ = rw.parse(dict(self.FORM, period_1_turns="2.5"))
        calc = rw.calculate(worksheet)
        profile = {"seats": "50", "average_ticket": "20", "weekday_occupancy": "0.6", "weekend_occupancy": "0.8", "operating_days": "300"}
        self.assertTrue(rw.compare(worksheet, calc, profile)["beyond_official_cap"])

    def test_comparison_names_what_the_draft_still_needs(self) -> None:
        worksheet, _ = rw.parse(self.FORM)
        comparison = rw.compare(worksheet, rw.calculate(worksheet), {"seats": "50"})
        self.assertIsNone(comparison["official"])
        self.assertIn("average_ticket", comparison["missing"])

    def test_round_trip_through_a_saved_worksheet(self) -> None:
        worksheet, _ = rw.parse(self.FORM)
        again, errors = rw.parse(rw.form_from_worksheet(worksheet))
        self.assertEqual(errors, [])
        self.assertEqual(rw.calculate(again), rw.calculate(worksheet))


if __name__ == "__main__":
    unittest.main()

"""Unit tests for the deterministic financial engine.

Methodology § Core Principles — deterministic calculations.
Methodology § Scoring Approach — cash-flow flag when base and downside are both
negative or marginal.
"""

import inspect
import unittest

from engine.financial import (
    FLAG_NEGATIVE_OR_MARGINAL_CASH_FLOW,
    FLAG_NO_GROSS_MARGIN,
    USER_SUPPLIED_ASSUMPTION,
    VERIFIED_DATA,
    FinancialInputs,
    result_to_dict,
    run_financials,
    seat_occupancy_revenue,
)


class TestFinancialEngine(unittest.TestCase):
    def test_positive_base_case_does_not_flag_when_only_downside_is_negative(self):
        inputs = FinancialInputs(
            initial_capital=50000,
            monthly_fixed_costs=10000,
            gross_margin_pct=0.5,
            projected_monthly_revenue_base=30000,
        )
        result = run_financials(inputs)
        self.assertEqual(result.base_monthly_contribution, 15000)
        self.assertEqual(result.base_monthly_cash_flow, 5000)
        self.assertEqual(result.downside_monthly_revenue, 18000)
        self.assertEqual(result.downside_monthly_contribution, 9000)
        self.assertEqual(result.downside_monthly_cash_flow, -1000)
        self.assertEqual(result.break_even_monthly_revenue, 20000)
        self.assertEqual(result.months_to_break_even_base, 10.0)
        self.assertEqual(result.flags, ())

    def test_negative_cash_flow_flag_requires_both_cases(self):
        inputs = FinancialInputs(
            initial_capital=10000,
            monthly_fixed_costs=15000,
            gross_margin_pct=0.4,
            projected_monthly_revenue_base=20000,
            downside_revenue_multiplier=0.5,
        )
        result = run_financials(inputs)
        self.assertEqual(result.base_monthly_cash_flow, -7000)
        self.assertEqual(result.downside_monthly_cash_flow, -11000)
        self.assertEqual(result.break_even_monthly_revenue, 37500)
        self.assertIsNone(result.months_to_break_even_base)
        self.assertIn(FLAG_NEGATIVE_OR_MARGINAL_CASH_FLOW, result.flags)

    def test_zero_base_cash_flow_is_marginal(self):
        inputs = FinancialInputs(
            initial_capital=0,
            monthly_fixed_costs=10000,
            gross_margin_pct=0.5,
            projected_monthly_revenue_base=20000,
        )
        result = run_financials(inputs)
        self.assertEqual(result.break_even_monthly_revenue, 20000)
        self.assertEqual(result.base_monthly_cash_flow, 0)
        self.assertEqual(result.downside_monthly_cash_flow, -4000)
        self.assertEqual(result.flags, (FLAG_NEGATIVE_OR_MARGINAL_CASH_FLOW,))

    def test_positive_downside_does_not_flag_a_negative_base(self):
        inputs = FinancialInputs(
            initial_capital=0,
            monthly_fixed_costs=6000,
            gross_margin_pct=0.5,
            projected_monthly_revenue_base=10000,
            downside_revenue_multiplier=1.5,
        )
        result = run_financials(inputs)
        self.assertEqual(result.base_monthly_cash_flow, -1000)
        self.assertEqual(result.downside_monthly_cash_flow, 1500)
        self.assertEqual(result.flags, ())

    def test_zero_gross_margin_is_undefined_break_even(self):
        inputs = FinancialInputs(
            initial_capital=0,
            monthly_fixed_costs=0,
            gross_margin_pct=0,
            projected_monthly_revenue_base=0,
        )
        result = run_financials(inputs)
        self.assertIsNone(result.break_even_monthly_revenue)
        self.assertEqual(result.base_monthly_cash_flow, 0)
        self.assertEqual(result.downside_monthly_cash_flow, 0)
        self.assertEqual(
            result.flags,
            (FLAG_NEGATIVE_OR_MARGINAL_CASH_FLOW, FLAG_NO_GROSS_MARGIN),
        )

    def test_full_margin_and_default_downside_multiplier(self):
        inputs = FinancialInputs(
            initial_capital=0,
            monthly_fixed_costs=0,
            gross_margin_pct=1,
            projected_monthly_revenue_base=100,
        )
        result = run_financials(inputs)
        self.assertEqual(inputs.downside_revenue_multiplier, 0.6)
        self.assertEqual(result.base_monthly_cash_flow, 100)
        self.assertEqual(result.downside_monthly_revenue, 60)
        self.assertEqual(result.downside_monthly_cash_flow, 60)
        self.assertEqual(result.break_even_monthly_revenue, 0)
        self.assertEqual(result.months_to_break_even_base, 0.0)
        self.assertEqual(result.flags, ())

    def test_break_even_rounds_half_even_to_cents(self):
        inputs = FinancialInputs(
            initial_capital=0,
            monthly_fixed_costs=10,
            gross_margin_pct=0.3,
            projected_monthly_revenue_base=0,
        )
        result = run_financials(inputs)
        self.assertEqual(result.break_even_monthly_revenue, round(10 / 0.3, 2))
        self.assertEqual(result.break_even_monthly_revenue, 33.33)

    def test_capital_recovery_months_use_half_even(self):
        inputs = FinancialInputs(
            initial_capital=125,
            monthly_fixed_costs=0,
            gross_margin_pct=0.5,
            projected_monthly_revenue_base=200,
            downside_revenue_multiplier=1,
        )
        result = run_financials(inputs)
        self.assertEqual(result.base_monthly_cash_flow, 100)
        self.assertEqual(result.months_to_break_even_base, 1.2)

    def test_sub_cent_cash_flow_is_treated_as_zero(self):
        inputs = FinancialInputs(
            initial_capital=0,
            monthly_fixed_costs=0,
            gross_margin_pct=1,
            projected_monthly_revenue_base=0.004,
            downside_revenue_multiplier=1,
        )
        result = run_financials(inputs)
        self.assertEqual(result.base_monthly_cash_flow, 0)
        self.assertEqual(result.flags, (FLAG_NEGATIVE_OR_MARGINAL_CASH_FLOW,))
        self.assertIsNone(result.months_to_break_even_base)

    def test_result_to_dict_exports_engine_fields(self):
        result = run_financials(
            FinancialInputs(
                initial_capital=0,
                monthly_fixed_costs=0,
                gross_margin_pct=0,
                projected_monthly_revenue_base=0,
            )
        )
        payload = result_to_dict(result)
        self.assertIsNone(payload["break_even_monthly_revenue"])
        self.assertEqual(
            payload["flags"],
            [FLAG_NEGATIVE_OR_MARGINAL_CASH_FLOW, FLAG_NO_GROSS_MARGIN],
        )
        self.assertIn("months_to_break_even_base", payload["field_definitions"])
        self.assertEqual(payload["model_version"], "0.1-pilot")

    def test_rejects_non_finite_or_out_of_range_inputs(self):
        cases = [
            FinancialInputs(float("nan"), 0, 0.5, 0),
            FinancialInputs(-1, 0, 0.5, 0),
            FinancialInputs(0, -1, 0.5, 0),
            FinancialInputs(0, 0, -0.1, 0),
            FinancialInputs(0, 0, 1.1, 0),
            FinancialInputs(0, 0, 0.5, -1),
            FinancialInputs(0, 0, 0.5, 0, downside_revenue_multiplier=-0.1),
            FinancialInputs(True, 0, 0.5, 0),  # type: ignore[arg-type]
        ]
        for inputs in cases:
            with self.assertRaises(ValueError):
                run_financials(inputs)


class TestSeatOccupancyRevenue(unittest.TestCase):
    def test_primary_path_is_seats_times_occupancy_times_ticket(self):
        result = seat_occupancy_revenue(
            seats=10,
            average_ticket=20,
            weekday_occupancy=1,
            weekend_occupancy=0,
            operating_days=7,
        )
        self.assertEqual(result.occupancy, 5 / 7)
        self.assertEqual(result.revenue, 1_000.00)
        self.assertEqual(
            result.revenue,
            round(10 * result.occupancy * 20 * 7, 2),
        )

    def test_unverified_drivers_are_user_supplied_assumptions(self):
        result = seat_occupancy_revenue(200, 28, 0.45, 0.75, 360)
        self.assertEqual(result.revenue, 1_080_000.00)
        self.assertEqual(
            [item["key"] for item in result.assumption_sources],
            [
                "seats",
                "average_ticket",
                "weekday_occupancy",
                "weekend_occupancy",
                "operating_days",
            ],
        )
        self.assertTrue(
            all(item["source"] == "user" for item in result.assumption_sources)
        )
        self.assertTrue(
            all(
                item["evidence_label"] == USER_SUPPLIED_ASSUMPTION
                for item in result.assumption_sources
            )
        )

    def test_verified_driver_is_not_labeled_a_user_assumption(self):
        result = seat_occupancy_revenue(
            seats=10,
            average_ticket=20,
            weekday_occupancy=0.5,
            weekend_occupancy=0.5,
            operating_days=10,
            verified={"seats": True},
        )
        by_key = {item["key"]: item for item in result.assumption_sources}
        self.assertEqual(by_key["seats"]["source"], "verified")
        self.assertEqual(by_key["seats"]["evidence_label"], VERIFIED_DATA)
        self.assertEqual(by_key["average_ticket"]["evidence_label"], USER_SUPPLIED_ASSUMPTION)
        self.assertEqual(result.revenue, round(10 * 0.5 * 20 * 10, 2))

    def test_drivers_have_no_market_defaults(self):
        signature = inspect.signature(seat_occupancy_revenue)
        for name in (
            "seats",
            "average_ticket",
            "weekday_occupancy",
            "weekend_occupancy",
            "operating_days",
        ):
            self.assertIs(signature.parameters[name].default, inspect.Parameter.empty)

    def test_rejects_unmarked_or_invalid_drivers(self):
        with self.assertRaises(ValueError):
            seat_occupancy_revenue(1.5, 10, 0.5, 0.5, 10)
        with self.assertRaises(ValueError):
            seat_occupancy_revenue(10, 10, 1.1, 0.5, 10)
        with self.assertRaises(ValueError):
            seat_occupancy_revenue(10, 10, 0.5, 0.5, 10, verified={"covers": True})
        with self.assertRaises(ValueError):
            seat_occupancy_revenue(10, 10, 0.5, 0.5, 10, verified={"seats": 1})  # type: ignore[dict-item]


if __name__ == "__main__":
    unittest.main()

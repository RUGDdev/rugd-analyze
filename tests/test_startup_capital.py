"""Unit tests for the startup capital calculator. Scoring is not involved."""

import unittest

from engine.startup_capital_calculator import StartupInputs, calculate


class TestStartupCapital(unittest.TestCase):
    def test_seat_model_defaults_on_one_million_construction(self):
        result = calculate(StartupInputs(construction_cost=1_000_000))
        self.assertEqual(result.construction_cost, 1_000_000.00)
        self.assertEqual(result.soft_costs, 150_000.00)
        self.assertEqual(result.contingency, 115_000.00)
        self.assertEqual(result.total_project_cost, 1_265_000.00)
        self.assertEqual(result.debt, round(1_265_000.00 * 0.70, 2))
        self.assertEqual(result.equity, round(result.total_project_cost - result.debt, 2))
        self.assertEqual(result.food_and_beverage_revenue_base, 1_080_000.00)
        self.assertTrue(result.revenue_assumption_sources)
        self.assertTrue(
            all(
                item["evidence_label"] == "user-supplied assumption"
                for item in result.revenue_assumption_sources
            )
        )
        self.assertEqual(result.ticketed_events_base, 350_000.00)
        self.assertEqual(result.other_revenue_base, 21_600.00)
        self.assertEqual(result.year1_revenue_base, 1_451_600.00)
        self.assertEqual(result.food_and_beverage_revenue_downside, 648_000.00)
        self.assertEqual(result.ticketed_events_downside, 210_000.00)
        self.assertEqual(result.other_revenue_downside, 12_960.00)
        self.assertEqual(result.year1_revenue_downside, 870_960.00)
        self.assertEqual(result.ebitda_base, 290_320.00)
        self.assertEqual(result.ebitda_downside, 174_192.00)
        self.assertEqual(result.cash_flow_before_debt_service_base, 290_320.00)
        self.assertEqual(
            result.dscr_base,
            round(290_320.00 / result.annual_debt_service, 4),
        )
        self.assertEqual(
            result.dscr_downside,
            round(174_192.00 / result.annual_debt_service, 4),
        )

    def test_food_and_beverage_uses_weekday_and_weekend_weights(self):
        result = calculate(
            StartupInputs(
                construction_cost=1,
                soft_cost_pct=0,
                contingency_pct=0,
                debt_share=0,
                seats=10,
                average_ticket=20,
                weekday_occupancy=1,
                weekend_occupancy=0,
                operating_days=7,
                ticketed_events=0,
                other_revenue_pct=0,
            )
        )
        self.assertEqual(result.weekday_operating_days, 5.0)
        self.assertEqual(result.weekend_operating_days, 2.0)
        self.assertEqual(result.food_and_beverage_revenue_base, 1_000.00)

    def test_zero_interest_uses_straight_principal(self):
        result = calculate(
            StartupInputs(
                construction_cost=120_000,
                soft_cost_pct=0,
                contingency_pct=0,
                debt_share=1,
                annual_interest_rate=0,
                amortization_years=10,
                seats=120,
                average_ticket=100,
                weekday_occupancy=1,
                weekend_occupancy=1,
                operating_days=10,
                ticketed_events=0,
                other_revenue_pct=0,
                ebitda_margin=1,
                downside_revenue_multiplier=0.6,
            )
        )
        self.assertEqual(result.total_project_cost, 120_000.00)
        self.assertEqual(result.debt, 120_000.00)
        self.assertEqual(result.equity, 0.00)
        self.assertEqual(result.monthly_debt_service, 1_000.00)
        self.assertEqual(result.annual_debt_service, 12_000.00)
        self.assertEqual(result.year1_revenue_base, 120_000.00)
        self.assertEqual(result.dscr_base, 10.0)
        self.assertEqual(result.dscr_downside, 6.0)

    def test_zero_debt_leaves_dscr_undefined(self):
        result = calculate(
            StartupInputs(
                construction_cost=100,
                soft_cost_pct=0,
                contingency_pct=0,
                debt_share=0,
            )
        )
        self.assertEqual(result.annual_debt_service, 0.0)
        self.assertIsNone(result.dscr_base)
        self.assertIsNone(result.dscr_downside)
        self.assertEqual(result.equity, 100.00)

    def test_rejects_missing_or_out_of_range_construction(self):
        for construction in (0, -1, float("nan")):
            with self.assertRaises(ValueError):
                calculate(StartupInputs(construction_cost=construction))


if __name__ == "__main__":
    unittest.main()

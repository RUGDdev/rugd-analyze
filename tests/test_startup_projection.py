"""Cost-build totals and the three startup projection views.

Methodology § Core Principles — deterministic calculations.
Methodology § Investor Readiness Gate — this path does not mark investor-ready.
"""

import unittest

from engine.startup_projection import (
    USER_SUPPLIED_ASSUMPTION,
    VERIFIED_DATA,
    empty_projection,
    format_projection,
    project_startup,
)


def _project(**overrides):
    values = {
        "construction_cost": 1_000_000,
        "seats": 10,
        "average_ticket": 20,
        "weekday_occupancy": 1,
        "weekend_occupancy": 0,
        "operating_days": 7,
        "contribution_margin": 0.5,
        "equipment": 200_000,
        "soft_costs": 50_000,
        "preopening_working_capital": 30_000,
        "contingency_pct": 0.10,
        "debt_share": 0.5,
        "annual_interest_rate": 0,
        "amortization_years": 10,
        "annual_fixed_costs": 100,
        "downside_multiplier": 0.6,
    }
    values.update(overrides)
    construction = values.pop("construction_cost")
    seats = values.pop("seats")
    ticket = values.pop("average_ticket")
    weekday = values.pop("weekday_occupancy")
    weekend = values.pop("weekend_occupancy")
    days = values.pop("operating_days")
    margin = values.pop("contribution_margin")
    return project_startup(
        construction, seats, ticket, weekday, weekend, days, margin, **values
    )


class TestStartupProjection(unittest.TestCase):
    def test_cost_build_totals(self):
        result = _project()
        uses = result.sources_and_uses["uses"]
        sources = result.sources_and_uses["sources"]
        self.assertEqual(uses["contingency"]["amount"], 128_000.00)
        self.assertEqual(uses["total_project_cost"]["amount"], 1_408_000.00)
        self.assertEqual(sources["debt"]["amount"], 704_000.00)
        self.assertEqual(sources["equity"]["amount"], 704_000.00)
        self.assertEqual(sources["total_sources"]["amount"], 1_408_000.00)
        self.assertEqual(sources["monthly_debt_service"], round(704_000 / 120, 2))
        self.assertEqual(
            sources["annual_debt_service"],
            round(sources["monthly_debt_service"] * 12, 2),
        )

    def test_contingency_defaults_to_ten_percent(self):
        result = project_startup(
            1_000,
            10,
            20,
            1,
            0,
            7,
            1,
            debt_share=0,
            annual_fixed_costs=0,
        )
        self.assertEqual(result.sources_and_uses["uses"]["contingency"]["amount"], 100.00)
        self.assertEqual(result.sources_and_uses["uses"]["total_project_cost"]["amount"], 1_100.00)

    def test_three_views_use_the_seat_model(self):
        result = _project()
        annual_debt = result.sources_and_uses["sources"]["annual_debt_service"]
        self.assertEqual(result.base["revenue"], 1_000.00)
        self.assertEqual(result.downside["applied_to"], "occupancy")
        self.assertEqual(result.downside["revenue"], 600.00)
        self.assertEqual(result.base["cash_flow_before_debt_service"], 400.00)
        self.assertEqual(result.downside["cash_flow_before_debt_service"], 200.00)
        self.assertEqual(result.base["dscr"], round(400.00 / annual_debt, 4))
        self.assertEqual(result.downside["dscr"], round(200.00 / annual_debt, 4))
        self.assertEqual(
            result.break_even["revenue"],
            round((100 + annual_debt) / 0.5, 2),
        )

    def test_unverified_inputs_are_user_supplied_assumptions(self):
        result = _project(verified={"construction_cost": True})
        by_key = {item["key"]: item for item in result.assumptions}
        self.assertEqual(by_key["construction_cost"]["evidence_label"], VERIFIED_DATA)
        self.assertEqual(by_key["construction_cost"]["source"], "verified")
        for key in ("equipment", "soft_costs", "preopening_working_capital", "contingency_pct"):
            self.assertEqual(by_key[key]["evidence_label"], USER_SUPPLIED_ASSUMPTION)
            self.assertEqual(by_key[key]["source"], "user")

    def test_approval_flag_does_not_mark_investor_ready(self):
        withheld = _project()
        self.assertFalse(withheld.human_review_approved)
        self.assertFalse(withheld.is_final)
        self.assertFalse(withheld.investor_ready)
        approved = _project(human_review_approved=True)
        self.assertTrue(approved.human_review_approved)
        self.assertTrue(approved.is_final)
        self.assertFalse(approved.investor_ready)
        text = format_projection(approved.to_dict())
        self.assertIn("### Sources and uses", text)
        self.assertIn("### Assumption list", text)
        self.assertIn("### Base case", text)
        self.assertIn("### Downside case", text)
        self.assertIn("### Break-even", text)
        self.assertIn("investor_ready: false", text)
        self.assertIn("user-supplied assumption", text)

    def test_missing_worksheet_invents_no_figures(self):
        record = empty_projection()
        self.assertFalse(record["calculated"])
        self.assertIsNone(record["sources_and_uses"])
        self.assertFalse(record["investor_ready"])
        self.assertFalse(record["is_final"])
        self.assertIn("not calculated", record["note"])


if __name__ == "__main__":
    unittest.main()

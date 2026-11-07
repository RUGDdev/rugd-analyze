"""Secondary industry benchmarks stay out of recommend-against scoring."""

import unittest

from engine.financial import FinancialInputs, result_to_dict, run_financials
from scoring.industry_benchmarks import (
    LABEL,
    audit_record,
    printed_lines,
    reasonableness_check,
    reasonableness_note,
)
from scoring.rules import RECOMMEND_AGAINST_FLAGS, build_recommendation


class TestIndustryBenchmarks(unittest.TestCase):
    def test_catalog_is_labeled_and_sourced(self):
        record = audit_record()
        by_id = {item["id"]: item for item in record["benchmarks"]}
        self.assertEqual(record["label"], LABEL)
        self.assertFalse(record["may_raise_recommend_against_flags"])
        self.assertFalse(record["may_clear_recommend_against_flags"])
        self.assertEqual(by_id["full_service_income_before_taxes"]["value"], 0.028)
        self.assertEqual(by_id["full_service_labor"]["value"], 0.365)
        self.assertEqual(by_id["full_service_labor"]["label"], "secondary industry benchmark")
        self.assertIn("National Restaurant Association", by_id["full_service_labor"]["source"])
        self.assertIsInstance(record["not_loaded"][0], str)
        self.assertIn("food-and-beverage cost was not loaded", record["not_loaded"][0])
        self.assertTrue(all(line.startswith("secondary industry benchmark:") for line in printed_lines()))

    def test_reasonableness_check_does_not_change_recommend_against_flags(self):
        intake = {
            "assumptions": [],
            "verified_data": {"revenue_trailing_12m": None},
            "financial_inputs": {"inputs_are_measured": True},
        }
        financial = result_to_dict(
            run_financials(
                FinancialInputs(
                    initial_capital=0,
                    monthly_fixed_costs=15000,
                    gross_margin_pct=0.4,
                    projected_monthly_revenue_base=20000,
                    downside_revenue_multiplier=0.5,
                )
            )
        )
        before = build_recommendation(intake, financial["flags"], financial)
        check = reasonableness_check("full_service_labor", 0.40)
        after = build_recommendation(intake, financial["flags"], financial)
        self.assertEqual(before.blocking_flags, after.blocking_flags)
        self.assertEqual(before.gap_flags, after.gap_flags)
        self.assertEqual(check["recommend_against_flags"], [])
        self.assertFalse(check["raises_recommend_against_flags"])
        self.assertFalse(check["clears_recommend_against_flags"])
        self.assertEqual(check["label"], LABEL)
        self.assertTrue(set(check["recommend_against_flags"]).isdisjoint(RECOMMEND_AGAINST_FLAGS))
        self.assertIn("INSUFFICIENT_DEMAND_EVIDENCE", before.blocking_flags)

    def test_report_note_compares_ratios_without_changing_the_recommendation(self):
        intake = {
            "assumptions": [],
            "verified_data": {"revenue_trailing_12m": None},
            "financial_inputs": {"inputs_are_measured": True},
        }
        financial = result_to_dict(
            run_financials(
                FinancialInputs(
                    initial_capital=0,
                    monthly_fixed_costs=15000,
                    gross_margin_pct=0.4,
                    projected_monthly_revenue_base=20000,
                    downside_revenue_multiplier=0.5,
                )
            )
        )
        financial["labor_pct_of_sales"] = 0.40
        financial["occupancy_pct_of_sales"] = 0.057
        financial["pretax_margin"] = 0.02
        before = build_recommendation(intake, financial["flags"], financial)
        note = reasonableness_note(financial)
        after = build_recommendation(intake, financial["flags"], financial)
        self.assertEqual(before.draft_recommendation, after.draft_recommendation)
        self.assertEqual(before.blocking_flags, after.blocking_flags)
        self.assertEqual(before.gap_flags, after.gap_flags)
        self.assertIn("### Reasonableness check", note)
        self.assertIn("Secondary industry benchmark", note)
        self.assertIn("Labor %: calculated 40.0% is above the secondary industry benchmark", note)
        self.assertIn("NRA median 36.5% of sales", note)
        self.assertIn("Occupancy %: calculated 5.7% is equal to the secondary industry benchmark", note)
        self.assertIn("Pre-tax margin: calculated 2.0% is below the secondary industry benchmark", note)
        self.assertIn("NRA median 2.8% of sales", note)

    def test_missing_ratios_are_not_compared(self):
        note = reasonableness_note({})
        self.assertIn("Labor %: not calculated", note)
        self.assertIn("Occupancy %: not calculated", note)
        self.assertIn("Pre-tax margin: not calculated", note)
        self.assertIn("secondary industry benchmark", note)


if __name__ == "__main__":
    unittest.main()
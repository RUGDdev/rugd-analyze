"""Unit tests for methodology scoring. Weights are not applied."""

import unittest

from engine.financial import (
    FLAG_NEGATIVE_OR_MARGINAL_CASH_FLOW,
    FLAG_NO_GROSS_MARGIN,
    FinancialInputs,
    result_to_dict,
    run_financials,
)
from scoring.rules import (
    RECOMMEND_AGAINST_FLAGS,
    build_recommendation,
    evaluate_flags,
    investor_readiness_gate,
    report_context,
)


def assumption(key, value, source="verified", rationale="recorded for the test"):
    return {"key": key, "value": value, "source": source, "rationale": rationale}


def cleared_intake(**overrides):
    intake = {
        "engagement_type": "startup_feasibility",
        "business_name": "Example",
        "verified_data": {"revenue_trailing_12m": 120},
        "assumptions": [
            assumption("operator_capacity_adequate", True),
            assumption("unresolved_regulatory_or_liability", False),
            assumption("extraction_without_reinvestment", False),
        ],
        "financial_inputs": {"inputs_are_measured": True},
    }
    intake.update(overrides)
    return intake


class TestScoring(unittest.TestCase):
    def test_clear_measured_case_drafts_go_and_stays_unfinal(self):
        recommendation = build_recommendation(cleared_intake(), [])
        self.assertEqual(recommendation.draft_recommendation, "go")
        self.assertFalse(recommendation.is_final)
        self.assertTrue(recommendation.requires_human_review)
        self.assertEqual(recommendation.human_review_status, "pending")
        self.assertIsNone(recommendation.overall_feasibility_score)
        self.assertEqual(recommendation.blocking_flags, ())
        self.assertEqual(recommendation.gap_flags, ())
        self.assertIn("No weights are approved", recommendation.score_note)

    def test_verified_demand_statement_clears_when_trailing_revenue_is_absent(self):
        intake = cleared_intake(
            verified_data={"revenue_trailing_12m": None},
            assumptions=[
                assumption(" Demand_Evidence ", True, source="verified"),
                assumption("operator_capacity_adequate", True),
                assumption("unresolved_regulatory_or_liability", False),
                assumption("extraction_without_reinvestment", False),
            ],
        )
        recommendation = build_recommendation(intake, [])
        self.assertEqual(recommendation.criteria[0].status, "clear")
        self.assertNotIn("INSUFFICIENT_DEMAND_EVIDENCE", recommendation.blocking_flags)
        self.assertNotIn("DEMAND_EVIDENCE_UNVERIFIED", recommendation.gap_flags)
        self.assertFalse(recommendation.is_final)
        self.assertIsNone(recommendation.overall_feasibility_score)

    def test_verification_plan_and_non_boolean_claim_do_not_clear_demand(self):
        for claim in (
            assumption("demand_verification_plan", True, source="verified"),
            assumption("demand_evidence", "true", source="verified"),
            assumption("demand_evidence", 1, source="verified"),
        ):
            intake = cleared_intake(
                verified_data={"revenue_trailing_12m": None},
                assumptions=[
                    claim,
                    assumption("operator_capacity_adequate", True),
                    assumption("unresolved_regulatory_or_liability", False),
                    assumption("extraction_without_reinvestment", False),
                ],
            )
            recommendation = build_recommendation(intake, [])
            self.assertIn("INSUFFICIENT_DEMAND_EVIDENCE", recommendation.blocking_flags)
            self.assertEqual(recommendation.draft_recommendation, "do-not-proceed")

    def test_user_demand_claim_is_conditional_not_a_clear(self):
        intake = cleared_intake(
            verified_data={"revenue_trailing_12m": None},
            assumptions=[
                assumption("demand_evidence", True, source="user"),
                assumption("operator_capacity_adequate", True),
                assumption("unresolved_regulatory_or_liability", False),
                assumption("extraction_without_reinvestment", False),
            ],
        )
        recommendation = build_recommendation(intake, [])
        self.assertEqual(recommendation.draft_recommendation, "conditional")
        self.assertEqual(recommendation.blocking_flags, ())
        self.assertIn("DEMAND_EVIDENCE_UNVERIFIED", recommendation.gap_flags)

    def test_missing_demand_evidence_recommends_against(self):
        intake = cleared_intake(verified_data={"revenue_trailing_12m": None})
        recommendation = build_recommendation(intake, [])
        self.assertEqual(recommendation.draft_recommendation, "do-not-proceed")
        self.assertIn("INSUFFICIENT_DEMAND_EVIDENCE", recommendation.blocking_flags)
        self.assertIn("INSUFFICIENT_DEMAND_EVIDENCE", RECOMMEND_AGAINST_FLAGS)

    def test_zero_trailing_revenue_does_not_clear_demand(self):
        intake = cleared_intake(verified_data={"revenue_trailing_12m": 0})
        recommendation = build_recommendation(intake, [])
        self.assertIn("INSUFFICIENT_DEMAND_EVIDENCE", recommendation.blocking_flags)

    def test_unrelated_demand_key_does_not_clear_the_flag(self):
        intake = cleared_intake(
            verified_data={"revenue_trailing_12m": None},
            assumptions=[
                assumption("demand_notes", True),
                assumption("operator_capacity_adequate", True),
                assumption("unresolved_regulatory_or_liability", False),
                assumption("extraction_without_reinvestment", False),
            ],
        )
        recommendation = build_recommendation(intake, [])
        self.assertIn("INSUFFICIENT_DEMAND_EVIDENCE", recommendation.blocking_flags)

    def test_ai_interpretation_cannot_clear_or_raise_flags(self):
        intake = cleared_intake(
            verified_data={"revenue_trailing_12m": None},
            assumptions=[
                assumption("demand_evidence", True, source="ai_interpretation"),
                assumption("operator_capacity_adequate", False, source="ai_interpretation"),
            ],
        )
        recommendation = build_recommendation(intake, [])
        self.assertIn("INSUFFICIENT_DEMAND_EVIDENCE", recommendation.blocking_flags)
        self.assertNotIn("INADEQUATE_OPERATOR_CAPACITY", recommendation.blocking_flags)
        self.assertIn("UNEVALUATED_OPERATOR_CAPACITY", recommendation.gap_flags)
        self.assertTrue(recommendation.ai_interpretations_noted)

    def test_conflicting_operator_values_keep_the_blocking_flag(self):
        intake = cleared_intake(
            assumptions=[
                assumption("operator_capacity_adequate", True, source="user"),
                assumption("operator_capacity_adequate", False, source="verified"),
                assumption("unresolved_regulatory_or_liability", False),
                assumption("extraction_without_reinvestment", False),
            ]
        )
        recommendation = build_recommendation(intake, [])
        self.assertIn("INADEQUATE_OPERATOR_CAPACITY", recommendation.blocking_flags)

    def test_demand_denial_conflicts_with_trailing_revenue(self):
        intake = cleared_intake(
            assumptions=[
                assumption("demand_evidence", False),
                assumption("operator_capacity_adequate", True),
                assumption("unresolved_regulatory_or_liability", False),
                assumption("extraction_without_reinvestment", False),
            ]
        )
        recommendation = build_recommendation(intake, [])
        self.assertIn("INSUFFICIENT_DEMAND_EVIDENCE", recommendation.blocking_flags)
        demand = recommendation.criteria[0]
        self.assertIn("Conflicting", demand.evidence)

    def test_measured_negative_cash_flow_blocks_even_when_other_criteria_are_clear(self):
        recommendation = build_recommendation(
            cleared_intake(), [FLAG_NEGATIVE_OR_MARGINAL_CASH_FLOW]
        )
        self.assertEqual(recommendation.draft_recommendation, "do-not-proceed")
        self.assertIn(
            FLAG_NEGATIVE_OR_MARGINAL_CASH_FLOW, recommendation.blocking_flags
        )

    def test_unmeasured_inputs_do_not_apply_the_cash_flow_flag(self):
        intake = cleared_intake(
            financial_inputs={"inputs_are_measured": False, "initial_capital": 0}
        )
        recommendation = build_recommendation(
            intake,
            [FLAG_NEGATIVE_OR_MARGINAL_CASH_FLOW, FLAG_NO_GROSS_MARGIN],
        )
        self.assertEqual(recommendation.draft_recommendation, "conditional")
        self.assertEqual(recommendation.blocking_flags, ())
        self.assertIn("FINANCIAL_INPUTS_NOT_MEASURED", recommendation.gap_flags)
        self.assertEqual(recommendation.notices, ())
        self.assertEqual(
            recommendation.engine_flags,
            (FLAG_NEGATIVE_OR_MARGINAL_CASH_FLOW, FLAG_NO_GROSS_MARGIN),
        )

    def test_positive_base_and_negative_downside_can_draft_go(self):
        financial = result_to_dict(
            run_financials(
                FinancialInputs(
                    initial_capital=50000,
                    monthly_fixed_costs=10000,
                    gross_margin_pct=0.5,
                    projected_monthly_revenue_base=30000,
                )
            )
        )
        self.assertEqual(financial["flags"], [])
        recommendation = build_recommendation(cleared_intake(), financial["flags"], financial)
        self.assertEqual(recommendation.draft_recommendation, "go")
        self.assertFalse(recommendation.is_final)

    def test_zero_margin_notice_accompanies_the_cash_flow_flag_when_measured(self):
        financial = result_to_dict(
            run_financials(
                FinancialInputs(
                    initial_capital=0,
                    monthly_fixed_costs=0,
                    gross_margin_pct=0,
                    projected_monthly_revenue_base=0,
                )
            )
        )
        recommendation = build_recommendation(
            cleared_intake(), financial["flags"], financial
        )
        self.assertIn(FLAG_NEGATIVE_OR_MARGINAL_CASH_FLOW, recommendation.blocking_flags)
        self.assertEqual(recommendation.notices, (FLAG_NO_GROSS_MARGIN,))

    def test_evaluate_flags_keeps_the_draft_contract(self):
        payload = evaluate_flags(cleared_intake(), [])
        self.assertEqual(payload["recommendation"], "go")
        self.assertTrue(payload["requires_human_review"])
        self.assertFalse(payload["is_final"])
        self.assertIsNone(payload["overall_feasibility_score"])
        self.assertEqual(payload["flags"], [])

    def test_unknown_or_mismatched_engine_flags_are_rejected(self):
        with self.assertRaises(ValueError):
            build_recommendation(cleared_intake(), ["NOT_A_FLAG"])
        financial = result_to_dict(
            run_financials(
                FinancialInputs(0, 0, 0.5, 0)
            )
        )
        with self.assertRaises(ValueError):
            build_recommendation(cleared_intake(), [], financial)

    def test_unmeasured_figures_are_labeled_and_measured_figures_are_not(self):
        financial = {"base_monthly_cash_flow": 5, "flags": []}
        unmeasured = report_context(
            cleared_intake(financial_inputs={"inputs_are_measured": False}),
            build_recommendation(
                cleared_intake(financial_inputs={"inputs_are_measured": False}),
                [],
            ),
            financial,
            as_of_date="2026-10-26",
        )
        measured = report_context(
            cleared_intake(),
            build_recommendation(cleared_intake(), []),
            financial,
            as_of_date="2026-10-26",
        )
        self.assertIn("not a cash-flow finding", unmeasured["base_monthly_cash_flow"])
        self.assertEqual(measured["base_monthly_cash_flow"], "5.00")

    def test_silent_intake_cannot_draft_go(self):
        recommendation = build_recommendation(
            {"assumptions": [], "financial_inputs": {"inputs_are_measured": True}},
            [],
        )
        self.assertNotEqual(recommendation.draft_recommendation, "go")
        self.assertIn("INSUFFICIENT_DEMAND_EVIDENCE", recommendation.blocking_flags)
        self.assertIn("UNEVALUATED_OPERATOR_CAPACITY", recommendation.gap_flags)
        self.assertIn("UNEVALUATED_REGULATORY_OR_LIABILITY", recommendation.gap_flags)
        self.assertIn("UNEVALUATED_STEWARDSHIP", recommendation.gap_flags)


class TestInvestorReadinessGate(unittest.TestCase):
    def _ready_financials(self, dscr: float) -> dict:
        financial = result_to_dict(
            run_financials(
                FinancialInputs(
                    initial_capital=0,
                    monthly_fixed_costs=1000,
                    gross_margin_pct=0.5,
                    projected_monthly_revenue_base=10000,
                )
            )
        )
        financial["dscr_downside"] = dscr
        return financial

    def test_do_not_proceed_stays_internal_when_release_is_approved(self):
        intake = cleared_intake(verified_data={"revenue_trailing_12m": None})
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
        financial["dscr_downside"] = 2.0
        recommendation = build_recommendation(intake, financial["flags"], financial)
        self.assertEqual(recommendation.draft_recommendation, "do-not-proceed")
        self.assertIn(FLAG_NEGATIVE_OR_MARGINAL_CASH_FLOW, recommendation.engine_flags)
        gate = investor_readiness_gate(
            recommendation.engine_flags,
            financial,
            blocking_flags=recommendation.blocking_flags,
            conditional_flags=recommendation.gap_flags,
            accepted_mitigations=recommendation.blocking_flags,
            human_review_complete=True,
            release_approved=True,
            human_review_approved=True,
            demand_verified=True,
            regulatory_resolved=True,
        )
        self.assertEqual(gate.status, "internal")
        self.assertNotEqual(gate.status, "investor-ready")
        self.assertIn("INSUFFICIENT_DEMAND_EVIDENCE", RECOMMEND_AGAINST_FLAGS)

    def test_conditional_draft_is_not_investor_ready(self):
        intake = cleared_intake(
            verified_data={"revenue_trailing_12m": None},
            assumptions=[
                assumption("demand_evidence", True, source="user"),
                assumption("operator_capacity_adequate", True),
                assumption("unresolved_regulatory_or_liability", False),
                assumption("extraction_without_reinvestment", False),
            ],
        )
        financial = self._ready_financials(1.30)
        recommendation = build_recommendation(intake, financial["flags"], financial)
        self.assertEqual(recommendation.draft_recommendation, "conditional")
        self.assertEqual(recommendation.blocking_flags, ())
        gate = investor_readiness_gate(
            recommendation.engine_flags,
            financial,
            blocking_flags=recommendation.blocking_flags,
            conditional_flags=recommendation.gap_flags,
            human_review_complete=True,
            release_approved=True,
            human_review_approved=True,
            demand_verification_plan=True,
            regulatory_resolved=True,
        )
        self.assertEqual(gate.status, "conditional")
        self.assertNotEqual(gate.status, "investor-ready")

        below_minimum = investor_readiness_gate(
            [],
            self._ready_financials(1.10),
            human_review_complete=True,
            release_approved=True,
            human_review_approved=True,
            demand_verified=True,
            regulatory_resolved=True,
            lender_oriented=True,
        )
        self.assertEqual(below_minimum.status, "conditional")
        self.assertEqual(below_minimum.dscr_minimum, 1.25)

    def test_investor_ready_requires_human_review_approved(self):
        financial = self._ready_financials(1.30)
        shared = {
            "human_review_complete": True,
            "release_approved": True,
            "demand_verified": True,
            "regulatory_resolved": True,
        }
        withheld = investor_readiness_gate([], financial, **shared)
        self.assertEqual(withheld.status, "conditional")
        self.assertFalse(withheld.human_review_approved)
        self.assertNotEqual(withheld.status, "investor-ready")
        approved = investor_readiness_gate(
            [],
            financial,
            human_review_approved=True,
            **shared,
        )
        self.assertEqual(approved.status, "investor-ready")
        self.assertTrue(approved.human_review_approved)


if __name__ == "__main__":
    unittest.main()

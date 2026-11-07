"""The investor summary is written only after the readiness gate and approval.

Methodology § Investor Readiness Gate — investor-ready, and human_review_approved
explicitly true, are both required before a file is written.
"""

import tempfile
import unittest
from pathlib import Path

from engine.financial import FinancialInputs, result_to_dict, run_financials
from run_assessment import ROOT, write_investor_summary
from scoring.rules import build_recommendation


def _ready_case():
    intake = {
        "engagement_type": "startup_feasibility",
        "business_name": "Example",
        "verified_data": {"revenue_trailing_12m": 120},
        "assumptions": [
            {
                "key": "operator_capacity_adequate",
                "value": True,
                "source": "verified",
                "rationale": "recorded for the test",
            },
            {
                "key": "unresolved_regulatory_or_liability",
                "value": False,
                "source": "verified",
                "rationale": "recorded for the test",
            },
            {
                "key": "extraction_without_reinvestment",
                "value": False,
                "source": "verified",
                "rationale": "recorded for the test",
            },
        ],
        "financial_inputs": {"inputs_are_measured": True},
    }
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
    financial["dscr_downside"] = 1.0
    recommendation = build_recommendation(intake, financial["flags"], financial)
    return intake, recommendation, financial


class TestInvestorSummary(unittest.TestCase):
    def test_refuses_unless_investor_ready_and_approved(self):
        intake, recommendation, financial = _ready_case()
        with tempfile.TemporaryDirectory(dir=ROOT) as directory:
            target = Path(directory) / "summary.md"
            with self.assertRaises(ValueError):
                write_investor_summary(
                    intake,
                    recommendation,
                    financial,
                    human_review_approved=False,
                    output_path=target,
                )
            self.assertFalse(target.exists())

            blocked = dict(intake)
            blocked["verified_data"] = {"revenue_trailing_12m": None}
            blocked_recommendation = build_recommendation(
                blocked, financial["flags"], financial
            )
            self.assertEqual(blocked_recommendation.draft_recommendation, "do-not-proceed")
            with self.assertRaises(ValueError):
                write_investor_summary(
                    blocked,
                    blocked_recommendation,
                    financial,
                    human_review_approved=True,
                    output_path=target,
                )
            self.assertFalse(target.exists())

    def test_refuses_a_do_not_proceed_case(self):
        intake, _, financial = _ready_case()
        intake = dict(intake)
        intake["verified_data"] = {"revenue_trailing_12m": None}
        recommendation = build_recommendation(intake, financial["flags"], financial)
        self.assertEqual(recommendation.draft_recommendation, "do-not-proceed")
        with tempfile.TemporaryDirectory(dir=ROOT) as directory:
            target = Path(directory) / "summary.md"
            with self.assertRaises(ValueError) as caught:
                write_investor_summary(
                    intake,
                    recommendation,
                    financial,
                    human_review_approved=True,
                    output_path=target,
                )
            self.assertIn("refused", str(caught.exception))
            self.assertFalse(target.exists())

    def test_writes_summary_when_ready_and_approved(self):
        intake, recommendation, financial = _ready_case()
        with tempfile.TemporaryDirectory(dir=ROOT) as directory:
            target = Path(directory) / "summary.md"
            written = write_investor_summary(
                intake,
                recommendation,
                financial,
                human_review_approved=True,
                output_path=target,
            )
            text = written.read_text(encoding="utf-8")
            self.assertIn("## Recommendation and score", text)
            self.assertIn("Recommendation: go", text)
            self.assertIn("Score: not computed", text)
            self.assertIn("## Evidence labels", text)
            self.assertIn("revenue_trailing_12m: verified", text)
            self.assertIn("## Base and downside financials", text)
            self.assertIn("base_monthly_cash_flow: 4000.00", text)
            self.assertIn("downside_monthly_cash_flow: 2000.00", text)
            self.assertEqual(
                [line for line in text.splitlines() if line.startswith("## ")],
                [
                    "## Recommendation and score",
                    "## Evidence labels",
                    "## Base and downside financials",
                    "## Key risks and mitigations",
                    "## Stewardship observations",
                ],
            )


if __name__ == "__main__":
    unittest.main()

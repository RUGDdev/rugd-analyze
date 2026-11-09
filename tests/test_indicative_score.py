"""The indicative score stays beside the engine and cannot override a hard gate."""

import copy
import hashlib
import unittest
from pathlib import Path

from app.future import scoring_methodology
from app.indicative_score import LABEL, indicative_score
from app.pages import audit_html_page, results_page
from app.store import SAMPLE

ROOT = Path(__file__).resolve().parent.parent
ROOT_REPORT = ROOT / "reports" / "output" / "rugd-intelligence-draft.md"


def _result(**overrides):
    result = {
        "engine_ran": True,
        "recommendation": "do-not-proceed",
        "blocking_flags": ["INSUFFICIENT_DEMAND_EVIDENCE"],
        "gap_flags": [],
        "readiness_status": "internal",
        "human_review_status": "pending",
        "human_review_approved": False,
        "is_final": False,
        "demand": {"status": "uncleared"},
        "financial": None,
        "projection": None,
        "score_line": "Not calculated — methodology pending approval.",
    }
    result.update(overrides)
    return result


class TestIndicativeScore(unittest.TestCase):
    def test_hard_gates_force_blocked_and_leave_the_recommendation(self) -> None:
        before_sample = hashlib.sha256(SAMPLE.read_bytes()).hexdigest()
        before_report = hashlib.sha256(ROOT_REPORT.read_bytes()).hexdigest()
        result = _result()
        before = copy.deepcopy(result)
        score = indicative_score(result)
        self.assertEqual(score["band"], "Blocked")
        self.assertEqual(score["hard_gates"], ["INSUFFICIENT_DEMAND_EVIDENCE"])
        self.assertEqual(result, before)
        self.assertEqual(result["recommendation"], "do-not-proceed")
        self.assertEqual(result["readiness_status"], "internal")
        self.assertFalse(result["human_review_approved"])
        self.assertFalse(score["overrides_flags"])
        self.assertFalse(score["sets_human_review_approved"])
        self.assertFalse(score["changes_investor_readiness"])
        self.assertFalse(score["changes_recommendation"])
        self.assertIn("does not override that flag", score["explanation"])
        self.assertIn("does not set human_review_approved", score["explanation"])
        capacity = _result(
            blocking_flags=["INADEQUATE_OPERATOR_CAPACITY"],
            financial={
                "base_monthly_contribution": 400,
                "base_monthly_cash_flow": 200,
                "months_to_break_even_base": 12,
            },
            demand={"status": "cleared"},
        )
        blocked = indicative_score(capacity)
        self.assertEqual(blocked["band"], "Blocked")
        self.assertEqual(capacity["recommendation"], "do-not-proceed")
        self.assertGreater(blocked["score"], 0)
        seam = scoring_methodology()
        self.assertFalse(seam["enabled"])
        self.assertIsNone(seam["score"])
        self.assertEqual(hashlib.sha256(SAMPLE.read_bytes()).hexdigest(), before_sample)
        self.assertEqual(hashlib.sha256(ROOT_REPORT.read_bytes()).hexdigest(), before_report)

    def test_score_responds_to_verified_demand_and_engine_financials(self) -> None:
        uncleared = indicative_score(_result())
        cleared = indicative_score(
            _result(
                recommendation="conditional",
                blocking_flags=[],
                readiness_status="conditional",
                demand={"status": "cleared"},
            )
        )
        unverified = indicative_score(
            _result(
                recommendation="conditional",
                blocking_flags=[],
                gap_flags=["DEMAND_EVIDENCE_UNVERIFIED"],
                demand={"status": "unverified"},
            )
        )
        self.assertEqual(uncleared["components"]["market_validity"]["score"], 0)
        self.assertEqual(unverified["components"]["market_validity"]["score"], 25)
        self.assertEqual(cleared["components"]["market_validity"]["score"], 60)
        self.assertGreater(cleared["score"], uncleared["score"])
        self.assertEqual(cleared["band"], "Weak")
        self.assertEqual(cleared["score"], 45)
        financed = indicative_score(
            _result(
                recommendation="conditional",
                blocking_flags=[],
                readiness_status="conditional",
                demand={"status": "cleared"},
                financial={
                    "base_monthly_contribution": 400,
                    "base_monthly_cash_flow": 200,
                    "months_to_break_even_base": 12,
                },
            )
        )
        self.assertEqual(financed["components"]["profitability"]["score"], 90)
        self.assertGreater(financed["score"], cleared["score"])
        self.assertEqual(financed["band"], "Conditional")
        self.assertNotEqual(financed["band"], "Blocked")
        covered = indicative_score(
            _result(
                recommendation="conditional",
                blocking_flags=[],
                demand={"status": "cleared"},
                financial={
                    "base_monthly_contribution": 400,
                    "base_monthly_cash_flow": 200,
                    "months_to_break_even_base": 12,
                },
                projection={"calculated": True, "views": {"downside": {"dscr": 1.2}}},
            )
        )
        self.assertEqual(covered["components"]["profitability"]["score"], 100)
        self.assertEqual(covered["components"]["durable_value"]["score"], 70)
        noted = indicative_score(
            _result(
                recommendation="conditional",
                blocking_flags=[],
                demand={"status": "cleared"},
            ),
            notes=[{"pillar_id": "stewardship", "note": "Reinvest the first surplus."}],
        )
        self.assertEqual(noted["components"]["durable_value"]["score"], 74)
        self.assertGreater(noted["components"]["durable_value"]["score"], 70)
        strong = indicative_score(
            _result(
                recommendation="conditional",
                blocking_flags=[],
                readiness_status="conditional",
                demand={"status": "cleared"},
                financial={
                    "base_monthly_contribution": 400,
                    "base_monthly_cash_flow": 200,
                    "months_to_break_even_base": 12,
                },
                projection={"calculated": True, "views": {"downside": {"dscr": 1.2}}},
            ),
            notes=[{"pillar_id": pillar, "note": "Noted."} for pillar in (
                "market-demand",
                "competitive-position",
                "financial-feasibility",
                "operational-readiness",
                "risk-profile",
                "stewardship",
                "implementation",
            )],
            observations=[
                {
                    "source": "U.S. Bureau of Labor Statistics, Quarterly Census of Employment and Wages",
                    "measure": "Private annual average employment",
                    "value": "1842",
                }
            ],
        )
        self.assertEqual(strong["components"]["market_validity"]["score"], 80)
        self.assertEqual(strong["score"], 91)
        self.assertEqual(strong["band"], "Strong")
        self.assertEqual(strong["weights"], {"market_validity": 40, "profitability": 35, "durable_value": 25})
        gated = copy.deepcopy(strong)
        source = _result(
            recommendation="do-not-proceed",
            blocking_flags=["INSUFFICIENT_DEMAND_EVIDENCE"],
            demand={"status": "cleared"},
            financial={
                "base_monthly_contribution": 400,
                "base_monthly_cash_flow": 200,
                "months_to_break_even_base": 12,
            },
            projection={"calculated": True, "views": {"downside": {"dscr": 1.2}}},
        )
        still_blocked = indicative_score(
            source,
            notes=[{"pillar_id": "stewardship", "note": "Noted."}],
            observations=[
                {
                    "source": "U.S. Bureau of Labor Statistics, Quarterly Census of Employment and Wages",
                    "measure": "Private annual average employment",
                    "value": "1842",
                }
            ],
        )
        self.assertGreater(still_blocked["score"], 50)
        self.assertEqual(still_blocked["band"], "Blocked")
        self.assertEqual(source["recommendation"], "do-not-proceed")
        self.assertEqual(source["blocking_flags"], ["INSUFFICIENT_DEMAND_EVIDENCE"])
        self.assertFalse(source["human_review_approved"])
        self.assertNotEqual(gated, source)

    def test_pages_label_the_score_and_keep_the_baseline_status(self) -> None:
        record = {
            "id": "rugd-intelligence-baseline",
            "business_name": "RUGD Intelligence",
            "tier": "analyze",
            "read_only": True,
            "pilot_label": "Official baseline. Not a completed customer study.",
            "human_review_approved": False,
        }
        result = _result()
        page = results_page(record, result)
        audit = audit_html_page(record, result)
        for shown in (page, audit):
            self.assertIn(LABEL, shown)
            self.assertIn("Indicative score:</strong> ", shown)
            self.assertIn("Band:</strong> Blocked", shown)
            self.assertIn("Recommendation:</strong> do-not-proceed", shown)
            self.assertIn("INSUFFICIENT_DEMAND_EVIDENCE:</strong> present", shown)
            self.assertIn("Investor readiness:</strong> internal", shown)
            self.assertIn("human_review_approved:</strong> false", shown)
            self.assertNotIn("Investor readiness:</strong> investor-ready", shown)
        self.assertIn("Not calculated — methodology pending approval.", page)

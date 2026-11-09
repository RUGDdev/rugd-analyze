"""Indicative 0–100 score. It does not replace the engine.

The feasibility score in scoring.rules stays uncalculated. This module reads an
engine result and optional educational notes. It does not write them, clear a
recommend-against flag, set human_review_approved, or change investor readiness.
"""

from __future__ import annotations

from typing import Any

from app.durable_value import PILLARS
from scoring.rules import RECOMMEND_AGAINST_FLAGS

LABEL = (
    "Indicative assessment — market validity, financial viability, and stewardship readiness. "
    "Does not override engine flags or human review."
)

WEIGHTS = {
    "market_validity": 45,
    "financial_viability": 40,
    "stewardship_readiness": 15,
}

DEMAND_POINTS = {"cleared": 60, "unverified": 25, "uncleared": 0}
MARKET_SIGNAL_POINTS = 20
COMPETITIVE_DENSITY_POINTS = 0
CONTRIBUTION_POSITIVE = 30
CONTRIBUTION_ZERO = 10
CASH_FLOW_POSITIVE = 30
CASH_FLOW_ZERO = 10
DSCR_COVERS = 20
DSCR_BELOW_ONE = 5
DSCR_NOT_CALCULATED = 10
RECOVERY_WITHIN_24 = 20
RECOVERY_WITHIN_60 = 12
RECOVERY_LONGER = 6
STEWARDSHIP_FLOOR = 90
STEWARDSHIP_NOTE_POINTS = 1
PILLAR_IDS = tuple(str(item["id"]) for item in PILLARS)


def indicative_score(
    result: dict[str, Any],
    notes: list[dict[str, Any]] | None = None,
    observations: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Return the score for a completed engine result. The inputs are not changed."""
    blocking = [str(flag) for flag in result.get("blocking_flags") or []]
    hard_gates = [flag for flag in blocking if flag in RECOMMEND_AGAINST_FLAGS]
    market = _market(result, observations)
    financial = _profitability(result, blocking)
    stewardship = _stewardship(notes)
    overall = (
        market["score"] * WEIGHTS["market_validity"]
        + financial["score"] * WEIGHTS["financial_viability"]
        + stewardship["score"] * WEIGHTS["stewardship_readiness"]
    ) // 100
    blocked = bool(hard_gates)
    band = _band(overall, blocked)
    explanation = _explanation(overall, band, hard_gates, market, financial, stewardship)
    stored_recommendation = str(result.get("recommendation") or "")
    return {
        "label": LABEL,
        "gate_status": "Blocked" if blocked else "Open",
        "gate_recommendation": "do-not-proceed" if blocked else stored_recommendation,
        "score": overall,
        "score_role": "indicative only",
        "band": band,
        "hard_gates": hard_gates,
        "weights": dict(WEIGHTS),
        "components": {
            "market_validity": market,
            "financial_viability": financial,
            "stewardship_readiness": stewardship,
        },
        "explanation": explanation,
        "overrides_flags": False,
        "sets_human_review_approved": False,
        "changes_investor_readiness": False,
        "changes_recommendation": False,
    }


def _market(result: dict[str, Any], observations: list[dict[str, Any]] | None) -> dict[str, Any]:
    status = _demand_status(result)
    demand_points = DEMAND_POINTS[status]
    signal = _market_signal(observations)
    signal_points = MARKET_SIGNAL_POINTS if signal else 0
    demand_detail = {
        "cleared": "Demand evidence is verified, so this portion is 60.",
        "unverified": "Demand evidence is a user claim and is not verified, so this portion is 25.",
        "uncleared": "Demand evidence is not verified, so this portion is 0.",
    }[status]
    signal_detail = (
        "A stored public market figure adds 20. It does not clear a recommend-against flag."
        if signal
        else "No market-size or growth figure is stored on this result, so this portion is 0."
    )
    inputs = (
        {"name": "Demand evidence", "points": demand_points, "maximum": 60, "detail": demand_detail},
        {"name": "Market size or growth", "points": signal_points, "maximum": 20, "detail": signal_detail},
        {
            "name": "Competitive density",
            "points": COMPETITIVE_DENSITY_POINTS,
            "maximum": 20,
            "detail": "Competitive density is not measured, so this portion is 0.",
        },
    )
    return {"name": "Market Validity", "score": sum(item["points"] for item in inputs), "inputs": inputs}


def _profitability(result: dict[str, Any], blocking: list[str]) -> dict[str, Any]:
    financial = result.get("financial") if isinstance(result.get("financial"), dict) else None
    if financial is None:
        contribution = (0, "Monthly contribution was not calculated, so this portion is 0.")
        cash = (0, "Monthly cash flow was not calculated, so this portion is 0.")
        recovery = (0, "Capital recovery months were not calculated, so this portion is 0.")
    else:
        contribution_value = _number(financial.get("base_monthly_contribution"))
        cash_value = _number(financial.get("base_monthly_cash_flow"))
        months = _number(financial.get("months_to_break_even_base"))
        contribution = _contribution_points(contribution_value)
        if "NEGATIVE_OR_MARGINAL_CASH_FLOW" in blocking:
            cash = (0, "NEGATIVE_OR_MARGINAL_CASH_FLOW is active, so the cash-flow portion is 0.")
        else:
            cash = _cash_points(cash_value)
        recovery = _recovery_points(months, cash_value)
    dscr = _dscr_points(result.get("projection"))
    inputs = (
        {"name": "Contribution", "points": contribution[0], "maximum": 30, "detail": contribution[1]},
        {"name": "Cash-flow coverage", "points": cash[0], "maximum": 30, "detail": cash[1]},
        {"name": "Downside DSCR", "points": dscr[0], "maximum": 20, "detail": dscr[1]},
        {"name": "Capital recovery", "points": recovery[0], "maximum": 20, "detail": recovery[1]},
    )
    return {
        "name": "Financial Viability",
        "score": sum(item["points"] for item in inputs),
        "inputs": inputs,
    }


def _stewardship(notes: list[dict[str, Any]] | None) -> dict[str, Any]:
    counted: set[str] = set()
    for item in notes or []:
        pillar_id = str(item.get("pillar_id") or "").strip()
        text = str(item.get("note") or "").strip()
        if pillar_id in PILLAR_IDS and text:
            counted.add(pillar_id)
    note_points = STEWARDSHIP_NOTE_POINTS * len(counted)
    score = min(100, STEWARDSHIP_FLOOR + note_points)
    inputs = (
        {
            "name": "Floor for missing optional notes",
            "points": STEWARDSHIP_FLOOR,
            "maximum": 90,
            "detail": "Missing optional notes stay at 90. The penalty for a missing note is minimal.",
        },
        {
            "name": "Pillar notes",
            "points": note_points,
            "maximum": STEWARDSHIP_NOTE_POINTS * len(PILLAR_IDS),
            "detail": (
                f"{len(counted)} of {len(PILLAR_IDS)} pillars have a stored note. "
                "Each note adds 1 point."
            ),
        },
    )
    return {"name": "Stewardship Readiness", "score": score, "inputs": inputs}


def _demand_status(result: dict[str, Any]) -> str:
    status = str((result.get("demand") or {}).get("status") or "").strip()
    if status in DEMAND_POINTS:
        return status
    blocking = result.get("blocking_flags") or []
    gaps = result.get("gap_flags") or []
    if "DEMAND_EVIDENCE_UNVERIFIED" in gaps and "INSUFFICIENT_DEMAND_EVIDENCE" not in blocking:
        return "unverified"
    return "uncleared"


def _market_signal(observations: list[dict[str, Any]] | None) -> bool:
    words = (
        "employment",
        "population",
        "establishment",
        "gdp",
        "personal income",
        "payroll",
        "wage",
        "unemployment",
        "labor force",
    )
    for item in observations or []:
        source = str(item.get("source") or "").lower()
        if "synthetic" in source:
            continue
        measure = str(item.get("measure") or "").lower()
        value = str(item.get("value") or "").replace(",", "").strip()
        if _positive_number(value) and any(word in measure for word in words):
            return True
    return False


def _positive_number(value: str) -> bool:
    if not value or value.startswith("-") or value.startswith("("):
        return False
    try:
        return float(value) > 0
    except ValueError:
        return False


def _contribution_points(value: float | None) -> tuple[int, str]:
    if value is None:
        return 0, "Monthly contribution was not calculated, so this portion is 0."
    if value > 0:
        return CONTRIBUTION_POSITIVE, "Base monthly contribution is positive, so this portion is 30."
    if value == 0:
        return CONTRIBUTION_ZERO, "Base monthly contribution is zero, so this portion is 10."
    return 0, "Base monthly contribution is negative, so this portion is 0."


def _cash_points(value: float | None) -> tuple[int, str]:
    if value is None:
        return 0, "Monthly cash flow was not calculated, so this portion is 0."
    if value > 0:
        return CASH_FLOW_POSITIVE, "Base monthly cash flow is positive, so this portion is 30."
    if value == 0:
        return CASH_FLOW_ZERO, "Base monthly cash flow is zero, so this portion is 10."
    return 0, "Base monthly cash flow is negative, so this portion is 0."


def _recovery_points(months: float | None, cash_flow: float | None) -> tuple[int, str]:
    if months is None:
        return 0, "Capital recovery months were not calculated, so this portion is 0."
    if cash_flow is None or cash_flow <= 0:
        return 0, "Capital recovery months were not calculated, so this portion is 0."
    if months <= 24:
        return RECOVERY_WITHIN_24, "Capital recovery is 24 months or less, so this portion is 20."
    if months <= 60:
        return RECOVERY_WITHIN_60, "Capital recovery is 60 months or less, so this portion is 12."
    return RECOVERY_LONGER, "Capital recovery is longer than 60 months, so this portion is 6."


def _dscr_points(projection: Any) -> tuple[int, str]:
    views = projection.get("views") if isinstance(projection, dict) else None
    downside = views.get("downside") if isinstance(views, dict) else None
    value = _number(downside.get("dscr") if isinstance(downside, dict) else None)
    if value is None:
        return DSCR_NOT_CALCULATED, "Downside DSCR was not calculated, so this portion is 10."
    if value >= 1:
        return DSCR_COVERS, "Downside DSCR is at least 1, so this portion is 20."
    if value >= 0:
        return DSCR_BELOW_ONE, "Downside DSCR is below 1, so this portion is 5."
    return 0, "Downside DSCR is negative, so this portion is 0."


def _band(score: int, blocked: bool) -> str:
    if blocked:
        return "Blocked"
    if score >= 75:
        return "Strong"
    if score >= 50:
        return "Conditional"
    return "Weak"


def _explanation(
    score: int,
    band: str,
    hard_gates: list[str],
    market: dict[str, Any],
    profitability: dict[str, Any],
    durable: dict[str, Any],
) -> str:
    if hard_gates:
        opening = (
            f"Blocked. {', '.join(hard_gates)} keeps the recommendation do-not-proceed. "
            "The numeric score does not override that flag."
        )
    else:
        opening = f"Band {band}. The numeric score is {score} of 100."
    market_text = " ".join(item["detail"] for item in market["inputs"])
    profit_text = " ".join(item["detail"] for item in profitability["inputs"])
    durable_text = " ".join(item["detail"] for item in durable["inputs"])
    return (
        f"{opening} {market_text} {profit_text} {durable_text} "
        "This indicative score does not set human_review_approved and does not change investor readiness."
    )


def _number(value: Any) -> float | None:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip().replace(",", "")
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None

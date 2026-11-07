"""
Rule-based scoring and recommend-against flags.

Methodology § Scoring Approach — five automatic flags, and an overall score
that is a weighted average whose weights are adjustable by engagement type.
Methodology § Core Principles — evidence hierarchy, and human approval before
a final recommendation.
Methodology § Output Requirements — go / conditional / do-not-proceed, including stop.

This module does not assign dimension scores and does not apply weights.
No engagement-type weight table is approved. AI-authored assumption text cannot
raise or clear a recommend-against flag.
"""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass
from typing import Any

from engine.financial import (
    FLAG_NEGATIVE_OR_MARGINAL_CASH_FLOW,
    FLAG_NO_GROSS_MARGIN,
    FIELD_DEFINITIONS,
    MODEL_VERSION,
)
from scoring.industry_benchmarks import reasonableness_note

METHODOLOGY_VERSION = "1.0"

RECOMMEND_AGAINST_FLAGS = frozenset(
    {
        "INSUFFICIENT_DEMAND_EVIDENCE",
        "NEGATIVE_OR_MARGINAL_CASH_FLOW",
        "INADEQUATE_OPERATOR_CAPACITY",
        "UNRESOLVED_REGULATORY_OR_LIABILITY",
        "EXTRACTION_WITHOUT_REINVESTMENT",
    }
)

FLAG_DEMAND = "INSUFFICIENT_DEMAND_EVIDENCE"
FLAG_OPERATOR = "INADEQUATE_OPERATOR_CAPACITY"
FLAG_REGULATORY = "UNRESOLVED_REGULATORY_OR_LIABILITY"
FLAG_EXTRACTION = "EXTRACTION_WITHOUT_REINVESTMENT"
FLAG_DEMAND_UNVERIFIED = "DEMAND_EVIDENCE_UNVERIFIED"
FLAG_OPERATOR_GAP = "UNEVALUATED_OPERATOR_CAPACITY"
FLAG_REGULATORY_GAP = "UNEVALUATED_REGULATORY_OR_LIABILITY"
FLAG_STEWARDSHIP_GAP = "UNEVALUATED_STEWARDSHIP"
FLAG_FINANCIALS_UNMEASURED = "FINANCIAL_INPUTS_NOT_MEASURED"

KEY_DEMAND = "demand_evidence"
KEY_OPERATOR = "operator_capacity_adequate"
KEY_REGULATORY = "unresolved_regulatory_or_liability"
KEY_EXTRACTION = "extraction_without_reinvestment"

ACTIONABLE_SOURCES = frozenset({"user", "verified"})
KNOWN_ENGINE_FLAGS = frozenset(
    {FLAG_NEGATIVE_OR_MARGINAL_CASH_FLOW, FLAG_NO_GROSS_MARGIN}
)

REF_DEMAND = (
    "Methodology § Scoring Approach — insufficient evidence of demand."
)
REF_CASH = (
    "Methodology § Scoring Approach — negative or marginal cash-flow "
    "under base and downside cases."
)
REF_OPERATOR = (
    "Methodology § Scoring Approach — founder/operator capacity inadequate "
    "for the proposed scope."
)
REF_REGULATORY = (
    "Methodology § Scoring Approach — material unresolved regulatory or "
    "liability issues."
)
REF_STEWARDSHIP = (
    "Methodology § Scoring Approach — stewardship indicators show extraction "
    "without reinvestment capacity."
)
REF_UNMEASURED = (
    "Methodology § Core Principles — verified data and assumptions stay "
    "distinct. Unmeasured financial inputs are not a base case or a downside case."
)
REF_MARGIN = (
    "Engine notice — gross margin is not positive, so break-even revenue is "
    "undefined. This is not an additional recommend-against criterion."
)

DIMENSIONS = (
    "Market & Demand Reality",
    "Competitive Position & Differentiation",
    "Financial Feasibility & Capital Requirements",
    "Operational Readiness & Capacity",
    "Risk Profile (market, execution, financial, regulatory)",
    "Stewardship Indicators (reinvestment capacity, resilience, continuity potential)",
    "Implementation Feasibility (for AI or operational improvements)",
)

SCORE_NOTE = (
    "Not computed. Methodology § Scoring Approach defines the overall "
    "feasibility score as a weighted average and says weights are adjustable "
    "by engagement type. No weights are approved, and no 1–5 rubric is "
    "approved, so none of these dimensions received a score: "
    + "; ".join(DIMENSIONS)
    + "."
)

METHOD_ASSUMPTIONS: tuple[str, ...] = (
    "Marginal cash flow means monthly cash flow rounded half-even to cents is less than or equal to zero. No other marginal band is approved.",
    "NEGATIVE_OR_MARGINAL_CASH_FLOW is raised only when both the base case and the downside case meet that test.",
    "Any flag in the approved recommend-against set drafts do-not-proceed. No per-flag split between do-not-proceed and conditional-only is approved.",
    "A criterion with no user or verified input stays unevaluated. Unevaluated criteria draft conditional when no recommend-against flag fired, so a silent intake cannot draft go.",
    "Assumptions with source ai_interpretation are listed. They do not raise or clear recommend-against flags.",
    "demand_evidence true with source verified, or verified trailing revenue greater than zero, clears insufficient demand. Trailing revenue of zero does not. Trailing revenue is not a market-size score.",
    "demand_evidence true with source user leaves DEMAND_EVIDENCE_UNVERIFIED. That gap drafts conditional when no recommend-against flag fired. It does not draft do-not-proceed by itself.",
    "If demand support conflicts with demand_evidence false from a user or verified source, the insufficient-demand flag stays on.",
    "If operator capacity, regulatory exposure, or extraction has both true and false from user or verified sources, the recommend-against flag stays on.",
    "When financial_inputs is present and inputs_are_measured is omitted, the inputs are treated as measured. When the field is false, or financial_inputs is absent, the cash-flow criterion is not evaluated.",
    "months_to_break_even_base is months to recover initial capital at the base cash-flow rate. Break-even revenue is break_even_monthly_revenue.",
    "The overall feasibility score and the 1–5 dimension scores are not computed.",
    "No currency unit is defined on the intake. Amounts stay in the unit of the inputs.",
    "This module cannot record human approval. is_final stays false and human_review_status stays pending.",
)

NEXT_ACTIONS = {
    FLAG_DEMAND: (
        "Gather verified demand evidence and record it as verified trailing "
        "revenue above zero, or as demand_evidence true with source verified. "
        "Re-run before reconsideration."
    ),
    FLAG_NEGATIVE_OR_MARGINAL_CASH_FLOW: (
        "Measured base and downside monthly cash flow are both zero or "
        "negative. Stop on this capital plan, or replace the measured inputs "
        "and re-run, before any proceed decision."
    ),
    FLAG_OPERATOR: (
        "The intake states operator capacity is inadequate for the proposed "
        "scope. Narrow the scope or record a user or verified change in "
        "capacity, then re-run."
    ),
    FLAG_REGULATORY: (
        "Resolve the regulatory or liability issue and record "
        "unresolved_regulatory_or_liability false with source user or "
        "verified, then re-run."
    ),
    FLAG_EXTRACTION: (
        "The intake states extraction without reinvestment capacity. Stop "
        "unless a later user or verified assumption records otherwise and the "
        "assessment is re-run."
    ),
    FLAG_DEMAND_UNVERIFIED: (
        "Demand support on file is user-supplied only. Verify it, or keep "
        "the draft conditional."
    ),
    FLAG_OPERATOR_GAP: (
        "Record operator_capacity_adequate as true or false with source user "
        "or verified."
    ),
    FLAG_REGULATORY_GAP: (
        "Record unresolved_regulatory_or_liability as true or false with "
        "source user or verified."
    ),
    FLAG_STEWARDSHIP_GAP: (
        "Record extraction_without_reinvestment as true or false with source "
        "user or verified."
    ),
    FLAG_FINANCIALS_UNMEASURED: (
        "Replace unmeasured financial inputs with measured figures, set "
        "inputs_are_measured to true, and re-run."
    ),
}

HUMAN_REVIEW_ACTION = (
    "Human reviewer must approve or reject this draft before it is used as a "
    "recommendation. This runner cannot record that approval."
)
STOP_ACTION = (
    "Stop. Do not proceed on this evidence. Methodology § Output Requirements "
    "includes stop as a valid next action."
)
CONDITIONAL_ACTION = (
    "Keep this draft conditional until every unevaluated criterion is recorded "
    "and a human reviewer approves the result."
)
GO_ACTION = (
    "No recommend-against flag fired and no criterion was left unevaluated. "
    "A human reviewer still has to approve this draft before it is a "
    "recommendation."
)


@dataclass(frozen=True)
class CriterionAssessment:
    criterion_id: str
    methodology_ref: str
    status: str  # triggered, clear, gap
    flag: str | None
    evidence: str


@dataclass(frozen=True)
class Recommendation:
    draft_recommendation: str
    is_final: bool
    requires_human_review: bool
    human_review_status: str
    blocking_flags: tuple[str, ...]
    gap_flags: tuple[str, ...]
    notices: tuple[str, ...]
    criteria: tuple[CriterionAssessment, ...]
    overall_feasibility_score: None
    score_note: str
    engine_flags: tuple[str, ...]
    method_assumptions: tuple[str, ...]
    ai_interpretations_noted: tuple[str, ...]
    next_actions: tuple[str, ...]


def evaluate_flags(
    intake: dict[str, Any], financial_flags: list[str]
) -> dict[str, Any]:
    """
    Apply methodology automatic flags.
    Cite: Methodology § Scoring Approach.

    `recommendation` is a draft. `requires_human_review` is always true.
    """
    return recommendation_to_dict(build_recommendation(intake, financial_flags))


def build_recommendation(
    intake: dict[str, Any],
    financial_flags: list[str] | tuple[str, ...] | None = None,
    financial_result: dict[str, Any] | None = None,
) -> Recommendation:
    """Return a draft recommendation. Never a final one."""
    if not isinstance(intake, dict):
        raise ValueError("intake must be an object")
    flags = _engine_flags(financial_flags, financial_result)
    assumptions = _load_assumptions(intake)
    ai_notes = tuple(_ai_lines(assumptions))
    measured = _inputs_measured(intake)

    criteria = (
        _assess_demand(intake, assumptions),
        _assess_cash(flags, measured, financial_result),
        _assess_polarity(
            assumptions,
            key=KEY_OPERATOR,
            criterion_id="operator_capacity",
            methodology_ref=REF_OPERATOR,
            harmful_when=False,
            harmful_flag=FLAG_OPERATOR,
            gap_flag=FLAG_OPERATOR_GAP,
            harmful_sentence="Operator capacity is recorded as inadequate.",
            clear_sentence="Operator capacity is recorded as adequate.",
            gap_sentence="No user or verified value for operator_capacity_adequate.",
        ),
        _assess_polarity(
            assumptions,
            key=KEY_REGULATORY,
            criterion_id="regulatory_or_liability",
            methodology_ref=REF_REGULATORY,
            harmful_when=True,
            harmful_flag=FLAG_REGULATORY,
            gap_flag=FLAG_REGULATORY_GAP,
            harmful_sentence="An unresolved regulatory or liability issue is recorded.",
            clear_sentence="No unresolved regulatory or liability issue is recorded.",
            gap_sentence="No user or verified value for unresolved_regulatory_or_liability.",
        ),
        _assess_polarity(
            assumptions,
            key=KEY_EXTRACTION,
            criterion_id="stewardship_extraction",
            methodology_ref=REF_STEWARDSHIP,
            harmful_when=True,
            harmful_flag=FLAG_EXTRACTION,
            gap_flag=FLAG_STEWARDSHIP_GAP,
            harmful_sentence="Extraction without reinvestment capacity is recorded.",
            clear_sentence="Extraction without reinvestment capacity is recorded as false.",
            gap_sentence="No user or verified value for extraction_without_reinvestment.",
        ),
    )

    blocking = tuple(
        item.flag
        for item in criteria
        if item.status == "triggered" and item.flag is not None
    )
    gaps = tuple(
        item.flag
        for item in criteria
        if item.status == "gap" and item.flag is not None
    )
    notices: tuple[str, ...] = ()
    if measured and FLAG_NO_GROSS_MARGIN in flags:
        notices = (FLAG_NO_GROSS_MARGIN,)

    if blocking:
        draft = "do-not-proceed"
    elif gaps:
        draft = "conditional"
    else:
        draft = "go"

    unexpected = [flag for flag in blocking if flag not in RECOMMEND_AGAINST_FLAGS]
    if unexpected:
        raise ValueError(f"blocking flag outside the approved set: {unexpected}")

    return Recommendation(
        draft_recommendation=draft,
        is_final=False,
        requires_human_review=True,
        human_review_status="pending",
        blocking_flags=blocking,
        gap_flags=gaps,
        notices=notices,
        criteria=criteria,
        overall_feasibility_score=None,
        score_note=SCORE_NOTE,
        engine_flags=flags,
        method_assumptions=METHOD_ASSUMPTIONS,
        ai_interpretations_noted=ai_notes,
        next_actions=_next_actions(draft, blocking, gaps),
    )


# Methodology § Investor Readiness Gate — investor-ready only when human review
# is complete, release is approved, and human_review_approved is explicitly true;
# no recommend-against flag is active; base-case cash flow is non-negative;
# downside DSCR meets the engagement minimum (default 1.00x; lender-oriented
# 1.25x); demand evidence is verified or has a verification plan; regulatory or
# liability issues are resolved or disclosed with mitigations; and stewardship
# does not show extraction without reinvestment. Conditional flags block release
# unless their mitigations are accepted. A recommend-against flag stays blocking.
DEFAULT_DOWNSIDE_DSCR_MINIMUM = 1.00
LENDER_DOWNSIDE_DSCR_MINIMUM = 1.25
INVESTOR_STATUS_INTERNAL = "internal"
INVESTOR_STATUS_CONDITIONAL = "conditional"
INVESTOR_STATUS_READY = "investor-ready"


@dataclass(frozen=True)
class ReadinessCondition:
    name: str
    passed: bool
    detail: str


@dataclass(frozen=True)
class InvestorReadiness:
    status: str
    reasons: tuple[str, ...]
    dscr_minimum: float
    conditions: tuple[ReadinessCondition, ...] = ()
    human_review_approved: bool = False


def investor_readiness_gate(
    engine_flags: list[str] | tuple[str, ...] | None,
    financial_result: dict[str, Any] | None,
    *,
    blocking_flags: list[str] | tuple[str, ...] | None = None,
    conditional_flags: list[str] | tuple[str, ...] | None = None,
    accepted_mitigations: list[str] | tuple[str, ...] | None = None,
    human_review_complete: bool = False,
    release_approved: bool = False,
    human_review_approved: bool = False,
    demand_verified: bool = False,
    demand_verification_plan: bool = False,
    regulatory_resolved: bool = False,
    regulatory_disclosed_with_mitigations: bool = False,
    extraction_without_reinvestment: bool = False,
    lender_oriented: bool = False,
) -> InvestorReadiness:
    """Return internal, conditional, or investor-ready. Never a final recommendation."""
    engine = _flag_list("engine_flags", engine_flags)
    blocking = _flag_list("blocking_flags", blocking_flags)
    conditional = _flag_list("conditional_flags", conditional_flags)
    accepted = set(_flag_list("accepted_mitigations", accepted_mitigations))
    dscr_minimum = (
        LENDER_DOWNSIDE_DSCR_MINIMUM if lender_oriented else DEFAULT_DOWNSIDE_DSCR_MINIMUM
    )

    active: list[str] = []
    for flag in tuple(engine) + tuple(blocking):
        if flag in RECOMMEND_AGAINST_FLAGS and flag not in active:
            active.append(flag)
    if extraction_without_reinvestment and FLAG_EXTRACTION not in active:
        active.append(FLAG_EXTRACTION)

    reasons: list[str] = []
    if active:
        reasons.append("Recommend-against flags are active: " + ", ".join(active) + ".")
    human_passed = (
        human_review_complete and release_approved and human_review_approved is True
    )
    if not human_passed:
        reasons.append(
            "Investor-ready requires human review complete, release explicitly approved, "
            "and human_review_approved true."
        )
    open_conditional = [flag for flag in conditional if flag not in accepted]
    if open_conditional:
        reasons.append(
            "Conditional flags do not have accepted mitigations: "
            + ", ".join(open_conditional)
            + "."
        )
    base_cash_flow = _optional_number(financial_result, "base_monthly_cash_flow")
    cash_flow_passed = base_cash_flow is not None and base_cash_flow >= 0
    if not cash_flow_passed:
        reasons.append("Base-case cash flow is missing or negative.")
    downside_dscr = _optional_number(financial_result, "dscr_downside")
    dscr_passed = downside_dscr is not None and downside_dscr >= dscr_minimum
    if not dscr_passed:
        reasons.append(
            f"Downside DSCR is missing or below the engagement minimum of {dscr_minimum:.2f}x."
        )
    demand_passed = demand_verified or demand_verification_plan
    if not demand_passed:
        reasons.append("Demand evidence is not verified and has no verification plan.")
    regulatory_passed = regulatory_resolved or regulatory_disclosed_with_mitigations
    if not regulatory_passed:
        reasons.append(
            "Material regulatory or liability issues are not resolved or disclosed with mitigations."
        )
    conditional_passed = not open_conditional
    stewardship_passed = not extraction_without_reinvestment
    conditions = (
        ReadinessCondition(
            "Human review complete and release explicitly approved",
            human_passed,
            "Human review is complete, release is explicitly approved, and human_review_approved is true."
            if human_passed
            else (
                "Investor-ready requires human review complete, release explicitly approved, "
                "and human_review_approved true."
            ),
        ),
        ReadinessCondition(
            "No recommend-against flags are active",
            not active,
            "No recommend-against flags are active."
            if not active
            else "Active recommend-against flags: " + ", ".join(active) + ".",
        ),
        ReadinessCondition(
            "Conditional flags have accepted mitigations",
            conditional_passed,
            "No conditional flags are open without an accepted mitigation."
            if conditional_passed
            else "Open conditional flags: " + ", ".join(open_conditional) + ".",
        ),
        ReadinessCondition(
            "Base-case cash flow is non-negative",
            cash_flow_passed,
            _cash_flow_detail(base_cash_flow),
        ),
        ReadinessCondition(
            "Downside DSCR meets the engagement minimum",
            dscr_passed,
            _dscr_detail(downside_dscr, dscr_minimum),
        ),
        ReadinessCondition(
            "Demand evidence is verified or has a verification plan",
            demand_passed,
            _demand_detail(demand_verified, demand_verification_plan),
        ),
        ReadinessCondition(
            "Regulatory or liability issues are resolved or disclosed with mitigations",
            regulatory_passed,
            _regulatory_detail(regulatory_resolved, regulatory_disclosed_with_mitigations),
        ),
        ReadinessCondition(
            "Stewardship does not show extraction without reinvestment capacity",
            stewardship_passed,
            "Stewardship indicators do not show extraction without reinvestment capacity."
            if stewardship_passed
            else "Stewardship indicators show extraction without reinvestment capacity.",
        ),
    )

    if active:
        status = INVESTOR_STATUS_INTERNAL
    elif reasons:
        status = INVESTOR_STATUS_CONDITIONAL
    else:
        status = INVESTOR_STATUS_READY
    return InvestorReadiness(
        status=status,
        reasons=tuple(reasons),
        dscr_minimum=dscr_minimum,
        conditions=conditions,
        human_review_approved=human_review_approved is True,
    )


def _flag_list(name: str, flags: list[str] | tuple[str, ...] | None) -> tuple[str, ...]:
    if flags is None:
        return ()
    if not isinstance(flags, (list, tuple)) or not all(isinstance(flag, str) for flag in flags):
        raise ValueError(f"{name} must be a list of strings")
    return tuple(flags)


def _optional_number(financial_result: dict[str, Any] | None, key: str) -> float | None:
    if financial_result is None:
        return None
    if not isinstance(financial_result, dict):
        raise ValueError("financial_result must be an object")
    if key not in financial_result or financial_result[key] is None:
        return None
    value = financial_result[key]
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(f"financial_result.{key} must be a finite number or null")
    return float(value)


def _cash_flow_detail(base_cash_flow: float | None) -> str:
    if base_cash_flow is None:
        return "Base-case cash flow was not supplied as a measured engine result."
    return f"Base-case cash flow from the engine is {base_cash_flow:.2f}."


def _dscr_detail(downside_dscr: float | None, dscr_minimum: float) -> str:
    minimum = f"The engagement minimum is {dscr_minimum:.2f}x."
    if downside_dscr is None:
        return "Downside DSCR was not supplied by the deterministic engine. " + minimum
    return f"Downside DSCR supplied to the gate is {downside_dscr:.4f}. " + minimum


def _demand_detail(demand_verified: bool, demand_verification_plan: bool) -> str:
    if demand_verified:
        return "Demand evidence is verified."
    if demand_verification_plan:
        return "Demand evidence has a verification plan."
    return "Demand evidence is not verified and has no verification plan."


def _regulatory_detail(resolved: bool, disclosed: bool) -> str:
    if resolved:
        return "Material regulatory or liability issues are recorded as resolved."
    if disclosed:
        return "Material regulatory or liability issues are disclosed with mitigations."
    return (
        "Material regulatory or liability issues are not resolved or disclosed with mitigations."
    )


def assessment_investor_readiness(
    intake: dict[str, Any],
    recommendation: Recommendation,
    financial_result: dict[str, Any] | None,
    *,
    human_review: str = "pending",
) -> InvestorReadiness:
    """Map an assessment onto the Investor Readiness Gate. Methodology § Output Requirements."""
    assumptions = _load_assumptions(intake)
    measured = _inputs_measured(intake) if "financial_inputs" in intake else False
    gate_financial = None
    if financial_result is not None:
        if not isinstance(financial_result, dict):
            raise ValueError("financial_result must be an object")
        gate_financial = dict(financial_result)
        if not measured:
            gate_financial["base_monthly_cash_flow"] = None
    demand = _criterion_by_id(recommendation, "demand")
    regulatory = _criterion_by_id(recommendation, "regulatory_or_liability")
    stewardship = _criterion_by_id(recommendation, "stewardship_extraction")
    applied_engine_flags = tuple(
        flag for flag in recommendation.engine_flags if flag in recommendation.blocking_flags
    )
    review_approved = human_review == "approved"
    return investor_readiness_gate(
        applied_engine_flags,
        gate_financial,
        blocking_flags=recommendation.blocking_flags,
        conditional_flags=recommendation.gap_flags,
        human_review_complete=review_approved,
        release_approved=review_approved,
        human_review_approved=review_approved,
        demand_verified=demand.status == "clear",
        demand_verification_plan=_assumption_is_true(assumptions, "demand_verification_plan"),
        regulatory_resolved=regulatory.status == "clear",
        regulatory_disclosed_with_mitigations=_assumption_is_true(
            assumptions, "regulatory_disclosed_with_mitigations"
        ),
        extraction_without_reinvestment=stewardship.status == "triggered",
    )


def _criterion_by_id(recommendation: Recommendation, criterion_id: str) -> CriterionAssessment:
    for item in recommendation.criteria:
        if item.criterion_id == criterion_id:
            return item
    raise ValueError(f"recommendation is missing criterion {criterion_id}")


def _assumption_is_true(assumptions: list[dict[str, Any]], key: str) -> bool:
    return any(
        item["source"] in ACTIONABLE_SOURCES and item["value"] is True
        for item in _keyed(assumptions, key)
    )


def _readiness_conditions_text(readiness: InvestorReadiness) -> str:
    lines = []
    for item in readiness.conditions:
        state = "passed" if item.passed else "failed"
        lines.append(f"- **{item.name}:** {state}. {item.detail}")
    return "\n".join(lines)


def recommendation_to_dict(recommendation: Recommendation) -> dict[str, Any]:
    combined = sorted(
        set(recommendation.blocking_flags) | set(recommendation.gap_flags)
    )
    payload = asdict(recommendation)
    payload["criteria"] = [asdict(item) for item in recommendation.criteria]
    payload["flags"] = combined
    payload["recommendation"] = recommendation.draft_recommendation
    payload["overall_feasibility_score"] = None
    payload["methodology_version"] = METHODOLOGY_VERSION
    payload["model_version"] = MODEL_VERSION
    return payload


def report_context(
    intake: dict[str, Any],
    recommendation: Recommendation,
    financial_result: dict[str, Any] | None,
    *,
    as_of_date: str,
    extra_method_assumptions: tuple[str, ...] = (),
) -> dict[str, str]:
    """Deterministic Markdown fragments for the report template."""
    measured = _inputs_measured(intake) if "financial_inputs" in intake else False
    unmeasured = not measured
    assumptions = _load_assumptions(intake)
    method_lines = recommendation.method_assumptions + extra_method_assumptions
    readiness = assessment_investor_readiness(intake, recommendation, financial_result)
    return {
        "engagement_type": str(intake.get("engagement_type", "")),
        "business_name": str(intake.get("business_name", "")),
        "date": as_of_date,
        "executive_summary": _executive_summary(recommendation),
        "recommendation": recommendation.draft_recommendation,
        "review_status": "pending — draft only, not a final recommendation",
        "verified_data": _verified_block(intake),
        "assumptions_list": _assumptions_block(
            assumptions, recommendation, method_lines
        ),
        "risks": _risks_block(recommendation),
        "stewardship": _stewardship_block(recommendation, assumptions),
        "next_actions": "\n".join(
            f"- {action}" for action in recommendation.next_actions
        ),
        "base_monthly_contribution": _fmt_money(
            _maybe(financial_result, "base_monthly_contribution"), unmeasured
        ),
        "base_monthly_cash_flow": _fmt_money(
            _maybe(financial_result, "base_monthly_cash_flow"), unmeasured
        ),
        "downside_monthly_cash_flow": _fmt_money(
            _maybe(financial_result, "downside_monthly_cash_flow"), unmeasured
        ),
        "break_even_monthly_revenue": _fmt_money(
            _maybe(financial_result, "break_even_monthly_revenue"), unmeasured
        ),
        "months_to_recover_initial_capital": _fmt_months(
            _maybe(financial_result, "months_to_break_even_base"), unmeasured
        ),
        "engine_flags": (
            ", ".join(recommendation.engine_flags)
            if recommendation.engine_flags
            else "none"
        ),
        "overall_score": recommendation.score_note,
        "human_review_approved": "true" if readiness.human_review_approved else "false",
        "financial_notes": _financial_notes(measured),
        "reasonableness_check": reasonableness_note(financial_result),
        "investor_readiness_status": readiness.status,
        "investor_readiness_conditions": _readiness_conditions_text(readiness),
    }


def _engine_flags(
    financial_flags: list[str] | tuple[str, ...] | None,
    financial_result: dict[str, Any] | None,
) -> tuple[str, ...]:
    if financial_flags is None:
        financial_flags = []
    if not isinstance(financial_flags, (list, tuple)) or not all(
        isinstance(flag, str) for flag in financial_flags
    ):
        raise ValueError("financial_flags must be a list of strings")
    flags = tuple(financial_flags)
    unknown = [flag for flag in flags if flag not in KNOWN_ENGINE_FLAGS]
    if unknown:
        raise ValueError(f"unrecognized financial flags: {unknown}")
    if financial_result is not None:
        if not isinstance(financial_result, dict) or not isinstance(
            financial_result.get("flags"), list
        ):
            raise ValueError("financial_result.flags must be a list")
        if sorted(financial_result["flags"]) != sorted(flags):
            raise ValueError("financial_flags do not match financial_result.flags")
    return flags


def _load_assumptions(intake: dict[str, Any]) -> list[dict[str, Any]]:
    raw = intake.get("assumptions", [])
    if not isinstance(raw, list):
        raise ValueError("assumptions must be a list")
    cleaned: list[dict[str, Any]] = []
    for index, item in enumerate(raw):
        if not isinstance(item, dict):
            raise ValueError(f"assumptions[{index}] must be an object")
        for field in ("key", "value", "source", "rationale"):
            if field not in item:
                raise ValueError(f"assumptions[{index}] missing {field}")
        if not isinstance(item["key"], str) or not item["key"].strip():
            raise ValueError(f"assumptions[{index}].key must be a non-empty string")
        if item["source"] not in ("user", "verified", "ai_interpretation"):
            raise ValueError(f"assumptions[{index}].source is not allowed")
        if not isinstance(item["rationale"], str):
            raise ValueError(f"assumptions[{index}].rationale must be a string")
        cleaned.append(item)
    return cleaned


def _ai_lines(assumptions: list[dict[str, Any]]) -> list[str]:
    lines = []
    for item in assumptions:
        if item["source"] != "ai_interpretation":
            continue
        lines.append(
            f"{item['key']} = {item['value']!r}. {item['rationale']}"
        )
    return lines


def _inputs_measured(intake: dict[str, Any]) -> bool:
    if "financial_inputs" not in intake or intake["financial_inputs"] is None:
        return False
    financial = intake["financial_inputs"]
    if not isinstance(financial, dict):
        raise ValueError("financial_inputs must be an object")
    if "inputs_are_measured" not in financial:
        return True
    measured = financial["inputs_are_measured"]
    if not isinstance(measured, bool):
        raise ValueError("inputs_are_measured must be a boolean")
    return measured


def _trailing_revenue(intake: dict[str, Any]) -> float | None:
    if "verified_data" not in intake or intake["verified_data"] is None:
        return None
    verified = intake["verified_data"]
    if not isinstance(verified, dict):
        raise ValueError("verified_data must be an object")
    if "revenue_trailing_12m" not in verified or verified["revenue_trailing_12m"] is None:
        return None
    value = verified["revenue_trailing_12m"]
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("revenue_trailing_12m must be a finite number or null")
    if not math.isfinite(value) or value < 0:
        raise ValueError("revenue_trailing_12m must be a finite number >= 0 or null")
    return float(value)


def _keyed(assumptions: list[dict[str, Any]], key: str) -> list[dict[str, Any]]:
    target = key.lower()
    return [
        item
        for item in assumptions
        if str(item["key"]).strip().lower() == target
    ]


def _sources(items: list[dict[str, Any]]) -> str:
    names = sorted({str(item["source"]) for item in items})
    return ", ".join(names) if names else "none"


def _assess_demand(
    intake: dict[str, Any], assumptions: list[dict[str, Any]]
) -> CriterionAssessment:
    revenue = _trailing_revenue(intake)
    actionable = [
        item
        for item in _keyed(assumptions, KEY_DEMAND)
        if item["source"] in ACTIONABLE_SOURCES
    ]
    ai_ignored = any(
        item["source"] == "ai_interpretation"
        for item in _keyed(assumptions, KEY_DEMAND)
    )
    trues = [item for item in actionable if item["value"] is True]
    falses = [item for item in actionable if item["value"] is False]
    malformed = [
        item for item in actionable if item["value"] is not True and item["value"] is not False
    ]
    verified_true = any(item["source"] == "verified" for item in trues)
    user_true = any(item["source"] == "user" for item in trues)
    revenue_support = revenue is not None and revenue > 0
    verified_support = verified_true or revenue_support
    ignored = ""
    if ai_ignored:
        ignored = " An ai_interpretation for demand_evidence was recorded and ignored for this flag."
    if malformed:
        ignored += " Non-boolean user or verified values for demand_evidence were ignored."

    if falses and verified_support:
        evidence = (
            "Conflicting demand evidence: demand_evidence is false on a user or "
            "verified assumption while other verified support is present. The "
            "insufficient-demand flag stays on."
            + ignored
        )
        return _criterion(
            "demand", REF_DEMAND, "triggered", FLAG_DEMAND, evidence
        )
    if falses:
        evidence = (
            "demand_evidence is false "
            f"(sources: {_sources(falses)})."
            + ignored
        )
        return _criterion(
            "demand", REF_DEMAND, "triggered", FLAG_DEMAND, evidence
        )
    if verified_support:
        parts = []
        if revenue_support:
            parts.append(f"verified trailing revenue is {revenue:.2f}")
        if verified_true:
            parts.append("demand_evidence is true with source verified")
        evidence = "Verified demand support: " + "; ".join(parts) + "." + ignored
        return _criterion("demand", REF_DEMAND, "clear", None, evidence)
    if user_true:
        evidence = (
            "demand_evidence is true with source user only. That does not clear "
            "insufficient evidence, and it is not treated as verified."
            + ignored
        )
        return _criterion(
            "demand", REF_DEMAND, "gap", FLAG_DEMAND_UNVERIFIED, evidence
        )
    evidence = (
        "No verified trailing revenue above zero and no user or verified "
        "demand_evidence value of true."
        + ignored
    )
    return _criterion("demand", REF_DEMAND, "triggered", FLAG_DEMAND, evidence)


def _assess_cash(
    flags: tuple[str, ...],
    measured: bool,
    financial_result: dict[str, Any] | None,
) -> CriterionAssessment:
    figures = _cash_figures(financial_result)
    engine_listed = ", ".join(flags) if flags else "none"
    if not measured:
        evidence = (
            f"{REF_UNMEASURED} Engine flags on these inputs: {engine_listed}. "
            "Those flags were not applied as a recommend-against finding because "
            "the inputs are not a measured base case and downside case. "
            f"{figures}"
        )
        return _criterion(
            "cash_flow",
            REF_CASH,
            "gap",
            FLAG_FINANCIALS_UNMEASURED,
            evidence,
        )
    if FLAG_NEGATIVE_OR_MARGINAL_CASH_FLOW in flags:
        evidence = (
            "Both rounded monthly cash flows are zero or negative. " + figures
        )
        return _criterion(
            "cash_flow",
            REF_CASH,
            "triggered",
            FLAG_NEGATIVE_OR_MARGINAL_CASH_FLOW,
            evidence,
        )
    evidence = (
        "The measured base case and downside case did not both land at or "
        "below zero. " + figures
    )
    return _criterion("cash_flow", REF_CASH, "clear", None, evidence)


def _assess_polarity(
    assumptions: list[dict[str, Any]],
    *,
    key: str,
    criterion_id: str,
    methodology_ref: str,
    harmful_when: bool,
    harmful_flag: str,
    gap_flag: str,
    harmful_sentence: str,
    clear_sentence: str,
    gap_sentence: str,
) -> CriterionAssessment:
    keyed = _keyed(assumptions, key)
    actionable = [item for item in keyed if item["source"] in ACTIONABLE_SOURCES]
    ai_ignored = any(item["source"] == "ai_interpretation" for item in keyed)
    trues = [item for item in actionable if item["value"] is True]
    falses = [item for item in actionable if item["value"] is False]
    malformed = [
        item
        for item in actionable
        if item["value"] is not True and item["value"] is not False
    ]
    harmful_items = trues if harmful_when else falses
    clear_items = falses if harmful_when else trues
    ignored = ""
    if ai_ignored:
        ignored = (
            f" An ai_interpretation for {key} was recorded and ignored for this flag."
        )
    if malformed:
        ignored += f" Non-boolean user or verified values for {key} were ignored."

    if harmful_items and clear_items:
        evidence = (
            f"Conflicting user or verified values for {key} include both true and "
            f"false. The recommend-against flag stays on. {harmful_sentence}"
            + ignored
        )
        return _criterion(
            criterion_id, methodology_ref, "triggered", harmful_flag, evidence
        )
    if harmful_items:
        evidence = (
            f"{harmful_sentence} Sources: {_sources(harmful_items)}." + ignored
        )
        return _criterion(
            criterion_id, methodology_ref, "triggered", harmful_flag, evidence
        )
    if clear_items:
        evidence = f"{clear_sentence} Sources: {_sources(clear_items)}." + ignored
        return _criterion(criterion_id, methodology_ref, "clear", None, evidence)
    evidence = gap_sentence + ignored
    return _criterion(criterion_id, methodology_ref, "gap", gap_flag, evidence)


def _criterion(
    criterion_id: str,
    methodology_ref: str,
    status: str,
    flag: str | None,
    evidence: str,
) -> CriterionAssessment:
    return CriterionAssessment(
        criterion_id=criterion_id,
        methodology_ref=methodology_ref,
        status=status,
        flag=flag,
        evidence=evidence,
    )


def _cash_figures(financial_result: dict[str, Any] | None) -> str:
    if financial_result is None:
        return "No financial result payload was attached."
    base = financial_result.get("base_monthly_cash_flow")
    downside = financial_result.get("downside_monthly_cash_flow")
    return (
        f"Base monthly cash flow {base}. Downside monthly cash flow {downside}."
    )


def _next_actions(
    draft: str, blocking: tuple[str, ...], gaps: tuple[str, ...]
) -> tuple[str, ...]:
    actions = [HUMAN_REVIEW_ACTION]
    if draft == "do-not-proceed":
        actions.append(STOP_ACTION)
    elif draft == "conditional":
        actions.append(CONDITIONAL_ACTION)
    else:
        actions.append(GO_ACTION)
    for flag in blocking + gaps:
        actions.append(NEXT_ACTIONS[flag])
    return tuple(actions)


def _maybe(payload: dict[str, Any] | None, key: str) -> Any:
    if payload is None:
        return None
    return payload.get(key)


def _fmt_money(value: Any, unmeasured: bool) -> str:
    if value is None:
        text = "not defined"
    else:
        text = f"{float(value):.2f}"
    if unmeasured:
        text += " (arithmetic on unmeasured inputs; not a cash-flow finding)"
    return text


def _fmt_months(value: Any, unmeasured: bool) -> str:
    if value is None:
        text = "not defined — rounded base cash flow is not positive"
    else:
        text = f"{float(value):.1f}"
    if unmeasured:
        text += " (arithmetic on unmeasured inputs; not a finding)"
    return text


def _financial_notes(measured: bool) -> str:
    lines = [
        "Definitions from the deterministic engine (Methodology § Output Requirements):"
    ]
    for key, definition in FIELD_DEFINITIONS.items():
        lines.append(f"- {key}: {definition}")
    lines.append(
        "No currency unit is defined on the intake. Amounts stay in the unit of the inputs."
    )
    if measured:
        lines.append("Financial inputs were treated as measured.")
    else:
        lines.append(
            "inputs_are_measured is false, or financial inputs were absent. "
            "The figures are arithmetic on the supplied numbers. Scoring did not "
            "treat them as a measured base case or downside case."
        )
    return "\n".join(lines)


def _executive_summary(recommendation: Recommendation) -> str:
    blocking = (
        ", ".join(recommendation.blocking_flags)
        if recommendation.blocking_flags
        else "none"
    )
    gaps = (
        ", ".join(recommendation.gap_flags) if recommendation.gap_flags else "none"
    )
    return (
        f"Draft recommendation: {recommendation.draft_recommendation}. "
        f"Blocking flags: {blocking}. Gap flags: {gaps}. "
        "Review status: pending. This paragraph is assembled by scoring/rules.py "
        "from those flags. It is not a final recommendation and it is not a "
        "verified fact (Methodology § Core Principles; Methodology § Output Requirements)."
    )


def _verified_block(intake: dict[str, Any]) -> str:
    verified = intake.get("verified_data") or {}
    if not isinstance(verified, dict):
        raise ValueError("verified_data must be an object")
    lines = []
    known = ("revenue_trailing_12m", "current_cash", "headcount", "evidence_notes")
    for key in known:
        value = verified.get(key)
        shown = "not supplied" if value is None else value
        lines.append(f"- {key}: {shown}")
    for key in sorted(set(verified) - set(known)):
        lines.append(f"- {key}: {verified[key]}")
    lines.append(
        "Verified fields are copied from the intake. Missing fields were left empty."
    )
    return "\n".join(lines)


def _assumptions_block(
    assumptions: list[dict[str, Any]],
    recommendation: Recommendation,
    method_lines: tuple[str, ...],
) -> str:
    lines = [
        "#### Intake assumptions",
        "Each item keeps the source stored on the intake (Methodology § Core Principles — evidence hierarchy).",
    ]
    if not assumptions:
        lines.append("- None supplied.")
    for item in assumptions:
        lines.append(
            f"- `{item['key']}` = {item['value']!r} (source: {item['source']}). {item['rationale']}"
        )
    lines.append("#### Method assumptions used by this run")
    for line in method_lines:
        lines.append(f"- {line}")
    lines.append(
        "#### AI interpretations (listed, not used to raise or clear recommend-against flags)"
    )
    if recommendation.ai_interpretations_noted:
        for line in recommendation.ai_interpretations_noted:
            lines.append(f"- {line}")
    else:
        lines.append("- None on this intake.")
    return "\n".join(lines)


def _risks_block(recommendation: Recommendation) -> str:
    lines = [
        "Assembled from scoring flags by scoring/rules.py. This is not an independent qualitative risk essay."
    ]
    relevant = [
        item
        for item in recommendation.criteria
        if item.status in ("triggered", "gap") and item.flag is not None
    ]
    if not relevant and not recommendation.notices:
        lines.append(
            "- No automatic flag fired. Human review is still required before a final recommendation."
        )
    for item in relevant:
        mitigation = NEXT_ACTIONS[item.flag or ""]
        lines.append(
            f"- **{item.flag}** ({item.status}). {item.methodology_ref} {item.evidence} Mitigation: {mitigation}"
        )
    for notice in recommendation.notices:
        lines.append(f"- **{notice}** (engine notice). {REF_MARGIN}")
    return "\n".join(lines)


def _stewardship_block(
    recommendation: Recommendation, assumptions: list[dict[str, Any]]
) -> str:
    criterion = next(
        item
        for item in recommendation.criteria
        if item.criterion_id == "stewardship_extraction"
    )
    lines = [
        criterion.methodology_ref,
        f"Status: {criterion.status}.",
        criterion.evidence,
        (
            "Methodology § Core Principles sets a stewardship orientation for every "
            "assessment: long-term enterprise strength over short-term extraction. "
            "That principle is the standard being applied. It is not evidence that "
            "this venture reinvests."
        ),
    ]
    related = [
        item
        for item in assumptions
        if "steward" in item["key"].lower() or item["key"].strip().lower() == KEY_EXTRACTION
    ]
    if related:
        lines.append("Intake items that name stewardship or the extraction flag:")
        for item in related:
            lines.append(
                f"- `{item['key']}` = {item['value']!r} (source: {item['source']}). {item['rationale']}"
            )
    else:
        lines.append(
            "The intake has no additional stewardship narrative beyond the extraction criterion above."
        )
    return "\n\n".join(lines)

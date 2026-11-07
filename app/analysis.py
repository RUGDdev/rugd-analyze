"""Adapter from saved profiles to the 0.1 engine. Approval stays false."""

from __future__ import annotations

import math
from typing import Any

from engine.financial import FinancialInputs, result_to_dict, run_financials
from engine.startup_projection import format_projection, record_for_intake
from run_assessment import TEMPLATE_PATH, render_template, validate_intake
from scoring.rules import (
    MODEL_VERSION,
    assessment_investor_readiness,
    build_recommendation,
    report_context,
)

ENGINE_PURPOSES = {
    "startup_feasibility": "Startup feasibility",
    "expansion_feasibility": "Business expansion",
    "operational_diagnostic": "Existing business evaluation",
}
UNSUPPORTED_PURPOSES = {
    "acquisition": "Business acquisition",
    "investor_commissioned": "Investor-commissioned evaluation",
}

_MONTHLY_FIELDS = (
    "initial_capital",
    "monthly_fixed_costs",
    "gross_margin_pct",
    "projected_monthly_revenue_base",
)
_WORKSHEET_FIELDS = (
    "construction_cost",
    "seats",
    "average_ticket",
    "weekday_occupancy",
    "weekend_occupancy",
    "operating_days",
    "contribution_margin",
)
_YES_NO = {
    "demand_evidence": "demand_evidence",
    "operator_capacity_adequate": "operator_capacity_adequate",
    "unresolved_regulatory_or_liability": "unresolved_regulatory_or_liability",
    "extraction_without_reinvestment": "extraction_without_reinvestment",
}


def analyze_record(record: dict[str, Any]) -> dict[str, Any]:
    """Run the engine for a stored assessment. human_review_approved stays false."""
    if record.get("intake") and record.get("read_only"):
        stored = record["intake"].get("as_of_date") or _as_of(record)
        return analyze_intake(record["intake"], as_of_date=str(stored))
    profile = dict(record["profile"])
    if record.get("hypothetical"):
        profile["hypothetical"] = True
    purpose = str(profile.get("purpose") or record["purpose"])
    if purpose in UNSUPPORTED_PURPOSES:
        return {
            "ok": True,
            "engine_ran": False,
            "purpose_supported": False,
            "message": (
                f"{UNSUPPORTED_PURPOSES[purpose]} is saved on this assessment. "
                "The 0.1 scoring enum does not include that purpose, so Analyze "
                "did not produce a recommendation for it."
            ),
            "recommendation": None,
            "human_review_approved": False,
            "is_final": False,
            "readiness_status": None,
            "blocking_flags": [],
            "gap_flags": [],
            "missing": [],
            "financial": None,
            "projection_text": "",
            "report_markdown": "",
            "audit": None,
            "model_version": MODEL_VERSION,
        }
    intake, missing = profile_to_intake(profile, as_of_date=_as_of(record))
    result = analyze_intake(intake, as_of_date=_as_of(record))
    result["missing"] = missing + result.get("missing", [])
    result["intake"] = intake
    return result


def analyze_intake(
    intake: dict[str, Any],
    *,
    as_of_date: str,
    human_review: str = "pending",
    approval: dict[str, Any] | None = None,
) -> dict[str, Any]:
    errors = validate_intake(intake)
    if errors:
        return {
            "ok": False,
            "engine_ran": False,
            "errors": errors,
            "human_review_approved": False,
            "is_final": False,
        }
    financial = _monthly(intake)
    flags = list(financial["flags"]) if financial else []
    recommendation = build_recommendation(intake, flags, financial)
    review_state = "approved" if human_review == "approved" and approval else "pending"
    readiness = assessment_investor_readiness(
        intake, recommendation, financial, human_review=review_state
    )
    approved = review_state == "approved"
    startup = record_for_intake(intake, human_review_approved=False)
    startup["human_review_approved"] = False
    startup["is_final"] = False
    startup["investor_ready"] = False
    context = report_context(
        intake, recommendation, financial, as_of_date=as_of_date
    )
    if approved:
        context["human_review_approved"] = "true"
        context["investor_readiness_status"] = readiness.status
        context["investor_readiness_conditions"] = _conditions_text(readiness)
    else:
        context["human_review_approved"] = "false"
    context["startup_capital"] = format_projection(startup)
    report = render_template(TEMPLATE_PATH.read_text(encoding="utf-8"), context)
    missing = []
    if financial is None:
        missing.append(
            "Insufficient verified information to calculate monthly contribution, cash flow, and break-even."
        )
    if not startup.get("calculated"):
        missing.append(
            "Insufficient information to calculate the startup cost build. Construction cost, seats, average ticket, occupancy, operating days, and contribution margin are required."
        )
    demand = _demand_record(recommendation, intake)
    view_summary = build_view_summary(
        {
            "recommendation": recommendation.draft_recommendation,
            "blocking_flags": list(recommendation.blocking_flags),
            "readiness_status": readiness.status,
            "human_review_status": "approved" if approved else "pending",
            "human_review_approved": approved,
            "is_final": False,
            "demand": demand,
        }
    )
    report = report.rstrip() + "\n\n" + _demand_report(view_summary, demand)
    audit = {
        "model_version": MODEL_VERSION,
        "human_review_approved": approved,
        "is_final": False,
        "approvals": [approval] if approval else [],
        "investor_summary_written": False,
        "investor_readiness": {
            "status": readiness.status,
            "human_review_approved": approved,
            "investor_ready": readiness.status == "investor-ready",
        },
        "recommendation": {
            "draft_recommendation": recommendation.draft_recommendation,
            "blocking_flags": list(recommendation.blocking_flags),
            "gap_flags": list(recommendation.gap_flags),
            "overall_feasibility_score": None,
        },
        "demand_evidence": demand,
        "view_summary": view_summary,
        "financial_result": financial,
        "startup_capital": startup,
    }
    return {
        "ok": True,
        "engine_ran": True,
        "purpose_supported": True,
        "recommendation": recommendation.draft_recommendation,
        "score_line": "Not calculated — methodology pending approval.",
        "human_review_status": "approved" if approved else "pending",
        "human_review_approved": approved,
        "is_final": False,
        "readiness_status": readiness.status,
        "blocking_flags": list(recommendation.blocking_flags),
        "gap_flags": list(recommendation.gap_flags),
        "demand": demand,
        "view_summary": view_summary,
        "missing": missing,
        "financial": financial,
        "projection": startup if startup.get("calculated") else None,
        "projection_text": format_projection(startup),
        "report_markdown": report,
        "audit": audit,
        "model_version": MODEL_VERSION,
        "intake": intake,
    }


def profile_to_intake(profile: dict[str, Any], *, as_of_date: str) -> tuple[dict[str, Any], list[str]]:
    purpose = str(profile.get("purpose") or "startup_feasibility")
    if purpose not in ENGINE_PURPOSES:
        purpose = "startup_feasibility"
    assumptions: list[dict[str, Any]] = []
    missing: list[str] = []
    for field, key in _YES_NO.items():
        raw = str(profile.get(field) or "").strip().lower()
        if raw in ("yes", "true"):
            assumptions.append(_user_assumption(key, True, "Entered by the customer. Not verified."))
        elif raw in ("no", "false"):
            assumptions.append(_user_assumption(key, False, "Entered by the customer. Not verified."))
        else:
            missing.append(f"{key} was not answered.")
    verified_revenue, verified_notes = _apply_verified_demand(profile, assumptions, missing)
    notes = str(profile.get("evidence_notes") or "").strip()
    if notes:
        assumptions.append(_user_assumption("evidence_notes", notes, "Customer note. Not verified data."))
    if profile.get("hypothetical"):
        assumptions.append(
            _user_assumption(
                "hypothetical_demonstration",
                True,
                "This assessment is a labeled hypothetical demonstration.",
            )
        )
    intake: dict[str, Any] = {
        "engagement_type": purpose,
        "business_name": str(profile.get("business_name") or "Untitled"),
        "description": str(profile.get("concept") or ""),
        "as_of_date": as_of_date[:10],
        "verified_data": {
            "revenue_trailing_12m": verified_revenue,
            "current_cash": None,
            "headcount": None,
            "evidence_notes": verified_notes,
        },
        "assumptions": assumptions,
    }
    monthly = {key: _optional_number(profile.get(key)) for key in _MONTHLY_FIELDS}
    if all(value is not None for value in monthly.values()):
        measured = profile.get("inputs_are_measured") is True
        intake["financial_inputs"] = {
            **monthly,
            "downside_revenue_multiplier": _optional_number(profile.get("downside_multiplier")) or 0.6,
            "inputs_are_measured": measured,
        }
    else:
        missing.append(
            "Monthly capital, fixed costs, gross margin, and base revenue were not all supplied."
        )
    worksheet_numbers = {key: _optional_number(profile.get(key)) for key in _WORKSHEET_FIELDS}
    if all(value is not None for value in worksheet_numbers.values()):
        worksheet: dict[str, Any] = dict(worksheet_numbers)
        for key in (
            "equipment",
            "soft_costs",
            "preopening_working_capital",
            "contingency_pct",
            "debt_share",
            "annual_interest_rate",
            "amortization_years",
            "annual_fixed_costs",
            "downside_multiplier",
        ):
            number = _optional_number(profile.get(key))
            if number is not None:
                worksheet[key] = number
        worksheet["verified"] = {key: False for key in worksheet if key != "verified"}
        intake["startup_capital"] = worksheet
    return intake, missing


def _user_assumption(key: str, value: Any, rationale: str) -> dict[str, Any]:
    return {"key": key, "value": value, "source": "user", "rationale": rationale}


def _apply_verified_demand(
    profile: dict[str, Any],
    assumptions: list[dict[str, Any]],
    missing: list[str],
) -> tuple[float | None, str]:
    """Record verified demand inputs only when the controlled source is exactly verified."""
    customer_note = (
        "Customer entries are user-supplied assumptions. Nothing on this form was marked verified."
    )
    attempted = any(
        str(profile.get(key) or "").strip()
        for key in (
            "verified_record_source",
            "verified_revenue_trailing_12m",
            "verified_demand_evidence",
            "verified_demand_rationale",
        )
    )
    if not attempted:
        return None, customer_note
    if _is_true(profile.get("hypothetical")):
        missing.append(
            "Verified demand records are not applied on a hypothetical demonstration."
        )
        return None, customer_note
    if str(profile.get("verified_record_source") or "").strip() != "verified":
        missing.append(
            "Verified demand fields were not applied because verified_record_source is not verified."
        )
        return None, customer_note
    rationale = str(profile.get("verified_demand_rationale") or "").strip()
    if not rationale:
        missing.append(
            "Verified demand fields were not applied because a rationale is required."
        )
        return None, customer_note
    revenue = _verified_revenue(profile.get("verified_revenue_trailing_12m"))
    claim = str(profile.get("verified_demand_evidence") or "").strip().lower()
    applied = False
    if revenue == "invalid":
        missing.append(
            "Verified trailing revenue was not applied because it is not a finite number >= 0."
        )
        revenue_value = None
    else:
        revenue_value = revenue
        applied = revenue_value is not None
    if claim in ("true", "false"):
        assumptions.append(
            {
                "key": "demand_evidence",
                "value": claim == "true",
                "source": "verified",
                "rationale": rationale,
            }
        )
        applied = True
    elif claim:
        missing.append(
            "Verified demand_evidence was ignored because it is not boolean true or false."
        )
    if not applied:
        missing.append(
            "No verified trailing revenue or verified demand_evidence value was supplied."
        )
        return None, customer_note
    return revenue_value, f"Verified demand record, source verified. {rationale}"


def _verified_revenue(value: Any) -> float | None | str:
    if value is None or isinstance(value, bool):
        return "invalid" if isinstance(value, bool) else None
    text = str(value).strip()
    if not text:
        return None
    try:
        number = float(text)
    except ValueError:
        return "invalid"
    if not math.isfinite(number) or number < 0:
        return "invalid"
    return number


def _is_true(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value or "").strip().lower() in ("true", "1", "yes")


def _demand_record(recommendation: Any, intake: dict[str, Any]) -> dict[str, Any]:
    demand = next(
        item for item in recommendation.criteria if item.criterion_id == "demand"
    )
    if demand.flag == "INSUFFICIENT_DEMAND_EVIDENCE":
        status = "uncleared"
    elif demand.flag == "DEMAND_EVIDENCE_UNVERIFIED":
        status = "unverified"
    elif demand.status == "clear":
        status = "cleared"
    else:
        status = "uncleared"
    verified = intake.get("verified_data") or {}
    verified_claims = [
        item["value"]
        for item in intake.get("assumptions") or []
        if str(item.get("key", "")).strip().lower() == "demand_evidence"
        and item.get("source") == "verified"
        and isinstance(item.get("value"), bool)
    ]
    provenance = _demand_provenance(intake)
    return {
        "status": status,
        "criterion_status": demand.status,
        "flag": demand.flag,
        "evidence": demand.evidence,
        "revenue_trailing_12m": verified.get("revenue_trailing_12m"),
        "verified_demand_evidence": verified_claims,
        "provenance": provenance,
        "human_review_approved": False,
        "investor_ready": False,
    }


def _demand_provenance(intake: dict[str, Any]) -> list[dict[str, Any]]:
    verified = intake.get("verified_data") or {}
    revenue = verified.get("revenue_trailing_12m")
    rows = [
        {
            "field": "revenue_trailing_12m",
            "provenance": "placeholder" if revenue is None else "verified",
            "source": None if revenue is None else "verified",
            "value": revenue,
        }
    ]
    claims = [
        item
        for item in intake.get("assumptions") or []
        if str(item.get("key", "")).strip().lower() == "demand_evidence"
    ]
    if not claims:
        rows.append(
            {
                "field": "demand_evidence",
                "provenance": "placeholder",
                "source": None,
                "value": None,
            }
        )
        return rows
    for item in claims:
        source = str(item.get("source") or "")
        if source == "verified":
            provenance = "verified"
        elif source == "user":
            provenance = "user"
        else:
            provenance = "placeholder"
        rows.append(
            {
                "field": "demand_evidence",
                "provenance": provenance,
                "source": source or None,
                "value": item.get("value"),
            }
        )
    return rows


def build_view_summary(result: dict[str, Any]) -> dict[str, Any]:
    """Headlines for the results page, report, and audit. Approval stays pending here."""
    approved = (
        result.get("human_review_approved") is True
        and result.get("human_review_status") == "approved"
    )
    blocking = result.get("blocking_flags") or []
    demand = result.get("demand") or {}
    return {
        "recommendation": result.get("recommendation"),
        "insufficient_demand_evidence": (
            "present" if "INSUFFICIENT_DEMAND_EVIDENCE" in blocking else "not present"
        ),
        "demand_status": demand.get("status") or "uncleared",
        "investor_readiness": result.get("readiness_status"),
        "human_review_status": "approved" if approved else "pending",
        "human_review_approved": bool(approved),
        "is_final": result.get("is_final") is True,
        "demand_provenance": list(demand.get("provenance") or []),
    }


def _demand_report(summary: dict[str, Any], demand: dict[str, Any]) -> str:
    provenance = "\n".join(
        f"- {row['field']}: {row['provenance']}"
        + (f" (source: {row['source']})" if row.get("source") else "")
        for row in summary.get("demand_provenance") or []
    )
    approved = "true" if summary.get("human_review_approved") else "false"
    return (
        "## Demand evidence status\n\n"
        f"**Status:** {demand['status']}\n\n"
        f"{demand['evidence']}\n\n"
        "## Assessment view\n\n"
        f"**Recommendation:** {summary.get('recommendation')}\n\n"
        f"**INSUFFICIENT_DEMAND_EVIDENCE:** {summary.get('insufficient_demand_evidence')}\n\n"
        f"**Demand evidence status:** {summary.get('demand_status')}\n\n"
        f"**Investor readiness:** {summary.get('investor_readiness')}\n\n"
        f"**Human review status:** {summary.get('human_review_status')}\n\n"
        f"**human_review_approved:** {approved}\n\n"
        "**Demand evidence provenance:**\n\n"
        f"{provenance}\n\n"
        "This status comes from the 0.1 demand rule. "
        + (
            "human_review_approved is true. Approval does not clear recommend-against flags and does not by itself mark the assessment investor-ready.\n"
            if summary.get("human_review_approved")
            else "human_review_approved remains false. This report does not mark the assessment investor-ready.\n"
        )
    )


def _conditions_text(readiness: Any) -> str:
    lines = []
    for item in readiness.conditions:
        state = "passed" if item.passed else "failed"
        lines.append(f"- **{item.name}:** {state}. {item.detail}")
    return "\n".join(lines)


def _optional_number(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip()
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def _monthly(intake: dict[str, Any]) -> dict[str, Any] | None:
    financial = intake.get("financial_inputs")
    if not isinstance(financial, dict):
        return None
    if any(key not in financial for key in _MONTHLY_FIELDS):
        return None
    result = run_financials(
        FinancialInputs(
            initial_capital=financial["initial_capital"],
            monthly_fixed_costs=financial["monthly_fixed_costs"],
            gross_margin_pct=financial["gross_margin_pct"],
            projected_monthly_revenue_base=financial["projected_monthly_revenue_base"],
            downside_revenue_multiplier=financial.get("downside_revenue_multiplier", 0.6),
        )
    )
    return result_to_dict(result)


def _as_of(record: dict[str, Any]) -> str:
    created = str(record.get("created_at") or "2026-11-07")
    return created[:10]

"""Adapter from saved profiles to the 0.1 engine. Approval stays false."""

from __future__ import annotations

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
    purpose = str(record["profile"].get("purpose") or record["purpose"])
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
    intake, missing = profile_to_intake(record["profile"], as_of_date=_as_of(record))
    result = analyze_intake(intake, as_of_date=_as_of(record))
    result["missing"] = missing + result.get("missing", [])
    result["intake"] = intake
    return result


def analyze_intake(intake: dict[str, Any], *, as_of_date: str) -> dict[str, Any]:
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
    readiness = assessment_investor_readiness(
        intake, recommendation, financial, human_review="pending"
    )
    startup = record_for_intake(intake, human_review_approved=False)
    startup["human_review_approved"] = False
    startup["is_final"] = False
    startup["investor_ready"] = False
    context = report_context(
        intake, recommendation, financial, as_of_date=as_of_date
    )
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
    audit = {
        "model_version": MODEL_VERSION,
        "human_review_approved": False,
        "is_final": False,
        "investor_readiness": {
            "status": readiness.status,
            "human_review_approved": False,
        },
        "recommendation": {
            "draft_recommendation": recommendation.draft_recommendation,
            "blocking_flags": list(recommendation.blocking_flags),
            "gap_flags": list(recommendation.gap_flags),
            "overall_feasibility_score": None,
        },
        "financial_result": financial,
        "startup_capital": startup,
    }
    return {
        "ok": True,
        "engine_ran": True,
        "purpose_supported": True,
        "recommendation": recommendation.draft_recommendation,
        "score_line": "Not calculated — methodology pending approval.",
        "human_review_status": "pending",
        "human_review_approved": False,
        "is_final": False,
        "readiness_status": readiness.status,
        "blocking_flags": list(recommendation.blocking_flags),
        "gap_flags": list(recommendation.gap_flags),
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
            "revenue_trailing_12m": None,
            "current_cash": None,
            "headcount": None,
            "evidence_notes": "Customer entries are user-supplied assumptions. Nothing on this form was marked verified.",
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

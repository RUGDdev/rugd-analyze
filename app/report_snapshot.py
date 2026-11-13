"""Build a report from values already stored on an assessment.

This module does not call the engine and does not fill a missing figure.
"""

from __future__ import annotations

from typing import Any

from app.charts import render_engine_charts, render_financial_graphics, render_scenario_chart
from app import display
from app.inputs import MONTHLY_FIELDS, field_state
from app.scenarios import METRIC_KEYS, METRIC_LABELS

MISSING = "Missing. This blank is not stored as zero."
NOT_RUN = "Not calculated. Analyze has not been run."
NOT_STORED = "Not available. This value is not stored."

_PROFILE_LINES = (
    ("business_name", "Business name"),
    ("concept", "Concept"),
    ("industry", "Industry"),
    ("market", "Market"),
    ("customers", "Customers"),
    ("revenue_model", "Revenue model"),
    ("stage", "Stage"),
)

_ASSUMPTION_LABELS = {
    "initial_capital": "Initial capital",
    "monthly_fixed_costs": "Monthly fixed costs",
    "gross_margin_pct": "Gross margin",
    "projected_monthly_revenue_base": "Projected monthly base revenue",
    "downside_multiplier": "Downside multiplier",
}

_ENGINE_KEYS = (
    "base_monthly_contribution",
    "base_monthly_cash_flow",
    "downside_monthly_revenue",
    "downside_monthly_contribution",
    "downside_monthly_cash_flow",
    "break_even_monthly_revenue",
    "months_to_break_even_base",
)

_LIMITATIONS = (
    "Customer-entered values are user-supplied assumptions.",
    "This report copies stored figures. It does not calculate a new result.",
    "No feasibility score is calculated.",
    "This report does not set human_review_approved and it does not change investor readiness.",
    "Completing an action does not verify evidence or change the stored recommendation.",
    "Local prototype. Not production security. This screen does not grant investor-ready status.",
)


def build_report_snapshot(record: dict[str, Any]) -> dict[str, Any]:
    """Copy the saved assessment into a snapshot. Later edits to the draft do not change it."""
    profile = record.get("profile") if isinstance(record.get("profile"), dict) else {}
    result = record.get("result") if isinstance(record.get("result"), dict) else None
    financial = result.get("financial") if result and isinstance(result.get("financial"), dict) else None
    engine_ran = bool(result and result.get("engine_ran") and financial)
    return {
        "assessment_id": str(record.get("id") or ""),
        "source_updated_at": str(record.get("updated_at") or ""),
        "business_name": _text(profile.get("business_name") or record.get("business_name")),
        "business_overview": _profile_lines(profile, record),
        "objective": _objective(profile),
        "market_and_customers": _market_lines(profile),
        "assumptions": _assumptions(profile),
        "base_results": _base_results(financial, engine_ran),
        "downside_scenario": _downside(record),
        "evidence_gaps": _named_list(result, "gap_flags", engine_ran),
        "risk_indicators": _risks(result, financial, engine_ran),
        "recommendation": _recommendation(record, result, engine_ran),
        "limitations": list(_LIMITATIONS),
        "chart_html": (
            render_engine_charts(financial, live=False)
            if engine_ran
            else "<p>No chart is drawn. Analyze has not stored a monthly result.</p>"
        ),
        "scenario_chart_html": render_scenario_chart(record.get("scenarios")),
        "graphics": render_financial_graphics(
            financial if engine_ran else None,
            assumed_revenue=_stored_number(profile, "projected_monthly_revenue_base"),
            assumed_fixed_costs=_stored_number(profile, "monthly_fixed_costs"),
            projection=(
                result.get("projection")
                if result and isinstance(result.get("projection"), dict) and result["projection"].get("calculated")
                else None
            ),
            preview=False,
        ),
    }


def snapshot_markdown(snapshot: dict[str, Any]) -> str:
    """Plain export of one saved snapshot. Figures are copied, not recalculated."""
    lines = [
        f"# {snapshot.get('business_name') or 'Assessment'} report",
        "",
        "Saved report snapshot. This file does not change the assessment.",
        "",
    ]
    sections = (
        ("Business overview", snapshot.get("business_overview")),
        ("Customer objective", snapshot.get("objective")),
        ("Market and customers", snapshot.get("market_and_customers")),
        ("Financial assumptions", snapshot.get("assumptions")),
        ("Base financial results", snapshot.get("base_results")),
        ("Downside scenario", snapshot.get("downside_scenario")),
        ("Evidence gaps", snapshot.get("evidence_gaps")),
        ("Risk indicators", snapshot.get("risk_indicators")),
        ("Recommendation", snapshot.get("recommendation")),
        ("Limitations", snapshot.get("limitations")),
    )
    for title, items in sections:
        lines.append(f"## {title}")
        lines.append("")
        for item in items or [NOT_STORED]:
            lines.append(f"- {item}")
        lines.append("")
    lines.append("Charts in the application copy the same stored engine values.")
    lines.append("")
    return "\n".join(lines)


def _profile_lines(profile: dict[str, Any], record: dict[str, Any]) -> list[str]:
    lines = []
    for key, label in _PROFILE_LINES:
        if key == "business_name":
            value = profile.get(key) or record.get(key)
        else:
            value = profile.get(key)
        lines.append(f"{label}: {_present(value)}")
    purpose = profile.get("purpose") or record.get("purpose")
    lines.append(f"Purpose: {_present(purpose)}")
    return lines


def _objective(profile: dict[str, Any]) -> list[str]:
    from app.objectives import objective_label

    stored = str(profile.get("customer_objective") or "").strip()
    if not stored:
        return [NOT_STORED]
    return [f"Saved objective: {objective_label(stored)}"]


def _market_lines(profile: dict[str, Any]) -> list[str]:
    lines = []
    for key, label in (
        ("industry", "Industry"),
        ("market", "Market"),
        ("geographic_market", "Geographic market"),
        ("customers", "Customers"),
        ("target_customers", "Target customers"),
    ):
        lines.append(f"{label}: {_present(profile.get(key))}")
    return lines


def _assumptions(profile: dict[str, Any]) -> list[str]:
    lines = []
    fields = list(MONTHLY_FIELDS) + ["downside_multiplier"]
    for key in fields:
        label = _ASSUMPTION_LABELS[key]
        state = field_state(profile.get(key))
        if state == "missing":
            lines.append(f"{label}: {MISSING}")
        elif state == "zero":
            lines.append(f"{label}: 0. Entered as zero.")
        elif state == "invalid":
            lines.append(f"{label}: Not available. This entry is not a finite number.")
        else:
            lines.append(f"{label}: {display.figure(key, profile.get(key), missing=_present(profile.get(key)))}. Customer-supplied assumption.")
    return lines


def _base_results(financial: dict[str, Any] | None, engine_ran: bool) -> list[str]:
    if not engine_ran or financial is None:
        return [NOT_RUN]
    lines = ["Stored engine result. These figures were not recalculated for this report."]
    for key in _ENGINE_KEYS:
        number = _finite(financial.get(key))
        if number is None:
            lines.append(f"{key}: not calculated.")
        else:
            lines.append(f"{key}: {display.figure(key, number)}. Calculated by the engine.")
    flags = financial.get("flags") if isinstance(financial.get("flags"), list) else []
    if flags:
        lines.append("Engine flags: " + ", ".join(str(flag) for flag in flags) + ".")
    else:
        lines.append("Engine flags: none stored on the financial result.")
    return lines


def _downside(record: dict[str, Any]) -> list[str]:
    scenarios = record.get("scenarios") if isinstance(record.get("scenarios"), dict) else {}
    alternative = scenarios.get("alternative") if isinstance(scenarios.get("alternative"), dict) else None
    if alternative is None or alternative.get("kind") != "downside":
        return ["No Downside scenario is saved."]
    metrics = alternative.get("metrics") if isinstance(alternative.get("metrics"), dict) else {}
    lines = [
        "Saved Downside scenario. This extra engine run does not replace the official result.",
        str(alternative.get("note") or "Saved from an engine run."),
    ]
    for key in METRIC_KEYS:
        label = METRIC_LABELS.get(key, key)
        number = _finite(metrics.get(key))
        if number is None:
            lines.append(f"{label}: not calculated.")
        else:
            lines.append(f"{label}: {display.figure(key, number)}. Calculated by the engine.")
    return lines


def _named_list(result: dict[str, Any] | None, key: str, engine_ran: bool) -> list[str]:
    if result is None or not engine_ran:
        return [NOT_RUN]
    flags = result.get(key) if isinstance(result.get(key), list) else []
    if not flags:
        return ["None stored."]
    return [str(flag) for flag in flags]


def _risks(
    result: dict[str, Any] | None,
    financial: dict[str, Any] | None,
    engine_ran: bool,
) -> list[str]:
    if result is None or not engine_ran:
        return [NOT_RUN]
    lines = _named_list(result, "blocking_flags", True)
    extra = financial.get("flags") if isinstance(financial, dict) and isinstance(financial.get("flags"), list) else []
    for flag in extra:
        text = str(flag)
        if text not in lines:
            lines.append(text)
    return lines


def _recommendation(
    record: dict[str, Any],
    result: dict[str, Any] | None,
    engine_ran: bool,
) -> list[str]:
    if result is None or not result.get("engine_ran"):
        return [NOT_RUN]
    recommendation = result.get("recommendation")
    if recommendation is None:
        shown = "No recommendation is stored."
    else:
        shown = str(recommendation)
    approved = bool(record.get("human_review_approved"))
    return [
        f"Stored recommendation: {shown}",
        f"Investor readiness: {_present(result.get('readiness_status'))}",
        f"Human review: {_present(result.get('human_review_status'))}",
        f"human_review_approved: {'true' if approved else 'false'}",
        str(result.get("score_line") or "Not calculated — methodology pending approval."),
        "This snapshot does not change the stored recommendation.",
    ]


def _present(value: Any) -> str:
    if value is None:
        return NOT_STORED
    text = str(value).strip()
    if not text:
        return NOT_STORED
    return text


def _stored_number(profile: dict[str, Any], key: str) -> float | None:
    if field_state(profile.get(key)) not in {"entered", "zero"}:
        return None
    raw = profile.get(key)
    if isinstance(raw, bool):
        return None
    if isinstance(raw, (int, float)):
        return float(raw)
    return float(str(raw).strip())


def _text(value: Any) -> str:
    text = str(value or "").strip()
    return text or "Assessment"


def _finite(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    number = float(value)
    if number != number or number in {float("inf"), float("-inf")}:
        return None
    return number

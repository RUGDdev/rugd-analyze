"""Financial preview. Calls the existing engines and does not save or recommend."""

from __future__ import annotations

from html import escape
from typing import Any

from app.analysis import _WORKSHEET_FIELDS, profile_to_intake
from app.charts import render_financial_graphics, render_value_chart
from app.inputs import MONTHLY_FIELDS, field_state, monthly_problems
from engine.financial import FinancialInputs, result_to_dict, run_financials
from engine.startup_projection import record_for_intake

PREVIEW_NOTICE = (
    "Preview. These figures were calculated for this request and were not saved. "
    "They do not change the assessment, an evidence flag, human review, investor readiness, "
    "or the official recommendation. Run Analyze to store an official result."
)

_OPTIONAL_STARTUP = (
    ("equipment", "Equipment"),
    ("soft_costs", "Soft costs"),
    ("preopening_working_capital", "Pre-opening working capital"),
    ("contingency_pct", "Contingency percentage"),
    ("debt_share", "Debt share"),
    ("annual_interest_rate", "Annual interest rate"),
    ("amortization_years", "Amortization years"),
    ("annual_fixed_costs", "Annual fixed costs"),
)
_STARTUP_LABELS = {
    "construction_cost": "Construction cost",
    "seats": "Seats",
    "average_ticket": "Average ticket",
    "weekday_occupancy": "Weekday occupancy",
    "weekend_occupancy": "Weekend occupancy",
    "operating_days": "Operating days",
    "contribution_margin": "Contribution margin",
}
_ENGINE_KEYS = (
    ("base_monthly_contribution", "Base monthly contribution"),
    ("base_monthly_cash_flow", "Base monthly cash flow"),
    ("downside_monthly_revenue", "Downside monthly revenue"),
    ("downside_monthly_contribution", "Downside monthly contribution"),
    ("downside_monthly_cash_flow", "Downside monthly cash flow"),
    ("break_even_monthly_revenue", "Break-even monthly revenue"),
    ("months_to_break_even_base", "Months to recover initial capital"),
)


def calculate_preview(profile: dict[str, Any]) -> dict[str, Any]:
    """Return engine figures for the posted fields. Nothing is stored."""
    monthly_issues = monthly_problems(profile)
    startup_issues = _startup_issues(profile)
    financial = None
    downside_note = ""
    if not monthly_issues and _complete(profile, MONTHLY_FIELDS):
        intake, _missing = profile_to_intake(profile, as_of_date="2026-11-11")
        inputs = intake.get("financial_inputs")
        if isinstance(inputs, dict):
            financial = result_to_dict(
                run_financials(
                    FinancialInputs(
                        initial_capital=inputs["initial_capital"],
                        monthly_fixed_costs=inputs["monthly_fixed_costs"],
                        gross_margin_pct=inputs["gross_margin_pct"],
                        projected_monthly_revenue_base=inputs["projected_monthly_revenue_base"],
                        downside_revenue_multiplier=inputs.get("downside_revenue_multiplier", 0.6),
                    )
                )
            )
            if field_state(profile.get("downside_multiplier")) == "missing":
                downside_note = (
                    "Downside multiplier was not entered. This preview uses 0.6, "
                    "the same default Analyze uses. It is not saved."
                )
    projection = None
    projection_error = ""
    if not startup_issues and _complete(profile, _WORKSHEET_FIELDS):
        intake, _missing = profile_to_intake(profile, as_of_date="2026-11-11")
        worksheet = intake.get("startup_capital")
        if isinstance(worksheet, dict):
            try:
                projection = record_for_intake(
                    {"startup_capital": worksheet},
                    human_review_approved=False,
                )
            except ValueError as exc:
                projection_error = str(exc)
                projection = None
            else:
                projection["human_review_approved"] = False
                projection["is_final"] = False
                projection["investor_ready"] = False
    return {
        "monthly_issues": monthly_issues,
        "startup_issues": startup_issues,
        "financial": financial,
        "projection": projection if isinstance(projection, dict) and projection.get("calculated") else None,
        "projection_error": projection_error,
        "downside_note": downside_note,
        "monthly_complete": _complete(profile, MONTHLY_FIELDS),
        "startup_complete": _complete(profile, _WORKSHEET_FIELDS),
    }


def preview_markup(profile: dict[str, Any]) -> str:
    """HTML fragment for the preview panel. It contains no recommendation."""
    preview = calculate_preview(profile)
    parts = [
        f'<p id="preview-notice">{escape(PREVIEW_NOTICE)}</p>',
        '<p class="muted">Base and downside in this panel come from the monthly engine for the numbers in the form. '
        "A saved scenario comparison stays on the results page and is not replaced by this preview.</p>",
    ]
    issues = list(preview["monthly_issues"]) + list(preview["startup_issues"])
    if issues:
        parts.append("<ul>" + "".join(f"<li>{escape(item)}</li>" for item in issues) + "</ul>")
    financial = preview["financial"]
    if not isinstance(financial, dict):
        if preview["monthly_issues"]:
            parts.append("<p>The monthly preview was not calculated.</p>")
        else:
            parts.append(
                "<p>The monthly preview is not calculated. A blank monthly field stays missing and is not treated as zero.</p>"
            )
    else:
        if preview["downside_note"]:
            parts.append(f"<p>{escape(preview['downside_note'])}</p>")
        parts.append(_monthly_charts(financial))
        flags = financial.get("flags") if isinstance(financial.get("flags"), list) else []
        if flags:
            shown = ", ".join(str(flag) for flag in flags)
            parts.append(
                f"<p>Financial calculation flag from this preview: {escape(shown)}. "
                "These flags are not written to the assessment.</p>"
            )
        else:
            parts.append("<p>This preview did not raise a financial calculation flag. The stored assessment was not changed.</p>")
    projection = preview["projection"]
    if preview["projection_error"]:
        parts.append(
            f"<p>{escape(preview['projection_error'])} The startup capital preview was not drawn.</p>"
        )
    elif not isinstance(projection, dict):
        if preview["startup_issues"]:
            parts.append("<p>The startup capital preview was not calculated.</p>")
        else:
            parts.append(
                "<p>Startup capital summary is not calculated. The required startup fields are not all finite numbers.</p>"
            )
    else:
        parts.append(
            "<p>Startup capital preview uses the same projection Analyze uses. "
            "Optional worksheet lines left blank use that projection's coded defaults. This preview is not saved.</p>"
        )
        parts.append(_capital_chart(projection))
    parts.append("<p>No expense amount is drawn. The engine does not return a separate expense total.</p>")
    graphics = render_financial_graphics(
        financial if isinstance(financial, dict) else None,
        assumed_revenue=_entered_number(profile, "projected_monthly_revenue_base"),
        assumed_fixed_costs=_entered_number(profile, "monthly_fixed_costs"),
        projection=projection if isinstance(projection, dict) else None,
        preview=True,
    )
    parts.append(graphics["revenue"])
    parts.append(graphics["break_even"])
    parts.append(graphics["comparison"])
    parts.append(graphics["allocation"])
    parts.append(graphics["trend"])
    return f'<div data-preview="financial">{"".join(parts)}</div>'


def _entered_number(profile: dict[str, Any], key: str) -> float | None:
    if field_state(profile.get(key)) not in {"entered", "zero"}:
        return None
    raw = profile.get(key)
    if isinstance(raw, bool):
        return None
    if isinstance(raw, (int, float)):
        return float(raw)
    return float(str(raw).strip())


def _complete(profile: dict[str, Any], keys: tuple[str, ...]) -> bool:
    return all(field_state(profile.get(key)) in {"entered", "zero"} for key in keys)


def _startup_issues(profile: dict[str, Any]) -> list[str]:
    issues = []
    labeled = [(key, _STARTUP_LABELS[key]) for key in _WORKSHEET_FIELDS]
    labeled.extend(_OPTIONAL_STARTUP)
    for key, label in labeled:
        if key == "downside_multiplier" and any("Downside multiplier" in item for item in monthly_problems(profile)):
            continue
        if field_state(profile.get(key)) == "invalid":
            issues.append(
                f"{label} is not a finite number. A blank stays missing and is not used in the preview."
            )
    return issues


def _monthly_charts(financial: dict[str, Any]) -> str:
    lines = []
    for key, label in _ENGINE_KEYS:
        value = financial.get(key)
        if value is None:
            lines.append(f"<li>{escape(label)}: not calculated.</li>")
        else:
            lines.append(
                f"<li>{escape(key)}: {escape(str(value))}. Calculated by the engine for this preview. Not saved.</li>"
            )
    revenue = render_value_chart(
        "preview-revenue",
        "Revenue and contribution",
        [
            _point("base_monthly_contribution", "Base monthly contribution", financial),
            _point("downside_monthly_revenue", "Downside monthly revenue", financial),
            _point("downside_monthly_contribution", "Downside monthly contribution", financial),
        ],
        "Preview. Calculated by the engine for this request. Not saved.",
    )
    cash = render_value_chart(
        "preview-cash-flow",
        "Cash flow",
        [
            _point("base_monthly_cash_flow", "Base monthly cash flow", financial),
            _point("downside_monthly_cash_flow", "Downside monthly cash flow", financial),
        ],
        "Preview. Bar length is the absolute value. The label is the engine number. Not saved.",
    )
    break_even = render_value_chart(
        "preview-break-even",
        "Break-even monthly revenue",
        [_point("break_even_monthly_revenue", "Break-even monthly revenue", financial)],
        "Preview. Calculated by the engine. The customer's projected revenue is not drawn on this bar.",
    )
    return (
        '<div class="chart-grid">'
        + revenue
        + cash
        + break_even
        + "</div><ul>"
        + "".join(lines)
        + "</ul>"
    )


def _capital_chart(projection: dict[str, Any]) -> str:
    uses = projection.get("sources_and_uses") if isinstance(projection.get("sources_and_uses"), dict) else {}
    use_lines = uses.get("uses") if isinstance(uses.get("uses"), dict) else {}
    source_lines = uses.get("sources") if isinstance(uses.get("sources"), dict) else {}
    base = _view(projection, "base")
    downside = _view(projection, "downside")
    points = [
        _amount("total_project_cost", "Total project cost", use_lines),
        _amount("debt", "Debt", source_lines),
        _amount("equity", "Equity", source_lines),
        {"key": "startup_base_revenue", "label": "Startup base revenue", "value": base.get("revenue")},
        {"key": "startup_downside_revenue", "label": "Startup downside revenue", "value": downside.get("revenue")},
    ]
    chart = render_value_chart(
        "preview-capital",
        "Startup capital",
        points,
        "Preview. Amounts come from the startup projection. Not saved.",
    )
    rows = []
    for point in points:
        value = point.get("value")
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            rows.append(f"<li>{escape(str(point['label']))}: not calculated.</li>")
        else:
            rows.append(
                f"<li>{escape(str(point['key']))}: {escape(str(value))}. Calculated by the engine for this preview. Not saved.</li>"
            )
    return chart + "<ul>" + "".join(rows) + "</ul>"


def _view(projection: dict[str, Any], name: str) -> dict[str, Any]:
    views = projection.get("views") if isinstance(projection.get("views"), dict) else {}
    nested = views.get(name) if isinstance(views.get(name), dict) else {}
    if nested:
        return nested
    direct = projection.get(name) if isinstance(projection.get(name), dict) else {}
    return direct


def _point(key: str, label: str, financial: dict[str, Any]) -> dict[str, Any]:
    return {"key": key, "label": label, "value": financial.get(key)}


def _amount(key: str, label: str, container: dict[str, Any]) -> dict[str, Any]:
    item = container.get(key) if isinstance(container.get(key), dict) else {}
    return {"key": key, "label": label, "value": item.get("amount")}

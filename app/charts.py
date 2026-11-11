"""Draw charts from stored engine numbers. This module does not calculate them."""

from __future__ import annotations

import math
from html import escape
from typing import Any

CASH_FLOW_KEYS = (
    ("base_monthly_cash_flow", "Base monthly cash flow"),
    ("downside_monthly_cash_flow", "Downside monthly cash flow"),
)
CONTRIBUTION_KEYS = (
    ("base_monthly_contribution", "Base monthly contribution"),
    ("downside_monthly_contribution", "Downside monthly contribution"),
)
REVENUE_KEYS = (("downside_monthly_revenue", "Downside monthly revenue"),)

_READING_KEYS = (
    "base_monthly_contribution",
    "base_monthly_cash_flow",
    "downside_monthly_revenue",
    "downside_monthly_contribution",
    "downside_monthly_cash_flow",
    "break_even_monthly_revenue",
    "months_to_break_even_base",
)


def finite_number(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    number = float(value)
    if not math.isfinite(number):
        return None
    return number


def series(financial: dict[str, Any] | None, keys: tuple[tuple[str, str], ...]) -> list[dict[str, Any]]:
    if not isinstance(financial, dict):
        return []
    points = []
    for key, label in keys:
        number = finite_number(financial.get(key))
        if number is None:
            continue
        points.append({"key": key, "label": label, "value": number, "source": "engine"})
    return points


def reading_lines(financial: dict[str, Any] | None, *, live: bool) -> list[str]:
    """Repeat stored engine fields. A missing field is named and not filled in."""
    if live:
        lead = (
            "These lines copy the stored engine result. "
            "A configured adviser can explain them from Ask. This list is not a new calculation."
        )
    else:
        lead = (
            "Demonstration reading. No live model was called. "
            "Each figure below is copied from the stored engine result."
        )
    if not isinstance(financial, dict):
        return [lead, "No calculated monthly figures are stored. No chart was drawn."]
    lines = [lead]
    for key in _READING_KEYS:
        number = finite_number(financial.get(key))
        if number is None:
            lines.append(f"{key}: not calculated.")
        else:
            lines.append(f"{key}: {number}. Calculated by the engine.")
    lines.append("The engine does not return a separate expense total. No expense amount is drawn.")
    return lines


def render_engine_charts(financial: dict[str, Any] | None, *, live: bool) -> str:
    lines = "".join(f"<li>{escape(line)}</li>" for line in reading_lines(financial, live=live))
    if not isinstance(financial, dict):
        return (
            '<section class="card" id="engine-charts">'
            "<h2>Calculated charts</h2>"
            f"<ul>{lines}</ul></section>"
        )
    cash = _bar_chart(
        "cash-flow",
        "Cash flow",
        series(financial, CASH_FLOW_KEYS),
        "Calculated by the engine. Bar length is the absolute value. The label is the stored number.",
    )
    revenue = _bar_chart(
        "revenue-contribution",
        "Calculated revenue and contribution",
        series(financial, REVENUE_KEYS + CONTRIBUTION_KEYS),
        "Downside revenue and contribution come from the engine. Customer revenue assumptions are not drawn here.",
    )
    break_even = finite_number(financial.get("break_even_monthly_revenue"))
    if break_even is None:
        break_even_chart = (
            '<div class="chart" data-chart="break-even">'
            "<h3>Break-even</h3>"
            "<p>Break-even monthly revenue was not calculated. No break-even bar is drawn.</p>"
            "</div>"
        )
    else:
        break_even_chart = _bar_chart(
            "break-even",
            "Break-even monthly revenue",
            [
                {
                    "key": "break_even_monthly_revenue",
                    "label": "Break-even monthly revenue",
                    "value": break_even,
                    "source": "engine",
                }
            ],
            "Calculated by the engine. The customer's projected revenue is an assumption and is not drawn on this bar.",
        )
    return f"""
<section class="card" id="engine-charts">
<h2>Calculated charts</h2>
<p>These graphics use the stored engine result for this assessment. They are redrawn from that result after Analyze.</p>
<div class="chart-grid">{cash}{revenue}{break_even_chart}</div>
<ul>{lines}</ul>
</section>
"""


def render_scenario_chart(stored: dict[str, Any] | None) -> str:
    """Compare saved Base and alternative metrics. Both sides come from engine runs."""
    if not isinstance(stored, dict):
        return ""
    base = stored.get("base") if isinstance(stored.get("base"), dict) else None
    alternative = stored.get("alternative") if isinstance(stored.get("alternative"), dict) else None
    if not base and not alternative:
        return (
            '<div class="chart" data-chart="scenario">'
            "<h3>Scenario chart</h3>"
            "<p>No scenario chart is drawn until a Base or Downside case is saved from an engine run.</p>"
            "</div>"
        )
    left = base.get("metrics") if base and isinstance(base.get("metrics"), dict) else {}
    right = alternative.get("metrics") if alternative and isinstance(alternative.get("metrics"), dict) else {}
    right_label = str(alternative.get("label")) if alternative else "Alternative"
    keys = (
        ("monthly_cash_flow", "Monthly cash flow"),
        ("startup_revenue", "Startup revenue"),
        ("break_even_monthly_revenue", "Break-even monthly revenue"),
    )
    blocks = []
    for key, label in keys:
        points = []
        base_value = finite_number(left.get(key))
        other_value = finite_number(right.get(key))
        if base_value is not None:
            points.append({"key": f"base-{key}", "label": f"Base {label}", "value": base_value, "source": "engine"})
        if other_value is not None:
            points.append(
                {
                    "key": f"alternative-{key}",
                    "label": f"{right_label} {label}",
                    "value": other_value,
                    "source": "engine",
                }
            )
        if points:
            blocks.append(_bar_chart(f"scenario-{key}", label, points, "Saved from engine runs. This chart does not change the official result."))
    if not blocks:
        body = "<p>The saved cases have no charted metric. No number was added.</p>"
    else:
        body = "".join(blocks)
    return f'<div class="chart-grid" data-chart="scenario">{body}</div>'


def _bar_chart(chart_id: str, title: str, points: list[dict[str, Any]], note: str) -> str:
    if not points:
        return (
            f'<div class="chart" data-chart="{escape(chart_id)}">'
            f"<h3>{escape(title)}</h3>"
            "<p>This chart has no calculated number, so it is not drawn.</p>"
            "</div>"
        )
    span = max(abs(point["value"]) for point in points) or 1.0
    rows = []
    height = 28 * len(points) + 8
    for index, point in enumerate(points):
        width = max(2.0, abs(point["value"]) / span * 280)
        y = 8 + index * 28
        color = "#27323B" if point["value"] < 0 else "#A88958"
        rows.append(
            f'<rect x="250" y="{y}" width="{width:.2f}" height="16" fill="{color}"></rect>'
            f'<text x="8" y="{y + 12}" fill="#263746" font-size="12">{escape(point["label"])}</text>'
        )
        rows.append(
            f'<text x="{250 + width + 8:.2f}" y="{y + 12}" fill="#263746" font-size="12" '
            f'data-engine-key="{escape(point["key"])}" data-engine-value="{point["value"]}">{point["value"]}</text>'
        )
    svg = (
        f'<svg viewBox="0 0 640 {height}" role="img" aria-label="{escape(title)}">'
        + "".join(rows)
        + "</svg>"
    )
    return (
        f'<div class="chart" data-chart="{escape(chart_id)}">'
        f"<h3>{escape(title)}</h3>{svg}"
        f'<p class="muted">{escape(note)}</p></div>'
    )

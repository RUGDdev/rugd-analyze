"""Draw charts from stored engine numbers. This module does not calculate them."""

from __future__ import annotations

import math
from html import escape
from typing import Any

from app import display

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
            lines.append(f"{key}: {display.figure(key, number)}. Calculated by the engine.")
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


def render_value_chart(chart_id: str, title: str, points: list[dict[str, Any]], note: str) -> str:
    """Draw bars for numbers the caller already calculated. This function does not calculate them."""
    cleaned: list[dict[str, Any]] = []
    for point in points:
        number = finite_number(point.get("value"))
        if number is None:
            continue
        cleaned.append(
            {
                "key": str(point.get("key") or "value"),
                "label": str(point.get("label") or "Value"),
                "value": number,
                "source": str(point.get("source") or "engine"),
            }
        )
    return _bar_chart(chart_id, title, cleaned, note)


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
        if point.get("source") == "assumption":
            marker = f'data-assumption-key="{escape(point["key"])}" data-assumption-value="{point["value"]}"'
        else:
            marker = f'data-engine-key="{escape(point["key"])}" data-engine-value="{point["value"]}"'
        rows.append(
            f'<text x="{250 + width + 8:.2f}" y="{y + 12}" fill="#263746" font-size="12" '
            f"{marker}>{escape(display.figure(point['key'], point['value']))}</text>"
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


_ALLOCATION_KEYS = (
    ("construction_cost", "Construction"),
    ("equipment", "Equipment"),
    ("soft_costs", "Soft costs"),
    ("preopening_working_capital", "Pre-opening working capital"),
    ("contingency", "Contingency"),
)
_SLICE_COLORS = ("#263746", "#A88958", "#27323B", "#8C7350", "#E9D8B7")


def render_financial_graphics(
    financial: dict[str, Any] | None,
    *,
    assumed_revenue: float | None,
    assumed_fixed_costs: float | None,
    projection: dict[str, Any] | None,
    preview: bool,
) -> dict[str, str]:
    """Draw supported graphics from figures the caller already has. This does not run the engine."""
    label = "Preview. Not saved." if preview else "Copied from the stored result for this snapshot."
    revenue = _revenue_block(financial, assumed_revenue, assumed_fixed_costs, label)
    break_even = _break_even_block(financial, assumed_revenue, label)
    comparison = _comparison_block(financial, assumed_revenue, label)
    allocation = _allocation_block(projection, label)
    trend = (
        '<div class="chart" data-chart="cash-flow-trend">'
        "<h3>Cash-flow trend</h3>"
        "<p>No period-by-period cash-flow series is stored. A trend line is not drawn.</p>"
        "</div>"
    )
    return {
        "revenue": revenue,
        "break_even": break_even,
        "comparison": comparison,
        "allocation": allocation,
        "trend": trend,
    }


def _revenue_block(
    financial: dict[str, Any] | None,
    assumed_revenue: float | None,
    assumed_fixed_costs: float | None,
    label: str,
) -> str:
    rows = [
        _assumption_line("Monthly revenue", assumed_revenue),
        _engine_line(financial, "base_monthly_contribution", "Monthly contribution"),
        _assumption_line("Monthly fixed costs", assumed_fixed_costs),
        "<li>The engine does not return a separate expense total. No expense total is shown.</li>",
        _engine_line(financial, "base_monthly_cash_flow", "Monthly cash flow"),
        _engine_line(financial, "downside_monthly_revenue", "Downside monthly revenue"),
        _engine_line(financial, "downside_monthly_contribution", "Downside monthly contribution"),
        _engine_line(financial, "downside_monthly_cash_flow", "Downside monthly cash flow"),
    ]
    points = []
    if assumed_revenue is not None:
        points.append(
            {
                "key": "assumed_monthly_revenue",
                "label": "Monthly revenue (assumption)",
                "value": assumed_revenue,
                "source": "assumption",
            }
        )
    if isinstance(financial, dict):
        points.extend(
            [
                {"key": "base_monthly_contribution", "label": "Base monthly contribution", "value": financial.get("base_monthly_contribution")},
                {"key": "base_monthly_cash_flow", "label": "Base monthly cash flow", "value": financial.get("base_monthly_cash_flow")},
                {"key": "downside_monthly_cash_flow", "label": "Downside monthly cash flow", "value": financial.get("downside_monthly_cash_flow")},
            ]
        )
    chart = render_value_chart(
        "revenue-and-cash-flow",
        "Revenue, contribution, and cash flow",
        points,
        label + " Monthly revenue and fixed costs are customer-supplied assumptions. Contribution and cash flow come from the engine.",
    )
    return f'<section id="revenue-contribution">{chart}<ul>{"".join(rows)}</ul></section>'


def _break_even_block(
    financial: dict[str, Any] | None,
    assumed_revenue: float | None,
    label: str,
) -> str:
    break_even = finite_number(financial.get("break_even_monthly_revenue")) if isinstance(financial, dict) else None
    lines = [_assumption_line("Entered monthly revenue", assumed_revenue)]
    if break_even is None:
        lines.append("<li>Calculated break-even revenue: not calculated.</li>")
        lines.append("<li>The difference is not shown because break-even revenue was not calculated.</li>")
        explanation = "Break-even revenue is not available, so this preview cannot say whether the entered revenue is above or below it."
        gap_attr = ""
    else:
        lines.append(
            f"<li>break_even_monthly_revenue: {display.dollars(break_even)}. Calculated by the engine.</li>"
        )
        if assumed_revenue is None:
            lines.append("<li>The difference is not shown because monthly revenue was not entered. A blank is not treated as zero.</li>")
            explanation = "Enter monthly revenue to compare it with the calculated break-even revenue."
            gap_attr = ""
        else:
            gap = round(assumed_revenue - break_even, 2)
            lines.append(
                f'<li data-revenue-gap="{gap}">Revenue difference: {display.dollars(gap)}. '
                "This is the entered monthly revenue minus the engine break-even. It is not a separate engine output.</li>"
            )
            if gap > 0:
                explanation = f"The entered monthly revenue is {display.dollars(gap)} above the calculated break-even revenue."
            elif gap < 0:
                explanation = f"The entered monthly revenue is {display.dollars(abs(gap))} below the calculated break-even revenue."
            else:
                explanation = "The entered monthly revenue equals the calculated break-even revenue."
            gap_attr = f' data-revenue-gap="{gap}"'
    points = []
    if assumed_revenue is not None:
        points.append(
            {
                "key": "assumed_monthly_revenue",
                "label": "Entered monthly revenue",
                "value": assumed_revenue,
                "source": "assumption",
            }
        )
    if break_even is not None:
        points.append({"key": "break_even_monthly_revenue", "label": "Break-even monthly revenue", "value": break_even})
    chart = render_value_chart(
        "break-even-gap",
        "Break-even comparison",
        points,
        label + " The entered revenue is an assumption. Break-even is calculated by the engine.",
    )
    return (
        f'<section id="break-even-analysis"{gap_attr}>'
        f"{chart}<ul>{''.join(lines)}</ul><p>{escape(explanation)}</p></section>"
    )


def _comparison_block(
    financial: dict[str, Any] | None,
    assumed_revenue: float | None,
    label: str,
) -> str:
    rows = [
        _pair("Revenue", _money_text(assumed_revenue, assumed=True), _engine_text(financial, "downside_monthly_revenue")),
        _pair("Contribution", _engine_text(financial, "base_monthly_contribution"), _engine_text(financial, "downside_monthly_contribution")),
        _pair("Cash flow", _engine_text(financial, "base_monthly_cash_flow"), _engine_text(financial, "downside_monthly_cash_flow")),
        _pair(
            "Break-even monthly revenue",
            _engine_text(financial, "break_even_monthly_revenue"),
            "The monthly engine does not return a separate downside break-even.",
        ),
    ]
    body = "".join(
        f"<tr><th scope=\"row\">{escape(name)}</th><td>{base}</td><td>{downside}</td></tr>"
        for name, base, downside in rows
    )
    return (
        '<section id="base-versus-downside">'
        '<div class="chart" data-chart="base-downside">'
        "<h3>Base and Downside</h3>"
        "<table>"
        "<thead><tr><th>Metric</th><th>Base</th><th>Downside</th></tr></thead>"
        f"<tbody>{body}</tbody></table>"
        f"<p class=\"muted\">{escape(label)} Base revenue is the entered assumption. Downside revenue, contribution, and cash flow come from the engine.</p>"
        "</div></section>"
    )


def _allocation_block(projection: dict[str, Any] | None, label: str) -> str:
    if not isinstance(projection, dict) or not projection.get("calculated"):
        return (
            '<div class="chart" data-chart="capital-allocation">'
            "<h3>Startup capital allocation</h3>"
            "<p>Startup capital allocation is not drawn. The required sources and uses are not stored. No category was added.</p>"
            "</div>"
        )
    uses = projection.get("sources_and_uses") if isinstance(projection.get("sources_and_uses"), dict) else {}
    use_lines = uses.get("uses") if isinstance(uses.get("uses"), dict) else {}
    slices = []
    lines = []
    for key, name in _ALLOCATION_KEYS:
        item = use_lines.get(key) if isinstance(use_lines.get(key), dict) else None
        if item is None or finite_number(item.get("amount")) is None:
            lines.append(f"<li>{escape(name)}: Not available. This use is not in the stored projection.</li>")
            continue
        amount = finite_number(item.get("amount"))
        slices.append({"key": key, "label": name, "value": amount})
        state = "0. Stored as zero." if amount == 0 else f"{display.dollars(amount)}. Copied from the stored projection."
        lines.append(f"<li>{escape(key)}: {escape(state)}</li>")
    positive = [item for item in slices if item["value"] > 0]
    if not positive:
        graphic = "<p>Every stored use is zero or missing. No allocation slice is drawn.</p>"
    else:
        graphic = _doughnut(positive)
    return (
        '<div class="chart" data-chart="capital-allocation">'
        "<h3>Startup capital allocation</h3>"
        f"{graphic}<ul>{''.join(lines)}</ul>"
        f"<p class=\"muted\">{escape(label)} Slices are the stored uses. The total project cost is not drawn as an extra slice.</p>"
        "</div>"
    )


def _doughnut(slices: list[dict[str, Any]]) -> str:
    total = sum(item["value"] for item in slices)
    paths = []
    if len(slices) == 1:
        color = _SLICE_COLORS[0]
        paths.append(_wedge(180, 120, 78, -math.pi / 2, math.pi / 2, color))
        paths.append(_wedge(180, 120, 78, math.pi / 2, 3 * math.pi / 2, color))
    else:
        angle = -math.pi / 2
        for index, item in enumerate(slices):
            sweep = item["value"] / total * math.tau
            paths.append(_wedge(180, 120, 78, angle, angle + sweep, _SLICE_COLORS[index % len(_SLICE_COLORS)]))
            angle += sweep
    labels = "".join(
        f'<text x="250" y="{28 + index * 22}" fill="#263746" font-size="12">'
        f'{escape(item["label"])}: {escape(display.dollars(item["value"]))}</text>'
        for index, item in enumerate(slices)
    )
    svg = (
        '<svg viewBox="0 0 460 240" role="img" aria-label="Startup capital allocation">'
        + "".join(paths)
        + labels
        + "</svg>"
    )
    return svg


def _wedge(cx: float, cy: float, radius: float, start: float, end: float, color: str) -> str:
    large = 1 if end - start > math.pi else 0
    x0 = cx + radius * math.cos(start)
    y0 = cy + radius * math.sin(start)
    x1 = cx + radius * math.cos(end)
    y1 = cy + radius * math.sin(end)
    return (
        f'<path d="M {cx} {cy} L {x0:.2f} {y0:.2f} A {radius} {radius} 0 {large} 1 {x1:.2f} {y1:.2f} Z" '
        f'fill="{color}"></path>'
    )


def _assumption_line(label: str, value: float | None) -> str:
    if value is None:
        return f"<li>{escape(label)}: Missing. This blank is not stored as zero.</li>"
    if value == 0:
        return f"<li>{escape(label)}: 0. Customer-supplied assumption. Entered as zero.</li>"
    return f"<li>{escape(label)}: {display.dollars(value)}. Customer-supplied assumption.</li>"


def _engine_line(financial: dict[str, Any] | None, key: str, label: str) -> str:
    number = finite_number(financial.get(key)) if isinstance(financial, dict) else None
    if number is None:
        return f"<li>{escape(label)}: not calculated.</li>"
    return f"<li>{escape(key)}: {display.figure(key, number)}. Calculated by the engine.</li>"


def _engine_text(financial: dict[str, Any] | None, key: str) -> str:
    number = finite_number(financial.get(key)) if isinstance(financial, dict) else None
    if number is None:
        return "Not calculated."
    return escape(f"{display.figure(key, number)}. Calculated by the engine.")


def _money_text(value: float | None, *, assumed: bool) -> str:
    if value is None:
        return "Missing. This blank is not stored as zero."
    suffix = "Customer-supplied assumption." if assumed else "Calculated by the engine."
    return escape(f"{display.dollars(value)}. {suffix}")


def _pair(name: str, base: str, downside: str) -> tuple[str, str, str]:
    return name, base, downside

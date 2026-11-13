"""The Analyze results dashboard.

This module only reads what is already stored: the official engine result, the draft's
entries, saved benchmark records, the saved revenue worksheet, and saved improvement
scenarios. It adds no score, no readiness percentage, and no benchmark of its own.

Nothing here runs Analyze, clears a flag, sets human review, or changes a stored value.
A scenario or a worksheet is shown as a projection from the customer's assumptions.
"""

from __future__ import annotations

from html import escape
from typing import Any

from app import benchmarks, improve
from app import display as d
from app import revenue_worksheet as rw
from app.plain import TERMS
from scoring import rules

SECTIONS: tuple[tuple[str, str], ...] = (
    ("overview", "Overview"),
    ("key-numbers", "Key Numbers"),
    ("benchmarks", "Benchmarks"),
    ("revenue-model", "Revenue Model"),
    ("scenarios", "Scenarios"),
    ("recommendations", "Recommendations"),
)

SECTION_IDS = tuple(key for key, _label in SECTIONS)

OFFICIAL_UNCHANGED = "The official result, flags, and review status are unchanged by this."

_FLAG_SHORT = {
    rules.FLAG_DEMAND: "No verified demand evidence on file",
    rules.FLAG_DEMAND_UNVERIFIED: "Demand support is user-supplied only",
    rules.FLAG_OPERATOR: "Operator capacity is stated as inadequate",
    rules.FLAG_REGULATORY: "An unresolved regulatory or liability issue is recorded",
    rules.FLAG_EXTRACTION: "Extraction without reinvestment is recorded",
    rules.FLAG_OPERATOR_GAP: "Operator capacity has not been evaluated",
    rules.FLAG_REGULATORY_GAP: "Regulatory or liability review has not been recorded",
    rules.FLAG_STEWARDSHIP_GAP: "Reinvestment (stewardship) has not been recorded",
    rules.FLAG_FINANCIALS_UNMEASURED: "Financial inputs are not marked as measured",
}

_ICONS = {
    "shield": '<path d="M12 3l8 3v5c0 5-3.4 8.400-8 10-4.600-1.600-8-5-8-10V6z"/><path d="M9 12l2 2 4-4"/>',
    "cost": '<rect x="3" y="6" width="18" height="12" rx="2"/><circle cx="12" cy="12" r="2.500"/><path d="M6 9v.01M18 15v.01"/>',
    "loan": '<path d="M4 20h16M6 20V10M10 20V10M14 20V10M18 20V10M3 10l9-6 9 6z"/>',
    "gauge": '<path d="M4 17a8 8 0 1116 0"/><path d="M12 17l4-5"/>',
    "chart": '<path d="M4 20V4M4 20h16"/><path d="M8 16v-5M12 16V8M16 16v-3"/>',
    "scale": '<path d="M12 4v16M6 20h12M5 8h14"/><path d="M5 8l-3 6a3 3 0 006 0zM19 8l-3 6a3 3 0 006 0z"/>',
    "seat": '<path d="M7 11V6a2 2 0 012-2h6a2 2 0 012 2v5"/><path d="M5 11h14v5H5zM7 16v4M17 16v4"/>',
    "bulb": '<path d="M9 18h6M10 21h4"/><path d="M12 3a6 6 0 00-3.500 10.900c.6.500 1 1.200 1 2.100h5c0-.9.400-1.600 1-2.100A6 6 0 0012 3z"/>',
    "book": '<path d="M5 4h10a3 3 0 013 3v13H8a3 3 0 01-3-3z"/><path d="M5 17a3 3 0 013-3h10"/>',
    "layers": '<path d="M12 3l9 5-9 5-9-5z"/><path d="M3 13l9 5 9-5"/>',
    "doc": '<path d="M7 3h7l4 4v14H7z"/><path d="M14 3v4h4M9 12h6M9 16h6"/>',
}


def _icon(name: str) -> str:
    return (
        '<svg class="dicon" viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" '
        f'stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">{_ICONS.get(name, "")}</svg>'
    )


def _aid(record: dict[str, Any]) -> str:
    return escape(str(record.get("id") or ""))


# ---------------------------------------------------------------------------
# Help controls
# ---------------------------------------------------------------------------


def help_tip(
    title: str,
    *,
    means: str,
    how: str,
    source: str,
    assumptions: str,
    limits: str,
) -> str:
    """A compact help control. It explains a figure and never changes it."""
    rows = "".join(
        f"<p><strong>{label}.</strong> {escape(text)}</p>"
        for label, text in (
            ("What it means", means),
            ("How it is calculated", how),
            ("Where it came from", source),
            ("Assumptions used", assumptions),
            ("Limits", limits),
        )
        if text
    )
    return (
        '<details class="dh">'
        f'<summary aria-label="About {escape(title)}"><span aria-hidden="true">?</span></summary>'
        f'<div class="dh-body"><p class="dh-title">{escape(title)}</p>{rows}</div></details>'
    )


_ENGINE = "Calculated by the 0.1-pilot deterministic engine from your entries."
_YOURS = "Each input is your own assumption unless you attached a quote or a measurement."

METRIC_HELP: dict[str, dict[str, str]] = {
    "total_project_cost": {
        "title": "Total project cost",
        "means": "All the money the opening needs: build, equipment, soft costs, working capital, and a contingency.",
        "how": "The five uses added together. Contingency is your contingency percentage times the other four.",
        "source": _ENGINE,
        "assumptions": _YOURS + " Contingency may still be a coded placeholder.",
        "limits": "It is not a contractor quote and leaves out any cost you did not enter.",
    },
    "debt": {
        "title": "Debt",
        "means": "The part of the project paid for by borrowing.",
        "how": "Debt share times total project cost.",
        "source": _ENGINE,
        "assumptions": "The debt share is your assumption or a placeholder.",
        "limits": "A lender, not RUGD, decides what can be borrowed.",
    },
    "equity": {
        "title": "Equity",
        "means": "The part of the project paid for with your own or investors' money.",
        "how": "Total project cost minus debt.",
        "source": _ENGINE,
        "assumptions": "It follows from the debt share.",
        "limits": "It is not proof that the money exists. Bank statements or commitments do that.",
    },
    "annual_debt_service": {
        "title": "Yearly debt service",
        "means": "What the loan costs each year in payments.",
        "how": "A level monthly payment on the debt at your interest rate over your repayment years, times 12.",
        "source": _ENGINE,
        "assumptions": "Interest rate and repayment years are your assumptions or placeholders.",
        "limits": "A lender sets real terms and fees.",
    },
    "base_revenue": {
        "title": "Base revenue (per year)",
        "means": "Yearly sales in a typical year under your assumptions.",
        "how": "Seats times average ticket times blended occupancy times operating days. One cover per occupied seat per day.",
        "source": _ENGINE,
        "assumptions": "Seats, ticket, occupancy, and days are yours. Weekdays count 5/7 and weekends 2/7.",
        "limits": "No seat turnover or service periods. The proposed revenue worksheet tests those separately.",
    },
    "downside_revenue": {
        "title": "Downside revenue (per year)",
        "means": "Yearly sales in a weaker year.",
        "how": "The base calculation with occupancy cut by the downside multiplier.",
        "source": _ENGINE,
        "assumptions": "The downside multiplier is yours or a placeholder.",
        "limits": "It is not a forecast of the worst case.",
    },
    "cash_flow": {
        "title": "Cash flow before debt service (per year)",
        "means": "What the business keeps in a year before loan payments.",
        "how": "Revenue times contribution margin, minus annual fixed costs.",
        "source": _ENGINE,
        "assumptions": "Contribution margin and fixed costs are your assumptions.",
        "limits": "No taxes, ramp-up, or one-time costs.",
    },
    "dscr": {
        "title": "Debt service coverage (DSCR)",
        "means": "How many times cash flow covers the yearly loan payment. Below 1.00× means it does not cover it. A negative number means cash flow itself is negative.",
        "how": "Cash flow before debt service divided by yearly debt service.",
        "source": _ENGINE,
        "assumptions": "RUGD pages compare it with 1.00× (readiness default) and 1.25× (lender oriented).",
        "limits": "A lender sets its own test. Meeting a ratio does not clear a flag.",
    },
    "break_even": {
        "title": "Break-even revenue (per year)",
        "means": "The yearly sales needed to pay fixed costs and the loan.",
        "how": "Annual fixed costs plus yearly debt service, divided by contribution margin.",
        "source": _ENGINE,
        "assumptions": "Margin, fixed costs, and financing are yours.",
        "limits": "It assumes the margin holds at that sales level.",
    },
    "monthly": {
        "title": "Monthly operating view",
        "means": "A month-by-month view built only from your four monthly inputs.",
        "how": "Contribution is revenue times gross margin. Cash flow is contribution minus monthly fixed costs.",
        "source": _ENGINE,
        "assumptions": "All four inputs are yours. They are measured only if you marked them measured.",
        "limits": "It is separate from the startup build. Months to recover capital is not a revenue-ramp forecast.",
    },
}


def _metric_help(key: str) -> str:
    return help_tip(**METRIC_HELP[key])


def _term_help(key: str) -> str:
    item = TERMS[key]
    return help_tip(
        item["term"],
        means=item["plain"],
        how="Read from the stored engine result. It is not recalculated on this page.",
        source="The official engine result for this draft.",
        assumptions="",
        limits=item["precise"],
    )


# ---------------------------------------------------------------------------
# Read the stored result
# ---------------------------------------------------------------------------


def _amount(item: Any) -> float | None:
    if isinstance(item, dict):
        return d.number_of(item.get("amount"))
    return d.number_of(item)


def _projection(result: dict[str, Any]) -> dict[str, Any] | None:
    projection = result.get("projection")
    if isinstance(projection, dict) and projection.get("calculated"):
        return projection
    return None


def _views(projection: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    views = projection.get("views") or {}
    return views.get("base") or {}, views.get("downside") or {}, views.get("break_even") or {}


def _financial(result: dict[str, Any]) -> dict[str, Any] | None:
    financial = result.get("financial")
    return financial if isinstance(financial, dict) else None


def status_summary(result: dict[str, Any], startup_missing: list[str]) -> dict[str, Any]:
    """A qualitative label from stored flags and entries. It is not a score and not a readiness percentage."""
    if not result.get("engine_ran"):
        return {"label": "Not assessed", "tone": "plain", "labels": ["Not assessed"], "primary": "", "reason": "Analyze has not been run for this draft.", "action": ""}
    blocking = [str(flag) for flag in result.get("blocking_flags") or []]
    gaps = [str(flag) for flag in result.get("gap_flags") or []]
    labels: list[str] = []
    if rules.FLAG_DEMAND in blocking or rules.FLAG_DEMAND_UNVERIFIED in blocking:
        labels.append("Needs evidence")
    other = [flag for flag in blocking if flag not in {rules.FLAG_DEMAND, rules.FLAG_DEMAND_UNVERIFIED}]
    if other:
        labels.append("Recommend-against flag active")
    if rules.FLAG_FINANCIALS_UNMEASURED in gaps or startup_missing:
        labels.append("Financial assumptions incomplete")
    if str(result.get("human_review_status") or "pending") != "approved" or not result.get("human_review_approved"):
        labels.append("Review required")
    if not labels:
        labels.append("Review recorded")
    primary = blocking[0] if blocking else (gaps[0] if gaps else "")
    reason = ""
    if rules.FLAG_DEMAND in blocking:
        reason = TERMS["insufficient_demand_evidence"]["plain"]
    elif primary:
        reason = _FLAG_SHORT.get(primary) or rules.NEXT_ACTIONS.get(primary, "")
    return {
        "label": labels[0],
        "tone": "warn" if blocking or "Financial assumptions incomplete" in labels else "plain",
        "labels": labels,
        "primary": primary,
        "reason": reason,
        "action": rules.NEXT_ACTIONS.get(primary, "") if primary else "",
    }


def _is_placeholder(profile: dict[str, Any], key: str) -> bool:
    return improve.is_placeholder(profile, key)


# ---------------------------------------------------------------------------
# Small building blocks
# ---------------------------------------------------------------------------


def _coverage_note(value: Any) -> str:
    number = d.number_of(value)
    if number is None:
        return "Not calculated"
    if number < 0:
        return "Cash flow is negative"
    if number < improve.TARGETS[0]:
        return f"Below {d.multiple(improve.TARGETS[0])}"
    if number < improve.TARGETS[1]:
        return f"Between {d.multiple(improve.TARGETS[0])} and {d.multiple(improve.TARGETS[1])}"
    return f"At or above {d.multiple(improve.TARGETS[1])}"


def _kpi(icon: str, label: str, value: str, sub: str, href: str, *, help_html: str = "", chip_html: str = "", tone: str = "") -> str:
    return (
        f'<div class="dk{f" dk-{tone}" if tone else ""}">'
        f'<div class="dk-head">{_icon(icon)}<span class="dk-label">{escape(label)}</span>{help_html}</div>'
        f'<p class="dk-value">{escape(value)}</p>'
        f'<p class="dk-sub">{chip_html}{escape(sub)}</p>'
        f'<a class="dk-link" href="{escape(href)}" data-goto>Details</a></div>'
    )


def _table(headers: list[str], rows: list[list[str]], *, numeric_from: int = 1) -> str:
    head = "".join(f'<th scope="col"{" class=num" if i >= numeric_from else ""}>{escape(h)}</th>' for i, h in enumerate(headers))
    body = "".join(
        "<tr>" + "".join(
            (f'<th scope="row">{cell}</th>' if i == 0 else f'<td{" class=num" if i >= numeric_from else ""}>{cell}</td>')
            for i, cell in enumerate(row)
        ) + "</tr>"
        for row in rows
    )
    return f'<div class="dtable"><table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div>'


def _bars(rows: list[tuple[str, float | None, str]], *, reference: tuple[float, str] | None = None, unit_label: str = "") -> str:
    """Horizontal bars from real values. A missing value draws no bar and says so."""
    values = [value for _label, value, _text in rows if value is not None]
    if not values:
        return ""
    low = min([0.0, *values] + ([reference[0]] if reference else []))
    high = max([0.0, *values] + ([reference[0]] if reference else []))
    span = (high - low) or 1.0

    def pos(value: float) -> float:
        return (value - low) / span * 100

    zero = pos(0.0)
    out = []
    for label, value, text in rows:
        if value is None:
            out.append(
                f'<div class="dbar"><span class="dbar-l">{escape(label)}</span><span class="dbar-t dbar-none"></span>'
                f'<span class="dbar-v">{escape(text)}</span></div>'
            )
            continue
        left = min(zero, pos(value))
        width = max(abs(pos(value) - zero), 0.6)
        negative = " dbar-neg" if value < 0 else ""
        ref = (
            f'<i class="dbar-ref" style="left:{pos(reference[0]):.2f}%" title="{escape(reference[1])}"></i>'
            if reference
            else ""
        )
        out.append(
            f'<div class="dbar"><span class="dbar-l">{escape(label)}</span>'
            f'<span class="dbar-t"><i class="dbar-zero" style="left:{zero:.2f}%"></i>'
            f'<i class="dbar-fill{negative}" style="left:{left:.2f}%;width:{width:.2f}%"></i>{ref}</span>'
            f'<span class="dbar-v">{escape(text)}</span></div>'
        )
    note = f'<p class="muted dbar-note">{escape(unit_label)}</p>' if unit_label else ""
    return f'<div class="dbars" role="group">{"".join(out)}{note}</div>'


# ---------------------------------------------------------------------------
# Key numbers
# ---------------------------------------------------------------------------


def _uses_rows(projection: dict[str, Any], profile: dict[str, Any]) -> list[list[str]]:
    uses = (projection.get("sources_and_uses") or {}).get("uses") or {}
    names = (
        ("construction_cost", "Construction cost", "construction_cost"),
        ("equipment", "Equipment", "equipment"),
        ("soft_costs", "Soft costs", "soft_costs"),
        ("preopening_working_capital", "Pre-opening working capital", "preopening_working_capital"),
        ("contingency", "Contingency", "contingency_pct"),
        ("total_project_cost", "Total project cost", ""),
    )
    rows = []
    for key, label, profile_key in names:
        item = uses.get(key)
        amount = _amount(item)
        state = d.state_from_engine((item or {}).get("evidence_label") if isinstance(item, dict) else "")
        if amount is None:
            tag = d.chip("missing", "Not calculated")
        elif profile_key and state == "estimated" and _is_placeholder(profile, profile_key):
            tag = d.chip("placeholder")
        elif amount == 0 and state == "estimated":
            tag = d.chip("zero")
        else:
            tag = d.chip(state)
        text = d.money(amount, missing="Not calculated")
        if key == "total_project_cost":
            text = f"<strong>{escape(text)}</strong>"
            label = f"<strong>{escape(label)}</strong> {_metric_help('total_project_cost')}"
        else:
            text = escape(text)
            label = escape(label)
        rows.append([label, f"{text} {tag}"])
    return rows


def _sources_rows(projection: dict[str, Any], profile: dict[str, Any]) -> list[list[str]]:
    sources = (projection.get("sources_and_uses") or {}).get("sources") or {}
    rows = []
    for key, label, help_key in (("debt", "Debt", "debt"), ("equity", "Equity", "equity"), ("total_sources", "Total sources", "")):
        item = sources.get(key)
        amount = _amount(item)
        label_html = escape(label) + (f" {_metric_help(help_key)}" if help_key else "")
        rows.append([label_html, f"{escape(d.money(amount, missing='Not calculated'))} {d.chip('calculated') if amount is not None else d.chip('missing', 'Not calculated')}"])
    service = d.number_of(sources.get("annual_debt_service"))
    monthly = d.number_of(sources.get("monthly_debt_service"))
    rows.append(
        [
            f"Yearly debt service {_metric_help('annual_debt_service')}",
            f"{escape(d.money(service, missing='Not calculated'))} {d.chip('calculated') if service is not None else d.chip('missing', 'Not calculated')}",
        ]
    )
    rows.append(["Monthly debt service", f"{escape(d.money(monthly, missing='Not calculated', cents=True))} {d.chip('calculated') if monthly is not None else d.chip('missing', 'Not calculated')}"])
    return rows


def _terms_rows(profile: dict[str, Any]) -> list[list[str]]:
    rows = []
    for key, label, fmt in (
        ("debt_share", "Debt share", lambda v: d.percent(v, 0)),
        ("annual_interest_rate", "Interest rate (per year)", lambda v: d.percent(v, 1)),
        ("amortization_years", "Repayment term", lambda v: d.count(v, "years")),
        ("contingency_pct", "Contingency", lambda v: d.percent(v, 0)),
        ("downside_multiplier", "Downside multiplier", lambda v: d.percent(v, 0)),
    ):
        number = improve.entered(profile, key)
        if number is None:
            rows.append([escape(label), f"{escape(d.NOT_PROVIDED)} {d.chip('missing')}"])
        elif _is_placeholder(profile, key):
            rows.append([escape(label), f"{escape(fmt(number))} {d.chip('placeholder')}"])
        else:
            rows.append([escape(label), f"{escape(fmt(number))} {d.chip('estimated')}"])
    return rows


def _startup_block(result: dict[str, Any], projection: dict[str, Any], profile: dict[str, Any]) -> str:
    base, downside, break_even = _views(projection)
    base_dscr = d.multiple(base.get("dscr"))
    down_dscr = d.multiple(downside.get("dscr"))
    coverage = _table(
        ["Case (per year)", "Revenue", "Cash flow before debt service", "Coverage"],
        [
            [
                "Base",
                escape(d.money(base.get("revenue"), missing="Not calculated")),
                escape(d.money(base.get("cash_flow_before_debt_service"), missing="Not calculated")),
                f"<strong>{escape(base_dscr)}</strong><br><span class=\"muted\">{escape(_coverage_note(base.get('dscr')))}</span>",
            ],
            [
                "Downside",
                escape(d.money(downside.get("revenue"), missing="Not calculated")),
                escape(d.money(downside.get("cash_flow_before_debt_service"), missing="Not calculated")),
                f"<strong>{escape(down_dscr)}</strong><br><span class=\"muted\">{escape(_coverage_note(downside.get('dscr')))}</span>",
            ],
        ],
    )
    chart_rows = [
        ("Base", d.number_of(base.get("dscr")), base_dscr),
        ("Downside", d.number_of(downside.get("dscr")), down_dscr),
    ]
    coverage_chart = _bars(
        chart_rows,
        reference=(improve.TARGETS[0], f"{d.multiple(improve.TARGETS[0])} readiness default"),
        unit_label=f"Dashed line: {d.multiple(improve.TARGETS[0])} (readiness default). Coverage is a ratio, not a score.",
    )
    revenue_chart = _bars(
        [
            ("Downside revenue", d.number_of(downside.get("revenue")), d.money(downside.get("revenue"), missing="Not calculated")),
            ("Base revenue", d.number_of(base.get("revenue")), d.money(base.get("revenue"), missing="Not calculated")),
            ("Break-even revenue", d.number_of(break_even.get("revenue")), d.money(break_even.get("revenue"), missing="Not calculated")),
        ],
        unit_label="Yearly amounts from the engine.",
    )
    return f"""
<div class="dgrid2">
  <div class="dcard"><h3>Uses of money {_metric_help('total_project_cost')}</h3>{_table(['Use', 'Amount'], _uses_rows(projection, profile))}</div>
  <div class="dcard"><h3>Sources and financing</h3>{_table(['Source', 'Amount'], _sources_rows(projection, profile))}
  <p class="muted">Financing terms are your assumptions or placeholders. A lender sets real terms.</p></div>
</div>
<div class="dcard"><h3>Coverage of the loan payment {_metric_help('dscr')}</h3>{coverage}{coverage_chart}</div>
<div class="dgrid2">
  <div class="dcard"><h3>Revenue against break-even {_metric_help('break_even')}</h3>{revenue_chart}</div>
  <div class="dcard"><h3>Financing assumptions used</h3>{_table(['Assumption', 'Value'], _terms_rows(profile))}</div>
</div>
"""


def _monthly_block(financial: dict[str, Any] | None, *, startup_ran: bool) -> str:
    if not financial:
        return (
            '<div class="dcard"><h3>Monthly operating view</h3>'
            f'<p>{d.chip("missing", "Not calculated")} The four monthly inputs are not all saved, so no monthly figure is shown. '
            "A blank is not treated as zero, and nothing is filled in for you.</p></div>"
        )
    rows = []
    for key, label in (
        ("base_monthly_contribution", "Base contribution (per month)"),
        ("base_monthly_cash_flow", "Base cash flow (per month)"),
        ("downside_monthly_cash_flow", "Downside cash flow (per month)"),
        ("break_even_monthly_revenue", "Break-even revenue (per month)"),
    ):
        rows.append([escape(label), f"{escape(d.money(financial.get(key), missing='Not calculated'))} {d.chip('calculated') if d.number_of(financial.get(key)) is not None else d.chip('missing', 'Not calculated')}"])
    months = financial.get("months_to_break_even_base")
    rows.append(
        [
            "Months to recover initial capital",
            f"{escape(d.decimal_text(months, 1, 'months', missing='Not calculated'))} "
            f"{d.chip('calculated') if d.number_of(months) is not None else d.chip('missing', 'Not calculated')}",
        ]
    )
    chart = _bars(
        [
            ("Base cash flow", d.number_of(financial.get("base_monthly_cash_flow")), d.money(financial.get("base_monthly_cash_flow"), missing="Not calculated")),
            ("Downside cash flow", d.number_of(financial.get("downside_monthly_cash_flow")), d.money(financial.get("downside_monthly_cash_flow"), missing="Not calculated")),
        ],
        unit_label="Per month, from the four monthly inputs. Red means negative.",
    )
    note = (
        "This monthly view uses the monthly inputs. It is separate from the startup build above and the two are not added together."
        if startup_ran
        else "This view uses the monthly inputs only."
    )
    return (
        f'<div class="dcard"><h3>Monthly operating view {_metric_help("monthly")}</h3>'
        f"{_table(['Measure', 'Amount'], rows)}{chart}<p class=\"muted\">{escape(note)}</p></div>"
    )


def key_numbers_html(result: dict[str, Any], profile: dict[str, Any], startup_missing: list[str], legacy_tables: str) -> str:
    projection = _projection(result)
    parts = []
    if projection:
        parts.append(_startup_block(result, projection, profile))
    else:
        missing = ", ".join(startup_missing)
        parts.append(
            '<div class="dcard"><h3>Startup cost build</h3>'
            f'<p>{d.chip("missing", "Not calculated")} The engine did not calculate the startup cost build.'
            f"{(' Still needed: ' + escape(missing) + '.') if missing else ''} Nothing was filled in for you.</p></div>"
        )
    parts.append(_monthly_block(_financial(result), startup_ran=bool(projection)))
    parts.append(
        '<details class="dmore"><summary>Full engine tables and charts</summary>'
        f"{legacy_tables}</details>"
    )
    return "".join(parts)


# ---------------------------------------------------------------------------
# Benchmarks
# ---------------------------------------------------------------------------

_ASSUMPTION_CHECKS = (
    ("average_ticket", "average_check", "Average ticket", lambda v: d.money(v, cents=True) + " per cover"),
    ("avg_hourly_wage", "avg_hourly_wage", "Average hourly wage", lambda v: d.money(v, cents=True) + " per hour"),
)


def benchmark_summary(record: dict[str, Any], entries: list[dict[str, Any]]) -> dict[str, Any]:
    profile = record.get("profile") or {}
    context = benchmarks.match(profile, entries)
    records = context["records"]
    verified = [item for item in records if item.get("verified") is True]
    return {"context": context, "records": records, "verified": verified}


def _record_card(item: dict[str, Any]) -> str:
    tags = [f'<span class="dtag">{escape(item["status"])}</span>']
    if item.get("stale"):
        tags.append('<span class="dtag dtag-warn">Older than two years</span>')
    if item.get("undated"):
        tags.append('<span class="dtag dtag-warn">No publication date</span>')
    if item.get("conflict"):
        tags.append('<span class="dtag dtag-bad">Conflicts with another record</span>')
    link = " ".join(
        f'<a href="{escape(url)}" rel="noopener noreferrer" target="_blank">Source link</a>' for url in item.get("source_urls") or []
    )
    applies = "".join(f"<li>{escape(note)}</li>" for note in item.get("applicability") or []) or "<li>Applicability was not stated.</li>"
    limits = "".join(f"<li>{escape(note)}</li>" for note in item.get("limitations") or []) or "<li>No limitations were recorded.</li>"
    retrieved = item.get("retrieved") or "not recorded"
    return (
        '<div class="dbm">'
        f'<p class="dbm-top"><strong>{escape(item["metric"])}</strong><span class="dbm-val">{escape(item["value_text"])}</span></p>'
        f'<p>{"".join(tags)}</p>'
        f'<p class="muted">{escape(item["source"] or "Source not stated")} · published {escape(str(item.get("published") or "not stated"))} · '
        f'retrieved {escape(str(retrieved))} · {escape(item["geography"])} {link}</p>'
        '<details class="dmore dmore-tight"><summary>Applies to, and limits</summary>'
        f"<p><strong>Applicability.</strong></p><ul>{applies}</ul><p><strong>Limitations.</strong></p><ul>{limits}</ul></details></div>"
    )


def _assumption_checks(profile: dict[str, Any], records: list[dict[str, Any]], aid: str) -> str:
    rows = []
    for profile_key, metric_key, label, fmt in _ASSUMPTION_CHECKS:
        number = d.number_of(profile.get(profile_key))
        yours = escape(fmt(number)) + f" {d.chip('estimated')}" if number is not None else f"{escape(d.NOT_PROVIDED)} {d.chip('missing')}"
        found = benchmarks.reference_for(records, metric_key)
        if found:
            best = found[-1]
            theirs = (
                f"{escape(best['value_text'])} {d.chip('benchmark', best['status'])}"
                f'<br><span class="muted">{escape(best["source"])} · {escape(best["geography"])}</span>'
            )
        else:
            theirs = f'<strong>No verified benchmark available</strong> <a href="/assessments/{aid}/benchmarks#record-figure">Record one</a>'
        rows.append([escape(label), yours, theirs])
    return _table(["Your assumption", "Your entry", "Benchmark on file"], rows, numeric_from=9)


def benchmarks_html(record: dict[str, Any], summary: dict[str, Any]) -> str:
    aid = _aid(record)
    profile = record.get("profile") or {}
    context = summary["context"]
    records = summary["records"]
    industry = str(profile.get("industry") or "").strip() or "this industry"
    market = context["market"] or "this market"
    if summary["verified"]:
        verdict = (
            f'<div class="dverdict dverdict-ok">{_icon("scale")}<div><strong>Verified benchmarks are on file.</strong> '
            "Each one shows its source, date, place, and limits below.</div></div>"
        )
    else:
        verdict = (
            f'<div class="dverdict">{_icon("scale")}<div><strong>No verified benchmark available</strong> for {escape(industry)} in {escape(market)}.'
            "<br><span class=\"muted\">"
            + (
                f"RUGD holds {len(records)} stored record{'s' if len(records) != 1 else ''} below. "
                "They are secondary or customer-recorded context, not verification of your numbers. "
                if records
                else "No benchmark is stored for this draft, and RUGD does not estimate one. "
            )
            + "A benchmark is context. It is not a target or evidence about this business.</span></div></div>"
        )
    cards = "".join(_record_card(item) for item in records[:3]) or (
        '<p class="muted">No stored benchmark records apply to this draft.</p>'
    )
    if len(records) > 3:
        cards += (
            f'<details class="dmore"><summary>Show the other {len(records) - 3} stored record{"s" if len(records) - 3 != 1 else ""}</summary>'
            + "".join(_record_card(item) for item in records[3:])
            + "</details>"
        )
    unresolved = "".join(
        f'<div class="dbm"><p class="dbm-top"><strong>{escape(item["metric"])}</strong><span class="dbm-val">not loaded</span></p>'
        f'<p><span class="dtag dtag-bad">{escape(item["status"])}</span></p>'
        f'<p class="muted">Public sources disagree: {escape(" versus ".join(item["candidates"]))}. RUGD stores neither value.</p></div>'
        for item in context.get("unresolved") or []
    )
    missing = [benchmarks.METRICS[key]["label"] for key in context.get("missing") or []]
    missing_html = (
        f'<p class="muted"><strong>Not on file:</strong> {escape("; ".join(missing))}.</p>' if missing else ""
    )
    return f"""
{verdict}
<div class="dcard"><h3>Your assumptions against what is on file</h3>{_assumption_checks(profile, records, aid)}</div>
<div class="dcard"><h3>Stored records</h3>{cards}{unresolved}{missing_html}</div>
<div class="dactions">
  <a class="dbtn" href="/assessments/{aid}/benchmarks">Open Benchmarks</a>
  <a class="dbtn dbtn-ghost" href="/assessments/{aid}/benchmarks#record-figure">Record a figure or build an assumption</a>
  <a class="dbtn dbtn-ghost" href="/assessments/{aid}/intelligence">Research this market</a>
</div>
"""


# ---------------------------------------------------------------------------
# Revenue model
# ---------------------------------------------------------------------------


def revenue_html(record: dict[str, Any], result: dict[str, Any], worksheet_record: dict[str, Any] | None) -> str:
    aid = _aid(record)
    profile = record.get("profile") or {}
    projection = _projection(result)
    inputs = (
        ("Seats", d.count(profile.get("seats") if d.number_of(profile.get("seats")) is not None else None)),
        ("Average ticket", d.money(profile.get("average_ticket"), cents=True) if d.number_of(profile.get("average_ticket")) is not None else d.NOT_PROVIDED),
        ("Weekday occupancy", d.percent(profile.get("weekday_occupancy")) if d.number_of(profile.get("weekday_occupancy")) is not None else d.NOT_PROVIDED),
        ("Weekend occupancy", d.percent(profile.get("weekend_occupancy")) if d.number_of(profile.get("weekend_occupancy")) is not None else d.NOT_PROVIDED),
        ("Operating days (per year)", d.count(profile.get("operating_days")) if d.number_of(profile.get("operating_days")) is not None else d.NOT_PROVIDED),
    )
    input_rows = [[escape(label), f"{escape(value)} {d.chip('estimated') if value != d.NOT_PROVIDED else d.chip('missing')}"] for label, value in inputs]
    if projection:
        base, _down, _be = _views(projection)
        official_value = d.money(base.get("revenue"), missing="Not calculated")
        official = (
            f'<div class="dcard"><h3>Official revenue calculation {_metric_help("base_revenue")}</h3>'
            f'<p class="dbig">{escape(official_value)} <span class="muted">per year</span> {d.chip("calculated")}</p>'
            "<p class=\"muted\">Seats × average ticket × blended occupancy × operating days. One cover per occupied seat per day. "
            "Weekdays count 5/7 and weekends 2/7.</p>"
            f"{_table(['Input', 'Your entry'], input_rows)}</div>"
        )
    else:
        official = (
            '<div class="dcard"><h3>Official revenue calculation</h3>'
            f'<p>{d.chip("missing", "Not calculated")} The seat-based revenue was not calculated for this draft. '
            "Existing-business drafts use the monthly base revenue instead.</p>"
            f"{_table(['Input', 'Your entry'], input_rows)}</div>"
        )
    saved_line = ""
    if worksheet_record:
        parsed = (worksheet_record.get("payload") or {}).get("worksheet") or {}
        calc = rw.calculate(parsed)
        if calc:
            comparison = rw.compare(parsed, calc, profile)
            bars = ""
            verdict = ""
            if comparison.get("official") is not None:
                bars = _bars(
                    [
                        ("Official formula", d.number_of(comparison["official"]), d.money(comparison["official"])),
                        ("Proposed worksheet", d.number_of(calc["total_revenue"]), d.money(calc["total_revenue"])),
                    ],
                    unit_label="Yearly revenue. The worksheet is a proposal and does not feed the official result.",
                )
                diff = comparison["difference"]
                pct = comparison.get("difference_pct")
                verdict = (
                    f"<p><strong>The worksheet is {escape(d.money(abs(diff)))} {'above' if diff >= 0 else 'below'} the official figure"
                    f"{f' ({abs(pct):.0f}%)' if pct is not None else ''}.</strong></p>"
                )
            cap = ""
            if comparison.get("beyond_official_cap"):
                cap = (
                    f'<p class="dnote">The worksheet assumes {calc["covers_per_seat_per_open_day"]:.2f} covers per seat per open day. '
                    "The official formula cannot exceed one. Turn rates above one need evidence from a comparable place.</p>"
                )
            saved_line = (
                '<div class="dcard"><h3>Proposed revenue worksheet</h3>'
                f'<p class="dbig">{escape(d.money(calc["total_revenue"]))} <span class="muted">per year</span> {d.chip("estimated", "Proposal")}</p>'
                f'<p class="muted">{escape(d.money(calc["monthly_revenue"]))} per month · average check {escape(d.money(calc["average_check"], cents=True))} · '
                f'{calc["covers_per_seat_per_open_day"]:.2f} covers per seat per open day.</p>'
                f"{verdict}{bars}{cap}</div>"
            )
    if not saved_line:
        saved_line = (
            '<div class="dcard"><h3>Proposed revenue worksheet</h3>'
            f'<p>{d.chip("missing", "Not saved")} No worksheet is saved for this draft. '
            "The worksheet counts service periods, seat turns, and the days you are really open, and compares them with the official calculation. "
            "It does not replace the official result.</p></div>"
        )
    return f"""
<div class="dgrid2">{official}{saved_line}</div>
<div class="dactions">
  <a class="dbtn" href="/assessments/{aid}/revenue-worksheet">Open the revenue worksheet</a>
  <a class="dbtn dbtn-ghost" href="/assessments/{aid}">Edit revenue inputs in Explore</a>
</div>
"""


# ---------------------------------------------------------------------------
# Scenarios
# ---------------------------------------------------------------------------


def _current_metrics(record: dict[str, Any]) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    base = improve.base_inputs(record.get("profile") or {})
    if base["missing"]:
        return None, base
    metrics, _error = improve.evaluate(base["inputs"])
    return metrics, base


def scenarios_html(record: dict[str, Any], scenario_records: list[dict[str, Any]], legacy: str) -> str:
    aid = _aid(record)
    metrics, base = _current_metrics(record)
    if metrics is None:
        labels = ", ".join(improve.LABELS[key] for key in base["missing"])
        intro = (
            '<div class="dcard"><h3>Improvement scenarios</h3>'
            f'<p>{d.chip("missing", "Not available")} Scenarios need the startup numbers first. Not entered yet: {escape(labels)}.</p></div>'
        )
        return intro + f'<div class="dactions"><a class="dbtn" href="/assessments/{aid}/improve">Open Improve feasibility</a></div>' + legacy
    scenarios = [improve.recompute(item) for item in scenario_records[-4:]]
    scenarios = [item for item in scenarios if item["metrics"]]
    columns = [("Current draft", metrics, False)] + [(item["name"], item["metrics"], bool(item.get("applied"))) for item in scenarios]

    def row(label: str, key: str, fmt: Any) -> list[str]:
        cells = []
        for _n, m, _a in columns:
            if key.endswith("dscr") and m.get(key) is None and not m.get("annual_debt_service"):
                cells.append("No debt, so no payment to cover")
            else:
                cells.append(escape(fmt(m.get(key))))
        return [escape(label)] + cells

    def meets(m: dict[str, Any]) -> str:
        value = d.number_of(m.get("downside_dscr"))
        if value is None and not m.get("annual_debt_service"):
            return "No debt to cover"
        if value is None:
            return "Not calculated"
        return "Yes, under its assumptions" if value >= improve.TARGETS[0] - 1e-9 else "No"

    table = _table(
        ["Measure"] + [name + (" (applied)" if applied else "") for name, _m, applied in columns],
        [
            row("Total project cost", "total_project_cost", lambda v: d.money(v, missing="Not calculated")),
            row("Your equity", "equity", lambda v: d.money(v, missing="Not calculated")),
            row("Yearly debt service", "annual_debt_service", lambda v: d.money(v, missing="Not calculated")),
            row("Base coverage", "base_dscr", d.multiple),
            row("Downside coverage", "downside_dscr", d.multiple),
            row("Break-even revenue (per year)", "break_even_revenue", lambda v: d.money(v, missing="Not calculated")),
            [f"Reaches {d.multiple(improve.TARGETS[0])} downside coverage"] + [escape(meets(m)) for _n, m, _a in columns],
        ],
    )
    chart = _bars(
        [(name, d.number_of(m.get("downside_dscr")), d.multiple(m.get("downside_dscr"))) for name, m, _a in columns],
        reference=(improve.TARGETS[0], f"{d.multiple(improve.TARGETS[0])} readiness default"),
        unit_label="Downside coverage. Dashed line: 1.00×. Each bar is a projection from assumptions.",
    )
    if scenarios:
        body = (
            f'<div class="dcard"><h3>Saved scenarios beside your draft</h3>{table}{chart}'
            f'<p class="dnote">{escape(improve.NOT_APPROVED)} {escape(OFFICIAL_UNCHANGED)}</p></div>'
        )
    else:
        body = (
            '<div class="dcard"><h3>No improvement scenario is saved yet</h3>'
            "<p>Test a smaller venue, more capital, or a different build cost, then save it to compare it here. "
            f'{escape(OFFICIAL_UNCHANGED)}</p></div>'
        )
    return (
        body
        + f'<div class="dactions"><a class="dbtn" href="/assessments/{aid}/improve">Open Improve feasibility</a>'
        + (f'<a class="dbtn dbtn-ghost" href="/assessments/{aid}/improve#saved">Compare and edit saved scenarios</a>' if scenarios else "")
        + "</div>"
        + legacy
    )


# ---------------------------------------------------------------------------
# Recommendations
# ---------------------------------------------------------------------------

_PRESET_TITLES = {
    "owner_cash": "Increase available capital",
    "lower_build": "Revise construction costs",
    "smaller_venue": "Reduce project size",
    "higher_ticket": "Improve operating economics: revenue",
    "lower_fixed": "Improve operating economics: fixed costs",
    "longer_term": "Review financing assumptions",
}
_PRESET_ORDER = ("owner_cash", "lower_build", "smaller_venue", "higher_ticket", "lower_fixed", "longer_term")


def build_recommendations(
    record: dict[str, Any],
    result: dict[str, Any],
    *,
    has_worksheet: bool = False,
    benchmark_entries: int = 0,
) -> list[dict[str, Any]]:
    """Supported improvement opportunities, each tied to a stored result or an entry. Nothing is claimed beyond the arithmetic."""
    if not result.get("engine_ran"):
        return []
    aid = str(record.get("id") or "")
    profile = record.get("profile") or {}
    blocking = [str(flag) for flag in result.get("blocking_flags") or []]
    gaps = [str(flag) for flag in result.get("gap_flags") or []]
    recs: list[dict[str, Any]] = []

    if rules.FLAG_DEMAND in blocking or rules.FLAG_DEMAND_UNVERIFIED in blocking:
        flag = rules.FLAG_DEMAND if rules.FLAG_DEMAND in blocking else rules.FLAG_DEMAND_UNVERIFIED
        recs.append(
            {
                "id": "demand",
                "priority": 1,
                "icon": "shield",
                "title": "Strengthen demand evidence",
                "why": TERMS["insufficient_demand_evidence"]["plain"] if flag == rules.FLAG_DEMAND else _FLAG_SHORT[flag],
                "basis": f"Active flag {flag}.",
                "detail": rules.NEXT_ACTIONS[flag],
                "links": [
                    ("Save evidence in Research", f"/assessments/{aid}/intelligence"),
                    ("Evidence checklist", f"/assessments/{aid}/results#evidence-checklist-{aid}"),
                ],
                "caveat": "Adding evidence does not clear the flag. A verified demand record and an authorized review do.",
            }
        )
    unevaluated = [flag for flag in gaps if flag.startswith("UNEVALUATED")]
    if unevaluated:
        recs.append(
            {
                "id": "criteria",
                "priority": 7,
                "icon": "layers",
                "title": "Record the criteria not yet evaluated",
                "why": "; ".join(_FLAG_SHORT[flag] for flag in unevaluated) + ".",
                "basis": "Engine gap flags: " + ", ".join(unevaluated) + ".",
                "detail": "",
                "links": [("Answer in Explore", f"/assessments/{aid}")],
                "caveat": "Recording an answer does not by itself change the official recommendation.",
            }
        )

    base = improve.base_inputs(profile)
    startup = not base["missing"]
    placeholders = [improve.LABELS[key] for key in base["placeholders"]] if startup else []
    if rules.FLAG_FINANCIALS_UNMEASURED in gaps or placeholders:
        why = "The financial inputs are not marked as measured."
        if placeholders:
            why += " Still blank or at a coded placeholder: " + ", ".join(placeholders) + "."
        recs.append(
            {
                "id": "assumptions",
                "priority": 2,
                "icon": "cost",
                "title": "Replace estimates with quotes or measurements",
                "why": why,
                "basis": "Engine gap flag FINANCIAL_INPUTS_NOT_MEASURED." if rules.FLAG_FINANCIALS_UNMEASURED in gaps else "Your entries.",
                "detail": rules.NEXT_ACTIONS[rules.FLAG_FINANCIALS_UNMEASURED] if rules.FLAG_FINANCIALS_UNMEASURED in gaps else "",
                "links": [("Update inputs in Explore", f"/assessments/{aid}")],
                "caveat": "Placeholders are not market figures. Changing them does not run Analyze.",
            }
        )

    metrics = None
    if startup:
        metrics, _error = improve.evaluate(base["inputs"])
    if metrics:
        target = improve.TARGETS[0]
        down = d.number_of(metrics.get("downside_dscr"))
        short = down is not None and down < target - 1e-9
        revenue_gap = d.number_of(metrics.get("break_even_revenue"))
        base_revenue = d.number_of(metrics.get("base_revenue"))
        if short:
            negative_flow = (d.number_of(metrics.get("base_cash_flow")) or 0) <= 0 or (d.number_of(metrics.get("downside_cash_flow")) or 0) <= 0
            if negative_flow:
                recs.append(
                    {
                        "id": "operating",
                        "priority": 3,
                        "icon": "chart",
                        "title": "Fix operating economics first",
                        "why": (
                            f"Cash flow before debt service is {d.money(metrics.get('base_cash_flow'))} per year in the base case and "
                            f"{d.money(metrics.get('downside_cash_flow'))} in the downside case. "
                            "Changing the financing cannot fix that. More capital only pays for the losses."
                        ),
                        "basis": "Official base and downside views of the startup build.",
                        "detail": "",
                        "links": [
                            ("Test revenue in the worksheet", f"/assessments/{aid}/revenue-worksheet"),
                            ("Test costs in Improve feasibility", f"/assessments/{aid}/improve?target={target:g}&preset=lower_fixed#draft"),
                        ],
                        "caveat": "A change to your inputs is a projection. It does not change the official result until you run Analyze yourself.",
                    }
                )
            items = {item["id"]: item for item in improve.presets(base["inputs"], metrics, base["cash"], target, 0.25)}
            for rank, key in enumerate(_PRESET_ORDER):
                item = items.get(key)
                if not item or (key == "owner_cash" and negative_flow):
                    continue
                solved = bool(item["solved"])
                outcome = improve.build_scenario(
                    base,
                    {
                        "overrides": item["overrides"],
                        "cash": item["cash"],
                        "scale_with_size": bool(item["scale"]),
                        "derive_debt_from_cash": bool(item["derive"]),
                    },
                )
                result_metrics = outcome.get("metrics") or {}
                after = d.number_of(result_metrics.get("downside_dscr"))
                reaches = after is not None and after >= target - 1e-9
                if reaches:
                    caveat = f"Under your assumptions this gives {d.multiple(after)} downside coverage. "
                elif after is not None:
                    caveat = f"Under your assumptions this gives {d.multiple(after)} downside coverage, still below {d.multiple(target)}. "
                else:
                    caveat = ""
                recs.append(
                    {
                        "id": key,
                        "priority": 3.5 + rank * 0.1 if reaches else 5 + rank * 0.1,
                        "icon": "cost" if key in {"owner_cash", "lower_build", "smaller_venue"} else "chart",
                        "title": _PRESET_TITLES[key],
                        "why": item["basis"],
                        "basis": (
                            f"Your downside coverage is {d.multiple(down)}, below {d.multiple(target)}. "
                            + ("Solved with the same arithmetic as the engine." if solved else "A what-if, not a solved answer.")
                        ),
                        "detail": "",
                        "links": [("Try it in Improve feasibility", f"/assessments/{aid}/improve?target={target:g}&preset={key}#draft")],
                        "caveat": caveat + "That is a projection. It is not an official pass, and it does not clear any flag.",
                    }
                )
        if revenue_gap and base_revenue is not None and base_revenue < revenue_gap and not has_worksheet:
            share = base_revenue / revenue_gap if revenue_gap else None
            recs.append(
                {
                    "id": "revenue",
                    "priority": 4,
                    "icon": "seat",
                    "title": "Test revenue with seat turns",
                    "why": (
                        f"Base revenue of {d.money(base_revenue)} is {d.percent(share)} of break-even revenue of {d.money(revenue_gap)}. "
                        "The official formula allows one cover per occupied seat per day and has no service periods."
                    ),
                    "basis": "Official base and break-even revenue.",
                    "detail": "",
                    "links": [("Open the revenue worksheet", f"/assessments/{aid}/revenue-worksheet")],
                    "caveat": "A higher worksheet figure is a proposal and needs evidence. It does not change the official result.",
                }
            )
    else:
        financial = _financial(result)
        if financial:
            downside = d.number_of(financial.get("downside_monthly_cash_flow"))
            base_flow = d.number_of(financial.get("base_monthly_cash_flow"))
            if (downside is not None and downside <= 0) or (base_flow is not None and base_flow <= 0):
                recs.append(
                    {
                        "id": "operating",
                        "priority": 3,
                        "icon": "chart",
                        "title": "Improve operating economics",
                        "why": (
                            f"Base cash flow is {d.money(financial.get('base_monthly_cash_flow'), missing='not calculated')} per month "
                            f"and downside cash flow is {d.money(financial.get('downside_monthly_cash_flow'), missing='not calculated')} per month."
                        ),
                        "basis": "Monthly engine result.",
                        "detail": "",
                        "links": [("Review inputs in Explore", f"/assessments/{aid}")],
                        "caveat": "Changing an input does not change the official result until you run Analyze yourself.",
                    }
                )

    if startup and benchmark_entries == 0:
        recs.append(
            {
                "id": "sources",
                "priority": 6,
                "icon": "book",
                "title": "Add a source for the assumptions that matter most",
                "why": "No verified benchmark is on file, and none of your assumptions has a recorded source.",
                "basis": "Benchmarks on file.",
                "detail": "",
                "links": [("Open Benchmarks", f"/assessments/{aid}/benchmarks#record-figure")],
                "caveat": "A benchmark is context. It is not a target and it does not clear a flag.",
            }
        )
    return sorted(recs, key=lambda item: item["priority"])


def _recommendation_card(rec: dict[str, Any], number: int) -> str:
    links = "".join(
        f'<a class="dbtn dbtn-small" href="{escape(href)}">{escape(label)}</a>' for label, href in rec["links"]
    )
    detail = f'<details class="dmore dmore-tight"><summary>What the engine says to do</summary><p>{escape(rec["detail"])}</p></details>' if rec.get("detail") else ""
    return (
        '<article class="drec">'
        f'<div class="drec-n" aria-hidden="true">{number}</div>'
        '<div class="drec-body">'
        f'<h3>{_icon(rec["icon"])}{escape(rec["title"])}</h3>'
        f'<p>{escape(rec["why"])}</p>'
        f'<p class="muted"><strong>Based on:</strong> {escape(rec["basis"])}</p>'
        f"{detail}"
        f'<p class="drec-links">{links}</p>'
        f'<p class="muted drec-caveat">{escape(rec["caveat"])}</p>'
        "</div></article>"
    )


MAX_RECOMMENDATIONS = 6


def recommendations_html(recs: list[dict[str, Any]], legacy: str, aid: str = "") -> str:
    if recs:
        cards = "".join(_recommendation_card(rec, i) for i, rec in enumerate(recs[:MAX_RECOMMENDATIONS], 1))
        more = (
            f'<p class="muted">{len(recs) - MAX_RECOMMENDATIONS} more supported option{"s" if len(recs) - MAX_RECOMMENDATIONS != 1 else ""} '
            f'are on <a href="/assessments/{escape(aid)}/improve">Improve feasibility</a>.</p>'
            if len(recs) > MAX_RECOMMENDATIONS
            else ""
        )
        cards += more
        head = (
            '<p class="muted">Ordered by what the stored result supports. Each one links to the workflow that tests it. '
            "None is an instruction to proceed, and none changes the official result.</p>"
        )
    else:
        cards = '<div class="dcard"><p>The stored result does not support a specific recommendation yet. Run Analyze once the startup or monthly numbers are saved.</p></div>'
        head = ""
    return f"{head}{cards}{legacy}"


# ---------------------------------------------------------------------------
# Overview
# ---------------------------------------------------------------------------


def _facts(result: dict[str, Any]) -> str:
    from app.analysis import build_view_summary

    summary = build_view_summary(result)
    items = (
        ("Recommendation", str(summary.get("recommendation")), "recommendation"),
        ("Investor readiness", str(summary.get("investor_readiness")), "investor_readiness"),
        ("Human review", str(summary.get("human_review_status")), ""),
        ("Feasibility score", str(result.get("score_line") or "Not calculated"), "indicative_score"),
    )
    cells = []
    for label, value, term in items:
        help_html = _term_help(term) if term else ""
        cells.append(f'<div class="dfact"><dt>{escape(label)} {help_html}</dt><dd>{escape(value)}</dd></div>')
    return f'<dl class="dfacts">{"".join(cells)}</dl>'


def _gaps_list(result: dict[str, Any]) -> str:
    items = []
    for flag in [str(f) for f in result.get("blocking_flags") or []] + [str(f) for f in result.get("gap_flags") or []]:
        items.append(f'<li>{escape(_FLAG_SHORT.get(flag, flag))} <code>{escape(flag)}</code></li>')
    if not items:
        return '<p class="muted">The engine listed no gap flag on this result.</p>'
    shown = "".join(items[:5])
    extra = f'<li class="muted">{len(items) - 5} more in Recommendations.</li>' if len(items) > 5 else ""
    return f"<ul class=\"dgaps\">{shown}{extra}</ul>"


def _overview_kpis(result: dict[str, Any], aid: str) -> str:
    projection = _projection(result)
    cards = []
    if projection:
        uses = (projection.get("sources_and_uses") or {}).get("uses") or {}
        sources = (projection.get("sources_and_uses") or {}).get("sources") or {}
        base, downside, _be = _views(projection)
        cards = [
            _kpi("cost", "Total project cost", d.money(_amount(uses.get("total_project_cost")), missing="Not calculated"), "One-time, calculated", "#key-numbers", help_html=_metric_help("total_project_cost")),
            _kpi("loan", "Debt service", d.money(sources.get("annual_debt_service"), missing="Not calculated"), "per year, calculated", "#key-numbers", help_html=_metric_help("annual_debt_service")),
            _kpi("gauge", "Base coverage", d.multiple(base.get("dscr")), _coverage_note(base.get("dscr")), "#key-numbers", help_html=_metric_help("dscr"), tone=_tone(base.get("dscr"))),
            _kpi("gauge", "Downside coverage", d.multiple(downside.get("dscr")), _coverage_note(downside.get("dscr")), "#key-numbers", help_html=_metric_help("dscr"), tone=_tone(downside.get("dscr"))),
        ]
    else:
        financial = _financial(result)
        if financial:
            months = financial.get("months_to_break_even_base")
            cards = [
                _kpi("chart", "Base cash flow", d.money(financial.get("base_monthly_cash_flow"), missing="Not calculated"), "per month, calculated", "#key-numbers", help_html=_metric_help("monthly")),
                _kpi("chart", "Downside cash flow", d.money(financial.get("downside_monthly_cash_flow"), missing="Not calculated"), "per month, calculated", "#key-numbers", help_html=_metric_help("monthly")),
                _kpi("scale", "Break-even revenue", d.money(financial.get("break_even_monthly_revenue"), missing="Not calculated"), "per month, calculated", "#key-numbers", help_html=_metric_help("monthly")),
                _kpi("gauge", "Recover initial capital", d.decimal_text(months, 1, "months", missing="Not calculated"), "at the base cash-flow rate", "#key-numbers", help_html=_metric_help("monthly")),
            ]
    if not cards:
        return (
            '<div class="dcard"><h3>Financial summary</h3>'
            f'<p>{d.chip("missing", "Not calculated")} No financial figure was calculated. Missing inputs were not filled in, and a blank is not treated as zero.</p>'
            f'<p><a class="dbtn dbtn-small" href="/assessments/{aid}">Enter the missing numbers in Explore</a></p></div>'
        )
    return f'<div class="dkpis">{"".join(cards)}</div>'


def _tone(value: Any) -> str:
    number = d.number_of(value)
    if number is None:
        return ""
    return "bad" if number < improve.TARGETS[0] else "ok" if number >= improve.TARGETS[1] else "mid"


def _tiles(
    record: dict[str, Any],
    summary: dict[str, Any],
    scenario_count: int,
    worksheet_saved: bool,
    recs: list[dict[str, Any]],
    checklist: dict[str, Any],
) -> str:
    n_records = len(summary["records"])
    tiles = (
        ("benchmarks", "scale", "Benchmarks", "No verified benchmark available" if not summary["verified"] else f"{len(summary['verified'])} verified", f"{n_records} stored record{'s' if n_records != 1 else ''}"),
        ("revenue-model", "seat", "Revenue model", "Worksheet saved" if worksheet_saved else "No worksheet saved", "Proposal, not official"),
        ("scenarios", "layers", "Scenarios", f"{scenario_count} saved" if scenario_count else "None saved", "Projections, not approved"),
        ("recommendations", "bulb", "Recommendations", f"{min(len(recs), MAX_RECOMMENDATIONS)} supported" if recs else "None yet", f"{checklist['noted_or_recorded']} of {checklist['total']} evidence items noted"),
    )
    cells = "".join(
        f'<a class="dtile" href="#{key}" data-goto>{_icon(icon)}<span class="dtile-t">{escape(title)}</span>'
        f'<span class="dtile-v">{escape(value)}</span><span class="muted">{escape(sub)}</span></a>'
        for key, icon, title, value, sub in tiles
    )
    return f'<div class="dtiles">{cells}</div>'


def overview_html(
    record: dict[str, Any],
    result: dict[str, Any],
    status: dict[str, Any],
    *,
    summary: dict[str, Any],
    scenario_count: int,
    worksheet_saved: bool,
    recs: list[dict[str, Any]],
    checklist: dict[str, Any],
    next_step: str,
    standing: str,
    banner_extra: str,
) -> str:
    aid = _aid(record)
    chips = "".join(
        f'<span class="dpill dpill-{"warn" if i == 0 and status["tone"] == "warn" else "plain"}">{escape(label)}</span>'
        for i, label in enumerate(status["labels"])
    )
    primary = ""
    if status["primary"]:
        flag = escape(status["primary"])
        primary = (
            f'<p class="dreason"><strong>Primary reason:</strong> {escape(status["reason"])} <code>{flag}</code></p>'
        )
        if status["action"]:
            primary += (
                '<details class="dmore dmore-tight"><summary>What would address it</summary>'
                f'<p>{escape(status["action"])}</p><p class="muted">Doing this does not clear the flag by itself. An authorized review is still required.</p></details>'
            )
    top_recs = "".join(_recommendation_mini(rec) for rec in recs[:3]) or '<p class="muted">No supported recommendation yet.</p>'
    return f"""
<section class="dstatus">
  <div class="dstatus-main">
    <p class="deyebrow">{_icon("shield")} Assessment status</p>
    <p class="dlabel">{chips}</p>
    {primary}
    <p class="dstanding" role="note">{escape(standing)}</p>
    {banner_extra}
  </div>
  {_facts(result)}
</section>
{_overview_kpis(result, aid)}
{_tiles(record, summary, scenario_count, worksheet_saved, recs, checklist)}
<div class="dgrid2">
  <div class="dcard"><h3>Evidence gaps</h3>{_gaps_list(result)}
    <p><a href="#recommendations" data-goto>See what would address them</a></p></div>
  <div class="dcard"><h3>Top recommendations</h3>{top_recs}
    <p><a href="#recommendations" data-goto>All recommendations</a></p></div>
</div>
<div class="dcard dnext"><h3>{_icon("book")} Your next step</h3><p>{escape(next_step)}</p>
  <p class="muted">Completing a step does not clear a hard gate, change the recommendation, or make the file investor-ready.</p></div>
"""


def _recommendation_mini(rec: dict[str, Any]) -> str:
    href = rec["links"][0][1] if rec["links"] else "#recommendations"
    return (
        f'<p class="dmini"><a href="{escape(href)}"><strong>{escape(rec["title"])}</strong></a><br>'
        f'<span class="muted">{escape(rec["why"][:160])}{"…" if len(rec["why"]) > 160 else ""}</span></p>'
    )


# ---------------------------------------------------------------------------
# Page assembly
# ---------------------------------------------------------------------------


def render(
    record: dict[str, Any],
    result: dict[str, Any],
    *,
    context: dict[str, Any],
    startup_missing: list[str],
    checklist: dict[str, Any],
    next_step: str,
    standing: str,
    legacy: dict[str, str],
) -> str:
    aid = _aid(record)
    entries = list(context.get("benchmark_entries") or [])
    worksheet_record = context.get("worksheet")
    scenario_records = list(context.get("scenarios") or [])
    status = status_summary(result, startup_missing)
    bench = benchmark_summary(record, entries)
    recs = build_recommendations(
        record,
        result,
        has_worksheet=bool(worksheet_record),
        benchmark_entries=len(entries),
    )
    profile = record.get("profile") or {}
    panels = {
        "overview": overview_html(
            record,
            result,
            status,
            summary=bench,
            scenario_count=len(scenario_records),
            worksheet_saved=bool(worksheet_record),
            recs=recs,
            checklist=checklist,
            next_step=next_step,
            standing=standing,
            banner_extra=legacy.get("banner_extra", ""),
        ),
        "key-numbers": key_numbers_html(result, profile, startup_missing, legacy.get("tables", "")),
        "benchmarks": benchmarks_html(record, bench),
        "revenue-model": revenue_html(record, result, worksheet_record),
        "scenarios": scenarios_html(record, scenario_records, legacy.get("scenarios", "")),
        "recommendations": recommendations_html(recs, legacy.get("recommendations", ""), str(record.get("id") or "")),
    }
    tabs = "".join(
        f'<a href="#{key}" data-tab="{key}"{" aria-current=\"true\"" if key == "overview" else ""}>{escape(label)}</a>'
        for key, label in SECTIONS
    )
    sections = "".join(
        f'<section class="dpanel" id="{key}" data-panel="{key}" aria-labelledby="{key}-h">'
        f'<h2 id="{key}-h" class="dpanel-h">{escape(label)}</h2>{panels[key]}</section>'
        for key, label in SECTIONS
    )
    goto = (
        '<nav class="dgoto no-print" aria-label="Related workspaces">'
        f'<a href="/assessments/{aid}">Explore</a>'
        f'<a href="/assessments/{aid}/intelligence">Research</a>'
        f'<a href="/assessments/{aid}/revenue-worksheet">Revenue worksheet</a>'
        f'<a href="/assessments/{aid}/benchmarks">Benchmarks</a>'
        f'<a href="/assessments/{aid}/improve">Improvement scenarios</a>'
        f'<a href="/assessments/{aid}/reports">Reports</a>'
        "</nav>"
    )
    return f"""{STYLE}
<div class="dash" id="analyze-dashboard">
<header class="dhead">
  <h1>Results for {escape(str(record.get("business_name") or ""))}</h1>
  {goto}
</header>
<nav class="dtabs no-print" id="dash-tabs" aria-label="Analyze sections">{tabs}</nav>
{sections}
{legacy.get("more", "")}
</div>
{SCRIPT}"""


STYLE = """<style>
main:has(.dash) { max-width: 1180px; }
.dash { --card: #FFFEFB; --line: #E4DFD3; --soft: #FBF9F4; --sub: #5c6b76; --bad: #8a3030; --ok: #2e6b3a; }
.dash h1 { font-size: 1.75rem; margin: 0 0 0.4rem; }
.dash h2.dpanel-h { border: 0; margin: 0 0 0.8rem; font-size: 1.3rem; padding: 0; }
.dash h3 { margin: 0 0 0.5rem; font-size: 1.02rem; display: flex; align-items: center; gap: 0.45rem; flex-wrap: wrap; }
.dash .muted { color: var(--sub); }
.dash code { font-size: 0.78rem; background: var(--soft); border: 1px solid var(--line); border-radius: 6px; padding: 0.05rem 0.35rem; overflow-wrap: anywhere; }
.dicon { flex: 0 0 auto; color: var(--bronze); }
.dhead { display: flex; flex-wrap: wrap; gap: 0.4rem 1.2rem; align-items: baseline; justify-content: space-between; }
.dgoto { display: flex; flex-direction: row; flex-wrap: wrap; gap: 0.25rem 0.9rem; padding: 0; font-size: 0.88rem; }
.dgoto a { color: var(--ink); text-decoration: none; border: 0; border-bottom: 1px solid var(--line); padding: 0.1rem 0; }
.dgoto a:hover { background: transparent; border-bottom-color: var(--bronze); }
.dtabs { position: sticky; top: 0; z-index: 4; display: flex; flex-direction: row; flex-wrap: nowrap; gap: 0.3rem; overflow-x: auto; background: var(--ivory); padding: 0.55rem 0; margin: 0.6rem 0 1rem; border-bottom: 1px solid var(--line); scrollbar-width: thin; }
.dtabs a { flex: 0 0 auto; text-decoration: none; color: var(--ink); background: var(--card); border: 1px solid var(--line); border-radius: 999px; padding: 0.45rem 1rem; font-weight: 500; font-size: 0.93rem; white-space: nowrap; }
.dtabs a:hover { background: #F1E9D8; }
.dtabs a[aria-current="true"] { background: var(--ink); color: #fff; border-color: var(--ink); }
.js-dash .dpanel[hidden] { display: none; }
.dpanel { margin-bottom: 1.4rem; scroll-margin-top: 4rem; }
.js-dash .dpanel-h { position: absolute; width: 1px; height: 1px; overflow: hidden; clip: rect(0 0 0 0); }
.dcard, .dstatus, .dk, .dtile, .drec { background: var(--card); border: 1px solid var(--line); border-radius: 16px; }
.dcard { padding: 1rem 1.15rem; margin: 0 0 0.9rem; }
.dcard p { margin: 0.35rem 0; }
.dstatus { display: grid; grid-template-columns: minmax(0, 1.5fr) minmax(0, 1fr); gap: 1.2rem; padding: 1.25rem 1.4rem; margin-bottom: 0.9rem; border-top: 4px solid var(--bronze); }
.deyebrow { display: flex; align-items: center; gap: 0.4rem; margin: 0 0 0.3rem; font-size: 0.74rem; letter-spacing: 0.07em; text-transform: uppercase; color: #6f5a33; font-weight: 600; }
.dlabel { display: flex; flex-wrap: wrap; gap: 0.4rem; margin: 0.2rem 0 0.5rem; }
.dpill { display: inline-block; border-radius: 999px; padding: 0.3rem 0.85rem; font-weight: 600; font-size: 0.95rem; background: var(--soft); border: 1px solid var(--line); }
.dpill-warn { background: #F6E7CB; border-color: #D9BE88; color: #5b4519; font-size: 1.1rem; }
.dreason { margin: 0.35rem 0; }
.dstanding { background: var(--soft); border-left: 4px solid var(--bronze); border-radius: 0 10px 10px 0; padding: 0.55rem 0.8rem; margin: 0.7rem 0 0; font-size: 0.92rem; }
.dfacts { display: grid; grid-template-columns: 1fr 1fr; gap: 0.6rem; margin: 0; align-content: start; }
.dfact { background: var(--soft); border: 1px solid var(--line); border-radius: 12px; padding: 0.55rem 0.7rem; }
.dfact dt { font-size: 0.76rem; color: var(--sub); display: flex; align-items: center; gap: 0.3rem; flex-wrap: wrap; }
.dfact dd { margin: 0.15rem 0 0; font-weight: 600; overflow-wrap: anywhere; }
.dkpis { display: grid; grid-template-columns: repeat(auto-fit, minmax(13rem, 1fr)); gap: 0.7rem; margin: 0 0 0.9rem; }
.dk { padding: 0.85rem 1rem; }
.dk-head { display: flex; align-items: center; gap: 0.4rem; color: var(--sub); font-size: 0.86rem; }
.dk-label { flex: 1; }
.dk-value { font-size: 1.65rem; font-weight: 650; letter-spacing: -0.02em; margin: 0.3rem 0 0.1rem; overflow-wrap: anywhere; }
.dk-sub { margin: 0; font-size: 0.82rem; color: var(--sub); }
.dk-link { font-size: 0.82rem; color: var(--ink); }
.dk-bad .dk-value { color: var(--bad); }
.dk-ok .dk-value { color: var(--ok); }
.dtiles { display: grid; grid-template-columns: repeat(auto-fit, minmax(12rem, 1fr)); gap: 0.7rem; margin: 0 0 0.9rem; }
.dtile { display: flex; flex-direction: column; gap: 0.15rem; padding: 0.85rem 1rem; text-decoration: none; color: var(--ink); }
.dtile:hover { border-color: var(--bronze); background: #FBF6EA; }
.dtile-t { font-weight: 600; }
.dtile-v { font-size: 0.93rem; }
.dgrid2 { display: grid; grid-template-columns: repeat(auto-fit, minmax(19rem, 1fr)); gap: 0.9rem; align-items: start; }
.dgaps { margin: 0.2rem 0; padding-left: 1.1rem; }
.dgaps li { margin: 0.3rem 0; }
.dmini { margin: 0.5rem 0; }
.dnext { border-left: 4px solid var(--bronze); }
.dh { display: inline; margin: 0; }
.dh > summary { list-style: none; cursor: pointer; display: inline-flex; align-items: center; justify-content: center; width: 1.35rem; height: 1.35rem; border-radius: 50%; border: 1.5px solid #8c7a55; background: #fff; color: #6f5a33; font-size: 0.78rem; font-weight: 700; line-height: 1; }
.dh > summary::-webkit-details-marker { display: none; }
.dh[open] > summary, .dh > summary:hover { background: #F1E9D8; }
.dh-body { display: block; flex-basis: 100%; margin: 0.5rem 0 0.2rem; padding: 0.7rem 0.95rem; background: var(--soft); border: 1px solid var(--line); border-radius: 12px; font-size: 0.88rem; font-weight: 400; color: #33434f; text-align: left; letter-spacing: 0; white-space: normal; }
.dh-body p { margin: 0.35rem 0; }
.dh-title { font-weight: 650; }
.dk .dh[open] { display: block; flex-basis: 100%; }
.dtable { overflow-x: auto; margin: 0.4rem 0; }
.dtable table { margin: 0; min-width: 18rem; font-size: 0.9rem; background: transparent; }
.dtable th, .dtable td { padding: 0.4rem 0.55rem; border-bottom: 1px solid var(--line); vertical-align: top; }
.dtable thead th { background: var(--ink); color: #fff; font-weight: 600; }
.dtable tbody th { background: transparent; color: var(--ink); font-weight: 500; text-align: left; }
.dtable tr:nth-child(even) td { background: transparent; }
.dtable .num { text-align: right; white-space: nowrap; }
.dchip { display: inline-block; font-size: 0.7rem; padding: 0.02rem 0.45rem; border-radius: 999px; border: 1px solid var(--line); background: var(--soft); color: #4d5b66; margin-left: 0.25rem; vertical-align: middle; white-space: nowrap; }
.dchip-calculated { background: #E8EFF3; border-color: #C5D3DC; }
.dchip-placeholder, .dchip-missing { background: #F6E7CB; border-color: #D9BE88; color: #5b4519; }
.dchip-zero { background: #EEEAE0; }
.dchip-benchmark { background: #EFE9F4; border-color: #D3C6DF; }
.dtag { display: inline-block; font-size: 0.74rem; padding: 0.05rem 0.5rem; margin: 0 0.3rem 0.2rem 0; background: var(--stone); border-radius: 999px; }
.dtag-warn { background: #f1dcc0; }
.dtag-bad { background: #e8c4c4; }
.dbars { margin: 0.6rem 0 0.2rem; }
.dbar { display: grid; grid-template-columns: minmax(6.5rem, 9rem) minmax(0, 1fr) minmax(4.5rem, auto); gap: 0.6rem; align-items: center; margin: 0.35rem 0; font-size: 0.86rem; }
.dbar-t { position: relative; height: 0.85rem; background: #F0ECE2; border-radius: 999px; overflow: hidden; }
.dbar-fill { position: absolute; top: 0; bottom: 0; background: var(--bronze); border-radius: 999px; }
.dbar-neg { background: #b04a4a; }
.dbar-zero { position: absolute; top: 0; bottom: 0; width: 1px; background: #8a8577; z-index: 1; }
.dbar-ref { position: absolute; top: -2px; bottom: -2px; border-left: 2px dashed var(--ink); z-index: 2; }
.dbar-v { text-align: right; font-weight: 600; white-space: nowrap; }
.dbar-none { background: transparent; border: 1px dashed var(--line); }
.dbar-note { font-size: 0.8rem; margin: 0.3rem 0 0; }
.dbig { font-size: 1.6rem; font-weight: 650; margin: 0.2rem 0; overflow-wrap: anywhere; }
.dnote { background: var(--soft); border-left: 4px solid var(--bronze); border-radius: 0 10px 10px 0; padding: 0.5rem 0.8rem; font-size: 0.9rem; }
.dverdict { display: flex; gap: 0.7rem; align-items: flex-start; background: #F6E7CB; border: 1px solid #D9BE88; border-radius: 14px; padding: 0.8rem 1rem; margin: 0 0 0.9rem; }
.dverdict-ok { background: #E4F0E6; border-color: #B7D3BC; }
.dbm { border-top: 1px solid var(--line); padding: 0.65rem 0; }
.dbm:first-of-type { border-top: 0; }
.dbm p { margin: 0.2rem 0; }
.dbm-top { display: flex; justify-content: space-between; gap: 0.8rem; flex-wrap: wrap; }
.dbm-val { font-weight: 650; }
.dactions { display: flex; flex-wrap: wrap; gap: 0.5rem; margin: 0.4rem 0 1rem; }
.dbtn { display: inline-block; text-decoration: none; background: var(--ink); color: #fff; border-radius: 999px; padding: 0.55rem 1.1rem; font-size: 0.92rem; margin: 0; }
.dbtn:hover { background: #34495a; color: #fff; }
.dbtn-ghost { background: var(--card); color: var(--ink); border: 1px solid #cfc9bb; }
.dbtn-ghost:hover { background: #F1E9D8; color: var(--ink); }
.dbtn-small { padding: 0.35rem 0.85rem; font-size: 0.85rem; margin: 0 0.4rem 0.3rem 0; }
.drec { display: flex; gap: 0.9rem; padding: 0.95rem 1.1rem; margin: 0 0 0.8rem; }
.drec-n { flex: 0 0 2rem; height: 2rem; border-radius: 50%; background: var(--ink); color: #fff; display: grid; place-items: center; font-weight: 600; }
.drec-body { min-width: 0; flex: 1; }
.drec-body p { margin: 0.3rem 0; }
.drec-caveat { font-size: 0.82rem; }
.dmore { background: var(--card); border: 1px solid var(--line); border-radius: 14px; padding: 0.2rem 1rem; margin: 0.9rem 0; }
.dmore > summary { cursor: pointer; padding: 0.6rem 0; font-weight: 600; }
.dmore-tight { border: 0; background: transparent; padding: 0; margin: 0.3rem 0; }
.dmore-tight > summary { padding: 0.2rem 0; font-weight: 500; font-size: 0.9rem; color: #4d5b66; }
@media (max-width: 800px) {
  .dstatus { grid-template-columns: 1fr; padding: 1rem; }
  .dbar { grid-template-columns: 1fr minmax(4rem, auto); }
  .dbar-t { grid-column: 1 / -1; grid-row: 2; }
  .dbar-v { grid-row: 1; grid-column: 2; }
  .drec { padding: 0.8rem; }
  .dk-value { font-size: 1.4rem; }
}
@media print {
  .dtabs, .dgoto { display: none !important; }
  .js-dash .dpanel[hidden] { display: block; }
  .js-dash .dpanel-h { position: static; width: auto; height: auto; clip: auto; }
}
</style>"""

SCRIPT = """<script>
(function () {
  var root = document.getElementById('analyze-dashboard');
  if (!root) { return; }
  var tabs = Array.prototype.slice.call(root.querySelectorAll('#dash-tabs a[data-tab]'));
  var panels = Array.prototype.slice.call(root.querySelectorAll('.dpanel'));
  var ids = panels.map(function (p) { return p.id; });
  document.documentElement.classList.add('js-dash');
  function panelFor(hash) {
    var id = (hash || '').replace(/^#/, '');
    if (!id) { return { panel: 'overview', anchor: '' }; }
    if (ids.indexOf(id) >= 0) { return { panel: id, anchor: '' }; }
    var el = document.getElementById(id);
    var host = el && el.closest ? el.closest('.dpanel') : null;
    return host ? { panel: host.id, anchor: id } : { panel: 'overview', anchor: '' };
  }
  function show(hash, fromUser) {
    var target = panelFor(hash);
    panels.forEach(function (p) { p.hidden = p.id !== target.panel; });
    tabs.forEach(function (t) {
      if (t.getAttribute('data-tab') === target.panel) {
        t.setAttribute('aria-current', 'true');
        var bar = t.parentNode;
        if (bar && bar.scrollWidth > bar.clientWidth) { bar.scrollLeft = Math.max(0, t.offsetLeft - 12); }
      }
      else { t.removeAttribute('aria-current'); }
    });
    var scrollTo = target.anchor ? document.getElementById(target.anchor) : null;
    if (scrollTo) { scrollTo.scrollIntoView(); }
    else if (fromUser) { root.scrollIntoView(); }
  }
  window.addEventListener('hashchange', function () { show(location.hash, true); });
  root.addEventListener('click', function (event) {
    var link = event.target.closest ? event.target.closest('a[data-tab], a[data-goto]') : null;
    if (!link) { return; }
    var href = link.getAttribute('href') || '';
    if (href.charAt(0) !== '#') { return; }
    event.preventDefault();
    if (location.hash === href) { show(href, true); } else { location.hash = href; }
  });
  show(location.hash, false);
}());
</script>"""

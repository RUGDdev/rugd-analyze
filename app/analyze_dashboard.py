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

from app import benchmarks, improve, ui, wording
from app import display as d
from app import revenue_worksheet as rw
from app.plain import TERMS
from app.ui import bars as _bars
from app.ui import help_tip
from app.ui import icon as _icon
from app.ui import kpi as _kpi
from app.ui import table as _table
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

_FLAG_SHORT = {code: item.title for code, item in wording.FINDINGS.items()}

def _aid(record: dict[str, Any]) -> str:
    return escape(str(record.get("id") or ""))


# ---------------------------------------------------------------------------
# Help controls
# ---------------------------------------------------------------------------


_ENGINE = "Calculated by RUGD's analysis from the numbers you entered."
_YOURS = "Each input is your own estimate unless you attached a quote or a measurement."

METRIC_HELP: dict[str, dict[str, str]] = {
    "total_project_cost": {
        "title": "Total project cost",
        "means": "All the money the opening needs: build, equipment, soft costs, working capital, and a contingency.",
        "how": "The five uses added together. Contingency is your contingency percentage times the other four.",
        "source": _ENGINE,
        "assumptions": _YOURS + " Contingency may still be a standard starting number.",
        "limits": "It is not a contractor quote and leaves out any cost you did not enter.",
    },
    "debt": {
        "title": "Debt",
        "means": "The part of the project paid for by borrowing.",
        "how": "Debt share times total project cost.",
        "source": _ENGINE,
        "assumptions": "The debt share is your estimate or a standard starting number.",
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
        "assumptions": "Interest rate and repayment years are your estimates or standard starting numbers.",
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
        "assumptions": "The weaker-year factor is yours or a standard starting number.",
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
        "title": "Loan coverage (DSCR)",
        "means": "How many times cash flow covers the yearly loan payment. Below 1.00× means it does not cover it. A negative number means cash flow itself is negative.",
        "how": "Cash flow before debt service divided by yearly debt service.",
        "source": _ENGINE,
        "assumptions": "RUGD pages compare it with 1.00× (readiness default) and 1.25× (lender oriented).",
        "limits": "A lender sets its own test. Meeting a ratio does not by itself settle anything else on the assessment.",
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


METRIC_WHY: dict[str, tuple[str, str]] = {
    "total_project_cost": (
        "It is the amount you have to raise or borrow before the doors open.",
        "Check each cost against a quote. Costs you have not entered are left out.",
    ),
    "debt": (
        "Borrowed money has to be paid back with interest, whatever sales turn out to be.",
        "Ask a lender what you could really borrow. Change the borrowing share in Explore.",
    ),
    "equity": (
        "Lenders expect you to put in your own money and share the risk.",
        "Check how much you can really put in, and keep a bank statement or commitment ready.",
    ),
    "annual_debt_service": (
        "These payments come out of the business's cash every year.",
        "If they look too high, test a longer repayment term or less borrowing in Improve.",
    ),
    "base_revenue": (
        "Everything else in the plan depends on this sales estimate.",
        "Test it in the revenue worksheet, and back it up with a similar business's sales.",
    ),
    "downside_revenue": (
        "Plans should survive a weaker year, not only a good one.",
        "Check that the loan could still be paid at this level.",
    ),
    "cash_flow": (
        "It is the money left to pay the loan and to keep the business going.",
        "If it is low or negative, test higher sales or lower costs in Improve.",
    ),
    "dscr": (
        "Below 1.00× the cash does not cover the loan. Lenders often want about 1.25× or more.",
        "If it is low, test lower costs, higher sales, a smaller project, or more of your own money in Improve.",
    ),
    "break_even": (
        "If your expected sales are below it, the business loses money.",
        "Compare it with your expected sales, then test ways to raise sales or cut costs.",
    ),
    "monthly": (
        "It shows whether an ordinary month leaves cash, and how a weak month would look.",
        "Check the four monthly figures behind it. Replace estimates with real records.",
    ),
}


def _metric_help(key: str) -> str:
    matters, todo = METRIC_WHY.get(key, ("", ""))
    return help_tip(matters=matters, todo=todo, **METRIC_HELP[key])


def _term_help(key: str) -> str:
    item = TERMS[key]
    return help_tip(
        item["term"],
        means=item["plain"],
        how="Read from the stored result. It is not recalculated on this page.",
        source="The official analysis for this draft.",
        assumptions="",
        limits=item["precise"],
        matters=item["matters"],
        todo=item["todo"],
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
        labels.append("Customer evidence needed")
    other = [flag for flag in blocking if flag not in {rules.FLAG_DEMAND, rules.FLAG_DEMAND_UNVERIFIED}]
    if other:
        labels.append("A serious concern is on file")
    if rules.FLAG_FINANCIALS_UNMEASURED in gaps or startup_missing:
        labels.append("Some figures are still estimates")
    if str(result.get("human_review_status") or "pending") != "approved" or not result.get("human_review_approved"):
        labels.append("Waiting for an authorized review")
    if not labels:
        labels.append("Review recorded")
    primary = blocking[0] if blocking else (gaps[0] if gaps else "")
    reason = wording.finding(primary).found if primary else ""
    return {
        "label": labels[0],
        "tone": "warn" if blocking or "Some figures are still estimates" in labels else "plain",
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
        ["Case (per year)", "Revenue", "Cash left before loan payments", "Loan coverage"],
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
        ("Typical year", d.number_of(base.get("dscr")), base_dscr),
        ("Weaker year", d.number_of(downside.get("dscr")), down_dscr),
    ]
    coverage_chart = _bars(
        chart_rows,
        reference=(improve.TARGETS[0], f"{d.multiple(improve.TARGETS[0])} readiness default"),
        unit_label=f"Dashed line: {d.multiple(improve.TARGETS[0])} (readiness default). Coverage is a ratio, not a score.",
    )
    revenue_chart = _bars(
        [
            ("Weaker-year revenue", d.number_of(downside.get("revenue")), d.money(downside.get("revenue"), missing="Not calculated")),
            ("Typical-year revenue", d.number_of(base.get("revenue")), d.money(base.get("revenue"), missing="Not calculated")),
            ("Break-even revenue", d.number_of(break_even.get("revenue")), d.money(break_even.get("revenue"), missing="Not calculated")),
        ],
        unit_label="Yearly amounts worked out by RUGD.",
    )
    return f"""
<div class="dgrid2">
  <div class="dcard"><h3>Uses of money {_metric_help('total_project_cost')}</h3>{_table(['Use', 'Amount'], _uses_rows(projection, profile))}</div>
  <div class="dcard"><h3>Sources and financing</h3>{_table(['Source', 'Amount'], _sources_rows(projection, profile))}
  <p class="muted">Loan terms here are your estimates or standard starting numbers. A lender sets the real terms.</p></div>
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
            f'<p>{d.chip("missing", "Not calculated")} RUGD could not work out the startup costs yet.'
            f"{(' Still needed: ' + escape(missing) + '.') if missing else ''} Nothing was filled in for you.</p></div>"
        )
    parts.append(_monthly_block(_financial(result), startup_ran=bool(projection)))
    parts.append(
        '<details class="dmore"><summary>Detailed tables and charts (for advisers)</summary>'
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
    "higher_ticket": "Raise the average spend per guest",
    "lower_fixed": "Lower the yearly fixed costs",
    "longer_term": "Revisit the loan terms",
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
                "title": "Show that customers will buy",
                "why": wording.finding(flag).found,
                "matters": wording.finding(flag).matters,
                "do": wording.finding(flag).todo,
                "basis": f"The saved results list this as open: {wording.title_of(flag).lower()}.",
                "detail": rules.NEXT_ACTIONS[flag],
                "links": [
                    ("Save evidence in Research", f"/assessments/{aid}/intelligence"),
                    ("Evidence checklist", f"/assessments/{aid}/results#evidence-checklist-{aid}"),
                ],
                "caveat": "Adding evidence does not lift this by itself. A verified demand record and an authorized review do.",
            }
        )
    unevaluated = [flag for flag in gaps if flag.startswith("UNEVALUATED")]
    if unevaluated:
        recs.append(
            {
                "id": "criteria",
                "priority": 7,
                "icon": "layers",
                "title": "Answer the questions still open",
                "why": "; ".join(_FLAG_SHORT[flag] for flag in unevaluated) + ".",
                "matters": "These are among the first things a reviewer checks, and a blank answer is not treated as a good one.",
                "do": "Answer each question in Explore, even if the answer is that a problem exists.",
                "basis": "Questions not yet answered: " + ", ".join(unevaluated) + ".",
                "detail": "",
                "links": [("Answer in Explore", f"/assessments/{aid}")],
                "caveat": "Recording an answer does not by itself change the official recommendation.",
            }
        )

    base = improve.base_inputs(profile)
    startup = not base["missing"]
    placeholders = [improve.LABELS[key] for key in base["placeholders"]] if startup else []
    if rules.FLAG_FINANCIALS_UNMEASURED in gaps or placeholders:
        why = "The money figures are your own estimates, not quotes or records."
        if placeholders:
            why += " Still blank or using a standard starting number: " + ", ".join(placeholders) + "."
        recs.append(
            {
                "id": "assumptions",
                "priority": 2,
                "icon": "cost",
                "title": "Replace estimates with quotes or records",
                "why": why,
                "matters": "Estimates can be far off. Quotes and records make every result on this page more reliable.",
                "do": "Start with the biggest costs and your sales estimate. Enter contractor quotes, supplier prices, or real sales.",
                "basis": "The saved results list your costs and revenue as still estimates." if rules.FLAG_FINANCIALS_UNMEASURED in gaps else "Your entries.",
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
                        "title": "Make the business earn more than it costs first",
                        "why": (
                            f"Before loan payments, the business keeps {d.money(metrics.get('base_cash_flow'))} a year in a typical year and "
                            f"{d.money(metrics.get('downside_cash_flow'))} in a weaker year. "
                        ),
                        "matters": "Better financing cannot fix this. More money only pays for the losses.",
                        "do": "Test higher sales or lower yearly costs, and see which change closes the gap.",
                        "basis": "The typical-year and weaker-year views of the startup numbers.",
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
                        "matters": f"Loan coverage in a weaker year is {d.multiple(down)}. Lenders often want at least {d.multiple(target)}.",
                        "do": "Try it in Improve, compare it with your current plan, and keep the change only if you can really do it.",
                        "basis": (
                            f"Your weaker-year loan coverage is {d.multiple(down)}, below {d.multiple(target)}. "
                            + ("Worked out with the same arithmetic as the official analysis." if solved else "A what-if, not a solved answer.")
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
                    "title": "Test how often your seats can be filled",
                    "why": (
                        f"Expected yearly sales of {d.money(base_revenue)} are {d.percent(share)} of the {d.money(revenue_gap)} needed to break even. "
                        "The official calculation counts one guest per seat per day, with no separate lunch and dinner."
                    ),
                    "matters": "If real sales could be higher, the picture changes. If not, the plan needs a different shape.",
                    "do": "Use the revenue worksheet to count service periods and days open, then back the figures with a similar business.",
                    "basis": "Typical-year sales and sales needed to break even.",
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
                        "title": "Improve what the business earns each month",
                        "why": (
                            f"In a typical month the business keeps {d.money(financial.get('base_monthly_cash_flow'), missing='not calculated')} "
                            f"and in a weaker month {d.money(financial.get('downside_monthly_cash_flow'), missing='not calculated')}."
                        ),
                        "matters": "A business that keeps little or nothing each month has no room for surprises or growth.",
                        "do": "Check the four monthly figures, then look for higher sales or lower fixed costs.",
                        "basis": "The monthly view of your numbers.",
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
                "title": "Add a source for the numbers that matter most",
                "why": "No verified benchmark is on file, and none of your assumptions has a recorded source.",
                "matters": "A named source makes a number believable to a lender, an investor, or a reviewer.",
                "do": "Pick two or three key numbers, such as average spending per guest, and record where each comes from.",
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
    detail = (
        '<details class="techref"><summary>Technical reference</summary>'
        f"<p><strong>The official record says.</strong> {escape(rec['detail'])}</p></details>"
        if rec.get("detail")
        else ""
    )
    matters = f'<p><strong>Why it matters.</strong> {escape(rec["matters"])}</p>' if rec.get("matters") else ""
    todo = f'<p><strong>What to do.</strong> {escape(rec["do"])}</p>' if rec.get("do") else ""
    fine_print = ui.details(
        "How this was worked out",
        f'<p><strong>Based on.</strong> {escape(rec["basis"])}</p>{detail}<p class="muted">{escape(rec["caveat"])}</p>',
        tight=True,
    )
    return (
        '<article class="drec">'
        f'<div class="drec-n" aria-hidden="true">{number}</div>'
        '<div class="drec-body">'
        f'<h3>{_icon(rec["icon"])}{escape(rec["title"])}</h3>'
        f'<p><strong>What RUGD found.</strong> {escape(rec["why"])}</p>'
        f"{matters}{todo}"
        f'<p class="drec-links"><span class="dlabel-s">Where to go</span>{links}</p>'
        f"{fine_print}"
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
            '<p class="muted">Most important first. Each one links to the page where you can act on it. '
            "These are suggestions to test, not approvals, and none changes the official result.</p>"
        )
    else:
        cards = f'<div class="dcard"><p>There is nothing specific to suggest yet. Enter the startup or monthly numbers in <a href="/assessments/{escape(aid)}">Explore</a> and run Analyze to get suggestions.</p></div>'
        head = ""
    return f"{head}{cards}{legacy}"


# ---------------------------------------------------------------------------
# Overview
# ---------------------------------------------------------------------------


def _facts(result: dict[str, Any]) -> str:
    from app.analysis import build_view_summary

    summary = build_view_summary(result)
    raw = (
        ("Draft recommendation", str(summary.get("recommendation"))),
        ("Readiness to show investors", str(summary.get("investor_readiness"))),
        ("Expert review", str(summary.get("human_review_status"))),
        ("Overall score", str(result.get("score_line") or "Not calculated")),
    )
    items = (
        ("Draft recommendation", wording.recommendation_label(raw[0][1]), "recommendation"),
        ("Ready to show investors?", wording.readiness_label(raw[1][1]), "investor_readiness"),
        ("Expert review", wording.review_label(raw[2][1]), ""),
        ("Overall score", wording.score_words(raw[3][1]), "indicative_score"),
    )
    cells = []
    for label, value, term in items:
        help_html = _term_help(term) if term else ""
        cells.append(f'<div class="dfact"><dt>{escape(label)} {help_html}</dt><dd>{escape(value)}</dd></div>')
    reference = wording.tech_ref(*[f"{label}: {value}" for label, value in raw])
    return f'<dl class="dfacts">{"".join(cells)}</dl>{reference}'


def _gaps_list(result: dict[str, Any], aid: str = "") -> str:
    items = []
    for flag in [str(f) for f in result.get("blocking_flags") or []] + [str(f) for f in result.get("gap_flags") or []]:
        links = wording.links_for(flag, aid) if aid else []
        go = f' <a class="dgap-go" href="{escape(links[0][1])}">{escape(links[0][0])}</a>' if links else ""
        items.append(f"<li>{escape(wording.title_of(flag))}{go}</li>")
    if not items:
        return '<p class="muted">Nothing is listed as missing on this result.</p>'
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
            _kpi("cost", "Total project cost", d.money(_amount(uses.get("total_project_cost")), missing="Not calculated"), "one-time, calculated by RUGD", "#key-numbers", help_html=_metric_help("total_project_cost")),
            _kpi("loan", "Loan payments", d.money(sources.get("annual_debt_service"), missing="Not calculated"), "per year, calculated by RUGD", "#key-numbers", help_html=_metric_help("annual_debt_service")),
            _kpi("gauge", "Loan coverage, typical year", d.multiple(base.get("dscr")), _coverage_note(base.get("dscr")), "#key-numbers", help_html=_metric_help("dscr"), tone=_tone(base.get("dscr"))),
            _kpi("gauge", "Loan coverage, weaker year", d.multiple(downside.get("dscr")), _coverage_note(downside.get("dscr")), "#key-numbers", help_html=_metric_help("dscr"), tone=_tone(downside.get("dscr"))),
        ]
    else:
        financial = _financial(result)
        if financial:
            months = financial.get("months_to_break_even_base")
            cards = [
                _kpi("chart", "Base cash flow", d.money(financial.get("base_monthly_cash_flow"), missing="Not calculated"), "per month, calculated by RUGD", "#key-numbers", help_html=_metric_help("monthly")),
                _kpi("chart", "Downside cash flow", d.money(financial.get("downside_monthly_cash_flow"), missing="Not calculated"), "per month, calculated by RUGD", "#key-numbers", help_html=_metric_help("monthly")),
                _kpi("scale", "Break-even revenue", d.money(financial.get("break_even_monthly_revenue"), missing="Not calculated"), "per month, calculated by RUGD", "#key-numbers", help_html=_metric_help("monthly")),
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
    all_flags = [str(f) for f in result.get("blocking_flags") or []] + [str(f) for f in result.get("gap_flags") or []]
    if status["primary"]:
        item = wording.finding(status["primary"])
        buttons = "".join(
            ui.button(label, href, small=True, ghost=i > 0)
            for i, (label, href) in enumerate(wording.links_for(status["primary"], aid))
        )
        official = (
            f"<p>{escape(status['action'])}</p>" if status["action"] else ""
        )
        primary = (
            '<div class="dfinding">'
            f'<p class="dreason dfinding-t"><strong>{escape(item.title)}</strong></p>'
            f"<p><strong>What RUGD found.</strong> {escape(item.found)}</p>"
            f"<p><strong>Why it matters.</strong> {escape(item.matters)}</p>"
            f"<p><strong>What you can do.</strong> {escape(item.todo)}</p>"
            f'<p class="dactions">{buttons}</p>'
            + ui.details(
                "What the official record says",
                f'{official}<p class="muted">Adding information does not lift this on its own. The requirement has to be truly met, and an authorized reviewer has to confirm it.</p>',
                tight=True,
            )
            + "</div>"
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
  <div class="dcard"><h3>What is still missing</h3>{_gaps_list(result, aid)}
    <p><a href="#recommendations" data-goto>See what would address them</a></p>{wording.tech_ref(*all_flags)}</div>
  <div class="dcard"><h3>Top recommendations</h3>{top_recs}
    <p><a href="#recommendations" data-goto>All recommendations</a></p></div>
</div>
<div class="dcard dnext"><h3>{_icon("book")} Your next step</h3><p>{escape(next_step)}</p>
  <p class="muted">Finishing a step helps, but the result stays at not yet ready until the real requirement is met and an authorized person reviews it.</p></div>
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
    header = ui.page_header(
        f"Results for {record.get('business_name') or ''}",
    ) + ui.workspace_nav(aid, "analyze")
    return ui.tabbed(
        "analyze-dashboard",
        SECTIONS,
        panels,
        header=header,
        after=legacy.get("more", ""),
        aria="Analyze sections",
    )

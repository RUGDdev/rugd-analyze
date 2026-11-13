"""Contextual suggestion cards for the intake fields.

A card appears beside a field. It says what it suggests, shows the arithmetic, and says
where it came from. The customer can use it, adjust it, dismiss it, or type their own
value. Nothing here writes to the draft. The page fills a field only when the customer
clicks, and it asks before replacing a value the customer already entered.

A card carries a number only when that number comes from the customer's own entries
or from arithmetic on them. Where no benchmark is loaded, the card says so and gives
the method, not a figure.
"""

from __future__ import annotations

import math
from html import escape
from typing import Any

from app import benchmarks
from app.guidance import family_for
from app.improve import entered, is_placeholder

CONSTRUCTION_SCOPES = (
    ("ground_up", "New building from the ground up"),
    ("shell", "Build-out of an empty shell"),
    ("renovation", "Renovation of an existing space"),
    ("equipment_only", "Mostly equipment and finishes"),
)
SERVICE_STYLES = (
    ("full_service", "Full service (table service)"),
    ("limited_service", "Limited service (counter or quick service)"),
)
VENUE_FIELDS = ("service_style", "venue_sqft", "construction_scope", "available_cash", "staff_fte", "avg_hourly_wage")
ADVICE_FIELDS = (
    "service_style",
    "venue_sqft",
    "seats",
    "average_ticket",
    "weekday_occupancy",
    "construction_cost",
    "contribution_margin",
    "annual_fixed_costs",
    "preopening_working_capital",
    "contingency_pct",
    "debt_share",
    "annual_interest_rate",
    "amortization_years",
    "available_cash",
    "staff_fte",
)
STATUSES = ("accepted", "adjusted", "dismissed", "active")
HOURS_PER_FTE_YEAR = 2080


def _money(value: float) -> str:
    return f"{value:,.0f}"


def _plain(value: float, places: int = 2) -> str:
    text = f"{value:.{places}f}"
    return text.rstrip("0").rstrip(".") if "." in text else text


def _card(
    field: str,
    key: str,
    title: str,
    text: str,
    *,
    value: str = "",
    calc: list[str] | None = None,
    source: str = "",
    links: list[tuple[str, str]] | None = None,
    widget: str = "",
    widget_data: dict[str, str] | None = None,
) -> dict[str, Any]:
    return {
        "id": f"{field}:{key}",
        "field": field,
        "title": title,
        "text": text,
        "value": value,
        "calc": calc or [],
        "source": source,
        "links": links or [],
        "widget": widget,
        "widget_data": widget_data or {},
    }


def _worksheet_link(assessment_id: str) -> tuple[str, str]:
    return ("Open the benchmark worksheet", f"/assessments/{assessment_id}/benchmarks#record-figure")


def _total_cost(profile: dict[str, Any]) -> float | None:
    cost = entered(profile, "construction_cost")
    if cost is None:
        return None
    parts = cost + (entered(profile, "equipment") or 0) + (entered(profile, "soft_costs") or 0) + (
        entered(profile, "preopening_working_capital") or 0
    )
    contingency = entered(profile, "contingency_pct")
    return parts * (1 + (0.10 if contingency is None else contingency))


def _customer_value(records: list[dict[str, Any]], key: str) -> dict[str, Any] | None:
    return benchmarks.best_entry(records, key)


def _source_line(record: dict[str, Any]) -> str:
    when = record.get("published") or "no publication date"
    return f"{record['source']} ({when}). {record['status']}. You recorded this. RUGD has not checked it."


def build_cards(
    profile: dict[str, Any],
    entries: list[dict[str, Any]],
    assessment_id: str,
) -> dict[str, list[dict[str, Any]]]:
    """Suggestion cards by field. Pure: reads the profile and the customer's recorded figures only."""
    family = family_for(str(profile.get("industry") or ""))
    restaurant = family == "hospitality"
    context = benchmarks.match(profile, entries)
    records = context["records"]
    industry = str(profile.get("industry") or "").strip() or "your industry"
    market = str(profile.get("market") or "").strip() or "your market"
    cards: dict[str, list[dict[str, Any]]] = {}

    def add(card: dict[str, Any]) -> None:
        cards.setdefault(card["field"], []).append(card)

    sqft = entered(profile, "venue_sqft")
    seats = entered(profile, "seats")

    # Venue size and seat count
    if restaurant and not benchmarks.style_of(profile):
        add(
            _card(
                "service_style",
                "style",
                "Service style narrows the benchmarks",
                "Choosing full service or limited service narrows which national medians apply to you.",
                source="Service style is the only property of your concept the stored restaurant medians are split by.",
            )
        )
    per_seat = _customer_value(records, "sqft_per_seat")
    if restaurant and sqft and per_seat and per_seat["value"] > 0:
        suggested = math.floor(sqft / per_seat["value"])
        add(
            _card(
                "seats",
                "sqft",
                "Seats from your floor area",
                f"{_money(sqft)} sq ft at {_plain(per_seat['value'])} sq ft per seat holds about {suggested} seats.",
                value=str(suggested),
                calc=[f"{_money(sqft)} sq ft ÷ {_plain(per_seat['value'])} sq ft per seat = {sqft / per_seat['value']:.1f}, rounded down to {suggested}"],
                source=_source_line(per_seat) + " Dining area is usually less than the whole floor area, so check this against a floor plan.",
            )
        )
    elif restaurant and sqft and seats:
        add(
            _card(
                "seats",
                "ratio",
                "Floor area per seat in your plan",
                f"Your plan works out to {sqft / seats:.1f} sq ft per seat.",
                calc=[f"{_money(sqft)} sq ft ÷ {_money(seats)} seats = {sqft / seats:.1f}"],
                source="Arithmetic on your two entries. No benchmark is loaded for floor area per seat. Record one you find to compare.",
                links=[_worksheet_link(assessment_id)],
            )
        )
    elif restaurant and not seats:
        add(
            _card(
                "seats",
                "plan",
                "Seat count comes from a floor plan",
                "Seats are limited by floor area and by code. Enter the square footage under Venue and cash for a cross-check.",
                source="Method only. No seat benchmark is loaded.",
            )
        )

    # Average ticket
    check = _customer_value(records, "average_check")
    if check:
        add(
            _card(
                "average_ticket",
                "recorded",
                "Average check you recorded",
                f"You recorded {check['value_text']} for {check['geography']}.",
                value=_plain(check["value"]),
                source=_source_line(check),
                links=[_worksheet_link(assessment_id)],
            )
        )
    else:
        add(
            _card(
                "average_ticket",
                "none",
                f"No average-check benchmark for {market}",
                "Build it from your menu: the typical order per guest, with drinks and sides, at your planned prices.",
                source=f"No average-check figure is loaded for {industry} in {market}. RUGD does not estimate one.",
                links=[_worksheet_link(assessment_id)],
            )
        )

    # Seat turns and occupancy
    if restaurant and seats:
        add(
            _card(
                "weekday_occupancy",
                "turns",
                "Several seatings a day?",
                "The official formula counts one cover per occupied seat per day. If you expect more, the proposed revenue worksheet shows the effect side by side.",
                source="The official calculation is unchanged. The worksheet is a separate, labeled comparison.",
                links=[("Open the revenue worksheet", f"/assessments/{assessment_id}/revenue-worksheet")],
            )
        )

    # Construction cost
    per_sqft = _customer_value(records, "construction_per_sqft")
    scope = dict(CONSTRUCTION_SCOPES).get(str(profile.get("construction_scope") or ""), "")
    cost = entered(profile, "construction_cost")
    if sqft and per_sqft:
        suggested_cost = sqft * per_sqft["value"]
        add(
            _card(
                "construction_cost",
                "sqft",
                "Construction cost from your recorded rate",
                f"{_money(sqft)} sq ft at {_plain(per_sqft['value'])} per sq ft is about {_money(suggested_cost)}.",
                value=_plain(suggested_cost, 0),
                calc=[f"{_money(sqft)} sq ft × {_plain(per_sqft['value'])} per sq ft = {_money(suggested_cost)}"],
                source=_source_line(per_sqft) + (f" Your scope: {scope}." if scope else " Scope is not set, and rates differ a lot by scope."),
            )
        )
    elif sqft and cost:
        add(
            _card(
                "construction_cost",
                "ratio",
                "Cost per square foot in your plan",
                f"Your entry works out to {_money(cost / sqft)} per sq ft.",
                calc=[f"{_money(cost)} ÷ {_money(sqft)} sq ft = {_money(cost / sqft)} per sq ft"],
                source="Arithmetic on your entries. No build-out rate is loaded. A contractor bid for your scope is the right check."
                + (f" Your scope: {scope}." if scope else ""),
                links=[_worksheet_link(assessment_id)],
            )
        )
    elif not cost:
        add(
            _card(
                "construction_cost",
                "none",
                "A bid beats an average",
                "Ask one or two contractors for a written estimate for your scope and square footage.",
                source="No build-out cost benchmark is loaded for your market. RUGD does not estimate one.",
                links=[_worksheet_link(assessment_id)],
            )
        )

    # Contribution margin worksheet
    food = _customer_value(records, "food_cost_pct")
    labor = _customer_value(records, "labor_pct")
    other = _customer_value(records, "other_variable_pct")
    labels = (
        ("Food and beverage cost", "Direct labor that moves with sales", "Card fees, packaging, and supplies")
        if restaurant
        else ("Cost of goods or direct delivery", "Direct labor that moves with sales", "Fees and other costs that move with sales")
    )
    prefill = [food, labor, other]
    values = [f"{item['value'] * 100:.1f}".rstrip("0").rstrip(".") if item else "" for item in prefill]
    start = ""
    if all(prefill):
        total = sum(item["value"] for item in prefill if item)
        start = _plain(1 - total, 4)
    reference = [
        item
        for item in records
        if item.get("metric_key") == "labor_pct" and item["status"] == benchmarks.STATUS_SECONDARY and item.get("all_respondents")
    ]
    context_line = ""
    if reference:
        shown = reference[0]
        context_line = (
            f"For context only: the {shown['published']} national median for salaries, wages, and benefits was {shown['value_text']} "
            f"({shown['subsector']}). It includes salaried staff that may belong in fixed costs, so it is not a margin input."
        )
    add(
        _card(
            "contribution_margin",
            "calc",
            "Build your contribution margin",
            "Contribution margin is what is left of each sales dollar after the costs that move with sales. Enter each share as a percent.",
            value=start,
            calc=["Margin = 100% − food/goods − direct labor − other variable costs"],
            source=(
                "Your three entries, if any, come from figures you recorded."
                if all(prefill)
                else "No figures are prefilled. Fill the three lines from your recipe costing, labor schedule, and fee statements."
            )
            + (" " + context_line if context_line else ""),
            links=[_worksheet_link(assessment_id)],
            widget="margin",
            widget_data={
                "labels": "|".join(labels),
                "values": "|".join(values),
            },
        )
    )

    # Staffing against fixed costs
    fte = entered(profile, "staff_fte")
    wage = entered(profile, "avg_hourly_wage")
    fixed = entered(profile, "annual_fixed_costs")
    if fte and wage:
        payroll = fte * wage * HOURS_PER_FTE_YEAR
        line = f"{_plain(fte, 1)} full-time equivalents × {_plain(wage)} per hour × {HOURS_PER_FTE_YEAR:,} hours = {_money(payroll)} a year"
        relation = (
            f"Your annual fixed costs are {_money(fixed)}. Count each staff cost once: either in fixed costs or inside the contribution margin."
            if fixed is not None
            else "Annual fixed costs are blank. Staff you treat as fixed belong there, not in the margin."
        )
        add(
            _card(
                "annual_fixed_costs",
                "staff",
                "Staffing check",
                f"Your staffing plan implies about {_money(payroll)} a year in base wages before taxes and benefits.",
                calc=[line],
                source=f"Arithmetic on your entries. {HOURS_PER_FTE_YEAR:,} hours is a 40-hour week for 52 weeks. {relation}",
            )
        )
    else:
        add(
            _card(
                "staff_fte",
                "none",
                "Staffing drives fixed costs",
                "Enter the full-time equivalents and an all-in hourly wage to check your fixed costs against payroll.",
                source="BLS Occupational Employment and Wage Statistics lists wages by occupation and area. RUGD has not loaded them.",
                links=[("BLS wage data", "https://www.bls.gov/oes/")],
            )
        )

    # Pre-opening working capital
    months_entry = _customer_value(records, "working_capital_months")
    if fixed:
        if months_entry:
            amount = months_entry["value"] * fixed / 12
            add(
                _card(
                    "preopening_working_capital",
                    "months",
                    "Working capital from your recorded months",
                    f"{_plain(months_entry['value'])} months of fixed costs is about {_money(amount)}.",
                    value=_plain(amount, 0),
                    calc=[f"{_plain(months_entry['value'])} months × ({_money(fixed)} ÷ 12) = {_money(amount)}"],
                    source=_source_line(months_entry),
                )
            )
        else:
            add(
                _card(
                    "preopening_working_capital",
                    "calc",
                    "Size the cash cushion",
                    "Choose how many months of fixed costs you want in the bank at opening. The amount follows from your fixed costs.",
                    calc=[f"Amount = months × ({_money(fixed)} ÷ 12)"],
                    source="You choose the months. No working-capital benchmark is loaded.",
                    links=[_worksheet_link(assessment_id)],
                    widget="months",
                    widget_data={"fixed": _plain(fixed, 2)},
                )
            )

    # Financing
    total = _total_cost(profile)
    cash = entered(profile, "available_cash")
    if total and cash is not None:
        share = round(min(1.0, max(0.0, 1 - cash / total)), 4)
        add(
            _card(
                "debt_share",
                "cash",
                "Debt share from your cash",
                f"If you put in {_money(cash)} of about {_money(total)}, the rest, {share * 100:.0f}%, would be borrowed.",
                value=_plain(share, 4),
                calc=[f"1 − {_money(cash)} ÷ {_money(total)} = {share:.4f}"],
                source="Arithmetic on your entries, using the default 10% contingency if you left it blank. A lender may require more cash than this. The result is your assumption, not a loan offer.",
            )
        )
    elif is_placeholder(profile, "debt_share"):
        add(
            _card(
                "debt_share",
                "none",
                "Debt share is a lender decision",
                "Enter the cash you can put in under Venue and cash, and the share follows. Until then the engine uses its placeholder.",
                source="No lending benchmark is loaded. A lender's written terms are the right source.",
            )
        )
    if is_placeholder(profile, "contingency_pct"):
        add(
            _card(
                "contingency_pct",
                "none",
                "Ask what the bid already carries",
                "This is blank or still at a starting number from RUGD. Your contractor can say how much contingency their estimate includes.",
                source="No contingency benchmark is loaded. The placeholder is not a market figure.",
            )
        )
    if is_placeholder(profile, "annual_interest_rate") or is_placeholder(profile, "amortization_years"):
        add(
            _card(
                "annual_interest_rate",
                "none",
                "Rate and term come from a lender",
                "A rate or term that is blank or still at a starting number from RUGD is not a lender's figure. Get a term sheet or an indication before relying on it.",
                source="No lending benchmark is loaded. A Small Business Development Center advisor can help you compare lenders.",
                links=[("Find a free advisor", "https://www.sba.gov/local-assistance/resource-partners/small-business-development-centers-sbdc")],
            )
        )
    if cash is None and total:
        add(
            _card(
                "available_cash",
                "none",
                "How much can you put in?",
                f"The project is about {_money(total)} in your own numbers. Enter the cash you can document, and RUGD will show the gap.",
                source="Arithmetic on your entries. Lenders usually want to see the cash.",
                links=[("Open the improvement planner", f"/assessments/{assessment_id}/improve")],
            )
        )
    elif cash is not None and total:
        add(
            _card(
                "available_cash",
                "gap",
                "Your cash against the project",
                f"Your {_money(cash)} covers {min(100.0, cash / total * 100):.0f}% of about {_money(total)}.",
                calc=[f"{_money(cash)} ÷ {_money(total)} = {cash / total:.2f}"],
                source="Arithmetic on your entries. The improvement planner shows the funding gap and what could close it.",
                links=[("Open the improvement planner", f"/assessments/{assessment_id}/improve")],
            )
        )
    # Venue square feet when absent
    if restaurant and not sqft:
        add(
            _card(
                "venue_sqft",
                "none",
                "Square footage unlocks cross-checks",
                "With it, RUGD can compare your seats and construction cost to figures you record.",
                source="Optional. Nothing is estimated from it unless you record a figure with a source.",
            )
        )
    return cards


def split(cards: list[dict[str, Any]], decisions: dict[str, dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    shown, dismissed = [], []
    for card in cards:
        status = str((decisions.get(card["id"]) or {}).get("status") or "")
        card = dict(card, status=status)
        (dismissed if status == "dismissed" else shown).append(card)
    return shown, dismissed


def _card_html(card: dict[str, Any], profile: dict[str, Any], writable: bool) -> str:
    field = escape(card["field"])
    value = escape(card["value"])
    calc = "".join(f"<li>{escape(line)}</li>" for line in card["calc"])
    links = "".join(f'<a href="{escape(url)}">{escape(label)}</a> ' for label, url in card["links"])
    why = (
        f'<details class="advice-why"><summary aria-label="Why this suggestion"><span class="q" aria-hidden="true">?</span> Source and reasoning</summary>'
        f'<div class="advice-source"><p>{escape(card["source"])}</p></div></details>'
        if card["source"]
        else ""
    )
    widget = ""
    if card["widget"] == "margin":
        labels = card["widget_data"]["labels"].split("|")
        values = card["widget_data"]["values"].split("|")
        rows = "".join(
            f'<label class="advice-line">{escape(label)} (%)<input inputmode="decimal" data-calc-input="{index}" value="{escape(value_text)}"'
            f'{"" if writable else " disabled"}></label>'
            for index, (label, value_text) in enumerate(zip(labels, values))
        )
        widget = f'<div class="advice-widget" data-calc="margin">{rows}<p class="advice-result" aria-live="polite"></p></div>'
    elif card["widget"] == "months":
        widget = (
            f'<div class="advice-widget" data-calc="months" data-fixed="{escape(card["widget_data"]["fixed"])}">'
            f'<label class="advice-line">Months of fixed costs<input inputmode="decimal" data-calc-input="0"{"" if writable else " disabled"}></label>'
            '<p class="advice-result" aria-live="polite"></p></div>'
        )
    status = card.get("status") or ""
    state_note = {
        "accepted": "You used this suggestion.",
        "adjusted": "You started from this suggestion and changed it.",
    }.get(status, "")
    note = f'<p class="advice-state">{escape(state_note)}</p>' if state_note else ""
    actions = ""
    if writable:
        use = ""
        if card["value"] or card["widget"]:
            use = f'<button type="button" class="advice-btn" data-act="use">Use {value}</button>' if card["value"] else '<button type="button" class="advice-btn" data-act="use" disabled>Use result</button>'
            use += '<button type="button" class="advice-btn ghost" data-act="adjust">Adjust</button>'
        actions = f'<div class="advice-actions">{use}<button type="button" class="advice-btn ghost" data-act="dismiss">Dismiss</button></div>'
    return (
        f'<div class="advice-card" data-card="{escape(card["id"])}" data-field="{field}" data-value="{value}">'
        f'<p class="advice-title">{escape(card["title"])}</p>'
        f'<p class="advice-text">{escape(card["text"])}</p>'
        + (f'<ul class="advice-calc">{calc}</ul>' if calc else "")
        + widget
        + note
        + (f'<p class="advice-links">{links}</p>' if links else "")
        + actions
        + why
        + "</div>"
    )


def slot_html(
    field: str,
    cards: list[dict[str, Any]],
    decisions: dict[str, dict[str, Any]],
    profile: dict[str, Any],
    writable: bool,
) -> str:
    shown, dismissed = split(cards, decisions)
    body = "".join(_card_html(card, profile, writable) for card in shown)
    if dismissed:
        restore = "".join(
            f'<div class="advice-dismissed-row" data-card="{escape(card["id"])}" data-field="{escape(field)}"><span>{escape(card["title"])}</span>'
            + ('<button type="button" class="advice-btn ghost" data-act="restore">Show again</button>' if writable else "")
            + "</div>"
            for card in dismissed
        )
        body += f'<details class="advice-dismissed"><summary>{len(dismissed)} dismissed</summary>{restore}</details>'
    return body


def slots(
    profile: dict[str, Any],
    entries: list[dict[str, Any]],
    decisions: dict[str, dict[str, Any]],
    assessment_id: str,
    writable: bool,
) -> dict[str, str]:
    """Rendered card HTML for each advice-enabled field, empty string when a field has no cards."""
    cards = build_cards(profile, entries, assessment_id)
    return {field: slot_html(field, cards.get(field, []), decisions, profile, writable) for field in ADVICE_FIELDS}


def decision_payload(card_id: str, status: str, value: str) -> dict[str, Any]:
    return {"card": card_id[:80], "status": status, "value": str(value)[:40]}

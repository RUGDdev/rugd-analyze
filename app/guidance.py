"""Industry guidance for the intake. Methods are named. Benchmarks are not invented.

A customer fact is only a figure the customer marked as measured. A sourced
benchmark is not produced here: this module has no benchmark table. Illustrative
arithmetic uses numbers the customer already entered, or the existing seat
formula. It does not change an official assessment.
"""

from __future__ import annotations

import re
from html import escape
from typing import Any

from app.inputs import field_state
from engine.financial import seat_occupancy_revenue

BENCHMARK_NOTE = (
    "No sourced benchmark is on file for this industry. "
    "A publication, date, geography, and operating ratio were not invented."
)

_FAMILIES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("hospitality", ("coffee", "cafe", "restaurant", "food service", "dining", "bakery", "bistro", "pub", "bar", "food")),
    ("software", ("software", "saas", "subscription app")),
    ("healthcare", ("dental", "clinic", "health care", "healthcare", "medical", "therapy")),
    ("retail", ("ecommerce", "boutique", "retail", "store", "shop")),
    ("services", ("professional services", "bookkeeping", "consulting", "accounting", "legal", "agency")),
)

_METHODS: dict[str, dict[str, str]] = {
    "covers": {
        "id": "covers",
        "name": "Covers and average check",
        "why": (
            "A dining business is limited by seats, how full they are, and what a customer pays. "
            "The existing startup formula is seats × blended occupancy × average ticket × operating days. "
            "Blended occupancy is weekday occupancy × 5 plus weekend occupancy × 2, divided by 7."
        ),
        "formula": "seats × blended occupancy × average ticket × operating days",
        "unit": "period",
    },
    "billable": {
        "id": "billable",
        "name": "Billable time",
        "why": (
            "A services business is limited by people, the hours they can sell in a month, and the rate. "
            "This worksheet multiplies those three assumptions. It is not an industry rate."
        ),
        "formula": "people × billable hours per month × hourly rate",
        "unit": "month",
    },
    "retainer": {
        "id": "retainer",
        "name": "Monthly retainers",
        "why": "Some firms bill a set fee per client each month. The product is clients × monthly fee.",
        "formula": "clients × monthly fee",
        "unit": "month",
    },
    "transactions": {
        "id": "transactions",
        "name": "Transactions and average sale",
        "why": "A shop's revenue worksheet is how many sales you expect in a month times the average sale.",
        "formula": "transactions per month × average sale",
        "unit": "month",
    },
    "subscription": {
        "id": "subscription",
        "name": "Paying customers and monthly price",
        "why": "A subscription worksheet is how many customers pay times the price each month.",
        "formula": "paying customers × monthly price",
        "unit": "month",
    },
    "visits": {
        "id": "visits",
        "name": "Visits and fee",
        "why": "A clinic worksheet is expected visits in a month times the fee per visit. It is not a payer rate.",
        "formula": "visits per month × fee per visit",
        "unit": "month",
    },
    "independent": {
        "id": "independent",
        "name": "Independent monthly estimate",
        "why": (
            "Use this when you already have a monthly revenue figure, or when no closer method fits. "
            "The monthly engine stores that figure as your assumption."
        ),
        "formula": "the monthly revenue you enter",
        "unit": "month",
    },
}

_RECOMMENDED = {
    "hospitality": "covers",
    "services": "billable",
    "retail": "transactions",
    "software": "subscription",
    "healthcare": "visits",
    "general": "independent",
}

_ALTERNATIVES = {
    "hospitality": ("independent",),
    "services": ("retainer", "independent"),
    "retail": ("independent",),
    "software": ("independent",),
    "healthcare": ("independent",),
    "general": ("covers", "billable", "transactions", "subscription", "visits"),
}

_WORKSHEETS: dict[str, tuple[tuple[str, str], ...]] = {
    "billable": (
        ("forecast_people", "People who bill"),
        ("forecast_hours", "Billable hours per person each month"),
        ("forecast_rate", "Hourly rate"),
    ),
    "retainer": (
        ("forecast_clients", "Clients on retainer"),
        ("forecast_fee", "Monthly fee per client"),
    ),
    "transactions": (
        ("forecast_transactions", "Transactions per month"),
        ("forecast_average_sale", "Average sale"),
    ),
    "subscription": (
        ("forecast_customers", "Paying customers"),
        ("forecast_monthly_price", "Monthly price"),
    ),
    "visits": (
        ("forecast_visits", "Visits per month"),
        ("forecast_fee", "Fee per visit"),
    ),
}


def client_catalog() -> dict[str, Any]:
    """Phrases and method names for the page. No benchmark values are included."""
    families = []
    for family, phrases in _FAMILIES:
        method = _METHODS[_RECOMMENDED[family]]
        families.append(
            {
                "id": family,
                "phrases": list(phrases),
                "method_id": method["id"],
                "name": method["name"],
                "why": method["why"],
                "formula": method["formula"],
            }
        )
    general = _METHODS["independent"]
    return {
        "families": families,
        "general": {
            "id": "general",
            "method_id": general["id"],
            "name": general["name"],
            "why": general["why"],
            "formula": general["formula"],
        },
        "benchmark": BENCHMARK_NOTE,
    }


def family_for(industry: str) -> str:
    """Match a family from the industry words. An unknown industry stays general."""
    padded = f" {_words(industry)} "
    best_len = 0
    best = "general"
    for family, phrases in _FAMILIES:
        for phrase in phrases:
            needle = f" {_words(phrase)} "
            if needle.strip() and needle in padded and len(needle) > best_len:
                best_len = len(needle)
                best = family
    return best


def method_catalog() -> dict[str, dict[str, str]]:
    return {key: dict(value) for key, value in _METHODS.items()}


def recommendation(profile: dict[str, Any]) -> dict[str, Any]:
    """Name a method. Do not attach a benchmark value."""
    family = family_for(str(profile.get("industry") or ""))
    recommended_id = _RECOMMENDED[family]
    choice = str(profile.get("forecast_choice") or "recommended")
    if choice not in {"recommended", "customize", "other", "independent"}:
        choice = "recommended"
    selected = recommended_id
    if choice == "independent":
        selected = "independent"
    elif choice == "other":
        asked = str(profile.get("forecast_method") or "")
        selected = asked if asked in _METHODS else recommended_id
    method = dict(_METHODS[selected])
    return {
        "family": family,
        "choice": choice,
        "recommended_id": recommended_id,
        "recommended_name": _METHODS[recommended_id]["name"],
        "selected_id": selected,
        "method": method,
        "alternatives": [_METHODS[item]["name"] for item in _ALTERNATIVES[family]],
        "benchmark_note": BENCHMARK_NOTE,
        "math": illustrative_math(profile, selected),
    }


def illustrative_math(profile: dict[str, Any], method_id: str) -> dict[str, Any] | None:
    """Calculate only from entered assumptions. Missing inputs produce no figure."""
    if method_id == "covers":
        return _covers_math(profile)
    fields = _WORKSHEETS.get(method_id)
    if not fields:
        return None
    numbers = [_entered(profile, key) for key, _label in fields]
    if any(number is None for number in numbers):
        return None
    amount = 1.0
    parts: list[str] = []
    for number in numbers:
        assert number is not None
        amount *= number
        parts.append(_plain(number))
    return {
        "kind": "illustrative_example",
        "unit": "month",
        "lines": [f"{' × '.join(parts)} = {_plain(round(amount, 2))}"],
        "amount": round(amount, 2),
        "downside": None,
        "upside": "An upside case is not calculated. A higher figure was not invented.",
        "note": (
            "Illustrative example from the assumptions you entered. "
            "It is not a sourced benchmark and it is not the official assessment. "
            "Copy it into monthly revenue only if you want the monthly engine to use it."
        ),
    }


def progress_items(profile: dict[str, Any]) -> list[dict[str, str]]:
    """Short bullets. Blank fields stay missing and are not called zero."""
    rows: list[dict[str, str]] = []
    for key, label in (
        ("business_name", "Business"),
        ("industry", "Industry"),
        ("market", "Place"),
        ("products", "Offer"),
        ("customers", "Customers"),
        ("revenue_model", "Revenue model"),
    ):
        text = " ".join(str(profile.get(key) or "").split()).strip()
        if key == "business_name" and text.lower() in {"", "untitled", "new draft"}:
            text = ""
        if not text:
            rows.append({"kind": "missing", "text": f"{label}: missing"})
        else:
            rows.append({"kind": "customer_assumption", "text": f"{label}: {text[:80]}"})
    if profile.get("inputs_are_measured") is True:
        rows.append({
            "kind": "customer_fact",
            "text": "You marked the monthly figures as measured. That is your statement, not a verified demand record.",
        })
    return rows


def forecast_fields_html(profile: dict[str, Any], locked: str) -> str:
    """Method choice and worksheet inputs. The monthly engine fields stay separate."""
    from app.field_help import label_with_help, section_intro

    guide = recommendation(profile)
    family = guide["family"]
    blocks = []
    seen: set[str] = set()
    for method_id, fields in _WORKSHEETS.items():
        controls = []
        for key, label in fields:
            value = escape(str(profile.get(key) or ""))
            first = key not in seen
            seen.add(key)
            suffix = "" if first else f"-{method_id}"
            field_id = key if first else f"{key}-{method_id}"
            controls.append(
                label_with_help(key, label, profile, for_id=field_id, suffix=suffix)
                + f'<input id="{escape(field_id)}" name="{escape(key)}" value="{value}" {locked}>'
            )
        hidden = "" if method_id == guide["selected_id"] and guide["choice"] != "independent" else " hidden"
        blocks.append(
            f'<div class="forecast-inputs" data-method="{escape(method_id)}"{hidden}>'
            + "".join(controls)
            + "</div>"
        )
    options = []
    for method_id, method in _METHODS.items():
        if method_id == "independent":
            continue
        selected = " selected" if method_id == guide["selected_id"] else ""
        options.append(f'<option value="{escape(method_id)}"{selected}>{escape(method["name"])}</option>')
    choice = guide["choice"]

    def radio(value: str, label: str) -> str:
        checked = " checked" if choice == value else ""
        return (
            f'<label class="choice"><input type="radio" name="forecast_choice" value="{value}"{checked} {locked}> '
            f"{escape(label)}</label>"
        )

    math = _math_html(guide["math"])
    return f"""
<section id="forecast-guidance" data-family="{escape(family)}" data-recommended="{escape(guide["recommended_id"])}">
<h3>Revenue method</h3>
{section_intro("forecast", profile)}
<p id="forecast-recommended"><strong>Recommended method:</strong> {escape(guide["recommended_name"])}. {escape(_METHODS[guide["recommended_id"]]["why"])}</p>
<p id="forecast-formula"><strong>Formula:</strong> {escape(_METHODS[guide["recommended_id"]]["formula"])}</p>
<p class="muted" id="forecast-benchmark">{escape(BENCHMARK_NOTE)}</p>
<p class="muted">Other recognized approaches for this industry file: {escape(", ".join(guide["alternatives"]) or "an independent estimate")}.</p>
<fieldset>
<legend>How should this draft forecast revenue?</legend>
{radio("recommended", "Use the recommended method")}
{radio("customize", "Use the recommended method with my own figures")}
{radio("other", "Choose another method")}
{radio("independent", "Enter an independent monthly estimate")}
</fieldset>
<label for="forecast_method">Other method</label>
<select id="forecast_method" name="forecast_method" {locked}>{''.join(options)}</select>
{''.join(blocks)}
<div id="forecast-math">{math}</div>
</section>
"""


def progress_html(profile: dict[str, Any]) -> str:
    items = "".join(f'<li data-kind="{escape(item["kind"])}">{escape(item["text"])}</li>' for item in progress_items(profile))
    return f'<ul id="guided-progress">{items}</ul>'


def _math_html(math: dict[str, Any] | None) -> str:
    if not math:
        return (
            "<p id=\"forecast-waiting\">Enter the method's assumptions to see the arithmetic. "
            "A missing input is not filled with an industry average.</p>"
        )
    lines = "".join(f"<li>{escape(line)}</li>" for line in math["lines"])
    downside = ""
    if math.get("downside"):
        downside = f'<p><strong>Downside, from your multiplier:</strong> {escape(str(math["downside"]))}</p>'
    copy = ""
    if math.get("unit") == "month" and math.get("amount") is not None:
        copy = (
            f'<button type="button" data-copy-revenue="{escape(str(math["amount"]))}">'
            "Copy this figure into monthly revenue</button>"
            "<p class=\"muted\">Copying does not save by itself and does not run Analyze.</p>"
        )
    return (
        f'<p><strong>Illustrative example.</strong> {escape(str(math["note"]))}</p>'
        f"<ul>{lines}</ul>{downside}"
        f'<p>{escape(str(math["upside"]))}</p>{copy}'
    )


def _covers_math(profile: dict[str, Any]) -> dict[str, Any] | None:
    seats = _entered(profile, "seats")
    ticket = _entered(profile, "average_ticket")
    weekday = _entered(profile, "weekday_occupancy")
    weekend = _entered(profile, "weekend_occupancy")
    days = _entered(profile, "operating_days")
    if None in {seats, ticket, weekday, weekend, days}:
        return None
    assert seats is not None and ticket is not None and weekday is not None
    assert weekend is not None and days is not None
    try:
        base = seat_occupancy_revenue(seats, ticket, weekday, weekend, days)
    except ValueError:
        return None
    line = (
        f"{_plain(seats)} seats × {_plain(base.occupancy)} blended occupancy × "
        f"{_plain(ticket)} average ticket × {_plain(days)} days = {_plain(base.revenue)}"
    )
    downside_text = "Downside is not calculated until you enter a downside occupancy multiplier."
    multiplier = _entered(profile, "downside_multiplier")
    if multiplier is not None and multiplier > 0:
        try:
            downside = seat_occupancy_revenue(
                seats,
                ticket,
                weekday * multiplier,
                weekend * multiplier,
                days,
            )
        except ValueError:
            downside = None
        if downside is not None:
            downside_text = (
                f"{_plain(downside.revenue)} over the same operating days. "
                "The multiplier is your assumption, not an industry standard."
            )
        else:
            downside_text = (
                "Downside was not calculated. The multiplier pushes occupancy above 1, "
                "which the existing formula refuses."
            )
    return {
        "kind": "illustrative_example",
        "unit": "period",
        "lines": [line],
        "amount": None,
        "downside": downside_text,
        "upside": "An upside case is not calculated. A higher occupancy was not invented.",
        "note": (
            "This is the existing seat formula applied to your assumptions for the operating days you entered. "
            "It is a period total, not a monthly figure, and it is not saved as the official result. "
            "Enter the monthly revenue you want in the monthly field. "
            "The formula counts one cover per occupied seat per operating day. "
            "Table turns are not a separate input."
        ),
    }


def _entered(profile: dict[str, Any], key: str) -> float | None:
    if field_state(profile.get(key)) not in {"entered", "zero"}:
        return None
    return float(str(profile.get(key)).strip())


def _plain(number: float) -> str:
    if float(number).is_integer():
        return str(int(number))
    return str(round(number, 4)).rstrip("0").rstrip(".")


def _words(value: str) -> str:
    return " ".join(re.findall(r"[a-z0-9]+", value.lower()))

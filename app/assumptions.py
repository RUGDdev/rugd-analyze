"""Assumption planning for the Analyze > Key Numbers workspace.

This module only reads and proposes. It never runs Analyze, never writes a result,
and never touches a flag, a score, human review, or investor readiness. A preview
calls the same profile-to-intake and projection path Analyze uses (`app.preview`),
so there is one calculation, not a second copy of it.

Only underlying assumptions can be edited. Calculated figures (total project cost,
debt, equity, coverage, break-even) are outputs and have no input here.

A value a customer types is a customer estimate or a hypothetical planning figure.
It is never a verified fact and never a sourced benchmark.
"""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass
from typing import Any

from app import display as d
from app import improve
from app.analysis import profile_to_intake
from app.guidance import family_for
from app.inputs import field_state
from app.preview import calculate_preview

# ---------------------------------------------------------------------------
# What can be edited
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Field:
    key: str
    label: str
    kind: str  # money, share, whole, number
    hint: str
    impact: str


FIELDS: dict[str, Field] = {
    field.key: field
    for field in (
        Field("construction_cost", "Construction cost", "money", "Dollars", "A higher build cost raises the total project cost, the loan, and every yearly payment."),
        Field("equipment", "Equipment", "money", "Dollars", "Counts in the total project cost. Left blank it is counted as $0, which understates what you need to raise."),
        Field("soft_costs", "Soft costs", "money", "Dollars", "Design, permits, legal, and fees. Counts in the total. Left blank it is counted as $0."),
        Field("preopening_working_capital", "Pre-opening working capital", "money", "Dollars", "Cash for the weeks before opening. It raises the money you must raise, not your profit."),
        Field("contingency_pct", "Contingency", "share", "0 to 1 (0.10 = 10%)", "A cushion added on top of the cost lines. More contingency raises the total."),
        Field("debt_share", "Debt share", "share", "0 to 1 (0.70 = 70%)", "The share of the total that is borrowed. More debt means bigger payments and less cash from you."),
        Field("annual_interest_rate", "Interest rate (per year)", "share", "0 to 1 (0.08 = 8%)", "A higher rate raises every yearly loan payment and lowers loan coverage."),
        Field("amortization_years", "Repayment term (years)", "whole", "Whole years", "A longer term lowers each yearly payment and raises total interest."),
        Field("available_cash", "Cash you can put in", "money", "Dollars", "Compared with the equity the project needs. It does not change the calculated costs or coverage."),
        Field("seats", "Seats", "whole", "Whole number", "More seats raise potential sales. They usually raise build and fixed costs too."),
        Field("average_ticket", "Average ticket", "money", "Dollars per cover", "Each extra dollar of average ticket raises yearly sales by seats x occupancy x days."),
        Field("weekday_occupancy", "Weekday occupancy", "share", "0 to 1 (0.40 = 40%)", "How full the seats are on weekdays. Small changes move yearly sales a lot."),
        Field("weekend_occupancy", "Weekend occupancy", "share", "0 to 1 (0.70 = 70%)", "How full the seats are on weekends."),
        Field("operating_days", "Operating days (per year)", "number", "Days in a year", "More operating days raise sales and usually raise costs."),
        Field("contribution_margin", "Contribution margin", "share", "0 to 1 (0.35 = 35%)", "What is left of each sales dollar after direct costs. It sets how much sales can pay toward fixed costs and the loan."),
        Field("annual_fixed_costs", "Annual fixed costs", "money", "Dollars per year", "Rent, insurance, salaried staff. Left blank it is counted as $0, which makes coverage look better than it is."),
        Field("downside_multiplier", "Downside multiplier", "number", "A weaker-year factor (0.60 = 60% of typical sales)", "Sets how weak the weaker year is. A lower number is a harsher test."),
        Field("initial_capital", "Initial capital (monthly view)", "money", "Dollars", "Used by the monthly view to estimate how long it takes to recover your starting money."),
        Field("monthly_fixed_costs", "Monthly fixed costs", "money", "Dollars per month", "Raises break-even sales and lowers monthly cash flow."),
        Field("gross_margin_pct", "Gross margin (monthly view)", "share", "0 to 1 (0.65 = 65%)", "The share of each sales dollar left after direct costs in the monthly view."),
        Field("projected_monthly_revenue_base", "Typical monthly sales", "money", "Dollars per month", "The sales the monthly view assumes in a typical month."),
    )
}

SECTIONS: tuple[tuple[str, str, str, tuple[str, ...]], ...] = (
    (
        "project-costs",
        "Project costs",
        "What it costs to build and open. These add up to the total project cost, which you cannot edit directly.",
        ("construction_cost", "equipment", "soft_costs", "preopening_working_capital", "contingency_pct"),
    ),
    (
        "financing",
        "Financing and your cash",
        "How the total is paid for. A lender sets the real terms. Your cash is a balance you hold, not the same thing as equity.",
        ("debt_share", "annual_interest_rate", "amortization_years", "available_cash"),
    ),
    (
        "revenue",
        "Revenue assumptions",
        "What sales could be in a typical year. These are your estimates until real sales or reservations support them.",
        ("seats", "average_ticket", "weekday_occupancy", "weekend_occupancy", "operating_days"),
    ),
    (
        "operating",
        "Operating costs and margin",
        "What it costs to run the place and how much of each sales dollar is left to pay for it.",
        ("contribution_margin", "annual_fixed_costs", "downside_multiplier"),
    ),
    (
        "monthly",
        "Monthly operating view",
        "A separate month-by-month view built from four monthly inputs. It is not added to the startup build.",
        ("initial_capital", "monthly_fixed_costs", "gross_margin_pct", "projected_monthly_revenue_base"),
    ),
)
EDITABLE: tuple[str, ...] = tuple(key for _s, _t, _n, keys in SECTIONS for key in keys)
MONTHLY = ("initial_capital", "monthly_fixed_costs", "gross_margin_pct", "projected_monthly_revenue_base")
# A field the startup or monthly view cannot be calculated without. It cannot be cleared.
NEEDED = frozenset(improve.REQUIRED) | frozenset(MONTHLY)
STARTUP_OPTIONAL = tuple(improve.OPTIONAL_DEFAULTS)

BASIS_LABELS = {
    "estimate": "Your estimate",
    "hypothetical": "Hypothetical",
    "document": "From a document you hold",
}
BASIS_CHOICES = tuple(BASIS_LABELS)
BASIS_EXPLAINED = {
    "estimate": "Your own planning figure. RUGD has not checked it.",
    "hypothetical": "An illustrative figure used because the real one is not known yet. It is not a benchmark and not a market standard.",
    "document": "Taken from a quote, bid, bank statement, or similar record you hold. RUGD has not verified the document.",
}
# Illustrative restaurant planning figures. They fill blank fields in the form only and are never saved by themselves.
EXAMPLE_VALUES = {
    "equipment": "365000",
    "soft_costs": "225000",
    "preopening_working_capital": "200000",
}
EXAMPLE_NOTE = (
    "These are illustrative planning figures for a restaurant pilot. They are not industry standards, not benchmarks, "
    "and not your quotes. Nothing is saved until you review the preview and approve it."
)
_MAX = 1e12


def label(key: str) -> str:
    return FIELDS[key].label if key in FIELDS else key.replace("_", " ").capitalize()


# ---------------------------------------------------------------------------
# Numbers and display
# ---------------------------------------------------------------------------


def _num(text: Any) -> float | None:
    return improve._num(text)  # the cleaning the Improve scenarios use: commas and a dollar sign are allowed


def plain_text(number: float) -> str:
    return str(int(number)) if float(number).is_integer() else f"{number:.4f}".rstrip("0").rstrip(".")


def format_value(key: str, number: float | None) -> str:
    if number is None:
        return d.NOT_PROVIDED
    kind = FIELDS[key].kind if key in FIELDS else "number"
    if kind == "money":
        return d.money(number, cents=not float(number).is_integer())
    if kind == "share":
        return f"{number:g} ({number * 100:.4g}%)"
    if kind == "whole":
        return f"{int(number):,}" if float(number).is_integer() else f"{number:g}"
    return f"{number:g}"


def _saved_text(profile: dict[str, Any], key: str) -> str:
    value = profile.get(key)
    if value is None or isinstance(value, bool):
        return ""
    return str(value).strip()


def _same(first: str, second: str) -> bool:
    a, b = _num(first), _num(second)
    if a is not None and b is not None:
        return abs(a - b) < 1e-9
    return first.strip() == second.strip()


def field_status(profile: dict[str, Any], key: str) -> dict[str, str]:
    """Missing, zero, or entered for one field, and what the calculation does with it."""
    state = field_state(profile.get(key))
    default = improve.OPTIONAL_DEFAULTS.get(key)
    if state == "missing":
        if key == "available_cash":
            text = "Not entered. No cash is assumed, and a blank is not treated as $0."
        elif default is not None:
            kind = FIELDS[key].kind
            shown = format_value(key, default)
            if kind == "money":
                text = f"Not entered. The calculation counts it as {shown} (a built-in default, not your figure)."
            else:
                text = f"Not entered. The calculation uses {shown} (a built-in default, not your figure)."
        else:
            text = "Not entered. Nothing is calculated from it until you enter it."
        return {"state": "missing", "text": text}
    if state == "invalid":
        return {"state": "missing", "text": "The saved value is not a number, so the calculation ignores it."}
    number = _num(profile.get(key))
    if state == "zero":
        text = "Entered as 0 on purpose. A zero is a real value, not a blank."
        if key == "downside_multiplier":
            text += " The monthly view treats 0 as not entered and uses 0.6; the startup view uses your 0."
        return {"state": "zero", "text": text}
    if default is not None and number is not None and abs(number - default) < 1e-12:
        return {
            "state": "placeholder",
            "text": f"{format_value(key, number)}. Same as the built-in default, so it may be a starting number and not your own figure.",
        }
    return {"state": "estimated", "text": format_value(key, number)}


def defaults_used(profile: dict[str, Any]) -> list[dict[str, str]]:
    """Blank optional lines the calculation fills with a built-in default. Stated, not hidden."""
    rows = []
    for key in STARTUP_OPTIONAL:
        if field_state(profile.get(key)) == "missing":
            status = field_status(profile, key)
            rows.append({"field": key, "label": label(key), "text": status["text"]})
    return rows


# ---------------------------------------------------------------------------
# Basis labels
# ---------------------------------------------------------------------------


def basis_map(record: dict[str, Any] | None) -> dict[str, dict[str, str]]:
    fields = ((record or {}).get("payload") or {}).get("fields")
    if not isinstance(fields, dict):
        return {}
    result = {}
    for key, item in fields.items():
        if key in EDITABLE and isinstance(item, dict) and item.get("basis") in BASIS_CHOICES:
            result[key] = {"basis": str(item["basis"]), "value": str(item.get("value") or ""), "at": str(item.get("at") or "")}
    return result


def stored_basis(basis: dict[str, dict[str, str]], profile: dict[str, Any], key: str) -> str:
    """The label saved for a field, only while the value still matches what was labeled."""
    item = basis.get(key)
    if not item:
        return ""
    return item["basis"] if _same(item["value"], _saved_text(profile, key)) and _saved_text(profile, key) else ""


def hypothetical_fields(basis: dict[str, dict[str, str]], profile: dict[str, Any]) -> list[str]:
    return [key for key in EDITABLE if stored_basis(basis, profile, key) == "hypothetical"]


# ---------------------------------------------------------------------------
# Reading an edit
# ---------------------------------------------------------------------------


def _check(key: str, number: float) -> str:
    name = label(key)
    kind = FIELDS[key].kind
    if not math.isfinite(number) or abs(number) > _MAX:
        return f"{name} is too large to use."
    if number < 0:
        return f"{name} cannot be negative."
    if kind == "share" and not 0 <= number <= 1:
        return f"{name} must be from 0 to 1. Enter 0.40 for 40%."
    if kind == "whole" and (int(number) != number or number <= 0):
        return f"{name} must be a whole number above zero."
    if key == "operating_days" and not 0 < number <= 366:
        return f"{name} must be above 0 and at most 366."
    return ""


def stamp(profile: dict[str, Any], basis: dict[str, dict[str, str]]) -> str:
    """A fingerprint of the saved assumptions. If it changes while someone reviews, saving is refused."""
    material = {key: _saved_text(profile, key) for key in EDITABLE}
    material["_basis"] = {key: stored_basis(basis, profile, key) for key in EDITABLE}
    return hashlib.sha256(json.dumps(material, sort_keys=True).encode("utf-8")).hexdigest()[:20]


def read_proposal(profile: dict[str, Any], form: dict[str, str], basis: dict[str, dict[str, str]]) -> dict[str, Any]:
    """What the form proposes, against the saved draft. Nothing is saved here."""
    values: dict[str, str] = {}
    choices: dict[str, str] = {}
    errors: dict[str, str] = {}
    changes: list[dict[str, str]] = []
    proposed = dict(profile)
    for key in EDITABLE:
        current = _saved_text(profile, key)
        posted = f"a_{key}" in form
        raw = str(form.get(f"a_{key}") or "").strip() if posted else current
        values[key] = raw
        saved_basis = stored_basis(basis, profile, key)
        picked = str(form.get(f"b_{key}") or "").strip()
        picked = picked if picked in BASIS_CHOICES else ""
        choices[key] = picked or saved_basis
        if not posted:
            continue
        if raw == "":
            if current == "":
                continue
            if key in NEEDED:
                errors[key] = f"{label(key)} is needed for the calculation, so it cannot be cleared. Enter a value instead."
                continue
            proposed[key] = ""
            changes.append({"field": key, "label": label(key), "from": current, "to": "", "basis": "", "kind": "cleared"})
            continue
        number = _num(raw)
        if number is None:
            errors[key] = f"{label(key)} must be a number."
            continue
        problem = _check(key, number)
        if problem:
            errors[key] = problem
            continue
        canonical = plain_text(number)
        if current != "" and _same(current, canonical):
            if picked and picked != saved_basis:
                changes.append({"field": key, "label": label(key), "from": current, "to": current, "basis": picked, "kind": "label"})
            continue
        proposed[key] = canonical
        changes.append({"field": key, "label": label(key), "from": current, "to": canonical, "basis": picked or "estimate", "kind": "value"})
        choices[key] = picked or "estimate"
    return {"values": values, "choices": choices, "errors": errors, "changes": changes, "profile": proposed}


def value_changes(changes: list[dict[str, str]]) -> list[dict[str, str]]:
    return [item for item in changes if item["kind"] in {"value", "cleared"}]


def updated_basis(
    basis: dict[str, dict[str, str]], changes: list[dict[str, str]], proposed: dict[str, Any], at: str
) -> dict[str, dict[str, str]]:
    result = {key: dict(item) for key, item in basis.items()}
    for item in changes:
        key = item["field"]
        if item["kind"] == "cleared":
            result.pop(key, None)
        else:
            result[key] = {"basis": item["basis"], "value": _saved_text(proposed, key), "at": at}
    return result


# ---------------------------------------------------------------------------
# Calculation: the same path Analyze uses
# ---------------------------------------------------------------------------


def _amount(item: Any) -> float | None:
    if isinstance(item, dict):
        return d.number_of(item.get("amount"))
    return d.number_of(item)


def measures(projection: dict[str, Any] | None, financial: dict[str, Any] | None) -> dict[str, float | None]:
    out: dict[str, float | None] = {}
    if projection:
        views = projection.get("views") or {}
        sources = (projection.get("sources_and_uses") or {}).get("sources") or {}
        uses = (projection.get("sources_and_uses") or {}).get("uses") or {}
        base, down, even = views.get("base") or {}, views.get("downside") or {}, views.get("break_even") or {}
        out.update(
            {
                "total_project_cost": _amount(uses.get("total_project_cost")),
                "debt": _amount(sources.get("debt")),
                "equity": _amount(sources.get("equity")),
                "annual_debt_service": d.number_of(sources.get("annual_debt_service")),
                "base_revenue": d.number_of(base.get("revenue")),
                "base_cash_flow": d.number_of(base.get("cash_flow_before_debt_service")),
                "base_dscr": d.number_of(base.get("dscr")),
                "downside_dscr": d.number_of(down.get("dscr")),
                "break_even_revenue": d.number_of(even.get("revenue")),
            }
        )
    if financial:
        out.update(
            {
                "base_monthly_cash_flow": d.number_of(financial.get("base_monthly_cash_flow")),
                "downside_monthly_cash_flow": d.number_of(financial.get("downside_monthly_cash_flow")),
                "break_even_monthly_revenue": d.number_of(financial.get("break_even_monthly_revenue")),
                "months_to_break_even": d.number_of(financial.get("months_to_break_even_base")),
            }
        )
    return out


def run(profile: dict[str, Any]) -> dict[str, Any]:
    """Calculate a profile with the same path Analyze uses. Nothing is stored."""
    preview = calculate_preview(profile)
    return {
        "preview": preview,
        "measures": measures(preview.get("projection"), preview.get("financial")),
        "cash": improve.entered(profile, "available_cash"),
    }


def official_measures(result: dict[str, Any] | None) -> dict[str, float | None]:
    if not isinstance(result, dict) or not result.get("engine_ran"):
        return {}
    projection = result.get("projection")
    projection = projection if isinstance(projection, dict) and projection.get("calculated") else None
    financial = result.get("financial") if isinstance(result.get("financial"), dict) else None
    return measures(projection, financial)


def funding_gap(values: dict[str, float | None], cash: float | None) -> dict[str, Any]:
    """Total cost, debt, equity, your cash, and what is still unfunded. Cash is not equity until you commit it."""
    total, debt, equity = values.get("total_project_cost"), values.get("debt"), values.get("equity")
    if total is None or debt is None or equity is None:
        return {"calculated": False}
    remaining = None if cash is None else round(max(0.0, equity - cash), 2)
    left_over = None if cash is None else round(max(0.0, cash - equity), 2)
    return {
        "calculated": True,
        "total": total,
        "debt": debt,
        "equity": equity,
        "cash": cash,
        "remaining": remaining,
        "left_over": left_over,
    }


def example_for(profile: dict[str, Any]) -> dict[str, str]:
    """Illustrative restaurant figures for blank cost lines only. Empty for other industries or when nothing is blank."""
    if family_for(str(profile.get("industry") or "")) != "hospitality":
        return {}
    return {key: value for key, value in EXAMPLE_VALUES.items() if field_state(profile.get(key)) == "missing"}


def draft_differs(record: dict[str, Any]) -> list[str] | None:
    """Fields whose saved draft value differs from what the stored official run used. None when it cannot be told."""
    if record.get("read_only"):
        return []
    intake = record.get("intake")
    result = record.get("result")
    if not isinstance(intake, dict) or not isinstance(result, dict) or not result.get("engine_ran"):
        return None
    current, _missing = profile_to_intake(record.get("profile") or {}, as_of_date="2026-01-01")
    changed = []
    sources = (
        (current.get("startup_capital") or {}, intake.get("startup_capital") or {}, tuple(improve.FIELDS)),
        (current.get("financial_inputs") or {}, intake.get("financial_inputs") or {}, MONTHLY),
    )
    for now, then, keys in sources:
        for key in keys:
            left, right = now.get(key), then.get(key)
            if (left is None) != (right is None) or (left is not None and abs(float(left) - float(right)) > 1e-9):
                if key not in changed:
                    changed.append(key)
    return changed


def as_analyzed(record: dict[str, Any], differs: list[str] | None) -> dict[str, Any]:
    """The profile as the stored official run saw it. A draft edited since then must not relabel the official figures."""
    profile = dict(record.get("profile") or {})
    if not differs:
        return profile
    intake = record.get("intake") or {}
    sources = (intake.get("startup_capital") or {}, intake.get("financial_inputs") or {})
    for key in differs:
        value = next((source[key] for source in sources if key in source), None)
        profile[key] = "" if value is None else plain_text(float(value))
    return profile


def build_view(record: dict[str, Any], form: dict[str, str], basis: dict[str, dict[str, str]]) -> dict[str, Any]:
    """Everything the page shows: the proposal, the calculation for the saved draft and for the proposal, and the official figures."""
    profile = record.get("profile") or {}
    proposal = read_proposal(profile, form, basis)
    return {
        "record": record,
        "basis": basis,
        "proposal": proposal,
        "stamp": stamp(profile, basis),
        "draft_run": run(profile),
        "proposed_run": run(proposal["profile"]),
        "official": official_measures(record.get("result")),
    }

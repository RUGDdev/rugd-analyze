"""
Startup capital and projection path.

Methodology § Core Principles — deterministic calculations stay in code, and
verified data stays distinct from user-supplied assumptions.
Methodology § Core Principles — human approval is required before a final
recommendation.
Methodology § Evaluation Dimensions — item 3, financial feasibility and
capital requirements.
Methodology § Investor Readiness Gate — this path does not mark an assessment
investor-ready.
Architecture § Analysis Layer — deterministic financial engine.

Construction cost is required. Equipment, soft costs, and pre-opening working
capital are dollar amounts. Contingency defaults to 10 percent of those four
lines. Debt terms use the same coded shares already in the startup calculator.
Seat, ticket, and occupancy figures have no defaults here.
"""

from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from engine.financial import seat_occupancy_revenue

USER_SUPPLIED_ASSUMPTION = "user-supplied assumption"
VERIFIED_DATA = "verified data"
MODEL_ASSUMPTION = "model assumption"

DEFAULT_CONTINGENCY_PCT = 0.10
DEFAULT_DEBT_SHARE = 0.70
DEFAULT_ANNUAL_INTEREST_RATE = 0.08
DEFAULT_AMORTIZATION_YEARS = 20
DEFAULT_DOWNSIDE_MULTIPLIER = 0.6

INPUT_KEYS = (
    "construction_cost",
    "equipment",
    "soft_costs",
    "preopening_working_capital",
    "contingency_pct",
    "debt_share",
    "annual_interest_rate",
    "amortization_years",
    "seats",
    "average_ticket",
    "weekday_occupancy",
    "weekend_occupancy",
    "operating_days",
    "annual_fixed_costs",
    "contribution_margin",
    "downside_multiplier",
)

MODEL_NOTES = (
    "Contingency equals contingency_pct times (construction + equipment + soft costs + pre-opening working capital).",
    "Total project cost equals that subtotal plus contingency.",
    "Debt equals debt_share times total project cost. Equity is the residual after debt is rounded to cents.",
    "Annual debt service is twelve monthly level payments. Each monthly payment is rounded half-even to cents, then multiplied by 12. A zero interest rate sets the monthly payment to debt divided by the number of months.",
    "Base revenue is seats × occupancy × average ticket × operating days, from engine.financial.seat_occupancy_revenue.",
    "The downside view multiplies weekday occupancy and weekend occupancy by downside_multiplier, then recomputes that revenue. The default multiplier is 0.6.",
    "Cash flow before debt service equals revenue × contribution_margin − annual fixed costs.",
    "Break-even revenue equals (annual fixed costs + annual debt service) / contribution_margin when the margin is positive.",
    "DSCR equals cash flow before debt service divided by annual debt service. DSCR is undefined when rounded annual debt service is zero.",
    "Debt share 0.70, interest 0.08, and 20-year amortization are the coded terms already used by the startup calculator. They are not a market study.",
)


@dataclass(frozen=True)
class StartupProjection:
    sources_and_uses: dict[str, Any]
    assumptions: tuple[dict[str, Any], ...]
    base: dict[str, Any]
    downside: dict[str, Any]
    break_even: dict[str, Any]
    human_review_approved: bool
    is_final: bool
    investor_ready: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "calculated": True,
            "methodology_refs": _METHODOLOGY_REFS,
            "human_review_approved": self.human_review_approved,
            "is_final": self.is_final,
            "investor_ready": self.investor_ready,
            "sources_and_uses": self.sources_and_uses,
            "assumptions": [dict(item) for item in self.assumptions],
            "views": {
                "base": self.base,
                "downside": self.downside,
                "break_even": self.break_even,
            },
        }


_METHODOLOGY_REFS = (
    "Methodology § Core Principles — deterministic calculations",
    "Methodology § Core Principles — human approval required for final recommendations",
    "Methodology § Evaluation Dimensions — Financial Feasibility & Capital Requirements",
    "Methodology § Investor Readiness Gate",
    "Architecture § Analysis Layer",
)


def project_startup(
    construction_cost: float,
    seats: float,
    average_ticket: float,
    weekday_occupancy: float,
    weekend_occupancy: float,
    operating_days: float,
    contribution_margin: float,
    *,
    equipment: float = 0,
    soft_costs: float = 0,
    preopening_working_capital: float = 0,
    contingency_pct: float = DEFAULT_CONTINGENCY_PCT,
    debt_share: float = DEFAULT_DEBT_SHARE,
    annual_interest_rate: float = DEFAULT_ANNUAL_INTEREST_RATE,
    amortization_years: int = DEFAULT_AMORTIZATION_YEARS,
    annual_fixed_costs: float = 0,
    downside_multiplier: float = DEFAULT_DOWNSIDE_MULTIPLIER,
    verified: Mapping[str, bool] | None = None,
    human_review_approved: bool = False,
) -> StartupProjection:
    """Cost build plus base, downside, and break-even views.

    Methodology § Core Principles. investor_ready stays false. is_final is
    true only when human_review_approved is explicitly true.
    """
    flags = _verified_flags(verified)
    values = {
        "construction_cost": _money("construction_cost", construction_cost, minimum=0.01),
        "equipment": _money("equipment", equipment, minimum=0),
        "soft_costs": _money("soft_costs", soft_costs, minimum=0),
        "preopening_working_capital": _money(
            "preopening_working_capital", preopening_working_capital, minimum=0
        ),
        "contingency_pct": _share("contingency_pct", contingency_pct),
        "debt_share": _share("debt_share", debt_share),
        "annual_interest_rate": _share("annual_interest_rate", annual_interest_rate),
        "amortization_years": _years(amortization_years),
        "seats": _whole("seats", seats),
        "average_ticket": _money("average_ticket", average_ticket, minimum=0),
        "weekday_occupancy": _share("weekday_occupancy", weekday_occupancy),
        "weekend_occupancy": _share("weekend_occupancy", weekend_occupancy),
        "operating_days": _days(operating_days),
        "annual_fixed_costs": _money("annual_fixed_costs", annual_fixed_costs, minimum=0),
        "contribution_margin": _share("contribution_margin", contribution_margin),
        "downside_multiplier": _nonnegative("downside_multiplier", downside_multiplier),
    }
    approved = human_review_approved is True
    subtotal = (
        values["construction_cost"]
        + values["equipment"]
        + values["soft_costs"]
        + values["preopening_working_capital"]
    )
    contingency = round(subtotal * values["contingency_pct"], 2)
    total = round(subtotal + contingency, 2)
    debt = round(total * values["debt_share"], 2)
    equity = round(total - debt, 2)
    monthly_debt, annual_debt = _debt_service(
        debt, values["annual_interest_rate"], int(values["amortization_years"])
    )
    revenue_verified = {
        key: flags[key]
        for key in (
            "seats",
            "average_ticket",
            "weekday_occupancy",
            "weekend_occupancy",
            "operating_days",
        )
    }
    base_revenue = seat_occupancy_revenue(
        values["seats"],
        values["average_ticket"],
        values["weekday_occupancy"],
        values["weekend_occupancy"],
        values["operating_days"],
        verified=revenue_verified,
    )
    downside_weekday = values["weekday_occupancy"] * values["downside_multiplier"]
    downside_weekend = values["weekend_occupancy"] * values["downside_multiplier"]
    downside_revenue = seat_occupancy_revenue(
        values["seats"],
        values["average_ticket"],
        downside_weekday,
        downside_weekend,
        values["operating_days"],
    )
    margin = values["contribution_margin"]
    fixed = values["annual_fixed_costs"]
    base_cash = round(base_revenue.revenue * margin - fixed, 2)
    downside_cash = round(downside_revenue.revenue * margin - fixed, 2)
    if margin > 0:
        break_even = round((fixed + annual_debt) / margin, 2)
    else:
        break_even = None
    sources = _sources_and_uses(
        values, contingency, total, debt, equity, monthly_debt, annual_debt, flags
    )
    assumptions = _assumption_list(values, flags)
    return StartupProjection(
        sources_and_uses=sources,
        assumptions=assumptions,
        base={
            "revenue": base_revenue.revenue,
            "occupancy": base_revenue.occupancy,
            "cash_flow_before_debt_service": base_cash,
            "dscr": _dscr(base_cash, annual_debt),
        },
        downside={
            "multiplier": values["downside_multiplier"],
            "applied_to": "occupancy",
            "weekday_occupancy": downside_weekday,
            "weekend_occupancy": downside_weekend,
            "revenue": downside_revenue.revenue,
            "cash_flow_before_debt_service": downside_cash,
            "dscr": _dscr(downside_cash, annual_debt),
        },
        break_even={
            "revenue": break_even,
            "covers": "annual fixed costs plus annual debt service",
        },
        human_review_approved=approved,
        is_final=approved,
        investor_ready=False,
    )


def record_for_intake(
    intake: Mapping[str, Any],
    *,
    human_review_approved: bool = False,
) -> dict[str, Any]:
    """Audit record for an intake. A missing worksheet invents no figures."""
    worksheet = intake.get("startup_capital")
    if worksheet is None:
        return empty_projection(human_review_approved=human_review_approved)
    if not isinstance(worksheet, Mapping):
        raise ValueError("startup_capital must be an object")
    return projection_from_worksheet(
        worksheet, human_review_approved=human_review_approved
    ).to_dict()


def worksheet_errors(worksheet: Any) -> list[str]:
    if worksheet is None:
        return []
    if not isinstance(worksheet, dict):
        return ["startup_capital must be an object"]
    errors = []
    required = (
        "construction_cost",
        "seats",
        "average_ticket",
        "weekday_occupancy",
        "weekend_occupancy",
        "operating_days",
        "contribution_margin",
    )
    for key in required:
        if key not in worksheet:
            errors.append(f"startup_capital missing {key}")
    verified = worksheet.get("verified")
    if verified is not None and not isinstance(verified, dict):
        errors.append("startup_capital.verified must be an object")
    return errors


def empty_projection(*, human_review_approved: bool = False) -> dict[str, Any]:
    """Worksheet was not supplied. No cost or revenue figures are invented."""
    approved = human_review_approved is True
    return {
        "calculated": False,
        "methodology_refs": list(_METHODOLOGY_REFS),
        "note": (
            "Construction cost was not supplied. The cost build and the three "
            "views were not calculated."
        ),
        "human_review_approved": approved,
        "is_final": approved,
        "investor_ready": False,
        "sources_and_uses": None,
        "assumptions": [],
        "views": None,
    }


def projection_from_worksheet(
    worksheet: Mapping[str, Any],
    *,
    human_review_approved: bool = False,
) -> StartupProjection:
    """Build a projection from a structured worksheet. Missing optional lines use coded defaults."""
    required = (
        "construction_cost",
        "seats",
        "average_ticket",
        "weekday_occupancy",
        "weekend_occupancy",
        "operating_days",
        "contribution_margin",
    )
    missing = [key for key in required if key not in worksheet]
    if missing:
        raise ValueError("startup capital worksheet missing " + ", ".join(missing))
    verified = worksheet.get("verified")
    if verified is not None and not isinstance(verified, Mapping):
        raise ValueError("startup capital verified must be a mapping")
    optional = {
        key: worksheet[key]
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
        )
        if key in worksheet
    }
    return project_startup(
        worksheet["construction_cost"],
        worksheet["seats"],
        worksheet["average_ticket"],
        worksheet["weekday_occupancy"],
        worksheet["weekend_occupancy"],
        worksheet["operating_days"],
        worksheet["contribution_margin"],
        verified=verified,
        human_review_approved=human_review_approved,
        **optional,
    )


def format_projection(record: Mapping[str, Any]) -> str:
    """Sources-and-uses summary and assumption list for the report."""
    lines = [
        "Methodology § Core Principles — deterministic calculations, and human approval before a final recommendation.",
        "Methodology § Investor Readiness Gate — this path does not mark the assessment investor-ready.",
        f"human_review_approved: {str(record['human_review_approved']).lower()}",
        f"is_final: {str(record['is_final']).lower()}",
        "investor_ready: false",
    ]
    if not record.get("calculated"):
        lines.append(str(record["note"]))
        return "\n".join(lines)
    uses = record["sources_and_uses"]["uses"]
    sources = record["sources_and_uses"]["sources"]
    lines.append("")
    lines.append("### Sources and uses")
    lines.append("Uses")
    for key in (
        "construction_cost",
        "equipment",
        "soft_costs",
        "preopening_working_capital",
        "contingency",
        "total_project_cost",
    ):
        lines.append(f"- {key}: {_money_text(uses[key])}")
    lines.append("Sources")
    for key in ("debt", "equity", "total_sources"):
        lines.append(f"- {key}: {_money_text(sources[key])}")
    lines.append(f"- annual_debt_service: {_money_text(sources['annual_debt_service'])}")
    lines.append("")
    lines.append("### Assumption list")
    for item in record["assumptions"]:
        lines.append(
            f"- {item['key']} = {item['value']} ({item['evidence_label']})"
        )
    views = record["views"]
    base = views["base"]
    downside = views["downside"]
    break_even = views["break_even"]
    lines.extend(
        [
            "",
            "### Base case",
            f"- Revenue: {_money_text(base['revenue'])}",
            f"- Cash flow before debt service: {_money_text(base['cash_flow_before_debt_service'])}",
            f"- DSCR: {_dscr_text(base['dscr'])}",
            "",
            "### Downside case",
            (
                f"- downside_multiplier {downside['multiplier']} applied to occupancy."
            ),
            f"- Revenue: {_money_text(downside['revenue'])}",
            f"- Cash flow before debt service: {_money_text(downside['cash_flow_before_debt_service'])}",
            f"- DSCR: {_dscr_text(downside['dscr'])}",
            "",
            "### Break-even",
            f"- Revenue needed to cover fixed costs plus debt service: {_money_text(break_even['revenue'])}",
        ]
    )
    return "\n".join(lines)


def _sources_and_uses(
    values: dict[str, float],
    contingency: float,
    total: float,
    debt: float,
    equity: float,
    monthly_debt: float,
    annual_debt: float,
    flags: dict[str, bool],
) -> dict[str, Any]:
    def labeled(key: str) -> dict[str, Any]:
        return {"amount": values[key], "evidence_label": _label(flags[key])}

    return {
        "uses": {
            "construction_cost": labeled("construction_cost"),
            "equipment": labeled("equipment"),
            "soft_costs": labeled("soft_costs"),
            "preopening_working_capital": labeled("preopening_working_capital"),
            "contingency": {
                "amount": contingency,
                "evidence_label": "calculated by the deterministic engine",
            },
            "total_project_cost": {
                "amount": total,
                "evidence_label": "calculated by the deterministic engine",
            },
        },
        "sources": {
            "debt": {
                "amount": debt,
                "evidence_label": "calculated by the deterministic engine",
            },
            "equity": {
                "amount": equity,
                "evidence_label": "calculated by the deterministic engine",
            },
            "total_sources": {
                "amount": total,
                "evidence_label": "calculated by the deterministic engine",
            },
            "monthly_debt_service": monthly_debt,
            "annual_debt_service": annual_debt,
        },
    }


def _assumption_list(values: dict[str, float], flags: dict[str, bool]) -> tuple[dict[str, Any], ...]:
    items = [
        {
            "key": key,
            "value": values[key],
            "source": "verified" if flags[key] else "user",
            "evidence_label": _label(flags[key]),
        }
        for key in INPUT_KEYS
    ]
    items.extend(
        {"key": note, "value": None, "source": "model", "evidence_label": MODEL_ASSUMPTION}
        for note in MODEL_NOTES
    )
    return tuple(items)


def _label(verified: bool) -> str:
    return VERIFIED_DATA if verified else USER_SUPPLIED_ASSUMPTION


def _verified_flags(verified: Mapping[str, bool] | None) -> dict[str, bool]:
    if verified is None:
        return {key: False for key in INPUT_KEYS}
    if not isinstance(verified, Mapping):
        raise ValueError("verified must map each startup input to true or false")
    unknown = set(verified) - set(INPUT_KEYS)
    if unknown:
        raise ValueError("unknown verified startup input: " + ", ".join(sorted(unknown)))
    flags = {}
    for key in INPUT_KEYS:
        flag = verified.get(key, False)
        if not isinstance(flag, bool):
            raise ValueError(f"verified[{key}] must be true or false")
        flags[key] = flag
    return flags


def _money_text(value: Any) -> str:
    if isinstance(value, dict):
        amount = value.get("amount")
        label = value.get("evidence_label", "")
        if amount is None:
            return f"not defined ({label})"
        return f"{amount:.2f} ({label})"
    if value is None:
        return "not defined"
    return f"{value:.2f}"


def _dscr_text(value: float | None) -> str:
    if value is None:
        return "undefined"
    return f"{value:.4f}"


def _debt_service(debt: float, annual_rate: float, years: int) -> tuple[float, float]:
    months = years * 12
    if debt == 0:
        return 0.0, 0.0
    if annual_rate == 0:
        monthly = round(debt / months, 2)
    else:
        periodic = annual_rate / 12
        growth = (1 + periodic) ** months
        monthly = round(debt * (periodic * growth) / (growth - 1), 2)
    return monthly, round(monthly * 12, 2)


def _dscr(cash_flow: float, annual_debt_service: float) -> float | None:
    if annual_debt_service == 0:
        return None
    return round(cash_flow / annual_debt_service, 4)


def _money(name: str, value: Any, *, minimum: float) -> float:
    number = _finite(name, value)
    if number < minimum:
        raise ValueError(f"{name} must be >= {minimum}")
    return round(number, 2)


def _share(name: str, value: Any) -> float:
    number = _finite(name, value)
    if number < 0 or number > 1:
        raise ValueError(f"{name} must be from 0 to 1")
    return number


def _nonnegative(name: str, value: Any) -> float:
    number = _finite(name, value)
    if number < 0:
        raise ValueError(f"{name} must be >= 0")
    return number


def _whole(name: str, value: Any) -> float:
    number = _finite(name, value)
    if number < 0 or int(number) != number:
        raise ValueError(f"{name} must be a whole number >= 0")
    return number


def _days(value: Any) -> float:
    number = _finite("operating_days", value)
    if number <= 0 or number > 366:
        raise ValueError("operating_days must be > 0 and <= 366")
    return number


def _years(value: Any) -> float:
    number = _finite("amortization_years", value)
    if number < 1 or number > 100 or int(number) != number:
        raise ValueError("amortization_years must be a whole number from 1 to 100")
    return number


def _finite(name: str, value: Any) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(f"{name} must be a finite number")
    return float(value)

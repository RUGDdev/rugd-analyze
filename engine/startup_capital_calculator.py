"""
Startup capital calculator for the RUGD pilot.

Methodology § Core Principles — financial arithmetic stays in code, and
verified data, user inputs, and model assumptions stay distinct.
Methodology § Evaluation Dimensions — item 3, financial feasibility and
capital requirements.
Methodology § Output Requirements — base and downside figures. This file
does not issue the go / conditional / do-not-proceed recommendation.
That remains in scoring/rules.py, which this module does not call.

Year-1 food and beverage revenue is seats × average ticket × operating
days × the weekday/weekend occupancy mix. Ticketed events and a small
other-revenue share are added after that. Pressing Enter accepts a coded
default. The seat, ticket, occupancy, day-count, and event defaults below
are the pilot figures requested for this calculator. /docs contain no
separate market study. The 5/7 weekday split, one cover per occupied seat
per day, the 0.02 other-revenue share, the EBITDA margin, and the downside
multiplier are model assumptions.

Human review is required before any capital decision.
"""

from __future__ import annotations

import json
import math
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from engine.financial import seat_occupancy_revenue

OUTPUT_PATH = PROJECT_ROOT / "output" / "startup_capital_result.json"
MODEL_VERSION = "0.1-pilot"

# Coded defaults. Same press of Enter always feeds these constants.
# 0.60 matches FinancialInputs.downside_revenue_multiplier in engine/financial.py.
DEFAULT_SOFT_COST_PCT = 0.15
DEFAULT_CONTINGENCY_PCT = 0.10
DEFAULT_DEBT_SHARE = 0.70
DEFAULT_ANNUAL_INTEREST_RATE = 0.08
DEFAULT_AMORTIZATION_YEARS = 20
DEFAULT_SEATS = 200
DEFAULT_AVERAGE_TICKET = 28.0
DEFAULT_WEEKDAY_OCCUPANCY = 0.45
DEFAULT_WEEKEND_OCCUPANCY = 0.75
DEFAULT_OPERATING_DAYS = 360
DEFAULT_TICKETED_EVENTS = 350_000.0
DEFAULT_OTHER_REVENUE_PCT = 0.02
DEFAULT_EBITDA_MARGIN = 0.20
DEFAULT_DOWNSIDE_REVENUE_MULTIPLIER = 0.60

ASSUMPTIONS: tuple[str, ...] = (
    "Soft costs equal soft_cost_pct times construction cost.",
    "Contingency equals contingency_pct times (construction cost + soft costs).",
    "Total project cost equals construction + soft costs + contingency. Land, FF&E, and working capital are not separate lines.",
    "Debt equals debt_share times total project cost. Equity is the residual after debt is rounded to cents.",
    "Annual debt service is twelve monthly level payments on the debt at the nominal annual interest rate, amortized over amortization_years. Each monthly payment is rounded half-even to cents, then multiplied by 12.",
    "A zero interest rate sets the monthly payment to debt divided by the number of months.",
    "Operating days are split 5/7 weekday and 2/7 weekend. The revenue formula uses that exact weight, not a rounded day count.",
    "Food and beverage revenue equals seats × average ticket × operating days × ((weekday occupancy × 5) + (weekend occupancy × 2)) / 7. That is one cover per occupied seat per operating day. Table turns are not in this model.",
    "Other revenue equals other_revenue_pct times food and beverage revenue. The 0.02 default is a coded small share. It is not a figure from /docs.",
    "Year-1 revenue equals food and beverage revenue + ticketed events + other revenue.",
    "Downside food and beverage revenue and downside ticketed events equal the base amounts times downside_revenue_multiplier. Other revenue is then recalculated from downside food and beverage revenue. Debt service stays at the contractual amount. The default multiplier is 0.60, the same constant as FinancialInputs.downside_revenue_multiplier, and it is not a measured demand shock.",
    "EBITDA equals ebitda_margin times that year's total revenue. The margin is the same in the base case and the downside case.",
    "Cash flow before debt service equals EBITDA. Tax, depreciation, working capital, and replacement reserves are not in this model.",
    "Cash flow after debt service equals cash flow before debt service minus annual debt service.",
    "DSCR equals cash flow before debt service divided by annual debt service. DSCR is undefined when rounded annual debt service is zero.",
    "Amounts have no currency unit.",
    "Money is rounded half-even to cents. DSCR is rounded half-even to four decimal places.",
    "Coded defaults are model assumptions. /docs contain no market study, so the defaults are not verified market benchmarks.",
    "This calculator does not call scoring/rules.py and does not issue a recommendation. Human review is required before any capital decision (Methodology § Core Principles).",
)


@dataclass(frozen=True)
class StartupInputs:
    construction_cost: float
    soft_cost_pct: float = DEFAULT_SOFT_COST_PCT
    contingency_pct: float = DEFAULT_CONTINGENCY_PCT
    debt_share: float = DEFAULT_DEBT_SHARE
    annual_interest_rate: float = DEFAULT_ANNUAL_INTEREST_RATE
    amortization_years: int = DEFAULT_AMORTIZATION_YEARS
    seats: int = DEFAULT_SEATS
    average_ticket: float = DEFAULT_AVERAGE_TICKET
    weekday_occupancy: float = DEFAULT_WEEKDAY_OCCUPANCY
    weekend_occupancy: float = DEFAULT_WEEKEND_OCCUPANCY
    operating_days: int = DEFAULT_OPERATING_DAYS
    ticketed_events: float = DEFAULT_TICKETED_EVENTS
    other_revenue_pct: float = DEFAULT_OTHER_REVENUE_PCT
    ebitda_margin: float = DEFAULT_EBITDA_MARGIN
    downside_revenue_multiplier: float = DEFAULT_DOWNSIDE_REVENUE_MULTIPLIER


@dataclass(frozen=True)
class StartupResult:
    construction_cost: float
    soft_costs: float
    contingency: float
    total_project_cost: float
    debt: float
    equity: float
    monthly_debt_service: float
    annual_debt_service: float
    weekday_operating_days: float
    weekend_operating_days: float
    food_and_beverage_revenue_base: float
    food_and_beverage_revenue_downside: float
    ticketed_events_base: float
    ticketed_events_downside: float
    other_revenue_base: float
    other_revenue_downside: float
    year1_revenue_base: float
    year1_revenue_downside: float
    ebitda_base: float
    ebitda_downside: float
    cash_flow_before_debt_service_base: float
    cash_flow_before_debt_service_downside: float
    cash_flow_after_debt_service_base: float
    cash_flow_after_debt_service_downside: float
    dscr_base: float | None
    dscr_downside: float | None
    observations: tuple[str, ...]
    revenue_assumption_sources: tuple[dict[str, Any], ...] = ()


def calculate(inputs: StartupInputs) -> StartupResult:
    """Pure arithmetic. Methodology § Core Principles."""
    construction = _money_input("construction_cost", inputs.construction_cost, minimum=0.01)
    soft_pct = _share("soft_cost_pct", inputs.soft_cost_pct)
    contingency_pct = _share("contingency_pct", inputs.contingency_pct)
    debt_share = _share("debt_share", inputs.debt_share)
    interest = _share("annual_interest_rate", inputs.annual_interest_rate)
    years = _years(inputs.amortization_years)
    seats = _count("seats", inputs.seats, minimum=1, maximum=100_000)
    average_ticket = _money_input("average_ticket", inputs.average_ticket, minimum=0.01)
    weekday_occupancy = _share("weekday_occupancy", inputs.weekday_occupancy)
    weekend_occupancy = _share("weekend_occupancy", inputs.weekend_occupancy)
    operating_days = _count("operating_days", inputs.operating_days, minimum=1, maximum=366)
    ticketed_events = _money_input("ticketed_events", inputs.ticketed_events, minimum=0)
    other_pct = _share("other_revenue_pct", inputs.other_revenue_pct)
    margin = _share("ebitda_margin", inputs.ebitda_margin)
    downside_multiplier = _nonnegative(
        "downside_revenue_multiplier", inputs.downside_revenue_multiplier
    )

    soft_costs = round(construction * soft_pct, 2)
    contingency = round((construction + soft_costs) * contingency_pct, 2)
    total = round(construction + soft_costs + contingency, 2)
    debt = round(total * debt_share, 2)
    equity = round(total - debt, 2)

    monthly, annual = _debt_service(debt, interest, years)
    weekday_days = round(operating_days * 5 / 7, 4)
    weekend_days = round(operating_days * 2 / 7, 4)
    food = seat_occupancy_revenue(
        seats,
        average_ticket,
        weekday_occupancy,
        weekend_occupancy,
        operating_days,
    )
    food_base = food.revenue
    events_base = ticketed_events
    other_base = round(food_base * other_pct, 2)
    revenue_base = round(food_base + events_base + other_base, 2)
    food_downside = round(food_base * downside_multiplier, 2)
    events_downside = round(events_base * downside_multiplier, 2)
    other_downside = round(food_downside * other_pct, 2)
    revenue_downside = round(food_downside + events_downside + other_downside, 2)
    ebitda_base = round(revenue_base * margin, 2)
    ebitda_downside = round(revenue_downside * margin, 2)
    cash_before_base = ebitda_base
    cash_before_downside = ebitda_downside
    cash_after_base = round(cash_before_base - annual, 2)
    cash_after_downside = round(cash_before_downside - annual, 2)
    dscr_base = _dscr(cash_before_base, annual)
    dscr_downside = _dscr(cash_before_downside, annual)

    observations: list[str] = []
    if cash_before_base <= 0 and cash_before_downside <= 0:
        observations.append(
            "Base and downside cash flow before debt service are both zero or negative."
        )
    if dscr_base is not None and dscr_base < 1:
        observations.append("Base DSCR is below 1.00.")
    if dscr_downside is not None and dscr_downside < 1:
        observations.append("Downside DSCR is below 1.00.")
    if not observations:
        observations.append("No cash-flow or DSCR observation fired on the rounded figures.")

    return StartupResult(
        construction_cost=construction,
        soft_costs=soft_costs,
        contingency=contingency,
        total_project_cost=total,
        debt=debt,
        equity=equity,
        monthly_debt_service=monthly,
        annual_debt_service=annual,
        weekday_operating_days=weekday_days,
        weekend_operating_days=weekend_days,
        food_and_beverage_revenue_base=food_base,
        food_and_beverage_revenue_downside=food_downside,
        ticketed_events_base=events_base,
        ticketed_events_downside=events_downside,
        other_revenue_base=other_base,
        other_revenue_downside=other_downside,
        year1_revenue_base=revenue_base,
        year1_revenue_downside=revenue_downside,
        ebitda_base=ebitda_base,
        ebitda_downside=ebitda_downside,
        cash_flow_before_debt_service_base=cash_before_base,
        cash_flow_before_debt_service_downside=cash_before_downside,
        cash_flow_after_debt_service_base=cash_after_base,
        cash_flow_after_debt_service_downside=cash_after_downside,
        dscr_base=dscr_base,
        dscr_downside=dscr_downside,
        observations=tuple(observations),
        revenue_assumption_sources=food.assumption_sources,
    )


def build_record(
    inputs: StartupInputs,
    sources: dict[str, str],
    result: StartupResult,
) -> dict[str, Any]:
    uses_defaults = any(source == "coded_model_default" for source in sources.values())
    return {
        "model_version": MODEL_VERSION,
        "methodology_refs": [
            "Methodology § Core Principles",
            "Methodology § Evaluation Dimensions — Financial Feasibility & Capital Requirements",
            "Methodology § Output Requirements — base and downside",
        ],
        "is_final": False,
        "requires_human_review": True,
        "human_review_status": "pending",
        "recommendation": None,
        "scoring_applied": False,
        "uses_coded_defaults": uses_defaults,
        "inputs": {
            "construction_cost": _field(inputs.construction_cost, sources, "construction_cost"),
            "soft_cost_pct": _field(inputs.soft_cost_pct, sources, "soft_cost_pct"),
            "contingency_pct": _field(inputs.contingency_pct, sources, "contingency_pct"),
            "debt_share": _field(inputs.debt_share, sources, "debt_share"),
            "annual_interest_rate": _field(
                inputs.annual_interest_rate, sources, "annual_interest_rate"
            ),
            "amortization_years": _field(
                inputs.amortization_years, sources, "amortization_years"
            ),
            "seats": _field(inputs.seats, sources, "seats"),
            "average_ticket": _field(inputs.average_ticket, sources, "average_ticket"),
            "weekday_occupancy": _field(
                inputs.weekday_occupancy, sources, "weekday_occupancy"
            ),
            "weekend_occupancy": _field(
                inputs.weekend_occupancy, sources, "weekend_occupancy"
            ),
            "operating_days": _field(inputs.operating_days, sources, "operating_days"),
            "ticketed_events": _field(inputs.ticketed_events, sources, "ticketed_events"),
            "other_revenue_pct": _field(
                inputs.other_revenue_pct, sources, "other_revenue_pct"
            ),
            "ebitda_margin": _field(inputs.ebitda_margin, sources, "ebitda_margin"),
            "downside_revenue_multiplier": _field(
                inputs.downside_revenue_multiplier,
                sources,
                "downside_revenue_multiplier",
            ),
        },
        "results": {
            "total_project_cost": result.total_project_cost,
            "soft_costs": result.soft_costs,
            "contingency": result.contingency,
            "debt": result.debt,
            "equity": result.equity,
            "monthly_debt_service": result.monthly_debt_service,
            "annual_debt_service": result.annual_debt_service,
            "weekday_operating_days": result.weekday_operating_days,
            "weekend_operating_days": result.weekend_operating_days,
            "food_and_beverage_revenue_base": result.food_and_beverage_revenue_base,
            "food_and_beverage_revenue_downside": result.food_and_beverage_revenue_downside,
            "ticketed_events_base": result.ticketed_events_base,
            "ticketed_events_downside": result.ticketed_events_downside,
            "other_revenue_base": result.other_revenue_base,
            "other_revenue_downside": result.other_revenue_downside,
            "year1_revenue_base": result.year1_revenue_base,
            "year1_revenue_downside": result.year1_revenue_downside,
            "ebitda_base": result.ebitda_base,
            "ebitda_downside": result.ebitda_downside,
            "cash_flow_before_debt_service_base": result.cash_flow_before_debt_service_base,
            "cash_flow_before_debt_service_downside": result.cash_flow_before_debt_service_downside,
            "cash_flow_after_debt_service_base": result.cash_flow_after_debt_service_base,
            "cash_flow_after_debt_service_downside": result.cash_flow_after_debt_service_downside,
            "dscr_base": result.dscr_base,
            "dscr_downside": result.dscr_downside,
            "observations": list(result.observations),
        },
        "revenue_assumption_sources": [dict(item) for item in result.revenue_assumption_sources],
        "assumptions": list(ASSUMPTIONS),
    }


def write_record(record: dict[str, Any], path: Path = OUTPUT_PATH) -> Path:
    resolved = path.resolve()
    root = PROJECT_ROOT.resolve()
    if resolved != root and root not in resolved.parents:
        raise ValueError(f"path must stay inside {root}")
    resolved.parent.mkdir(parents=True, exist_ok=True)
    resolved.write_text(json.dumps(record, indent=2), encoding="utf-8")
    return resolved


def main() -> int:
    print("RUGD startup capital calculator (model 0.1-pilot)")
    print("Methodology § Core Principles — deterministic arithmetic.")
    print(
        "Methodology § Evaluation Dimensions — financial feasibility and capital requirements."
    )
    print("Press Enter to accept the coded default shown in brackets.")
    print(
        "Revenue is seats x average ticket x occupancy x operating days, plus ticketed events and other revenue."
    )
    print(
        "The seat, ticket, occupancy, day-count, and event defaults are the pilot figures requested for this calculator."
    )
    print(
        "The weekday/weekend split, one cover per occupied seat, the 0.02 other-revenue share, the EBITDA margin, and the downside multiplier are model assumptions. /docs contain no separate market study."
    )
    print(
        "This calculator does not issue a go / conditional / do-not-proceed recommendation."
    )
    print()
    try:
        inputs, sources = _prompt_inputs()
        result = calculate(inputs)
    except EOFError:
        print("Input ended before the calculator finished.", file=sys.stderr)
        return 2
    record = build_record(inputs, sources, result)
    path = write_record(record)
    _print_result(result, path)
    return 0


def _prompt_inputs() -> tuple[StartupInputs, dict[str, str]]:
    construction, construction_source = _prompt_float(
        "Construction cost",
        default=None,
        minimum=0.01,
        maximum=None,
    )
    prompts_before_years = (
        ("soft_cost_pct", "Soft costs as a share of construction", DEFAULT_SOFT_COST_PCT, 0.0, 1.0),
        (
            "contingency_pct",
            "Contingency as a share of construction plus soft costs",
            DEFAULT_CONTINGENCY_PCT,
            0.0,
            1.0,
        ),
        ("debt_share", "Debt as a share of total project cost", DEFAULT_DEBT_SHARE, 0.0, 1.0),
        (
            "annual_interest_rate",
            "Nominal annual interest rate",
            DEFAULT_ANNUAL_INTEREST_RATE,
            0.0,
            1.0,
        ),
    )
    prompts_after_years = (
        (
            "average_ticket",
            "Average food and beverage ticket",
            DEFAULT_AVERAGE_TICKET,
            0.01,
            None,
        ),
        (
            "weekday_occupancy",
            "Weekday occupancy",
            DEFAULT_WEEKDAY_OCCUPANCY,
            0.0,
            1.0,
        ),
        (
            "weekend_occupancy",
            "Weekend occupancy",
            DEFAULT_WEEKEND_OCCUPANCY,
            0.0,
            1.0,
        ),
    )
    prompts_after_days = (
        (
            "ticketed_events",
            "Year-1 ticketed-event revenue",
            DEFAULT_TICKETED_EVENTS,
            0.0,
            None,
        ),
        (
            "other_revenue_pct",
            "Other revenue as a share of food and beverage revenue",
            DEFAULT_OTHER_REVENUE_PCT,
            0.0,
            1.0,
        ),
        ("ebitda_margin", "EBITDA as a share of Year-1 revenue", DEFAULT_EBITDA_MARGIN, 0.0, 1.0),
        (
            "downside_revenue_multiplier",
            "Downside revenue multiplier",
            DEFAULT_DOWNSIDE_REVENUE_MULTIPLIER,
            0.0,
            None,
        ),
    )
    values: dict[str, float] = {}
    sources = {"construction_cost": construction_source}
    for key, label, default, minimum, maximum in prompts_before_years:
        value, source = _prompt_float(label, default, minimum, maximum)
        values[key] = value
        sources[key] = source
    years, year_source = _prompt_int(
        "Amortization years",
        DEFAULT_AMORTIZATION_YEARS,
        minimum=1,
        maximum=100,
    )
    sources["amortization_years"] = year_source
    seats, seats_source = _prompt_int(
        "Seats",
        DEFAULT_SEATS,
        minimum=1,
        maximum=100_000,
    )
    sources["seats"] = seats_source
    for key, label, default, minimum, maximum in prompts_after_years:
        value, source = _prompt_float(label, default, minimum, maximum)
        values[key] = value
        sources[key] = source
    operating_days, day_source = _prompt_int(
        "Operating days",
        DEFAULT_OPERATING_DAYS,
        minimum=1,
        maximum=366,
    )
    sources["operating_days"] = day_source
    for key, label, default, minimum, maximum in prompts_after_days:
        value, source = _prompt_float(label, default, minimum, maximum)
        values[key] = value
        sources[key] = source
    inputs = StartupInputs(
        construction_cost=construction,
        soft_cost_pct=values["soft_cost_pct"],
        contingency_pct=values["contingency_pct"],
        debt_share=values["debt_share"],
        annual_interest_rate=values["annual_interest_rate"],
        amortization_years=years,
        seats=seats,
        average_ticket=values["average_ticket"],
        weekday_occupancy=values["weekday_occupancy"],
        weekend_occupancy=values["weekend_occupancy"],
        operating_days=operating_days,
        ticketed_events=values["ticketed_events"],
        other_revenue_pct=values["other_revenue_pct"],
        ebitda_margin=values["ebitda_margin"],
        downside_revenue_multiplier=values["downside_revenue_multiplier"],
    )
    return inputs, sources


def _prompt_float(
    label: str,
    default: float | None,
    minimum: float | None,
    maximum: float | None,
) -> tuple[float, str]:
    while True:
        entered = input(_hint(label, default)).strip().replace(",", "")
        if entered == "" and default is None:
            print("Construction cost is required.")
            continue
        if entered == "" and default is not None:
            print(f"Accepted {label}: {default} (source: coded_model_default)")
            return float(default), "coded_model_default"
        try:
            value = float(entered)
        except ValueError:
            print("Enter a number, or press Enter for the coded default.")
            continue
        if isinstance(value, float) and not math.isfinite(value):
            print("Enter a finite number.")
            continue
        if minimum is not None and value < minimum:
            print(f"Enter a number >= {minimum}.")
            continue
        if maximum is not None and value > maximum:
            print(f"Enter a number <= {maximum}. Shares and rates use 0.15 for 15 percent.")
            continue
        print(f"Accepted {label}: {value} (source: user)")
        return value, "user"


def _prompt_int(label: str, default: int, *, minimum: int, maximum: int) -> tuple[int, str]:
    while True:
        entered = input(_hint(label, default)).strip().replace(",", "")
        if entered == "":
            print(f"Accepted {label}: {default} (source: coded_model_default)")
            return default, "coded_model_default"
        try:
            value = int(entered)
        except ValueError:
            print("Enter a whole number, or press Enter for the coded default.")
            continue
        if value < minimum or value > maximum:
            print(f"Enter a whole number from {minimum} to {maximum}.")
            continue
        print(f"Accepted {label}: {value} (source: user)")
        return value, "user"


def _hint(label: str, default: float | int | None) -> str:
    if default is None:
        return f"{label} (required): "
    return f"{label} [Enter = {default} coded default]: "


def _print_result(result: StartupResult, path: Path) -> None:
    print()
    print("Results (arithmetic on the accepted inputs)")
    print(f"Weekday operating days (5/7 weight): {result.weekday_operating_days:.4f}")
    print(f"Weekend operating days (2/7 weight): {result.weekend_operating_days:.4f}")
    rows = (
        ("Total project cost", result.total_project_cost),
        ("  Construction", result.construction_cost),
        ("  Soft costs", result.soft_costs),
        ("  Contingency", result.contingency),
        ("Debt", result.debt),
        ("Equity", result.equity),
        ("Annual debt service", result.annual_debt_service),
        ("Food and beverage revenue, base", result.food_and_beverage_revenue_base),
        ("Food and beverage revenue, downside", result.food_and_beverage_revenue_downside),
        ("Ticketed events, base", result.ticketed_events_base),
        ("Ticketed events, downside", result.ticketed_events_downside),
        ("Other revenue, base", result.other_revenue_base),
        ("Other revenue, downside", result.other_revenue_downside),
        ("Year-1 revenue, base", result.year1_revenue_base),
        ("Year-1 revenue, downside", result.year1_revenue_downside),
        ("EBITDA, base", result.ebitda_base),
        ("EBITDA, downside", result.ebitda_downside),
        ("Cash flow before debt service, base", result.cash_flow_before_debt_service_base),
        (
            "Cash flow before debt service, downside",
            result.cash_flow_before_debt_service_downside,
        ),
        ("Cash flow after debt service, base", result.cash_flow_after_debt_service_base),
        (
            "Cash flow after debt service, downside",
            result.cash_flow_after_debt_service_downside,
        ),
    )
    for label, value in rows:
        print(f"{label}: {value:.2f}")
    print(f"DSCR, base: {_fmt_dscr(result.dscr_base)}")
    print(f"DSCR, downside: {_fmt_dscr(result.dscr_downside)}")
    print("Observations:")
    for item in result.observations:
        print(f"- {item}")
    print("Human review: pending. No recommendation was issued.")
    print(f"Wrote {path}")


def _fmt_dscr(value: float | None) -> str:
    if value is None:
        return "undefined"
    return f"{value:.4f}"


def _field(value: float | int, sources: dict[str, str], key: str) -> dict[str, Any]:
    return {"value": value, "source": sources.get(key, "unspecified")}


def _count(name: str, value: Any, *, minimum: int, maximum: int) -> int:
    number = _finite(name, value)
    if int(number) != number or number < minimum or number > maximum:
        raise ValueError(f"{name} must be a whole number from {minimum} to {maximum}")
    return int(number)


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


def _money_input(name: str, value: Any, *, minimum: float) -> float:
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


def _years(value: Any) -> int:
    number = _finite("amortization_years", value)
    if number < 1 or number > 100 or int(number) != number:
        raise ValueError("amortization_years must be a whole number from 1 to 100")
    return int(number)


def _finite(name: str, value: Any) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be a number")
    if not math.isfinite(value):
        raise ValueError(f"{name} must be finite")
    return float(value)


if __name__ == "__main__":
    raise SystemExit(main())

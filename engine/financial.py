"""
Deterministic financial engine for RUGD assessments.

All arithmetic is pure Python. No figure in this module is produced by a
language model.

Methodology § Core Principles — deterministic calculations.
Methodology § Scoring Approach — automatic flag when cash flow is negative or
marginal under the base case and the downside case.
Methodology § Output Requirements — financial summary (base, downside, break-even).

Method assumptions (also exported as FIELD_DEFINITIONS):
- "Marginal" has no approved numeric band. A case is marginal when monthly
  cash flow, rounded half-even to cents, is less than or equal to zero.
- The cash-flow flag fires only when both the base case and the downside case
  meet that test. The methodology joins those cases with "and".
- months_to_break_even_base is initial capital divided by unrounded base
  monthly cash flow, then rounded half-even to one decimal. It is the time to
  recover initial capital at the base cash-flow rate. It is not a forecast of
  a revenue ramp. Break-even itself is break_even_monthly_revenue.
- Gross margin of zero cannot define a break-even revenue and is flagged
  NO_GROSS_MARGIN. Negative margin and margin above 1 are rejected. The notice
  is not one of the five methodology recommend-against criteria.
- Currency is whatever unit the caller used. This module does not convert.
- Primary revenue path: seats × occupancy × average ticket × operating days.
  Occupancy is the 5/7 weekday and 2/7 weekend mix. Those weights are calendar
  shares, not market benchmarks. Callers pass every driver. This module does
  not supply seat, ticket, occupancy, or day-count defaults.
- An input marked verified is logged as verified data. Every other driver is
  logged as a user-supplied assumption. Architecture § Analysis Layer —
  verified inputs stay separate from generated text.
"""

from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

MODEL_VERSION = "0.1-pilot"

FLAG_NEGATIVE_OR_MARGINAL_CASH_FLOW = "NEGATIVE_OR_MARGINAL_CASH_FLOW"
FLAG_NO_GROSS_MARGIN = "NO_GROSS_MARGIN"

FIELD_DEFINITIONS: dict[str, str] = {
    "base_monthly_contribution": (
        "projected_monthly_revenue_base × gross_margin_pct"
    ),
    "base_monthly_cash_flow": (
        "base_monthly_contribution − monthly_fixed_costs, rounded half-even to cents"
    ),
    "downside_monthly_cash_flow": (
        "(projected_monthly_revenue_base × downside_revenue_multiplier × "
        "gross_margin_pct) − monthly_fixed_costs, rounded half-even to cents"
    ),
    "break_even_monthly_revenue": (
        "monthly_fixed_costs / gross_margin_pct when gross margin is positive; "
        "otherwise undefined (Methodology § Output Requirements)"
    ),
    "months_to_break_even_base": (
        "initial_capital / unrounded base monthly cash flow when the rounded "
        "base cash flow is positive. This is months to recover initial capital "
        "at the base cash-flow rate, not a revenue-ramp forecast. "
        "Methodology § Output Requirements asks for break-even; that amount is "
        "break_even_monthly_revenue."
    ),
}


REVENUE_DRIVERS = (
    "seats",
    "average_ticket",
    "weekday_occupancy",
    "weekend_occupancy",
    "operating_days",
)

USER_SUPPLIED_ASSUMPTION = "user-supplied assumption"
VERIFIED_DATA = "verified data"

SEAT_REVENUE_FORMULA = (
    "revenue = seats × occupancy × average_ticket × operating_days; "
    "occupancy = (weekday_occupancy × 5 + weekend_occupancy × 2) / 7. "
    "One cover per occupied seat per operating day."
)


@dataclass(frozen=True)
class SeatRevenueResult:
    revenue: float
    occupancy: float
    assumption_sources: tuple[dict[str, Any], ...]
    formula: str = SEAT_REVENUE_FORMULA


@dataclass(frozen=True)
class FinancialInputs:
    initial_capital: float
    monthly_fixed_costs: float
    gross_margin_pct: float  # 0.0 – 1.0
    projected_monthly_revenue_base: float
    downside_revenue_multiplier: float = 0.6


@dataclass(frozen=True)
class FinancialResult:
    base_monthly_contribution: float
    base_monthly_cash_flow: float
    downside_monthly_revenue: float
    downside_monthly_contribution: float
    downside_monthly_cash_flow: float
    break_even_monthly_revenue: float | None
    months_to_break_even_base: float | None
    flags: tuple[str, ...]


def _number(
    name: str,
    value: Any,
    *,
    minimum: float | None = None,
    maximum: float | None = None,
) -> float:
    """Reject bools, non-numbers, and non-finite values before any arithmetic."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be a number")
    if not math.isfinite(value):
        raise ValueError(f"{name} must be finite")
    if minimum is not None and value < minimum:
        raise ValueError(f"{name} must be >= {minimum}")
    if maximum is not None and value > maximum:
        raise ValueError(f"{name} must be <= {maximum}")
    return float(value)


def seat_occupancy_revenue(
    seats: float,
    average_ticket: float,
    weekday_occupancy: float,
    weekend_occupancy: float,
    operating_days: float,
    verified: Mapping[str, bool] | None = None,
) -> SeatRevenueResult:
    """Primary revenue path. Architecture § Analysis Layer.

    Returns the calculated revenue and a source record for every driver.
    A driver is a user-supplied assumption unless ``verified`` marks it true.
    """
    flags = _verified_flags(verified)
    seat_count = _whole_number("seats", seats, minimum=0)
    ticket = _number("average_ticket", average_ticket, minimum=0)
    weekday = _number("weekday_occupancy", weekday_occupancy, minimum=0, maximum=1)
    weekend = _number("weekend_occupancy", weekend_occupancy, minimum=0, maximum=1)
    days = _number("operating_days", operating_days, minimum=0, maximum=366)
    if days == 0:
        raise ValueError("operating_days must be > 0")
    occupancy = (weekday * 5 + weekend * 2) / 7
    revenue = round(seat_count * occupancy * ticket * days, 2)
    values = {
        "seats": seat_count,
        "average_ticket": ticket,
        "weekday_occupancy": weekday,
        "weekend_occupancy": weekend,
        "operating_days": days,
    }
    sources = tuple(
        {
            "key": key,
            "value": values[key],
            "source": "verified" if flags[key] else "user",
            "evidence_label": VERIFIED_DATA if flags[key] else USER_SUPPLIED_ASSUMPTION,
        }
        for key in REVENUE_DRIVERS
    )
    return SeatRevenueResult(
        revenue=revenue,
        occupancy=occupancy,
        assumption_sources=sources,
    )


def _verified_flags(verified: Mapping[str, bool] | None) -> dict[str, bool]:
    if verified is None:
        return {key: False for key in REVENUE_DRIVERS}
    if not isinstance(verified, Mapping):
        raise ValueError("verified must map each revenue driver to true or false")
    unknown = set(verified) - set(REVENUE_DRIVERS)
    if unknown:
        names = ", ".join(sorted(unknown))
        raise ValueError(f"unknown verified revenue driver: {names}")
    flags: dict[str, bool] = {}
    for key in REVENUE_DRIVERS:
        flag = verified.get(key, False)
        if not isinstance(flag, bool):
            raise ValueError(f"verified[{key}] must be true or false")
        flags[key] = flag
    return flags


def _whole_number(name: str, value: Any, *, minimum: int) -> float:
    number = _number(name, value, minimum=minimum)
    if int(number) != number:
        raise ValueError(f"{name} must be a whole number")
    return number


def run_financials(inputs: FinancialInputs) -> FinancialResult:
    """Pure deterministic calculation. Cite Methodology § Scoring Approach."""
    initial_capital = _number(
        "initial_capital", inputs.initial_capital, minimum=0
    )
    monthly_fixed_costs = _number(
        "monthly_fixed_costs", inputs.monthly_fixed_costs, minimum=0
    )
    gross_margin_pct = _number(
        "gross_margin_pct", inputs.gross_margin_pct, minimum=0, maximum=1
    )
    projected_monthly_revenue_base = _number(
        "projected_monthly_revenue_base",
        inputs.projected_monthly_revenue_base,
        minimum=0,
    )
    downside_revenue_multiplier = _number(
        "downside_revenue_multiplier",
        inputs.downside_revenue_multiplier,
        minimum=0,
    )

    contribution = projected_monthly_revenue_base * gross_margin_pct
    base_cf = contribution - monthly_fixed_costs

    downside_revenue = (
        projected_monthly_revenue_base * downside_revenue_multiplier
    )
    downside_contribution = downside_revenue * gross_margin_pct
    downside_cf = downside_contribution - monthly_fixed_costs

    flags: list[str] = []
    base_cf_out = round(base_cf, 2)
    downside_cf_out = round(downside_cf, 2)
    if base_cf_out <= 0 and downside_cf_out <= 0:
        flags.append(FLAG_NEGATIVE_OR_MARGINAL_CASH_FLOW)

    if gross_margin_pct > 0:
        break_even_out: float | None = round(
            monthly_fixed_costs / gross_margin_pct, 2
        )
    else:
        break_even_out = None
        flags.append(FLAG_NO_GROSS_MARGIN)

    months_out: float | None = None
    if base_cf_out > 0:
        months_out = round(initial_capital / base_cf, 1)

    return FinancialResult(
        base_monthly_contribution=round(contribution, 2),
        base_monthly_cash_flow=base_cf_out,
        downside_monthly_revenue=round(downside_revenue, 2),
        downside_monthly_contribution=round(downside_contribution, 2),
        downside_monthly_cash_flow=downside_cf_out,
        break_even_monthly_revenue=break_even_out,
        months_to_break_even_base=months_out,
        flags=tuple(flags),
    )


def result_to_dict(result: FinancialResult) -> dict[str, Any]:
    return {
        "base_monthly_contribution": result.base_monthly_contribution,
        "base_monthly_cash_flow": result.base_monthly_cash_flow,
        "downside_monthly_revenue": result.downside_monthly_revenue,
        "downside_monthly_contribution": result.downside_monthly_contribution,
        "downside_monthly_cash_flow": result.downside_monthly_cash_flow,
        "break_even_monthly_revenue": result.break_even_monthly_revenue,
        "months_to_break_even_base": result.months_to_break_even_base,
        "flags": list(result.flags),
        "field_definitions": dict(FIELD_DEFINITIONS),
        "model_version": MODEL_VERSION,
    }

"""Check customer money fields before they are stored or sent to the engine.

A blank stays missing. Zero is an entered assumption. Text that is not a finite
number is refused. This module does not calculate a result.
"""

from __future__ import annotations

import math
from typing import Any

MONTHLY_FIELDS = (
    "initial_capital",
    "monthly_fixed_costs",
    "gross_margin_pct",
    "projected_monthly_revenue_base",
)

# Inclusive bounds already enforced by engine.financial.run_financials.
_BOUNDS: dict[str, tuple[str, float, float | None]] = {
    "initial_capital": ("Initial capital", 0.0, None),
    "monthly_fixed_costs": ("Monthly fixed costs", 0.0, None),
    "gross_margin_pct": ("Gross margin", 0.0, 1.0),
    "projected_monthly_revenue_base": ("Projected monthly base revenue", 0.0, None),
    "downside_multiplier": ("Downside multiplier", 0.0, None),
}


def field_state(value: Any) -> str:
    """Return missing, zero, entered, or invalid. Blank is never zero."""
    if value is None or isinstance(value, bool):
        return "invalid" if isinstance(value, bool) else "missing"
    if isinstance(value, (int, float)):
        number = float(value)
    else:
        text = str(value).strip()
        if not text:
            return "missing"
        try:
            number = float(text)
        except ValueError:
            return "invalid"
    if not math.isfinite(number):
        return "invalid"
    if number == 0:
        return "zero"
    return "entered"


def monthly_problems(profile: dict[str, Any]) -> list[str]:
    """Refuse a bad monthly entry. A blank field is not a problem and is not filled."""
    problems: list[str] = []
    for key, (label, low, high) in _BOUNDS.items():
        raw = profile.get(key)
        state = field_state(raw)
        if state == "missing":
            continue
        if state == "invalid":
            problems.append(
                f"{label} is not a finite number. A blank stays missing and is not stored as zero."
            )
            continue
        number = float(raw) if isinstance(raw, (int, float)) else float(str(raw).strip())
        if number < low or (high is not None and number > high):
            limit = f"from {low} to {high}" if high is not None else f"at least {low}"
            problems.append(f"{label} must be {limit}. The draft was not changed.")
    return problems

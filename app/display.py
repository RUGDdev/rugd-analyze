"""Presentation formatting for customer-facing financial results.

These helpers only change how a stored number is written on a page. They never round,
convert, or store anything. The database and the engine keep the full values.

A value is in one of four states, and a page must not blur them:

* missing: the customer or the engine gave nothing. Shown as words, never as zero.
* zero: a real zero. Shown as ``$0`` and so on.
* estimated: a customer entry or a coded placeholder. It is an assumption, not data.
* calculated: the deterministic engine produced it from the inputs.
"""

from __future__ import annotations

import math
from decimal import ROUND_HALF_UP, Decimal
from html import escape
from typing import Any

NOT_PROVIDED = "Not provided"
NOT_CALCULATED = "Not calculated"

# Engine evidence labels, in everyday words.
STATE_LABELS = {
    "calculated": "Calculated",
    "estimated": "Your assumption",
    "placeholder": "Default placeholder",
    "missing": "Missing",
    "zero": "Entered as zero",
    "benchmark": "Benchmark context",
}

_ENGINE_LABELS = {
    "calculated by the deterministic engine": "calculated",
    "user-supplied assumption": "estimated",
}


def number_of(value: Any) -> float | None:
    """A finite float, or None. Booleans, blanks, and text are not numbers."""
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        number = float(value)
    else:
        text = str(value).strip().replace(",", "").replace("$", "").replace("%", "")
        if not text:
            return None
        try:
            number = float(text)
        except ValueError:
            return None
    return number if math.isfinite(number) else None


def _whole(number: float) -> int:
    return int(Decimal(repr(number)).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def money(value: Any, *, missing: str = NOT_PROVIDED, cents: bool = False) -> str:
    """$2,537,206, -$125,000, $0. A missing value is words, not zero."""
    number = number_of(value)
    if number is None:
        return missing
    if cents:
        rounded = Decimal(repr(number)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        body = f"{abs(rounded):,.2f}"
        negative = rounded < 0
    else:
        whole = _whole(number)
        body = f"{abs(whole):,}"
        negative = whole < 0
    return f"-${body}" if negative else f"${body}"


def percent(value: Any, places: int = 0, *, missing: str = NOT_PROVIDED) -> str:
    """A fraction written as a percent: 0.55 gives 55%, 0.08 with places=1 gives 8.0%."""
    number = number_of(value)
    if number is None:
        return missing
    scaled = Decimal(repr(number)) * 100
    quantum = Decimal(1).scaleb(-places)
    rounded = scaled.quantize(quantum, rounding=ROUND_HALF_UP)
    text = f"{abs(rounded):,.{places}f}%"
    return f"-{text}" if rounded < 0 else text


def multiple(value: Any, places: int = 2, *, missing: str = NOT_CALCULATED) -> str:
    """A ratio such as debt service coverage: 1.25×, -0.69×."""
    number = number_of(value)
    if number is None:
        return missing
    quantum = Decimal(1).scaleb(-places)
    rounded = Decimal(repr(number)).quantize(quantum, rounding=ROUND_HALF_UP)
    text = f"{abs(rounded):,.{places}f}×"
    return f"-{text}" if rounded < 0 else text


def count(value: Any, unit: str = "", *, missing: str = NOT_PROVIDED) -> str:
    number = number_of(value)
    if number is None:
        return missing
    text = f"{_whole(number):,}"
    return f"{text} {unit}".strip()


def decimal_text(value: Any, places: int = 1, unit: str = "", *, missing: str = NOT_CALCULATED) -> str:
    number = number_of(value)
    if number is None:
        return missing
    quantum = Decimal(1).scaleb(-places)
    rounded = Decimal(repr(number)).quantize(quantum, rounding=ROUND_HALF_UP)
    return f"{rounded:,.{places}f} {unit}".strip()


def state_from_engine(label: Any) -> str:
    """Map an engine evidence label to a display state."""
    return _ENGINE_LABELS.get(str(label or "").strip().lower(), "estimated")


def chip(state: str, text: str = "") -> str:
    """A small state tag that sits beside a figure."""
    label = text or STATE_LABELS.get(state, state)
    return f'<span class="dchip dchip-{escape(state)}">{escape(label)}</span>'

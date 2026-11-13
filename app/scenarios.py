"""One saved Base case and one alternative case.

The alternative is an extra engine run. It uses the assessment's current inputs
and the stored downside multiplier. It is not written over the official result,
so it cannot change the recommendation or a hard gate.
"""

from __future__ import annotations

import copy
from datetime import datetime, timezone
from typing import Any

DISCLAIMER = (
    "Scenario comparison. Base is a saved copy of the official result. "
    "A weaker-year or stronger-year case is one additional what-if calculation that uses the current inputs "
    "and the saved weaker-year setting. It does not change the official recommendation, "
    "lift a serious concern, or approve anything."
)

METRIC_KEYS = (
    "monthly_contribution",
    "monthly_cash_flow",
    "break_even_monthly_revenue",
    "startup_revenue",
    "startup_cash_flow",
    "dscr",
)

METRIC_LABELS = {
    "monthly_contribution": "Monthly contribution",
    "monthly_cash_flow": "Monthly cash flow",
    "break_even_monthly_revenue": "Break-even monthly revenue",
    "startup_revenue": "Startup revenue",
    "startup_cash_flow": "Cash flow before debt service",
    "dscr": "DSCR",
}


def blank_scenarios() -> dict[str, Any]:
    return {
        "base": None,
        "alternative": None,
        "affects_official_recommendation": False,
        "clears_hard_gates": False,
        "sets_human_review_approved": False,
    }


def key_metrics(result: dict[str, Any] | None) -> dict[str, float | None]:
    """Read key engine figures. Flags and the recommendation are not included."""
    financial = result.get("financial") if isinstance(result, dict) and isinstance(result.get("financial"), dict) else {}
    projection = result.get("projection") if isinstance(result, dict) and isinstance(result.get("projection"), dict) else {}
    views = projection.get("views") if isinstance(projection.get("views"), dict) else {}
    base = views.get("base") if isinstance(views.get("base"), dict) else {}
    return {
        "monthly_contribution": _metric(financial.get("base_monthly_contribution")),
        "monthly_cash_flow": _metric(financial.get("base_monthly_cash_flow")),
        "break_even_monthly_revenue": _metric(financial.get("break_even_monthly_revenue")),
        "startup_revenue": _metric(base.get("revenue")),
        "startup_cash_flow": _metric(base.get("cash_flow_before_debt_service")),
        "dscr": _metric(base.get("dscr")),
    }


def update_scenarios(record: dict[str, Any], case: str) -> dict[str, Any]:
    """Return new scenario state. The record and its official result are not changed."""
    stored = record.get("result") if isinstance(record.get("result"), dict) else None
    if not stored or not stored.get("engine_ran"):
        raise ValueError(
            "Analyze has not been run. No scenario was saved and the assessment was not changed."
        )
    state = normalize_stored(record.get("scenarios"))
    kind = str(case or "").strip().lower()
    official = _case(
        "Base",
        "base",
        key_metrics(stored),
        None,
        "Saved from the current official engine result.",
    )
    if kind == "base":
        state["base"] = official
        return state
    if kind not in {"downside", "upside"}:
        raise ValueError("Choose Base, Downside, or Upside.")
    if state["base"] is None:
        state["base"] = official
    state["alternative"] = _run_alternative(record, kind)
    return state


def normalize_stored(raw: Any) -> dict[str, Any]:
    state = blank_scenarios()
    if not isinstance(raw, dict):
        return state
    base = _clean_case(raw.get("base"), allowed={"base"})
    alternative = _clean_case(raw.get("alternative"), allowed={"downside", "upside"})
    state["base"] = base
    state["alternative"] = alternative
    return state


def _run_alternative(record: dict[str, Any], kind: str) -> dict[str, Any]:
    from app.analysis import analyze_record

    multiplier = _stored_multiplier(record)
    revenue_factor, occupancy_cap, note = _factors(kind, multiplier)
    probed = copy.deepcopy(record)
    _shock(probed, revenue_factor, occupancy_cap)
    shadow = analyze_record(probed)
    label = "Downside" if kind == "downside" else "Upside"
    return _case(label, kind, key_metrics(shadow), multiplier, note)


def _shock(record: dict[str, Any], factor: float, occupancy_cap: float | None) -> None:
    if record.get("read_only") and isinstance(record.get("intake"), dict):
        _shock_intake(record["intake"], factor, occupancy_cap)
        return
    profile = record.get("profile")
    if not isinstance(profile, dict):
        record["profile"] = {}
        profile = record["profile"]
    revenue = _number(profile.get("projected_monthly_revenue_base"))
    if revenue is not None:
        profile["projected_monthly_revenue_base"] = _format_number(revenue * factor)
    _shock_occupancy(profile, factor, occupancy_cap)


def _shock_intake(intake: dict[str, Any], factor: float, occupancy_cap: float | None) -> None:
    financial = intake.get("financial_inputs")
    if isinstance(financial, dict):
        revenue = _number(financial.get("projected_monthly_revenue_base"))
        if revenue is not None:
            financial["projected_monthly_revenue_base"] = round(revenue * factor, 2)
    startup = intake.get("startup_capital")
    if isinstance(startup, dict):
        _shock_occupancy(startup, factor, occupancy_cap, rounded=4)


def _shock_occupancy(
    values: dict[str, Any],
    factor: float,
    occupancy_cap: float | None,
    *,
    rounded: int = 4,
) -> None:
    for key in ("weekday_occupancy", "weekend_occupancy"):
        current = _number(values.get(key))
        if current is None:
            continue
        scaled = current * factor
        if occupancy_cap is not None:
            scaled = min(occupancy_cap, scaled)
        values[key] = round(scaled, rounded) if isinstance(values.get(key), (int, float)) else _format_number(scaled, rounded)


def _factors(kind: str, multiplier: float) -> tuple[float, float | None, str]:
    if kind == "downside":
        return (
            multiplier,
            1.0,
            f"Downside scales revenue and occupancy by the stored downside multiplier {multiplier}.",
        )
    if multiplier <= 0:
        return (
            1.0,
            1.0,
            "The stored downside multiplier is 0, so upside was not scaled.",
        )
    return (
        1.0 / multiplier,
        1.0,
        (
            "Upside scales revenue and occupancy by the inverse of the stored downside "
            f"multiplier {multiplier}. Occupancy stops at 1 because the engine rejects a higher value."
        ),
    )


def _stored_multiplier(record: dict[str, Any]) -> float:
    profile = record.get("profile") if isinstance(record.get("profile"), dict) else {}
    intake = record.get("intake") if isinstance(record.get("intake"), dict) else {}
    financial = intake.get("financial_inputs") if isinstance(intake.get("financial_inputs"), dict) else {}
    startup = intake.get("startup_capital") if isinstance(intake.get("startup_capital"), dict) else {}
    for raw in (
        profile.get("downside_multiplier"),
        financial.get("downside_revenue_multiplier"),
        startup.get("downside_multiplier"),
    ):
        number = _number(raw)
        if number is not None and number >= 0:
            return number
    return 0.6


def _case(
    label: str,
    kind: str,
    metrics: dict[str, float | None],
    multiplier: float | None,
    note: str,
) -> dict[str, Any]:
    return {
        "label": label,
        "kind": kind,
        "saved_at": _now(),
        "multiplier": multiplier,
        "note": note,
        "metrics": {key: metrics.get(key) for key in METRIC_KEYS},
        "authoritative": False,
        "changes_recommendation": False,
        "clears_hard_gates": False,
        "sets_human_review_approved": False,
    }


def _clean_case(raw: Any, *, allowed: set[str]) -> dict[str, Any] | None:
    if not isinstance(raw, dict):
        return None
    kind = str(raw.get("kind") or "")
    if kind not in allowed:
        return None
    metrics_raw = raw.get("metrics") if isinstance(raw.get("metrics"), dict) else {}
    metrics = {key: _metric(metrics_raw.get(key)) for key in METRIC_KEYS}
    multiplier = _metric(raw.get("multiplier"))
    label = str(raw.get("label") or kind.title())
    note = str(raw.get("note") or "")
    return {
        "label": label,
        "kind": kind,
        "saved_at": str(raw.get("saved_at") or ""),
        "multiplier": multiplier,
        "note": note,
        "metrics": metrics,
        "authoritative": False,
        "changes_recommendation": False,
        "clears_hard_gates": False,
        "sets_human_review_approved": False,
    }


def _metric(value: Any) -> float | None:
    number = _number(value)
    return number


def _number(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        number = float(value)
    else:
        text = str(value).strip()
        if not text:
            return None
        try:
            number = float(text)
        except ValueError:
            return None
    if number != number or number in {float("inf"), float("-inf")}:
        return None
    return number


def _format_number(value: float, places: int = 2) -> str:
    return f"{round(value, places):.{places}f}"


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()

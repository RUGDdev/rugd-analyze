"""Proposed restaurant revenue worksheet. It is separate from the official calculation.

The official seat formula counts one cover per occupied seat per operating day and
weights weekdays and weekends 5/7 and 2/7. This worksheet adds service periods, seat
turns, the days actually open, utilization, an average check per period, and other
revenue streams. It is labeled proposed. The official engine, scoring, and baseline
do not read it. Every figure is a customer assumption.
"""

from __future__ import annotations

import math
from typing import Any

from app.field_help import DAYS
from app.inputs import field_state
from engine.financial import seat_occupancy_revenue

PERIOD_SLOTS = 4
STREAM_SLOTS = 3
MAX_TURNS = 20.0
MAX_TICKET = 10_000.0
PROPOSED_LABEL = (
    "Proposed worksheet. It is not the official calculation. The official result, flags, "
    "and scoring do not use it. Every figure is your assumption."
)
_WEEKEND = {"sat", "sun"}
_DAY_CODES = [code for code, _label in DAYS]


def _number(value: Any) -> float | None:
    text = str(value if value is not None else "").strip().replace(",", "").replace("$", "")
    if not text:
        return None
    try:
        number = float(text)
    except ValueError:
        return None
    return number if math.isfinite(number) else None


def default_form(profile: dict[str, Any]) -> dict[str, str]:
    """Prefill from entered answers. Nothing is invented, and an empty answer stays empty."""
    form: dict[str, str] = {}
    for key in ("seats", "operating_weeks", "operating_schedule"):
        if str(profile.get(key) or "").strip():
            form[key] = str(profile[key]).strip()
    return form


def parse(form: dict[str, str]) -> tuple[dict[str, Any], list[str]]:
    errors: list[str] = []
    seats_raw = _number(form.get("seats"))
    seats = None
    if seats_raw is not None:
        if seats_raw < 1 or seats_raw > 5000 or int(seats_raw) != seats_raw:
            errors.append("Seats must be a whole number from 1 to 5000.")
        else:
            seats = int(seats_raw)
    picked = [code for code in _DAY_CODES if code in {part.strip().lower() for part in str(form.get("operating_schedule") or "").split(",")}]
    weeks_raw = str(form.get("operating_weeks") or "").strip()
    weeks = None
    if weeks_raw:
        value = _number(weeks_raw)
        if value is None or value <= 0 or value > 52:
            errors.append("Weeks open per year must be a number above 0 and at most 52.")
        else:
            weeks = value
    periods = []
    for index in range(1, PERIOD_SLOTS + 1):
        name = " ".join(str(form.get(f"period_{index}_name") or "").split())[:40]
        raw = {
            "turns": form.get(f"period_{index}_turns"),
            "util_weekday": form.get(f"period_{index}_util_weekday"),
            "util_weekend": form.get(f"period_{index}_util_weekend"),
            "ticket": form.get(f"period_{index}_ticket"),
        }
        if not name and not any(str(value or "").strip() for value in raw.values()):
            continue
        label = name or f"Period {index}"
        turns = _number(raw["turns"])
        util_weekday = _number(raw["util_weekday"])
        util_weekend = _number(raw["util_weekend"])
        ticket = _number(raw["ticket"])
        row_ok = True
        if turns is None or turns <= 0 or turns > MAX_TURNS:
            errors.append(f"{label}: seat turns must be above 0 and at most {MAX_TURNS:g}.")
            row_ok = False
        for caption, util in (("weekday", util_weekday), ("weekend", util_weekend)):
            if util is None or util < 0 or util > 1:
                errors.append(f"{label}: {caption} utilization must be from 0 to 1 (0.60 means 60%).")
                row_ok = False
        if ticket is None or ticket < 0 or ticket > MAX_TICKET:
            errors.append(f"{label}: average check must be a number from 0 to {MAX_TICKET:,.0f}.")
            row_ok = False
        if row_ok:
            periods.append(
                {
                    "name": label,
                    "turns": float(turns),
                    "util_weekday": float(util_weekday),
                    "util_weekend": float(util_weekend),
                    "ticket": float(ticket),
                }
            )
    streams = []
    for index in range(1, STREAM_SLOTS + 1):
        name = " ".join(str(form.get(f"stream_{index}_name") or "").split())[:60]
        amount_raw = str(form.get(f"stream_{index}_annual") or "").strip()
        if not name and not amount_raw:
            continue
        amount = _number(amount_raw)
        if not name or amount is None or amount < 0:
            errors.append(f"Other revenue {index}: give a name and a yearly amount of zero or more.")
            continue
        streams.append({"name": name, "annual": float(amount), "basis": " ".join(str(form.get(f"stream_{index}_basis") or "").split())[:160]})
    worksheet = {
        "seats": seats,
        "days": picked,
        "weeks": weeks,
        "periods": periods,
        "streams": streams,
        "note": " ".join(str(form.get("note") or "").split())[:400],
    }
    return worksheet, errors


def form_from_worksheet(worksheet: dict[str, Any]) -> dict[str, str]:
    """Round-trip a saved worksheet back into form values."""
    form = {
        "seats": "" if worksheet.get("seats") is None else str(worksheet["seats"]),
        "operating_schedule": ",".join(worksheet.get("days") or []),
        "operating_weeks": "" if worksheet.get("weeks") is None else f"{worksheet['weeks']:g}",
        "note": str(worksheet.get("note") or ""),
    }
    for index, period in enumerate(worksheet.get("periods") or [], start=1):
        form[f"period_{index}_name"] = str(period["name"])
        form[f"period_{index}_turns"] = f"{period['turns']:g}"
        form[f"period_{index}_util_weekday"] = f"{period['util_weekday']:g}"
        form[f"period_{index}_util_weekend"] = f"{period['util_weekend']:g}"
        form[f"period_{index}_ticket"] = f"{period['ticket']:g}"
    for index, stream in enumerate(worksheet.get("streams") or [], start=1):
        form[f"stream_{index}_name"] = str(stream["name"])
        form[f"stream_{index}_annual"] = f"{stream['annual']:g}"
        form[f"stream_{index}_basis"] = str(stream.get("basis") or "")
    return form


def missing(worksheet: dict[str, Any]) -> list[str]:
    needed = []
    if not worksheet.get("seats"):
        needed.append("seats")
    if not worksheet.get("days"):
        needed.append("the days you are open")
    if not worksheet.get("weeks"):
        needed.append("weeks open per year")
    if not worksheet.get("periods"):
        needed.append("at least one service period")
    return needed


def calculate(worksheet: dict[str, Any]) -> dict[str, Any] | None:
    """Annual revenue with every line shown. Returns None until the required inputs exist."""
    if missing(worksheet):
        return None
    seats = int(worksheet["seats"])
    weeks = float(worksheet["weeks"])
    days = worksheet["days"]
    weekend_per_week = len([code for code in days if code in _WEEKEND])
    weekday_per_week = len(days) - weekend_per_week
    weekday_days = weekday_per_week * weeks
    weekend_days = weekend_per_week * weeks
    lines = []
    core = 0.0
    covers_year = 0.0
    for period in worksheet["periods"]:
        for kind, count, util in (
            ("weekday", weekday_days, period["util_weekday"]),
            ("weekend", weekend_days, period["util_weekend"]),
        ):
            if count <= 0:
                continue
            covers_day = seats * period["turns"] * util
            covers = covers_day * count
            revenue = round(covers * period["ticket"], 2)
            core += revenue
            covers_year += covers
            lines.append(
                {
                    "period": period["name"],
                    "day_type": kind,
                    "open_days": count,
                    "covers_per_day": covers_day,
                    "covers": covers,
                    "ticket": period["ticket"],
                    "revenue": revenue,
                    "formula": (
                        f"{seats} seats × {period['turns']:g} turns × {util:g} utilization × "
                        f"{period['ticket']:,.2f} check × {count:g} {kind} days"
                    ),
                }
            )
    core = round(core, 2)
    other = round(sum(stream["annual"] for stream in worksheet["streams"]), 2)
    total = round(core + other, 2)
    open_days = weekday_days + weekend_days
    return {
        "seats": seats,
        "open_days_per_year": open_days,
        "weekday_days": weekday_days,
        "weekend_days": weekend_days,
        "lines": lines,
        "core_revenue": core,
        "other_revenue": other,
        "total_revenue": total,
        "monthly_revenue": round(total / 12, 2),
        "covers_per_year": covers_year,
        "average_check": round(core / covers_year, 2) if covers_year else None,
        "covers_per_seat_per_open_day": (covers_year / (seats * open_days)) if seats and open_days else None,
    }


def _entered(profile: dict[str, Any], key: str) -> float | None:
    if field_state(profile.get(key)) not in {"entered", "zero"}:
        return None
    return _number(profile.get(key))


def compare(worksheet: dict[str, Any], proposed: dict[str, Any], profile: dict[str, Any]) -> dict[str, Any]:
    """Side by side with the official seat formula, using only the entries already in the draft."""
    keys = ("seats", "average_ticket", "weekday_occupancy", "weekend_occupancy", "operating_days")
    values = {key: _entered(profile, key) for key in keys}
    absent = [key for key, value in values.items() if value is None]
    result: dict[str, Any] = {"official": None, "missing": absent, "steps": [], "error": ""}
    margin = _entered(profile, "contribution_margin")
    fixed = _entered(profile, "annual_fixed_costs")
    if absent:
        return result
    try:
        official = seat_occupancy_revenue(
            values["seats"], values["average_ticket"], values["weekday_occupancy"], values["weekend_occupancy"], values["operating_days"]
        ).revenue
    except ValueError as exc:
        result["error"] = str(exc)
        return result
    result["official"] = official
    result["official_occupancy"] = (values["weekday_occupancy"] * 5 + values["weekend_occupancy"] * 2) / 7
    result["official_covers_per_seat_per_day"] = result["official_occupancy"]
    total = proposed["total_revenue"]
    result["difference"] = round(total - official, 2)
    result["difference_pct"] = None if official == 0 else round((total - official) / official * 100, 1)
    days_effect = round(
        values["seats"]
        * values["average_ticket"]
        * (proposed["weekday_days"] * values["weekday_occupancy"] + proposed["weekend_days"] * values["weekend_occupancy"]),
        2,
    )
    result["steps"] = [
        {"label": "Official formula", "value": official, "note": "Seats × blended occupancy × average ticket × operating days from your draft."},
        {
            "label": "Use the days you are actually open",
            "value": days_effect,
            "note": f"Same seats, ticket, and occupancy, with {proposed['weekday_days']:g} weekday and {proposed['weekend_days']:g} weekend open days instead of a 5/7 and 2/7 split of {values['operating_days']:g} days.",
        },
        {
            "label": "Add service periods and seat turns",
            "value": proposed["core_revenue"],
            "note": "Each period uses its own turns, utilization, and check.",
        },
        {"label": "Add other revenue", "value": total, "note": "The yearly amounts you entered for other streams."},
    ]
    result["effects"] = [
        {"label": result["steps"][i]["label"], "delta": round(result["steps"][i]["value"] - result["steps"][i - 1]["value"], 2)}
        for i in range(1, len(result["steps"]))
    ]
    cap = proposed.get("covers_per_seat_per_open_day")
    result["beyond_official_cap"] = bool(cap is not None and cap > 1.0 + 1e-9)
    if margin is not None and fixed is not None:
        result["cash_flow"] = {
            "official": round(official * margin - fixed, 2),
            "proposed": round(total * margin - fixed, 2),
            "basis": "Revenue × your contribution margin − your annual fixed costs. Before debt service.",
        }
    return result

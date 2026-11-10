"""Evidence checklist. Guidance only.

Checking or completing an item stores progress on the assessment. It does not
run the engine, clear a recommend-against flag, change a recommendation, or
set human_review_approved.
"""

from __future__ import annotations

import math
import re
from typing import Any

DISCLAIMER = (
    "Checking or completing an item updates guidance only. "
    "It does not clear a recommend-against flag, change the recommendation, "
    "or set human_review_approved."
)

ITEM_ID = re.compile(r"^[A-Za-z0-9]+(?:-[A-Za-z0-9_]+)*$")
_FLAG_ID = re.compile(r"^[A-Z0-9_]+$")

_MONTHLY = (
    ("initial_capital", "Initial capital"),
    ("monthly_fixed_costs", "Monthly fixed costs"),
    ("gross_margin_pct", "Gross margin"),
    ("projected_monthly_revenue_base", "Projected monthly base revenue"),
)
_STARTUP = (
    ("construction_cost", "Construction cost"),
    ("seats", "Seats"),
    ("average_ticket", "Average ticket"),
    ("weekday_occupancy", "Weekday occupancy"),
    ("weekend_occupancy", "Weekend occupancy"),
    ("operating_days", "Operating days"),
    ("contribution_margin", "Contribution margin"),
)
_KEY_NOTES = (
    "market-demand",
    "financial-feasibility",
    "stewardship",
)


def build_checklist(
    record: dict[str, Any],
    result: dict[str, Any] | None = None,
    notes: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Describe the items that would strengthen this assessment. The record is not changed."""
    profile = record.get("profile") if isinstance(record.get("profile"), dict) else {}
    stored = result if isinstance(result, dict) else {}
    if not stored and isinstance(record.get("result"), dict):
        stored = record["result"]
    checks = record.get("checklist") if isinstance(record.get("checklist"), dict) else {}
    blocking = [str(flag) for flag in stored.get("blocking_flags") or []]
    items: list[dict[str, Any]] = []

    def add(item_id: str, title: str, guidance: str, recorded: bool, plain: str) -> None:
        checked = checks.get(item_id) is True
        if recorded:
            status = "recorded"
        elif checked:
            status = "noted"
        else:
            status = "open"
        items.append(
            {
                "id": item_id,
                "title": title,
                "plain": plain,
                "guidance": guidance,
                "status": status,
                "recorded": recorded,
                "checked": checked,
                "clears_hard_gate": False,
            }
        )

    demand_extra = (
        " INSUFFICIENT_DEMAND_EVIDENCE is still active. This checklist did not clear it."
        if "INSUFFICIENT_DEMAND_EVIDENCE" in blocking
        else (
            " Analyze has not been run. Checking this item does not clear INSUFFICIENT_DEMAND_EVIDENCE."
            if not stored.get("engine_ran")
            else " Checking this item does not clear a recommend-against flag."
        )
    )
    add(
        "verified-demand",
        "Verified demand evidence",
        (
            "A strengthening record has source verified, a rationale, and either a true "
            "demand_evidence value or trailing revenue greater than zero. "
            "A check here does not create that record."
            + demand_extra
        ),
        _verified_support(profile),
        "In everyday words: show proof that people will pay, such as signed orders or past sales. Checking this box does not create that proof.",
    )
    monthly_guidance, monthly_recorded = _financial_copy(profile, _MONTHLY, "monthly")
    add(
        "monthly-inputs",
        "Monthly financial inputs",
        monthly_guidance,
        monthly_recorded,
        "In everyday words: enter the four monthly money figures. A blank stays blank, and checking the box does not invent a number.",
    )
    if _venture_path(record) != "existing":
        startup_guidance, startup_recorded = _financial_copy(profile, _STARTUP, "startup")
        add(
            "startup-inputs",
            "Startup capital inputs",
            startup_guidance,
            startup_recorded,
            "In everyday words: enter the one-time opening costs and the seat assumptions. Checking the box does not fill them in.",
        )
    for pillar in _note_pillars(blocking):
        stored_note = any(
            str(item.get("pillar_id") or "") == pillar["id"] and str(item.get("note") or "").strip()
            for item in notes or []
        )
        add(
            f"note-{pillar['id']}",
            f"Durable Value note: {pillar['title']}",
            (
                "An educational note on this pillar records the open question. "
                "Checking this item or saving a note does not clear a flag and is not a DVT evaluation."
            ),
            stored_note,
            "In everyday words: write the open question in your own words. The note is guidance, not a score.",
        )
    for flag in blocking:
        if flag == "INSUFFICIENT_DEMAND_EVIDENCE" or not _FLAG_ID.fullmatch(flag):
            continue
        add(
            f"gate-{flag}",
            f"Hard gate still active: {flag}",
            (
                f"{flag} remains an engine recommend-against flag. "
                "Checking this item does not clear it."
            ),
            False,
            "In everyday words: the engine still blocks a go-ahead on this point. Checking the box does not remove the block.",
        )
    noted_or_recorded = sum(1 for item in items if item["status"] != "open")
    return {
        "label": "Evidence checklist",
        "disclaimer": DISCLAIMER,
        "items": items,
        "noted_or_recorded": noted_or_recorded,
        "total": len(items),
        "clears_hard_gates": False,
        "sets_human_review_approved": False,
        "changes_recommendation": False,
    }


def posted_checks(form: dict[str, str]) -> dict[str, bool]:
    """Read checklist boxes. Any other posted field is ignored."""
    known: list[str] = []
    checked: set[str] = set()
    for key, value in form.items():
        if key.startswith("known_"):
            item_id = key[6:]
            if ITEM_ID.fullmatch(item_id):
                known.append(item_id)
        elif key.startswith("check_") and value == "1":
            item_id = key[6:]
            if ITEM_ID.fullmatch(item_id):
                checked.add(item_id)
    return {item_id: item_id in checked for item_id in known}


def apply_posted(
    record: dict[str, Any],
    checked: dict[str, bool],
    result: dict[str, Any] | None = None,
    notes: list[dict[str, Any]] | None = None,
) -> dict[str, bool]:
    """Merge posted boxes into checklist state. Unknown ids are dropped."""
    view = build_checklist(record, result, notes)
    valid = {str(item["id"]) for item in view["items"]}
    previous = record.get("checklist") if isinstance(record.get("checklist"), dict) else {}
    updated: dict[str, bool] = {}
    for key, value in previous.items():
        if isinstance(key, str) and ITEM_ID.fullmatch(key) and key not in valid:
            updated[key] = value is True
    for item_id, is_checked in checked.items():
        if item_id in valid:
            updated[item_id] = is_checked is True
    return updated


def _financial_copy(
    profile: dict[str, Any],
    fields: tuple[tuple[str, str], ...],
    kind: str,
) -> tuple[str, bool]:
    missing = [label for key, label in fields if not str(profile.get(key) or "").strip()]
    if missing:
        names = ", ".join(missing)
        if kind == "monthly":
            text = (
                f"Missing financial inputs: {names}. Enter them on the intake. "
                "Checking this item does not invent a figure and does not clear a flag."
            )
        else:
            text = (
                f"Missing startup inputs: {names}. Enter them on the intake. "
                "Checking this item does not invent a figure and does not clear a flag."
            )
        return text, False
    if kind == "monthly":
        text = (
            "The four monthly engine inputs are saved. They remain user-supplied assumptions "
            "and do not clear a recommend-against flag."
        )
    else:
        text = (
            "The startup capital inputs are saved. They remain user-supplied assumptions "
            "and do not clear a recommend-against flag."
        )
    return text, True


def _note_pillars(blocking: list[str]) -> list[dict[str, Any]]:
    from app.durable_value import PILLARS

    chosen: list[dict[str, Any]] = []
    seen: set[str] = set()
    for pillar in PILLARS:
        matched = any(flag in blocking for flag in pillar["related_flags"])
        if pillar["id"] in _KEY_NOTES or matched:
            if pillar["id"] not in seen:
                chosen.append(pillar)
                seen.add(pillar["id"])
    return chosen


def _venture_path(record: dict[str, Any]) -> str:
    business = record.get("business_profile") if isinstance(record.get("business_profile"), dict) else {}
    profile = record.get("profile") if isinstance(record.get("profile"), dict) else {}
    raw = str(business.get("venture_path") or profile.get("venture_path") or "startup")
    return raw if raw in {"startup", "existing"} else "startup"


def _verified_support(profile: dict[str, Any]) -> bool:
    if profile.get("hypothetical") is True:
        return False
    if str(profile.get("verified_record_source") or "").strip() != "verified":
        return False
    if not str(profile.get("verified_demand_rationale") or "").strip():
        return False
    if str(profile.get("verified_demand_evidence") or "").strip().lower() == "true":
        return True
    raw = str(profile.get("verified_revenue_trailing_12m") or "").strip()
    if not raw:
        return False
    try:
        number = float(raw)
    except ValueError:
        return False
    return math.isfinite(number) and number > 0

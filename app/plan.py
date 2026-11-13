"""Business plan documents copied from a saved assessment. Narrative edits do not recalculate."""

from __future__ import annotations

import json
from typing import Any

from app import display
from app.report_snapshot import build_report_snapshot, snapshot_markdown

NOT_WRITTEN = "Not written. This section was left blank."
ASSEMBLED = "Assembled from the saved assessment. This is not a live adviser response."
NARRATIVE_KEYS = (
    ("executive_summary", "Executive Summary"),
    ("products_services", "Products and Services"),
    ("marketing", "Marketing and Customer Acquisition"),
    ("operations", "Operations and Resources"),
    ("management", "Management and Organization"),
    ("growth", "Growth and Development Strategy"),
    ("durable_value", "Durable Value Considerations"),
    ("implementation", "Implementation Priorities and Next Steps"),
)
SECTION_LIMIT = 8000


def build_plan_document(
    record: dict[str, Any],
    *,
    actions: list[dict[str, Any]] | None = None,
    notes: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Copy stored profile, engine, and startup figures. Missing sections stay missing."""
    result = record.get("result") if isinstance(record.get("result"), dict) else {}
    projection = result.get("projection") if isinstance(result.get("projection"), dict) else None
    if not (isinstance(projection, dict) and projection.get("calculated")):
        stored_projection = None
    else:
        stored_projection = json.loads(json.dumps(projection))
        stored_projection["human_review_approved"] = False
        stored_projection["is_final"] = False
        stored_projection["investor_ready"] = False
    copied_actions = [
        {
            "title": str(item.get("title") or ""),
            "status": str(item.get("status") or "open"),
            "description": str(item.get("description") or ""),
        }
        for item in (actions or [])
        if isinstance(item, dict)
    ]
    copied_notes = [
        {"pillar_id": str(item.get("pillar_id") or ""), "note": str(item.get("note") or "")}
        for item in (notes or [])
        if isinstance(item, dict) and str(item.get("note") or "").strip()
    ]
    return {
        "snapshot": build_report_snapshot(record),
        "projection": stored_projection,
        "sections": initial_sections(record, actions=copied_actions, notes=copied_notes),
        "actions": copied_actions,
        "notes": copied_notes,
        "stage": "existing" if is_existing_business(record) else "startup",
        "narrative_source": ASSEMBLED,
    }


def is_existing_business(record: dict[str, Any]) -> bool:
    profile = record.get("profile") if isinstance(record.get("profile"), dict) else {}
    business = record.get("business_profile") if isinstance(record.get("business_profile"), dict) else {}
    return str(profile.get("venture_path") or business.get("venture_path") or "") == "existing"


def initial_sections(
    record: dict[str, Any],
    *,
    actions: list[dict[str, Any]] | None = None,
    notes: list[dict[str, Any]] | None = None,
) -> dict[str, str]:
    profile = record.get("profile") if isinstance(record.get("profile"), dict) else {}
    concept = str(profile.get("concept") or "").strip()
    products = str(profile.get("products") or "").strip()
    customers = str(profile.get("customers") or "").strip()
    product_lines = [part for part in (products, customers) if part]
    note_lines = [str(item.get("note") or "").strip() for item in (notes or []) if str(item.get("note") or "").strip()]
    if note_lines:
        durable = (
            "Educational guidance. This is not a DVT evaluation and it is not a score.\n"
            + "\n".join(note_lines)
        )
    else:
        durable = (
            "Educational guidance. This is not a DVT evaluation and it is not a score. "
            "No durable-value note is stored."
        )
    if actions:
        implementation = "\n".join(
            f"{item.get('status') or 'open'}: {item.get('title') or item.get('description') or 'Action'}"
            for item in actions
        )
    else:
        implementation = NOT_WRITTEN
    return {
        "executive_summary": concept or NOT_WRITTEN,
        "products_services": "\n\n".join(product_lines) if product_lines else NOT_WRITTEN,
        "marketing": NOT_WRITTEN,
        "operations": NOT_WRITTEN,
        "management": NOT_WRITTEN,
        "growth": NOT_WRITTEN,
        "durable_value": durable,
        "implementation": implementation,
    }


def edited_sections(document: dict[str, Any], form: dict[str, str]) -> dict[str, str]:
    """Replace narrative text the customer submitted. Financial keys in the form are ignored."""
    current = document.get("sections") if isinstance(document.get("sections"), dict) else {}
    sections = {key: str(current.get(key) or NOT_WRITTEN) for key, _label in NARRATIVE_KEYS}
    for key, label in NARRATIVE_KEYS:
        if key not in form:
            continue
        text = str(form.get(key) or "").strip()
        if len(text) > SECTION_LIMIT:
            raise ValueError(f"{label} is limited to {SECTION_LIMIT} characters. The plan was not changed.")
        sections[key] = text or NOT_WRITTEN
    return sections


def plan_markdown(document: dict[str, Any], *, title: str) -> str:
    snapshot = document.get("snapshot") if isinstance(document.get("snapshot"), dict) else {}
    sections = document.get("sections") if isinstance(document.get("sections"), dict) else {}
    lines = [f"# {title}", ""]
    for key, label in NARRATIVE_KEYS:
        lines.append(f"## {label}")
        lines.append(str(sections.get(key) or NOT_WRITTEN))
        lines.append("")
    lines.append(snapshot_markdown(snapshot).strip())
    lines.append("")
    lines.append("## Startup capital")
    if document.get("stage") == "existing":
        lines.append("Startup capital requirements are not part of this existing or expanding business. No allocation was added.")
        lines.append("Funding requirements for a new startup are not part of this existing or expanding business.")
    else:
        lines.extend(capital_lines(document.get("projection")))
    lines.append("")
    lines.append(ASSEMBLED)
    lines.append("A demonstration market snapshot is not copied into this plan.")
    lines.append("Editing this plan does not change the stored assessment or the saved financial figures in this snapshot.")
    lines.append("This plan does not set human_review_approved and it does not grant investor-ready status.")
    return "\n".join(lines).rstrip() + "\n"


def capital_lines(projection: Any) -> list[str]:
    if not isinstance(projection, dict) or not projection.get("calculated"):
        return ["Startup capital summary: Not calculated. Required startup fields were not stored."]
    uses = projection.get("sources_and_uses") if isinstance(projection.get("sources_and_uses"), dict) else {}
    use_lines = uses.get("uses") if isinstance(uses.get("uses"), dict) else {}
    source_lines = uses.get("sources") if isinstance(uses.get("sources"), dict) else {}
    base = _view(projection, "base")
    downside = _view(projection, "downside")
    rows = [
        _amount_line("total_project_cost", "Total project cost", use_lines),
        _amount_line("debt", "Debt", source_lines),
        _amount_line("equity", "Equity", source_lines),
        _number_line("startup_base_revenue", "Startup base revenue", base.get("revenue")),
        _number_line("startup_downside_revenue", "Startup downside revenue", downside.get("revenue")),
        _number_line("startup_base_dscr", "Startup base DSCR", base.get("dscr")),
    ]
    rows.append("human_review_approved: false")
    rows.append("investor_ready: false")
    rows.append("This capital block is a copy of the stored projection. It was not recalculated for this plan.")
    return rows


def _view(projection: dict[str, Any], name: str) -> dict[str, Any]:
    views = projection.get("views") if isinstance(projection.get("views"), dict) else {}
    nested = views.get(name) if isinstance(views.get(name), dict) else {}
    if nested:
        return nested
    direct = projection.get(name) if isinstance(projection.get(name), dict) else {}
    return direct


def _amount_line(key: str, label: str, container: dict[str, Any]) -> str:
    item = container.get(key) if isinstance(container.get(key), dict) else {}
    return _number_line(key, label, item.get("amount"))


def _number_line(key: str, label: str, value: Any) -> str:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return f"{label}: Not available. This figure is not in the stored projection."
    return f"{key}: {display.figure(key, value)}. {label}. Copied from the stored projection."

"""Customer objectives. Each one opens a real draft. None of them approve a file."""

from __future__ import annotations

from typing import Any

OBJECTIVES: tuple[dict[str, str], ...] = (
    {
        "id": "start-business",
        "label": "Start a Business",
        "purpose": "startup_feasibility",
        "venture_path": "startup",
        "availability": "Available now",
        "note": "Opens a startup draft and asks for the idea before any calculation.",
    },
    {
        "id": "evaluate-idea",
        "label": "Evaluate a Business Idea",
        "purpose": "startup_feasibility",
        "venture_path": "startup",
        "availability": "Available now",
        "note": "Opens a startup draft. RUGD analyzes it only when you choose Analyze.",
    },
    {
        "id": "existing-business",
        "label": "Analyze My Existing Business",
        "purpose": "operational_diagnostic",
        "venture_path": "existing",
        "availability": "Available now",
        "note": "Opens an existing-business draft. Startup-only cost questions are skipped.",
    },
    {
        "id": "improve-profitability",
        "label": "Improve Profitability",
        "purpose": "operational_diagnostic",
        "venture_path": "existing",
        "availability": "Available now",
        "note": "Opens an existing-business draft and asks how the business makes money.",
    },
    {
        "id": "business-plan",
        "label": "Develop a Business Plan",
        "purpose": "startup_feasibility",
        "venture_path": "startup",
        "availability": "Available now",
        "note": "Collects the concept and the gaps. It does not write a pitch deck.",
    },
    {
        "id": "research-market",
        "label": "Research a Market",
        "purpose": "startup_feasibility",
        "venture_path": "startup",
        "availability": "Available now",
        "note": "Saves the industry and place, then points to Market Intelligence.",
    },
    {
        "id": "expansion",
        "label": "Evaluate an Expansion",
        "purpose": "expansion_feasibility",
        "venture_path": "existing",
        "availability": "Available now",
        "note": "Opens an expansion draft. The choice does not lift a concern.",
    },
    {
        "id": "prepare-investment",
        "label": "Prepare for Investment",
        "purpose": "startup_feasibility",
        "venture_path": "startup",
        "availability": "Available now",
        "note": "Collects the draft an investor would ask about. It does not grant investor-ready status.",
    },
    {
        "id": "prepare-sale",
        "label": "Prepare for Sale or Exit",
        "purpose": "acquisition",
        "venture_path": "existing",
        "availability": "Available now",
        "note": "The workspace opens. RUGD does not score a sale or exit yet.",
    },
    {
        "id": "durable-value",
        "label": "Build Durable Value",
        "purpose": "startup_feasibility",
        "venture_path": "startup",
        "availability": "Available now",
        "note": "Asks about the business, then shows one educational Durable Value theme. It is not a score.",
    },
    {
        "id": "monitor",
        "label": "Monitor My Business or Industry",
        "purpose": "operational_diagnostic",
        "venture_path": "existing",
        "availability": "Demonstration",
        "note": "Opens a draft. Market Pulse monitoring is not active and no job is scheduled.",
    },
)

_BY_ID = {item["id"]: item for item in OBJECTIVES}


def objective_by_id(value: str) -> dict[str, str] | None:
    return _BY_ID.get(str(value or "").strip())


def objective_label(value: str) -> str:
    found = objective_by_id(value)
    return found["label"] if found else "this draft"

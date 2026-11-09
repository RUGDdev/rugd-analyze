"""Educational Durable Value prompts. Not a DVT evaluation and not a score.

The seven pillars use the evaluation-dimension names already listed in
scoring.rules.DIMENSIONS. This module does not import Longarc_Platform,
does not score a pillar, and does not read or write engine results.
"""

from __future__ import annotations

from typing import Any

LABEL = "Educational guidance — not a DVT evaluation."

PILLARS: tuple[dict[str, Any], ...] = (
    {
        "id": "market-demand",
        "title": "Market & Demand Reality",
        "introductory_question": (
            "What observable evidence would show that customers will buy, "
            "and which statements are still assumptions?"
        ),
        "practical_prompt": (
            "Write the demand question that is still open. "
            "This note does not clear INSUFFICIENT_DEMAND_EVIDENCE."
        ),
        "related_flags": ("INSUFFICIENT_DEMAND_EVIDENCE", "DEMAND_EVIDENCE_UNVERIFIED"),
    },
    {
        "id": "competitive-position",
        "title": "Competitive Position & Differentiation",
        "introductory_question": (
            "Who else can the customer choose, and what is different about this offer?"
        ),
        "practical_prompt": (
            "Name the alternatives already described by the user. "
            "Do not add a share, a rank, or a score."
        ),
        "related_flags": (),
    },
    {
        "id": "financial-feasibility",
        "title": "Financial Feasibility & Capital Requirements",
        "introductory_question": (
            "Which capital and monthly figures are measured, and which are still blank?"
        ),
        "practical_prompt": (
            "Restate the cash-flow or capital flag in plain language. "
            "Do not replace an engine number."
        ),
        "related_flags": (
            "NEGATIVE_OR_MARGINAL_CASH_FLOW",
            "FINANCIAL_INPUTS_NOT_MEASURED",
            "NO_GROSS_MARGIN",
        ),
    },
    {
        "id": "operational-readiness",
        "title": "Operational Readiness & Capacity",
        "introductory_question": (
            "Who will do the work, and is that capacity enough for the scope being considered?"
        ),
        "practical_prompt": (
            "Write the capacity question that is still open. "
            "Do not mark capacity adequate in this note."
        ),
        "related_flags": ("INADEQUATE_OPERATOR_CAPACITY", "UNEVALUATED_OPERATOR_CAPACITY"),
    },
    {
        "id": "risk-profile",
        "title": "Risk Profile (market, execution, financial, regulatory)",
        "introductory_question": "What regulatory, liability, or execution question is still unresolved?",
        "practical_prompt": (
            "Describe the open risk as a question. This note does not resolve it."
        ),
        "related_flags": (
            "UNRESOLVED_REGULATORY_OR_LIABILITY",
            "UNEVALUATED_REGULATORY_OR_LIABILITY",
        ),
    },
    {
        "id": "stewardship",
        "title": "Stewardship Indicators (reinvestment capacity, resilience, continuity potential)",
        "introductory_question": (
            "If the business produces cash, what would be reinvested, and what would be taken out?"
        ),
        "practical_prompt": (
            "Write the reinvestment question only. "
            "This note does not clear EXTRACTION_WITHOUT_REINVESTMENT."
        ),
        "related_flags": ("EXTRACTION_WITHOUT_REINVESTMENT", "UNEVALUATED_STEWARDSHIP"),
    },
    {
        "id": "implementation",
        "title": "Implementation Feasibility (for AI or operational improvements)",
        "introductory_question": (
            "What would have to be true before an operational change is attempted?"
        ),
        "practical_prompt": (
            "List the next practical check. This note is not an implementation result."
        ),
        "related_flags": (),
    },
)


def pillar_by_id(pillar_id: str) -> dict[str, Any] | None:
    for pillar in PILLARS:
        if pillar["id"] == pillar_id:
            return pillar
    return None


def guidance_for(depth: str, result: dict[str, Any] | None = None) -> dict[str, Any]:
    """Return educational copy for a tier view. The result is read, never changed."""
    if depth not in ("explore", "analyze", "demonstration"):
        depth = "explore"
    flags: list[str] = []
    if isinstance(result, dict):
        flags.extend(str(item) for item in result.get("blocking_flags") or [])
        flags.extend(str(item) for item in result.get("gap_flags") or [])
    seen = set(flags)
    pillars = []
    for pillar in PILLARS:
        matched = [flag for flag in pillar["related_flags"] if flag in seen]
        pillars.append(
            {
                "id": pillar["id"],
                "title": pillar["title"],
                "introductory_question": pillar["introductory_question"],
                "practical_prompt": pillar["practical_prompt"],
                "matched_flags": matched,
                "relevant": bool(matched),
            }
        )
    return {
        "label": LABEL,
        "depth": depth,
        "authoritative": False,
        "pillars": pillars,
    }

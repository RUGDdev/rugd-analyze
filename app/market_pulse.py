"""Static Market Pulse demonstration.

No scheduler, connector, notification, or market provider is used.
The payload cannot change an assessment, a flag, or a score.
"""

from __future__ import annotations

from typing import Any

from app.durable_value import LABEL, PILLARS

PULSE_LABEL = "Hypothetical demonstration — monitoring not active."

QUESTIONS: tuple[str, ...] = (
    "What changed in this example, and which period would it cover if it were real?",
    "Is this example internal to the business or external to its market?",
    "Which assessment assumption would the example touch if it were real?",
    "Which recommend-against flag is already active, and does this example leave that flag active?",
    "What evidence is still missing before anyone treats the example as a fact?",
    "What would a manager check before changing a plan?",
    "Who must review a change before it is treated as a decision?",
    "What would have to be connected before this card could leave the demonstration?",
)

_CARDS: tuple[dict[str, Any], ...] = (
    {
        "id": "revenue-trend",
        "side": "internal",
        "title": "Revenue trend",
        "example": (
            "Example only: an invented revenue line steps from one blank month to the next. "
            "No accounting system is connected."
        ),
        "pillar_ids": ("financial-feasibility", "market-demand"),
    },
    {
        "id": "labor",
        "side": "internal",
        "title": "Labor",
        "example": (
            "Example only: an invented labor note for an unnamed crew. "
            "No payroll system is connected."
        ),
        "pillar_ids": ("operational-readiness",),
    },
    {
        "id": "local-demographics",
        "side": "external",
        "title": "Local demographics",
        "example": (
            "Example only: an invented population note for an unspecified demonstration market. "
            "No Census feed is connected."
        ),
        "pillar_ids": ("market-demand",),
    },
    {
        "id": "competitive-developments",
        "side": "external",
        "title": "Competitive developments",
        "example": (
            "Example only: an invented note that a neighboring offer exists. "
            "No competitor dataset is connected."
        ),
        "pillar_ids": ("competitive-position",),
    },
    {
        "id": "cost-pressure",
        "side": "external",
        "title": "Operating-cost pressure",
        "example": (
            "Example only: an invented note that a supply cost could move. "
            "No price feed is connected."
        ),
        "pillar_ids": ("financial-feasibility", "risk-profile"),
    },
    {
        "id": "emerging-opportunity",
        "side": "external",
        "title": "Emerging opportunity",
        "example": (
            "Example only: an invented note that a new use of the offer might exist. "
            "No opportunity feed is connected."
        ),
        "pillar_ids": ("implementation", "stewardship"),
    },
)


def _pillar_title(pillar_id: str) -> str:
    for pillar in PILLARS:
        if pillar["id"] == pillar_id:
            return str(pillar["title"])
    return pillar_id


def market_pulse() -> dict[str, Any]:
    """Return the demonstration dashboard. Monitoring stays off."""
    cards = []
    for spec in _CARDS:
        cards.append(
            {
                "id": spec["id"],
                "side": spec["side"],
                "title": spec["title"],
                "example": spec["example"],
                "label": PULSE_LABEL,
                "monitoring_active": False,
                "connector": None,
                "scheduled": False,
                "notification": None,
                "authoritative": False,
                "pillar_labels": [_pillar_title(pillar_id) for pillar_id in spec["pillar_ids"]],
                "pillar_label_note": LABEL,
            }
        )
    return {
        "title": "Market Pulse",
        "label": PULSE_LABEL,
        "monitoring_active": False,
        "live_feed_connected": False,
        "scheduled_jobs": [],
        "connectors": [],
        "notifications": [],
        "authoritative": False,
        "cards": cards,
        "questions": list(QUESTIONS),
    }

"""One market-intelligence snapshot shared by every service tier.

The snapshot is a demonstration. It does not call a data provider and it does
not run monitoring.
"""

from __future__ import annotations

from typing import Any

DEMONSTRATION_LABEL = "Demonstration. Not market research and not active monitoring."


def market_framework(industry: str | None = None) -> dict[str, Any]:
    """Return the only market snapshot the application renders."""
    return {
        "label": DEMONSTRATION_LABEL,
        "mode": "demonstration",
        "live_feed": False,
        "monitoring_active": False,
        "industry": industry or "Not selected",
        "geographic_market": "Not selected",
        "source_dataset": None,
        "observations": [],
        "synthetic_examples": [
            "Synthetic example only: a cost-pressure note with no source dataset.",
            "Synthetic example only: a competitive-opening note with no source dataset.",
        ],
    }

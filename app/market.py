"""One market-intelligence snapshot shared by every service tier.

The snapshot is a demonstration. It does not call a data provider and it does
not run monitoring.
"""

from __future__ import annotations

from typing import Any

DEMONSTRATION_LABEL = "Demonstration. Not market research and not active monitoring."
DEMONSTRATION_INDUSTRIES = ("Not selected", "Restaurant", "Professional services", "Retail")
DEMONSTRATION_GEOGRAPHIES = (
    "Not selected",
    "Unspecified demonstration market",
    "Example county",
)


def market_framework(
    industry: str | None = None,
    geographic_market: str | None = None,
) -> dict[str, Any]:
    """Return the only market snapshot the application renders."""
    return {
        "label": DEMONSTRATION_LABEL,
        "mode": "demonstration",
        "live_feed": False,
        "monitoring_active": False,
        "industry": _choice(industry, DEMONSTRATION_INDUSTRIES),
        "geographic_market": _choice(geographic_market, DEMONSTRATION_GEOGRAPHIES),
        "source_dataset": None,
        "observations": [],
        "synthetic_examples": [
            "Synthetic example only: a cost-pressure note with no source dataset.",
            "Synthetic example only: a competitive-opening note with no source dataset.",
        ],
    }


def assessment_implications(
    records: list[dict[str, Any]],
    industry: str | None = None,
    geographic_market: str | None = None,
) -> list[str]:
    """Name saved industry and stage. Do not add a market fact."""
    snapshot = market_framework(industry, geographic_market)
    lines = []
    for record in records:
        if record.get("read_only"):
            continue
        profile = record.get("profile") or {}
        lines.append(
            f"{record.get('business_name')} lists industry {profile.get('industry') or 'not entered'} "
            f"and stage {profile.get('stage') or 'not entered'}. "
            "No market fact is supplied for that industry or stage."
        )
    if not lines:
        lines.append("No customer draft has an industry and stage to reference. No market fact is invented.")
    lines.append(
        "The demonstration selection is industry "
        f"{snapshot['industry']} and geographic market {snapshot['geographic_market']}. "
        "That selection does not load a dataset and does not describe a real market."
    )
    return lines


def _choice(value: str | None, allowed: tuple[str, ...]) -> str:
    text = str(value or "").strip()
    if text in allowed:
        return text
    return "Not selected"

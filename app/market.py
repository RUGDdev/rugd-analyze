"""Market snapshot and optional public observations.

The synthetic snapshot is the default. A public provider is used only when
configured. It does not run monitoring and it does not change an assessment.
"""

from __future__ import annotations

import csv
import io
import os
import urllib.error
import urllib.request
from datetime import datetime, timezone
from typing import Any, Callable

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


OBSERVATION_FIELDS = (
    "source",
    "geographic_coverage",
    "industry_classification",
    "measurement_period",
    "retrieval_date",
    "limitations",
    "measure",
    "value",
)
PUBLIC_SOURCE = "U.S. Bureau of Labor Statistics, Quarterly Census of Employment and Wages"
PUBLIC_LABEL = (
    "Public source: U.S. Bureau of Labor Statistics, Quarterly Census of Employment and Wages. "
    "Not a live feed. Not monitoring. These figures do not clear INSUFFICIENT_DEMAND_EVIDENCE "
    "or any recommend-against flag."
)
FALLBACK_LABEL = (
    "Fallback: synthetic snapshot. The public market provider did not return observations. "
    "Synthetic example only."
)
NOT_COVERED_LABEL = (
    "This industry and geography are not covered by the public provider. "
    "Fallback: synthetic snapshot. Synthetic example only."
)


class NotCovered(LookupError):
    """The selection is outside the mapped public extract."""
_PUBLIC_LIMITATION = (
    "Annual average for private ownership in the Quarterly Census of Employment and Wages. "
    "This is covered employment and wages for an industry and geography, not revenue or demand "
    "for any one business. It does not clear INSUFFICIENT_DEMAND_EVIDENCE or any other "
    "recommend-against flag, and it does not set human_review_approved. "
    "It is not a live feed. Monitoring is not active. BLS may suppress a cell or revise a release."
)
_INDUSTRIES = {
    "Restaurant": ("722", "NAICS 722 Food services and drinking places"),
    "Professional services": ("54", "NAICS 54 Professional, scientific, and technical services"),
    "Retail": ("44-45", "NAICS 44-45 Retail trade"),
    "Construction": ("23", "NAICS 23 Construction"),
    "Manufacturing": ("31-33", "NAICS 31-33 Manufacturing"),
    "Accommodation": ("721", "NAICS 721 Accommodation"),
    "Health care": ("62", "NAICS 62 Health care and social assistance"),
}
PUBLIC_INDUSTRIES = ("Not selected",) + tuple(_INDUSTRIES)
_CORE_MEASURES = (
    ("annual_avg_emplvl", "Private annual average employment"),
    ("annual_avg_wkly_wage", "Private annual average weekly wage"),
    ("annual_avg_estabs", "Private annual average establishments"),
)
_EXTRA_MEASURES = (
    ("total_annual_wages", "Private total annual wages"),
    ("avg_annual_pay", "Private average annual pay"),
)
_GEOGRAPHIES = {
    "United States": ("US000", "United States"),
    "Alabama": ("01000", "Alabama"),
    "Colbert County, Alabama": ("01033", "Colbert County, Alabama"),
}
PUBLIC_GEOGRAPHIES = ("Not selected",) + tuple(_GEOGRAPHIES) + (
    "Unspecified demonstration market",
    "Example county",
)
Fetch = Callable[[str], str]


class SyntheticMarketProvider:
    """The labeled demonstration snapshot. It does not request a public file."""

    name = "synthetic"

    def observations(self, industry: str | None, geography: str | None) -> list[dict[str, str]]:
        return []


class UnavailableMarketProvider:
    """A named provider this prototype does not call."""

    name = "unavailable"

    def __init__(self, requested: str) -> None:
        self.requested = requested

    def observations(self, industry: str | None, geography: str | None) -> list[dict[str, str]]:
        raise LookupError("market provider is not configured")


class BlsQcewProvider:
    """Annual QCEW employment and wages for a mapped industry and geography."""

    name = "bls-qcew"

    def __init__(
        self,
        *,
        year: str = "2024",
        transport: Fetch | None = None,
        retrieved_on: str | None = None,
    ) -> None:
        self.year = year if len(year) == 4 and year.isdigit() else "2024"
        self._transport = transport or _fetch_text
        self._retrieved_on = retrieved_on

    def observations(self, industry: str | None, geography: str | None) -> list[dict[str, str]]:
        industry_name = str(industry or "").strip()
        geography_name = str(geography or "").strip()
        industry_spec = _INDUSTRIES.get(industry_name)
        geography_spec = _GEOGRAPHIES.get(geography_name)
        if industry_spec is None or geography_spec is None:
            raise NotCovered("selection is not covered")
        code, classification = industry_spec
        area_fips, coverage = geography_spec
        url = f"https://data.bls.gov/cew/data/api/{self.year}/a/area/{area_fips}.csv"
        body = self._transport(url)
        return _observations_from_qcew(
            body,
            industry_code=code,
            classification=classification,
            coverage=f"{coverage} (area {area_fips})",
            period=f"{self.year} annual",
            retrieved_on=self._retrieved_on or _today(),
        )


def get_market_provider(environ: Any | None = None, transport: Fetch | None = None) -> Any:
    """Return the synthetic snapshot unless MARKET_PROVIDER asks for BLS QCEW."""
    env = os.environ if environ is None else environ
    raw = str(env.get("MARKET_PROVIDER") or "").strip().lower()
    if raw in {"", "synthetic", "demo", "demonstration", "none"}:
        return SyntheticMarketProvider()
    if raw in {"bls", "qcew", "bls-qcew"}:
        year = str(env.get("MARKET_YEAR") or "2024").strip()
        return BlsQcewProvider(year=year, transport=transport)
    return UnavailableMarketProvider(raw)


def load_market(
    industry: str | None = None,
    geographic_market: str | None = None,
    provider: Any | None = None,
) -> dict[str, Any]:
    """Observations for a selection. Failure returns the synthetic snapshot."""
    snapshot = market_framework(industry, geographic_market)
    selected = provider if provider is not None else SyntheticMarketProvider()
    if getattr(selected, "name", "") == "synthetic":
        return {
            "status": "synthetic",
            "label": DEMONSTRATION_LABEL,
            "reason": None,
            "provider_name": "synthetic",
            "year": "",
            "snapshot": snapshot,
            "observations": [],
        }
    try:
        observations = list(selected.observations(industry, geographic_market))
        if not observations:
            raise ValueError("empty market response")
        for item in observations:
            missing = [field for field in OBSERVATION_FIELDS if not str(item.get(field) or "").strip()]
            if missing:
                raise ValueError("market observation is missing provenance")
        return {
            "status": "public",
            "label": PUBLIC_LABEL,
            "reason": None,
            "provider_name": str(getattr(selected, "name", "") or ""),
            "year": str(getattr(selected, "year", "") or ""),
            "snapshot": snapshot,
            "observations": observations,
        }
    except NotCovered:
        return _fallback_view(selected, snapshot, NOT_COVERED_LABEL, "This industry and geography are not covered by the public provider.")
    except Exception:
        return _fallback_view(
            selected,
            snapshot,
            FALLBACK_LABEL,
            "The public market provider did not return observations.",
        )


def _observations_from_qcew(
    body: str,
    *,
    industry_code: str,
    classification: str,
    coverage: str,
    period: str,
    retrieved_on: str,
) -> list[dict[str, str]]:
    rows = list(csv.DictReader(io.StringIO(body)))
    match = next(
        (
            row
            for row in rows
            if str(row.get("own_code") or "") == "5" and str(row.get("industry_code") or "") == industry_code
        ),
        None,
    )
    if match is None:
        raise LookupError("industry row is not in the public file")
    base = {
        "source": PUBLIC_SOURCE,
        "geographic_coverage": coverage,
        "industry_classification": f"{classification}; private ownership",
        "measurement_period": period,
        "retrieval_date": retrieved_on,
    }
    disclosure = str(match.get("disclosure_code") or "").strip()
    if disclosure:
        limitations = (
            f"{_PUBLIC_LIMITATION} This cell is not disclosed (disclosure code {disclosure}). "
            "A zero in the file is not shown as a measured zero."
        )
        return [
            {
                **base,
                "limitations": limitations,
                "measure": (
                    "Private annual average employment, weekly wage, establishments, "
                    "total annual wages, average annual pay, and establishment size coverage"
                ),
                "value": "Not disclosed",
            }
        ]
    limitations = _PUBLIC_LIMITATION
    observations = []
    for field, label in _CORE_MEASURES:
        value = str(match.get(field) or "").strip()
        if not value:
            raise ValueError("public measure is blank")
        observations.append({**base, "limitations": limitations, "measure": label, "value": value})
    for field, label in _EXTRA_MEASURES:
        value = str(match.get(field) or "").strip()
        if value:
            observations.append({**base, "limitations": limitations, "measure": label, "value": value})
    size_code = str(match.get("size_code") or "").strip()
    if size_code:
        coverage = "All size classes combined" if size_code == "0" else f"Size code {size_code}"
        observations.append(
            {**base, "limitations": limitations, "measure": "Establishment size coverage", "value": coverage}
        )
    return observations


def _fallback_view(provider: Any, snapshot: dict[str, Any], label: str, reason: str) -> dict[str, Any]:
    return {
        "status": "fallback",
        "label": label,
        "reason": reason,
        "provider_name": str(getattr(provider, "name", "") or ""),
        "year": str(getattr(provider, "year", "") or ""),
        "snapshot": snapshot,
        "observations": [],
    }


def _fetch_text(url: str) -> str:
    request = urllib.request.Request(url, headers={"User-Agent": "RUGD-Analyze-prototype"})
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            payload = response.read(5_000_001)
    except urllib.error.URLError as exc:
        raise RuntimeError("market provider request failed") from exc
    if len(payload) > 5_000_000:
        raise RuntimeError("market response too large")
    return payload.decode("utf-8")


def _today() -> str:
    return datetime.now(timezone.utc).date().isoformat()

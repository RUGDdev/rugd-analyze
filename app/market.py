"""Market snapshot and optional public observations.

The synthetic snapshot is the default. A public provider is used only when
configured. It does not run monitoring and it does not change an assessment.
"""

from __future__ import annotations

import csv
import io
import json
import os
import urllib.error
import urllib.request
from datetime import datetime, timezone
from typing import Any, Callable

from app.export import _without_secrets

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
CENSUS_SOURCE = "U.S. Census Bureau, American Community Survey 5-year estimates"
CBP_SOURCE = "U.S. Census Bureau, County Business Patterns"
ACS_LABEL = (
    "Public source: U.S. Census Bureau, American Community Survey 5-year estimates. "
    "Not a live feed. Not monitoring. These figures do not clear INSUFFICIENT_DEMAND_EVIDENCE "
    "or any recommend-against flag."
)
PUBLIC_LABEL = (
    "Public source: U.S. Bureau of Labor Statistics, Quarterly Census of Employment and Wages. "
    "Not a live feed. Not monitoring. These figures do not clear INSUFFICIENT_DEMAND_EVIDENCE "
    "or any recommend-against flag."
)
CBP_LABEL = (
    "Public source: U.S. Census Bureau, County Business Patterns. "
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
    ("annual_avg_emplvl", "Private annual average employment", "headline"),
    ("annual_avg_wkly_wage", "Private annual average weekly wage", "detail"),
    ("annual_avg_estabs", "Private annual average establishments", "detail"),
)
_EXTRA_MEASURES = (
    ("total_annual_wages", "Private total annual wages", "detail"),
    ("avg_annual_pay", "Private average annual pay", "detail"),
)
_TREND_MEASURES = (
    ("oty_annual_avg_emplvl_pct_chg", "Private employment change from the prior year (percent)"),
    ("oty_annual_avg_wkly_wage_pct_chg", "Private weekly wage change from the prior year (percent)"),
    ("oty_annual_avg_estabs_pct_chg", "Private establishment count change from the prior year (percent)"),
)
_GEOGRAPHIES = {
    "United States": ("US000", "United States"),
    "Alabama": ("01000", "Alabama"),
    "Colbert County, Alabama": ("01033", "Colbert County, Alabama"),
    "Tennessee": ("47000", "Tennessee"),
    "Hamilton County, Tennessee": ("47065", "Hamilton County, Tennessee"),
    "Georgia": ("13000", "Georgia"),
    "Fulton County, Georgia": ("13121", "Fulton County, Georgia"),
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


_ACS_GEOGRAPHIES = {
    "United States": "010XX00US",
    "Alabama": "040XX00US01",
    "Colbert County, Alabama": "050XX00US01033",
    "Tennessee": "040XX00US47",
    "Hamilton County, Tennessee": "050XX00US47065",
    "Georgia": "040XX00US13",
    "Fulton County, Georgia": "050XX00US13121",
}
_ACS_TABLES = (
    ("B01003", "B01003_001E", "Total population"),
    ("B19013", "B19013_001E", "Median household income (dollars)"),
)
_ACS_LIMITATION = (
    "American Community Survey 5-year estimates, tables B01003 (total population) and "
    "B19013 (median household income). These are residence-based survey estimates, not revenue "
    "or demand for any one business. Margins of error are not shown. "
    "It does not clear INSUFFICIENT_DEMAND_EVIDENCE or any other recommend-against flag, "
    "and it does not set human_review_approved. It is not a live feed. Monitoring is not active. "
    "Census may suppress a cell or revise a release."
)


class CensusAcsProvider:
    """ACS 5-year population and median household income for a mapped geography."""

    name = "census-acs"

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
        geography_name = str(geography or "").strip()
        geo_code = _ACS_GEOGRAPHIES.get(geography_name)
        if geo_code is None:
            raise NotCovered("selection is not covered")
        retrieved_on = self._retrieved_on or _today()
        period = f"{int(self.year) - 4}-{self.year} 5-year"
        coverage = f"{geography_name} (ACS geography {geo_code})"
        observations = []
        for table, column, measure in _ACS_TABLES:
            url = (
                "https://data.census.gov/api/access/data/table"
                f"?id=ACSDT5Y{self.year}.{table}&g={geo_code}"
            )
            value = _acs_estimate(self._transport(url), column)
            observations.append(
                {
                    "source": CENSUS_SOURCE,
                    "geographic_coverage": coverage,
                    "industry_classification": "Demographic. Not a NAICS industry.",
                    "measurement_period": period,
                    "retrieval_date": retrieved_on,
                    "limitations": _ACS_LIMITATION,
                    "measure": measure,
                    "value": value,
                    "detail": "headline",
                }
            )
        change = self._population_change(
            geo_code,
            observations[0]["value"],
            coverage,
            retrieved_on,
        )
        if change is not None:
            observations.append(change)
        distribution = self._income_distribution(geo_code, coverage, period, retrieved_on)
        if distribution is not None:
            observations.append(distribution)
        return observations

    def _population_change(
        self,
        geo_code: str,
        current_value: str,
        coverage: str,
        retrieved_on: str,
    ) -> dict[str, str] | None:
        if not str(current_value).isdigit():
            return None
        prior_year = str(int(self.year) - 1)
        url = (
            "https://data.census.gov/api/access/data/table"
            f"?id=ACSDT5Y{prior_year}.B01003&g={geo_code}"
        )
        try:
            prior_value = _acs_estimate(self._transport(url), "B01003_001E")
        except (LookupError, ValueError, RuntimeError, OSError):
            return None
        if not str(prior_value).isdigit():
            return None
        prior_period = f"{int(prior_year) - 4}-{prior_year} 5-year"
        current_period = f"{int(self.year) - 4}-{self.year} 5-year"
        return {
            "source": CENSUS_SOURCE,
            "geographic_coverage": coverage,
            "industry_classification": "Demographic. Not a NAICS industry.",
            "measurement_period": f"{prior_period} to {current_period}",
            "retrieval_date": retrieved_on,
            "limitations": (
                "Derived by subtracting the prior ACS 5-year total population, table B01003, "
                "from the selected vintage. The two 5-year periods overlap, so this is not a "
                "one-year population change. It does not clear INSUFFICIENT_DEMAND_EVIDENCE or "
                "any other recommend-against flag, and it does not set human_review_approved."
            ),
            "measure": "Population change between overlapping ACS 5-year vintages",
            "value": str(int(current_value) - int(prior_value)),
            "detail": "extended",
        }

    def _income_distribution(
        self,
        geo_code: str,
        coverage: str,
        period: str,
        retrieved_on: str,
    ) -> dict[str, str] | None:
        url = (
            "https://data.census.gov/api/access/data/table"
            f"?id=ACSDT5Y{self.year}.B19001&g={geo_code}"
        )
        try:
            counts = _acs_columns(
                self._transport(url),
                ("B19001_001E", "B19001_002E", "B19001_017E"),
            )
        except (LookupError, ValueError, RuntimeError, OSError):
            return None
        limitations = (
            "American Community Survey 5-year table B19001 household income brackets. "
            "The note uses the published count under $10,000 and the published count at "
            "$200,000 or more. A whole-number share is derived from those counts and is rounded down. "
            "This is not a recommendation. It does not clear INSUFFICIENT_DEMAND_EVIDENCE or any "
            "other recommend-against flag, and it does not set human_review_approved."
        )
        base = {
            "source": CENSUS_SOURCE,
            "geographic_coverage": coverage,
            "industry_classification": "Demographic. Not a NAICS industry.",
            "measurement_period": period,
            "retrieval_date": retrieved_on,
            "limitations": limitations,
            "measure": "Household income distribution note",
            "detail": "extended",
        }
        if counts is None:
            return {**base, "value": "Not disclosed"}
        total, low, high = counts
        if total <= 0:
            return {**base, "value": "Not disclosed"}
        low_share = (low * 100) // total
        high_share = (high * 100) // total
        return {
            **base,
            "value": (
                f"Households under $10,000: {low} of {total} "
                f"(derived whole-number share {low_share} percent, rounded down). "
                f"Households at $200,000 or more: {high} of {total} "
                f"(derived whole-number share {high_share} percent, rounded down)."
            ),
        }


class CensusCbpProvider:
    """County Business Patterns establishments, employment, and payroll for one mapped industry."""

    name = "census-cbp"

    def __init__(
        self,
        *,
        year: str = "2023",
        transport: Fetch | None = None,
        retrieved_on: str | None = None,
    ) -> None:
        self.year = year if len(year) == 4 and year.isdigit() else "2023"
        self._transport = transport or _fetch_text
        self._retrieved_on = retrieved_on

    def observations(self, industry: str | None, geography: str | None) -> list[dict[str, str]]:
        industry_name = str(industry or "").strip()
        geography_name = str(geography or "").strip()
        industry_spec = _INDUSTRIES.get(industry_name)
        geo_code = _ACS_GEOGRAPHIES.get(geography_name)
        if industry_spec is None or geo_code is None:
            raise NotCovered("selection is not covered")
        code, classification = industry_spec
        table = f"CBP{self.year}.CB{self.year[-2:]}00CBP"
        url = f"https://data.census.gov/api/access/data/table?id={table}&g={geo_code}"
        row = _cbp_row(self._transport(url), code)
        retrieved_on = self._retrieved_on or _today()
        limitations = (
            f"County Business Patterns table {table}, all legal forms and all employment sizes. "
            "This release is published at sector grain, so a 6-digit NAICS code that is not in the "
            "table is not covered. Annual payroll is published in thousands of dollars. "
            "These are establishment counts, employment, and payroll, not revenue or demand for any "
            "one business. They do not clear INSUFFICIENT_DEMAND_EVIDENCE or any other "
            "recommend-against flag, and they do not set human_review_approved. "
            "This is not a live feed. Monitoring is not active."
        )
        base = {
            "source": CBP_SOURCE,
            "geographic_coverage": f"{geography_name} (CBP geography {geo_code})",
            "industry_classification": f"{classification}; County Business Patterns",
            "measurement_period": f"{self.year} annual",
            "retrieval_date": retrieved_on,
            "limitations": limitations,
        }
        fields = (
            ("ESTAB", "Establishments", "headline"),
            ("EMP", "CBP employment", "detail"),
            ("PAYANN", "Annual payroll (thousands of dollars)", "extended"),
        )
        observations = []
        for field, label, detail in fields:
            flag = str(row.get(f"{field}_F") or "").strip()
            raw = "" if row.get(field) is None else str(row.get(field)).strip()
            if flag or not raw.isdigit():
                value = "Not disclosed"
            else:
                value = raw
            observations.append({**base, "measure": label, "value": value, "detail": detail})
        return observations


class CombinedMarketProvider:
    """BLS and Census together. A failed part does not remove the other part."""

    name = "combined"

    def __init__(self, parts: list[Any]) -> None:
        self.parts = parts
        years = {str(getattr(part, "year", "") or "") for part in parts}
        self.year = next(iter(years)) if len(years) == 1 else "multiple"


def get_market_provider(environ: Any | None = None, transport: Fetch | None = None) -> Any:
    """Return the synthetic snapshot unless BLS or Census is requested."""
    env = os.environ if environ is None else environ
    raw = str(env.get("MARKET_PROVIDER") or "").strip().lower()
    census_raw = str(env.get("MARKET_CENSUS") or "").strip().lower()
    cbp_raw = str(env.get("MARKET_CBP") or "").strip().lower()
    parts: list[Any] = []
    if raw in {"bls", "qcew", "bls-qcew"}:
        parts.append(BlsQcewProvider(year=_year(env, "MARKET_YEAR", "2024"), transport=transport))
    elif raw not in {"", "synthetic", "demo", "demonstration", "none"}:
        parts.append(UnavailableMarketProvider(raw))
    if census_raw in {"acs", "census", "census-acs"}:
        parts.append(CensusAcsProvider(year=_year(env, "ACS_YEAR", "2024"), transport=transport))
    elif census_raw not in {"", "none", "off", "synthetic", "demo", "demonstration"}:
        parts.append(UnavailableMarketProvider(census_raw))
    if cbp_raw in {"cbp", "census-cbp", "patterns"}:
        parts.append(CensusCbpProvider(year=_year(env, "CBP_YEAR", "2023"), transport=transport))
    elif cbp_raw not in {"", "none", "off", "synthetic", "demo", "demonstration"}:
        parts.append(UnavailableMarketProvider(cbp_raw))
    if not parts:
        return SyntheticMarketProvider()
    if len(parts) == 1 and not isinstance(parts[0], UnavailableMarketProvider):
        return parts[0]
    if len(parts) == 1:
        return parts[0]
    return CombinedMarketProvider(parts)


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
    if getattr(selected, "name", "") == "combined":
        return _load_combined(selected, industry, geographic_market, snapshot)
    try:
        observations = list(selected.observations(industry, geographic_market))
        if not observations:
            raise ValueError("empty market response")
        for item in observations:
            missing = [field for field in OBSERVATION_FIELDS if not str(item.get(field) or "").strip()]
            if missing:
                raise ValueError("market observation is missing provenance")
        provider_name = str(getattr(selected, "name", "") or "")
        return {
            "status": "public",
            "label": {"census-acs": ACS_LABEL, "census-cbp": CBP_LABEL}.get(provider_name, PUBLIC_LABEL),
            "reason": None,
            "provider_name": provider_name,
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


def export_market_observations(
    industry: str | None = None,
    geographic_market: str | None = None,
    provider: Any | None = None,
    tier: str | None = None,
) -> dict[str, Any]:
    """Copy the observations for this selection. This does not read or change an assessment."""
    selected_tier = _tier_name(tier)
    view = load_market(industry, geographic_market, provider)
    observations = [
        {field: str(item.get(field) or "") for field in OBSERVATION_FIELDS}
        for item in _for_tier(view.get("observations") or [], selected_tier)
    ]
    synthetic = _synthetic_observations(view)
    if selected_tier == "explore":
        synthetic = synthetic[:1]
    payload = {
        "kind": "rugd-market-observations",
        "tier": selected_tier,
        "status": view.get("status") or "",
        "industry": str(industry or ""),
        "geographic_market": str(geographic_market or ""),
        "provider_name": str(view.get("provider_name") or ""),
        "year": str(view.get("year") or ""),
        "active_providers": [str(item) for item in view.get("active_providers") or []],
        "label": str(view.get("label") or ""),
        "does_not_clear_recommend_against_flags": True,
        "observations": observations,
        "synthetic_observations": synthetic,
        "partial_notes": [str(item) for item in view.get("partial_notes") or []],
    }
    return _without_secrets(payload)


def _synthetic_observations(view: dict[str, Any]) -> list[dict[str, str]]:
    if view.get("status") == "public" and not view.get("partial_notes"):
        return []
    snapshot = view.get("snapshot") or {}
    limitations = (
        "Synthetic example only. Not market research and not a public dataset. "
        "These figures do not clear INSUFFICIENT_DEMAND_EVIDENCE or any other recommend-against flag."
    )
    return [
        {
            "source": "Synthetic snapshot",
            "geographic_coverage": str(snapshot.get("geographic_market") or ""),
            "industry_classification": str(snapshot.get("industry") or ""),
            "measurement_period": "not a measurement period",
            "retrieval_date": "not retrieved",
            "limitations": limitations,
            "measure": "Synthetic example",
            "value": str(example),
        }
        for example in snapshot.get("synthetic_examples") or []
    ]


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
                "detail": "headline",
            }
        ]
    limitations = _PUBLIC_LIMITATION
    trend_limitations = (
        f"{_PUBLIC_LIMITATION} The percent is the over-the-year change published in the annual file. "
        "A direction word derived from its sign is not a recommendation."
    )
    observations = []
    for field, label, detail in _CORE_MEASURES:
        value = str(match.get(field) or "").strip()
        if not value:
            raise ValueError("public measure is blank")
        observations.append(
            {**base, "limitations": limitations, "measure": label, "value": value, "detail": detail}
        )
    for field, label, detail in _EXTRA_MEASURES:
        value = str(match.get(field) or "").strip()
        if value:
            observations.append(
                {**base, "limitations": limitations, "measure": label, "value": value, "detail": detail}
            )
    size_code = str(match.get("size_code") or "").strip()
    if size_code:
        coverage = "All size classes combined" if size_code == "0" else f"Size code {size_code}"
        observations.append(
            {
                **base,
                "limitations": limitations,
                "measure": "Establishment size coverage",
                "value": coverage,
                "detail": "detail",
            }
        )
    for field, label in _TREND_MEASURES:
        value = _percent_text(str(match.get(field) or ""))
        if value is None:
            continue
        observations.append(
            {
                **base,
                "limitations": trend_limitations,
                "measure": label,
                "value": value,
                "detail": "extended",
            }
        )
    return observations


def _load_combined(
    selected: CombinedMarketProvider,
    industry: str | None,
    geographic_market: str | None,
    snapshot: dict[str, Any],
) -> dict[str, Any]:
    observations: list[dict[str, str]] = []
    notes: list[str] = []
    active: list[str] = []
    not_covered = 0
    failed = 0
    for part in selected.parts:
        caption = _provider_caption(part)
        try:
            rows = list(part.observations(industry, geographic_market))
            if not rows:
                raise ValueError("empty market response")
            for item in rows:
                missing = [field for field in OBSERVATION_FIELDS if not str(item.get(field) or "").strip()]
                if missing:
                    raise ValueError("market observation is missing provenance")
            observations.extend(rows)
            active.append(f"{caption} (year {getattr(part, 'year', '') or 'not set'})")
        except NotCovered:
            not_covered += 1
            notes.append(f"{caption} is not covered for this selection. Synthetic example only.")
        except Exception:
            failed += 1
            notes.append(f"{caption} did not return observations. Synthetic example only.")
    if not observations:
        label = NOT_COVERED_LABEL if not_covered and not failed else FALLBACK_LABEL
        reason = notes[0] if notes else "The public market provider did not return observations."
        view = _fallback_view(selected, snapshot, label, reason)
        view["partial_notes"] = notes
        return view
    return {
        "status": "public",
        "label": (
            "Public sources: "
            + "; ".join(active)
            + ". Not a live feed. Not monitoring. "
            "These figures do not clear INSUFFICIENT_DEMAND_EVIDENCE or any recommend-against flag."
        ),
        "reason": None,
        "provider_name": "combined",
        "year": selected.year,
        "active_providers": active,
        "partial_notes": notes,
        "snapshot": snapshot,
        "observations": observations,
    }


def _provider_caption(provider: Any) -> str:
    name = str(getattr(provider, "name", "") or "")
    if name == "bls-qcew":
        return "BLS Quarterly Census of Employment and Wages"
    if name == "census-acs":
        return "U.S. Census Bureau, American Community Survey 5-year estimates"
    if name == "census-cbp":
        return "U.S. Census Bureau, County Business Patterns"
    if name == "unavailable":
        requested = str(getattr(provider, "requested", "") or "").strip()
        return f"Requested provider {requested}" if requested else "Requested provider"
    return name or "public market provider"


def _year(env: Any, key: str, default: str) -> str:
    year = str(env.get(key) or default).strip()
    return year if len(year) == 4 and year.isdigit() else default


def _tier_name(tier: str | None) -> str:
    text = str(tier or "analyze").strip().lower()
    if text in {"explore", "analyze", "validate", "partner"}:
        return text
    return "analyze"


def _for_tier(observations: list[dict[str, str]], tier: str) -> list[dict[str, str]]:
    if tier == "explore":
        return [item for item in observations if str(item.get("detail") or "") == "headline"]
    if tier == "analyze":
        return [item for item in observations if str(item.get("detail") or "") != "extended"]
    return list(observations)


def _percent_text(raw: str) -> str | None:
    text = raw.strip()
    if not text:
        return None
    try:
        float(text)
    except ValueError:
        return None
    return text


def _acs_estimate(body: str, column: str) -> str:
    try:
        payload = json.loads(body)
        rows = payload["response"]["data"]
        header = [str(item) for item in rows[0]]
        values = rows[1]
    except (KeyError, IndexError, TypeError, json.JSONDecodeError) as exc:
        raise ValueError("census table was not readable") from exc
    if column not in header:
        raise ValueError("census estimate column is missing")
    raw = values[header.index(column)]
    text = "" if raw is None else str(raw).strip()
    if not text or text.startswith("-") or not text.isdigit():
        return "Not disclosed"
    return text


def _acs_columns(body: str, columns: tuple[str, ...]) -> tuple[int, ...] | None:
    try:
        payload = json.loads(body)
        rows = payload["response"]["data"]
        header = [str(item) for item in rows[0]]
        values = rows[1]
    except (KeyError, IndexError, TypeError, json.JSONDecodeError) as exc:
        raise ValueError("census table was not readable") from exc
    if any(column not in header for column in columns):
        raise ValueError("census estimate column is missing")
    parsed: list[int] = []
    for column in columns:
        raw = values[header.index(column)]
        text = "" if raw is None else str(raw).strip()
        if not text.isdigit():
            return None
        parsed.append(int(text))
    return tuple(parsed)


def _cbp_row(body: str, naics: str) -> dict[str, Any]:
    try:
        payload = json.loads(body)
        rows = payload["response"]["data"]
        header = [str(item) for item in rows[0]]
    except (KeyError, IndexError, TypeError, json.JSONDecodeError) as exc:
        raise ValueError("county business patterns table was not readable") from exc
    for values in rows[1:]:
        record = {header[index]: values[index] for index in range(min(len(header), len(values)))}
        if (
            str(record.get("NAICS2017") or "") == naics
            and str(record.get("LFO") or "") == "001"
            and str(record.get("EMPSZES") or "") == "001"
        ):
            return record
    raise LookupError("CBP does not publish this NAICS code in this table")


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

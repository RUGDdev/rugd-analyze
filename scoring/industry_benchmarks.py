"""
Secondary industry benchmarks for a reasonableness check.

Methodology § Core Principles — evidence hierarchy. These figures are not
verified data, not user-supplied assumptions, and not AI-generated
interpretations. They are stored with the label "secondary industry benchmark"
and a source.

They are National Restaurant Association 2025 Restaurant Operations Data
Abstract medians for 2024, for the full-service and limited-service segments
(Census NAICS 722511 and 722513 name those segments). They are not
Census-published NAICS margin tables. The Association states that the
abstract is not a standard or a goal.

A reasonableness check may describe whether an observed ratio sits above,
below, or equal to a benchmark. It returns no recommend-against flags and
cannot clear one.
"""

from __future__ import annotations

import math
from collections.abc import Mapping
from typing import Any

LABEL = "secondary industry benchmark"

NRA_NOT_A_STANDARD = (
    "National Restaurant Association, 2025 Restaurant Operations Data Abstract "
    "(2024 medians). The Association states that this abstract is not a "
    "standard or a goal for an individual restaurant."
)

_LABOR_URL = (
    "https://www.restaurant.org/research-and-media/research/restaurant-economic-insights/"
    "analysis-commentary/elevated-labor-costs-had-a-significant-impact-on-restaurant-profitability-in-2024/"
)
_MARGIN_SUMMARY_URLS = (
    "https://fsdbco.com/restaurant-profitability-pandemic-decline/",
    "https://menuthere.com/en/guides/restaurant-profit-margin",
)

NOT_LOADED = (
    "Full-service food-and-beverage cost was not loaded. Public summaries of the "
    "same abstract disagree (30% of sales versus 32.0% of sales), so no single "
    "figure is stored."
)


def _benchmark(
    benchmark_id: str,
    *,
    naics: str,
    segment: str,
    metric: str,
    value: float,
    source: str,
    source_urls: tuple[str, ...],
) -> dict[str, Any]:
    return {
        "id": benchmark_id,
        "label": LABEL,
        "naics": naics,
        "segment": segment,
        "metric": metric,
        "value": value,
        "unit": "share of sales",
        "period": "2024",
        "source": source,
        "source_urls": list(source_urls),
    }


BENCHMARKS: tuple[dict[str, Any], ...] = (
    _benchmark(
        "full_service_income_before_taxes",
        naics="722511",
        segment="full-service restaurants",
        metric="median income before taxes",
        value=0.028,
        source=(
            f"{NRA_NOT_A_STANDARD} Median income before taxes of 2.8% of sales "
            "for full-service restaurants, as reported by secondary summaries "
            "of that abstract."
        ),
        source_urls=_MARGIN_SUMMARY_URLS,
    ),
    _benchmark(
        "full_service_labor",
        naics="722511",
        segment="full-service restaurants",
        metric="median salaries, wages, and benefits",
        value=0.365,
        source=(
            f"{NRA_NOT_A_STANDARD} Median labor cost of 36.5% of sales for "
            "full-service respondents, from the Association's public commentary."
        ),
        source_urls=(_LABOR_URL,),
    ),
    _benchmark(
        "full_service_labor_profitable",
        naics="722511",
        segment="full-service restaurants reporting a pre-tax profit",
        metric="median salaries, wages, and benefits",
        value=0.342,
        source=(
            f"{NRA_NOT_A_STANDARD} Median labor cost of 34.2% of sales among "
            "full-service operators who reported a pre-tax profit."
        ),
        source_urls=(_LABOR_URL,),
    ),
    _benchmark(
        "full_service_labor_loss",
        naics="722511",
        segment="full-service restaurants reporting a loss",
        metric="median salaries, wages, and benefits",
        value=0.429,
        source=(
            f"{NRA_NOT_A_STANDARD} Median labor cost of 42.9% of sales among "
            "full-service operators who reported a loss."
        ),
        source_urls=(_LABOR_URL,),
    ),
    _benchmark(
        "full_service_occupancy",
        naics="722511",
        segment="full-service restaurants",
        metric="median occupancy cost",
        value=0.057,
        source=(
            f"{NRA_NOT_A_STANDARD} Median occupancy cost of 5.7% of sales for "
            "full-service restaurants, agreed by the secondary summaries below."
        ),
        source_urls=_MARGIN_SUMMARY_URLS,
    ),
    _benchmark(
        "limited_service_income_before_taxes",
        naics="722513",
        segment="limited-service restaurants",
        metric="median income before taxes",
        value=0.04,
        source=(
            f"{NRA_NOT_A_STANDARD} Median income before taxes of 4% of sales "
            "for limited-service restaurants, as reported by secondary summaries "
            "of that abstract."
        ),
        source_urls=_MARGIN_SUMMARY_URLS,
    ),
    _benchmark(
        "limited_service_labor",
        naics="722513",
        segment="limited-service restaurants",
        metric="median salaries, wages, and benefits",
        value=0.317,
        source=(
            f"{NRA_NOT_A_STANDARD} Median labor cost of 31.7% of sales for "
            "limited-service respondents, from the Association's public commentary."
        ),
        source_urls=(_LABOR_URL,),
    ),
    _benchmark(
        "limited_service_labor_profitable",
        naics="722513",
        segment="limited-service restaurants reporting a pre-tax profit",
        metric="median salaries, wages, and benefits",
        value=0.30,
        source=(
            f"{NRA_NOT_A_STANDARD} Median labor cost of 30.0% of sales among "
            "limited-service operators who reported a pre-tax profit."
        ),
        source_urls=(_LABOR_URL,),
    ),
    _benchmark(
        "limited_service_labor_loss",
        naics="722513",
        segment="limited-service restaurants reporting a loss",
        metric="median salaries, wages, and benefits",
        value=0.341,
        source=(
            f"{NRA_NOT_A_STANDARD} Median labor cost of 34.1% of sales among "
            "limited-service operators who reported a loss."
        ),
        source_urls=(_LABOR_URL,),
    ),
    _benchmark(
        "limited_service_occupancy",
        naics="722513",
        segment="limited-service restaurants",
        metric="median occupancy cost",
        value=0.052,
        source=(
            f"{NRA_NOT_A_STANDARD} Median occupancy cost of 5.2% of sales for "
            "limited-service restaurants, agreed by the secondary summaries below."
        ),
        source_urls=_MARGIN_SUMMARY_URLS,
    ),
)

_BY_ID = {item["id"]: item for item in BENCHMARKS}


def reasonableness_check(benchmark_id: str, observed: float | None) -> dict[str, Any]:
    """Compare one observed ratio to a stored benchmark. Never a scoring flag."""
    if benchmark_id not in _BY_ID:
        raise KeyError(f"unknown secondary industry benchmark: {benchmark_id}")
    benchmark = _BY_ID[benchmark_id]
    if observed is not None and (
        isinstance(observed, bool)
        or not isinstance(observed, (int, float))
        or not math.isfinite(observed)
    ):
        raise ValueError("observed value must be a finite number or null")
    result: dict[str, Any] = {
        "label": LABEL,
        "benchmark_id": benchmark_id,
        "benchmark_value": benchmark["value"],
        "source": benchmark["source"],
        "observed": None if observed is None else float(observed),
        "recommend_against_flags": [],
        "raises_recommend_against_flags": False,
        "clears_recommend_against_flags": False,
    }
    if observed is None:
        result["relation"] = "not compared"
        result["note"] = (
            "No observed value was supplied. The secondary industry benchmark "
            "was not used as evidence."
        )
        return result
    if observed == benchmark["value"]:
        relation = "equal to"
    elif observed > benchmark["value"]:
        relation = "above"
    else:
        relation = "below"
    result["relation"] = relation
    result["difference"] = round(float(observed) - benchmark["value"], 4)
    result["note"] = (
        f"Observed value is {relation} the secondary industry benchmark. "
        "Reasonableness check only. This does not clear or raise a "
        "recommend-against flag."
    )
    return result


RATIO_COMPARISONS = (
    ("labor_pct_of_sales", "full_service_labor", "Labor %"),
    ("occupancy_pct_of_sales", "full_service_occupancy", "Occupancy %"),
    ("pretax_margin", "full_service_income_before_taxes", "Pre-tax margin"),
)


def reasonableness_note(observed: Mapping[str, Any] | None) -> str:
    """Financial-summary note. Methodology § Core Principles — evidence hierarchy.

    Compares calculated labor, occupancy, and pre-tax ratios with the stored
    full-service NRA medians. Returns an empty string when no secondary
    benchmarks are loaded. The text is not a scoring input.
    """
    if not BENCHMARKS:
        return ""
    lines = [
        "### Reasonableness check",
        "",
        (
            "Secondary industry benchmark. National Restaurant Association, "
            "2025 Restaurant Operations Data Abstract, 2024 full-service medians. "
            "This comparison is not a scoring input."
        ),
    ]
    payload = observed or {}
    for key, benchmark_id, label in RATIO_COMPARISONS:
        benchmark = _BY_ID[benchmark_id]
        median = _percent(benchmark["value"])
        if key not in payload or payload[key] is None:
            lines.append(
                f"- {label}: not calculated, so it was not compared with the "
                f"secondary industry benchmark (NRA median {median} of sales)."
            )
            continue
        check = reasonableness_check(benchmark_id, payload[key])
        lines.append(
            f"- {label}: calculated {_percent(check['observed'])} is "
            f"{check['relation']} the secondary industry benchmark "
            f"(NRA median {median} of sales)."
        )
    return "\n".join(lines)


def _percent(value: float) -> str:
    return f"{value * 100:.1f}%"


def printed_lines() -> list[str]:
    """One printed line per benchmark, with the required label and source."""
    lines = []
    for item in BENCHMARKS:
        lines.append(
            f"{LABEL}: {item['segment']} — {item['metric']} = {item['value']}. "
            f"Source: {item['source']}"
        )
    lines.append(f"{LABEL}: not loaded. {NOT_LOADED}")
    return lines


def audit_record() -> dict[str, Any]:
    """Catalog for the assessment audit. Methodology § Core Principles."""
    return {
        "label": LABEL,
        "methodology_ref": (
            "Methodology § Core Principles — evidence hierarchy. "
            "Secondary industry benchmarks are not verified data."
        ),
        "use": "reasonableness check only",
        "may_raise_recommend_against_flags": False,
        "may_clear_recommend_against_flags": False,
        "benchmarks": [dict(item) for item in BENCHMARKS],
        "not_loaded": [NOT_LOADED],
        "printed": printed_lines(),
    }

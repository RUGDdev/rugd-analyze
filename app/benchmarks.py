"""Benchmark records for planning. Nothing here is verified data and nothing scores.

A record states what a number measures, where it applies, where it came from, how old
it is, and how far to trust it. Records come from three places:

1. The secondary industry benchmarks already stored for the reasonableness check
   (`scoring.industry_benchmarks`). They are reused as they are.
2. Public retrieval results the customer already imported into research
   (`retrieved_public`, `customer_provided`). They describe a place or an industry,
   not the customer's own ratios.
3. Figures the customer found and recorded with a source. They are labeled
   customer-recorded and unverified.

When no record matches, the page says so and offers an editable worksheet. A
benchmark never changes a customer entry, a flag, a score, or an approval.
"""

from __future__ import annotations

import math
import re
from datetime import date
from typing import Any

from app.guidance import family_for
from scoring import industry_benchmarks as secondary

STATUS_SECONDARY = "secondary industry benchmark"
STATUS_CUSTOMER = "customer-recorded, unverified"
STATUS_PUBLIC = "public retrieval, not a benchmark for your ratios"

# A figure published more than this many days ago is flagged as stale.
STALE_AFTER_DAYS = 730
# Two records for the same measure and segment conflict when the larger is more
# than this fraction above the smaller.
CONFLICT_RELATIVE_GAP = 0.15

NOT_A_TARGET = "A benchmark is context. It is not a target, a standard, or evidence about this business."

# metric key: (label, unit, kind, families). kind controls how a value is entered and shown.
METRICS: dict[str, dict[str, Any]] = {
    "food_cost_pct": {"label": "Food and beverage cost", "unit": "share of sales", "kind": "share", "families": ("hospitality",)},
    "labor_pct": {"label": "Salaries, wages, and benefits", "unit": "share of sales", "kind": "share", "families": ()},
    "occupancy_cost_pct": {"label": "Occupancy cost (rent and related)", "unit": "share of sales", "kind": "share", "families": ()},
    "other_variable_pct": {"label": "Other variable costs (card fees, packaging, supplies)", "unit": "share of sales", "kind": "share", "families": ()},
    "pretax_margin": {"label": "Income before taxes", "unit": "share of sales", "kind": "share", "families": ()},
    "average_check": {"label": "Average check per cover", "unit": "currency per cover", "kind": "money", "families": ("hospitality",)},
    "seat_turns": {"label": "Seat turns per service period", "unit": "turns per period", "kind": "number", "families": ("hospitality",)},
    "construction_per_sqft": {"label": "Build-out cost per square foot", "unit": "currency per sq ft", "kind": "money", "families": ()},
    "sqft_per_seat": {"label": "Floor area per seat", "unit": "sq ft per seat", "kind": "number", "families": ("hospitality",)},
    "working_capital_months": {"label": "Opening working capital", "unit": "months of fixed costs", "kind": "number", "families": ()},
    "avg_hourly_wage": {"label": "Average hourly wage, all-in", "unit": "currency per hour", "kind": "money", "families": ()},
}

_SECONDARY_METRICS = {
    "median income before taxes": "pretax_margin",
    "median salaries, wages, and benefits": "labor_pct",
    "median occupancy cost": "occupancy_cost_pct",
}

SOURCE_DIRECTORY: tuple[dict[str, str], ...] = (
    {
        "name": "BLS Occupational Employment and Wage Statistics",
        "url": "https://www.bls.gov/oes/",
        "covers": "Wages by occupation, by state and metro area. Use for hourly wage and staffing cost.",
    },
    {
        "name": "BLS Quarterly Census of Employment and Wages",
        "url": "https://www.bls.gov/cew/",
        "covers": "Employment, establishments, and wages by industry and county. RUGD can retrieve it in Research.",
    },
    {
        "name": "U.S. Census Bureau County Business Patterns",
        "url": "https://www.census.gov/programs-surveys/cbp.html",
        "covers": "Establishments and payroll by industry and county. A count of competitors, not their revenue.",
    },
    {
        "name": "U.S. Census Bureau American Community Survey",
        "url": "https://www.census.gov/programs-surveys/acs",
        "covers": "Population and income by place. Context for demand, not a revenue forecast.",
    },
    {
        "name": "National Restaurant Association research",
        "url": "https://restaurant.org/research-and-media/research/",
        "covers": "Restaurant operating data and commentary. The full abstract may need membership or purchase.",
    },
    {
        "name": "Small Business Development Centers (SBA)",
        "url": "https://www.sba.gov/local-assistance/resource-partners/small-business-development-centers-sbdc",
        "covers": "Free local advising. An advisor can point to locally relevant figures.",
    },
)

_SECONDARY_LIMITATIONS = (
    "The primary abstract was not read by RUGD. The figure comes from the Association's public commentary "
    "or from secondary summaries of the abstract.",
    "It is a median across responding operators. It is not a standard or a goal for any one restaurant.",
    "It is a national figure for one year. It is not matched to your city, venue size, or concept.",
)

_DATE = re.compile(r"^\d{4}(-\d{2}-\d{2})?$")


def _display(value: float, kind: str, unit: str) -> str:
    if kind == "share":
        return f"{value * 100:.1f}% of sales"
    if unit.startswith("currency"):
        return f"{value:,.2f} {unit.replace('currency ', '')}"
    return f"{value:g} {unit}"


def _parse_when(text: str) -> date | None:
    text = str(text or "").strip()
    if not _DATE.match(text):
        return None
    try:
        if len(text) == 4:
            return date(int(text), 12, 31)
        return date.fromisoformat(text)
    except ValueError:
        return None


def is_stale(published: str, today: date | None = None) -> bool:
    """True when the publication date is known and older than the stale limit."""
    when = _parse_when(published)
    if when is None:
        return False
    return ((today or date.today()) - when).days > STALE_AFTER_DAYS


def registry() -> list[dict[str, Any]]:
    """Secondary benchmarks already stored for the reasonableness check, as full records."""
    records = []
    for item in secondary.BENCHMARKS:
        metric_key = _SECONDARY_METRICS.get(str(item["metric"]), "")
        if not metric_key:
            continue
        segment = str(item["segment"])
        full = segment.startswith("full-service")
        spec = METRICS[metric_key]
        records.append(
            {
                "id": f"secondary:{item['id']}",
                "status": STATUS_SECONDARY,
                "metric_key": metric_key,
                "metric": spec["label"],
                "unit": spec["unit"],
                "kind": spec["kind"],
                "value": float(item["value"]),
                "value_text": _display(float(item["value"]), spec["kind"], spec["unit"]),
                "industry": "Restaurants",
                "family": "hospitality",
                "subsector": f"{segment} (NAICS {item['naics']})",
                "style": "full_service" if full else "limited_service",
                "business_model": "Table service" if full else "Counter or quick service",
                "geography": "United States, national",
                "geography_scope": "national",
                "scale": "All responding sizes. Not matched to venue size.",
                "source": str(item["source"]),
                "source_urls": list(item["source_urls"]),
                "published": "2025",
                "period": str(item["period"]),
                "retrieved": "",
                "methodology": "Median across respondents to the Association's annual operations survey, reported as a share of sales.",
                "limitations": list(_SECONDARY_LIMITATIONS),
                "confidence": "Low to moderate",
                "applicability": ["National median. Not specific to your market."],
                "all_respondents": "profit" not in segment and "loss" not in segment,
            }
        )
    return records


def unresolved() -> list[dict[str, Any]]:
    """Measures where public sources disagree. No single value is stored."""
    return [
        {
            "metric": "Full-service food and beverage cost",
            "status": "conflicting evidence, not used",
            "candidates": ["30% of sales", "32.0% of sales"],
            "note": secondary.NOT_LOADED,
            "source_urls": list(secondary._MARGIN_SUMMARY_URLS),
        }
    ]


def prepare_entry(form: dict[str, str], today: date | None = None) -> tuple[dict[str, Any] | None, str]:
    """Validate a customer-recorded benchmark. Returns (record, "") or (None, reason)."""
    metric_key = str(form.get("metric_key") or "").strip()
    custom = " ".join(str(form.get("custom_label") or "").split())[:80]
    if metric_key == "custom":
        if not custom:
            return None, "Name the measure when you choose Other."
        spec = {"label": custom, "unit": " ".join(str(form.get("custom_unit") or "unit").split())[:40] or "unit", "kind": "number"}
    elif metric_key in METRICS:
        spec = METRICS[metric_key]
    else:
        return None, "Choose what the figure measures."
    raw = str(form.get("value") or "").strip().replace(",", "").replace("$", "")
    try:
        number = float(raw)
    except ValueError:
        return None, "Enter the figure as a number."
    if not math.isfinite(number) or number < 0:
        return None, "Enter a finite number that is zero or more."
    if spec["kind"] == "share":
        if number > 100:
            return None, "Enter a share of sales as a percent from 0 to 100."
        number = number / 100
    source_name = " ".join(str(form.get("source_name") or "").split())[:160]
    if not source_name:
        return None, "Name the source. If it is your own estimate, write that."
    url = str(form.get("source_url") or "").strip()
    if url and not re.match(r"^https?://[^\s<>\"']+$", url):
        return None, "A source link must start with http:// or https://."
    published = str(form.get("published_on") or "").strip()
    if published and not _DATE.match(published):
        return None, "Write the publication date as YYYY or YYYY-MM-DD, or leave it blank."
    retrieved = str(form.get("retrieved_on") or "").strip() or (today or date.today()).isoformat()
    if not re.match(r"^\d{4}-\d{2}-\d{2}$", retrieved):
        return None, "Write the date you found it as YYYY-MM-DD."
    confidence = str(form.get("confidence") or "low").strip().lower()
    if confidence not in {"low", "medium", "high"}:
        confidence = "low"
    geography = " ".join(str(form.get("geography") or "").split())[:120] or "Not stated"
    scale = " ".join(str(form.get("scale") or "").split())[:120] or "Not stated"
    note = " ".join(str(form.get("notes") or "").split())[:400]
    return (
        {
            "metric_key": metric_key,
            "metric": spec["label"],
            "unit": spec["unit"],
            "kind": spec["kind"],
            "value": number,
            "source": source_name,
            "source_url": url,
            "published": published,
            "retrieved": retrieved,
            "geography": geography,
            "scale": scale,
            "notes": note,
            "confidence": confidence,
        },
        "",
    )


def entry_record(stored: dict[str, Any]) -> dict[str, Any]:
    """A saved customer entry as a full benchmark record."""
    data = stored.get("payload") or {}
    kind = str(data.get("kind") or "number")
    unit = str(data.get("unit") or "unit")
    value = float(data.get("value") or 0)
    published = str(data.get("published") or "")
    limits = [
        "The customer recorded this figure. RUGD did not check the source or the number.",
        "Methodology is whatever the source states. Read the source before relying on it.",
    ]
    if data.get("notes"):
        limits.append(str(data["notes"]))
    return {
        "id": f"entry:{stored.get('id')}",
        "entry_id": stored.get("id"),
        "status": STATUS_CUSTOMER,
        "metric_key": str(data.get("metric_key") or ""),
        "metric": str(data.get("metric") or "Measure"),
        "unit": unit,
        "kind": kind,
        "value": value,
        "value_text": _display(value, kind, unit),
        "industry": "As described by the customer",
        "family": "",
        "subsector": "As described by the customer",
        "style": "",
        "business_model": "As described by the customer",
        "geography": str(data.get("geography") or "Not stated"),
        "geography_scope": "customer_stated",
        "scale": str(data.get("scale") or "Not stated"),
        "source": str(data.get("source") or ""),
        "source_urls": [data["source_url"]] if data.get("source_url") else [],
        "published": published,
        "period": "",
        "retrieved": str(data.get("retrieved") or ""),
        "methodology": "Not checked by RUGD.",
        "limitations": limits,
        "confidence": str(data.get("confidence") or "low").capitalize() + " (set by the customer)",
        "applicability": [],
        "all_respondents": True,
    }


def evidence_context(evidence: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Imported public or customer research as place-and-industry context records."""
    rows = []
    for item in evidence:
        document = item.get("document") if isinstance(item.get("document"), dict) else item
        klass = str(document.get("evidence_class") or "")
        if klass not in {"retrieved_public", "source_backed_unverified", "customer_provided"}:
            continue
        rows.append(
            {
                "id": f"evidence:{item.get('id') or document.get('source_identity') or len(rows)}",
                "status": STATUS_PUBLIC if klass == "retrieved_public" else "customer research, unverified",
                "metric": str(document.get("source_title") or "Research record"),
                "finding": str(document.get("finding") or ""),
                "industry": str(document.get("industry") or ""),
                "geography": str(document.get("geography") or "Not stated"),
                "source": " ".join(
                    part for part in (str(document.get("source_organization") or ""), str(document.get("source_title") or "")) if part
                ),
                "source_urls": [document["source_url"]] if document.get("source_url") else [],
                "published": str(document.get("published_on") or ""),
                "retrieved": str(document.get("retrieved_on") or ""),
                "limitations": [str(document.get("limitations") or "Not stated.")],
            }
        )
    return rows


def style_of(profile: dict[str, Any]) -> str:
    style = str(profile.get("service_style") or "").strip()
    return style if style in {"full_service", "limited_service"} else ""


def match(
    profile: dict[str, Any],
    entries: list[dict[str, Any]] | None = None,
    *,
    today: date | None = None,
) -> dict[str, Any]:
    """Records that apply to this profile, with flags. No record is changed or hidden to look better."""
    family = family_for(str(profile.get("industry") or ""))
    market = " ".join(str(profile.get("market") or "").split())
    style = style_of(profile)
    pool = []
    if family == "hospitality":
        for record in registry():
            if style and record["style"] != style:
                continue
            pool.append(dict(record))
    pool.extend(entry_record(item) for item in (entries or []))
    for record in pool:
        notes = list(record.get("applicability") or [])
        if record["geography_scope"] == "national" and market:
            notes = [f"National median. Not specific to {market}."]
        if record["geography_scope"] == "customer_stated":
            if market and market.lower() not in str(record["geography"]).lower():
                notes.append(f"The recorded geography ({record['geography']}) is not stated as {market}.")
        if record.get("family") == "hospitality" and not style:
            notes.append("Service style is not set. Choose one to narrow this list.")
        record["applicability"] = notes
        record["stale"] = is_stale(str(record.get("published") or ""), today)
        record["undated"] = not str(record.get("published") or "").strip()
    _flag_conflicts(pool)
    present = {record["metric_key"] for record in pool if record.get("metric_key")}
    wanted = [key for key, spec in METRICS.items() if not spec["families"] or family in spec["families"]]
    missing = [key for key in wanted if key not in present]
    return {
        "family": family,
        "market": market,
        "style": style,
        "records": pool,
        "missing": missing,
        "unresolved": unresolved() if family == "hospitality" and (not style or style == "full_service") else [],
        "caveat": NOT_A_TARGET,
    }


def _flag_conflicts(pool: list[dict[str, Any]]) -> None:
    groups: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for record in pool:
        key = str(record.get("metric_key") or "")
        if not key or not record.get("all_respondents", True):
            continue
        groups.setdefault((key, record["unit"]), []).append(record)
    for members in groups.values():
        values = [item["value"] for item in members]
        low, high = min(values), max(values)
        conflict = len(members) > 1 and low >= 0 and (high - low) > CONFLICT_RELATIVE_GAP * max(low, 1e-9)
        for item in members:
            item["conflict"] = bool(conflict)
            item["conflict_with"] = [other["id"] for other in members if other is not item] if conflict else []
    for record in pool:
        record.setdefault("conflict", False)
        record.setdefault("conflict_with", [])


def best_entry(records: list[dict[str, Any]], metric_key: str) -> dict[str, Any] | None:
    """The most recent customer-recorded entry for a measure, or None. Conflicts are not averaged."""
    candidates = [
        item
        for item in records
        if item.get("metric_key") == metric_key and item["status"] == STATUS_CUSTOMER
    ]
    if not candidates:
        return None
    return sorted(candidates, key=lambda item: (str(item.get("retrieved") or ""), str(item["id"])))[-1]


def reference_for(records: list[dict[str, Any]], metric_key: str) -> list[dict[str, Any]]:
    return [item for item in records if item.get("metric_key") == metric_key]

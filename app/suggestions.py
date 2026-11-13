"""Local example text for the Explore intake.

The phrases live in explore_suggestions.json. They are guidance, not market facts,
verified data, or engine inputs.
"""

from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path

CATALOG_PATH = Path(__file__).with_name("explore_suggestions.json")

SUGGESTION_NOTE = (
    "Examples only. Choosing a suggestion fills the field with your own estimate to edit. "
    "It does not change the analysis, lift a serious concern, count as proof of demand, "
    "or make a business ready to show investors."
)

SUGGESTION_FIELDS = ("stage", "products", "customers", "competition")

# Form field, industry list, general fallback list.
_JSON_KEYS = {
    "stage": ("development_stages", "development_stages"),
    "products": ("products_services", "fallback_products"),
    "customers": ("target_customers", "fallback_customers"),
    "competition": ("competition", "fallback_competition"),
}

_PHRASE_RANK = {"name": 3, "aliases": 2, "keywords": 1}


@lru_cache(maxsize=1)
def load_catalog() -> dict:
    """Read the local suggestion file. The file does not contain engine inputs."""
    loaded = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    if not isinstance(loaded, dict):
        raise ValueError("explore_suggestions.json must be an object")
    return loaded


def catalog_json() -> str:
    """JSON for the intake page. Angle brackets are escaped so the script tag stays closed."""
    return json.dumps(load_catalog(), ensure_ascii=True).replace("<", "\\u003c")


def suggestions_for(industry: str, stage: str = "") -> dict[str, list[str]]:
    """Example phrases for the four guided fields.

    A strong match is a whole word or phrase from the industry name, an alias,
    or a keyword. Search terms stay in the file and are not used for matching.
    The longest phrase wins. An equal length prefers a name or alias over a keyword.
    Anything else uses the general fallbacks.
    The supplied stage does not add examples that are not in the catalog.
    """
    del stage  # This catalog lists examples by industry. Stage does not invent a narrower list.
    catalog = load_catalog()
    general = catalog.get("general") if isinstance(catalog.get("general"), dict) else {}
    record = _match_industry(industry, catalog)
    chosen: dict[str, list[str]] = {}
    for field, (industry_key, general_key) in _JSON_KEYS.items():
        source = record.get(industry_key) if record else None
        fallback = general.get(general_key) or []
        if isinstance(source, list) and source:
            chosen[field] = [str(item) for item in source]
        elif isinstance(fallback, list):
            chosen[field] = [str(item) for item in fallback]
        else:
            chosen[field] = []
    return chosen


def _match_industry(industry: str, catalog: dict) -> dict | None:
    folded = _words(industry)
    if not folded:
        return None
    padded = f" {folded} "
    best_score = 0
    best: dict | None = None
    industries = catalog.get("industries")
    if not isinstance(industries, list):
        return None
    for record in industries:
        if not isinstance(record, dict):
            continue
        for kind, phrase in _phrases(record):
            needle = f" {_words(phrase)} "
            if not needle.strip() or needle not in padded:
                continue
            score = len(needle) * 10 + _PHRASE_RANK[kind]
            if score > best_score:
                best_score = score
                best = record
    return best


def _phrases(record: dict) -> list[tuple[str, str]]:
    phrases = [("name", str(record.get("name") or ""))]
    for key in ("aliases", "keywords"):
        values = record.get(key) or []
        if isinstance(values, list):
            phrases.extend((key, str(item)) for item in values)
    return [(kind, phrase) for kind, phrase in phrases if phrase.strip()]


def _words(value: str) -> str:
    return " ".join(re.findall(r"[a-z0-9]+", value.lower()))

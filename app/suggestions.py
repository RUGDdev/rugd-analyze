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
    "Examples only. Guidance. Selecting a suggestion fills the field as a user-supplied assumption. "
    "It does not affect the engine result, a recommend-against flag, demand evidence, "
    "or investor readiness."
)

SUGGESTION_FIELDS = ("stage", "products", "customers", "competition")

_JSON_KEYS = {
    "stage": "development_stage",
    "products": "products_services",
    "customers": "target_customers",
    "competition": "competition",
}


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
    a keyword, or a search term. Anything else uses the general fallbacks.
    """
    catalog = load_catalog()
    general = catalog.get("general") if isinstance(catalog.get("general"), dict) else {}
    record = _match_industry(industry, catalog)
    bucket = _stage_bucket(stage)
    chosen: dict[str, list[str]] = {}
    for field, key in _JSON_KEYS.items():
        source = record.get(key) if record else None
        if not source:
            source = general.get(key) or []
        chosen[field] = _pick(source, bucket, general.get(key) or [])
    return chosen


def _match_industry(industry: str, catalog: dict) -> dict | None:
    folded = _words(industry)
    if not folded:
        return None
    padded = f" {folded} "
    best_length = 0
    best: dict | None = None
    industries = catalog.get("industries")
    if not isinstance(industries, list):
        return None
    for record in industries:
        if not isinstance(record, dict):
            continue
        for phrase in _phrases(record):
            needle = f" {_words(phrase)} "
            if needle.strip() and needle in padded and len(needle) > best_length:
                best_length = len(needle)
                best = record
    return best


def _phrases(record: dict) -> list[str]:
    phrases = [str(record.get("name") or "")]
    for key in ("aliases", "keywords", "search_terms"):
        values = record.get(key) or []
        if isinstance(values, list):
            phrases.extend(str(item) for item in values)
    return [phrase for phrase in phrases if phrase.strip()]


def _pick(source: object, bucket: str, fallback: object) -> list[str]:
    if isinstance(source, list):
        return [str(item) for item in source]
    if isinstance(source, dict):
        picked = source.get(bucket) or source.get("default")
        if isinstance(picked, list) and picked:
            return [str(item) for item in picked]
    if isinstance(fallback, list):
        return [str(item) for item in fallback]
    return []


def _stage_bucket(stage: str) -> str:
    folded = _words(stage)
    if not folded:
        return "default"
    if any(token in folded for token in ("expanding", "expansion", "second location", "scale")):
        return "expanding"
    if any(token in folded for token in ("startup", "pre opening", "preopening", "prototype", "beta", "buildout")):
        return "startup"
    if any(token in folded for token in ("early revenue", "operating", "open")):
        return "operating"
    if any(token in folded for token in ("idea", "concept")):
        return "idea"
    return "default"


def _words(value: str) -> str:
    return " ".join(re.findall(r"[a-z0-9]+", value.lower()))

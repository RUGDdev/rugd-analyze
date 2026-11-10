"""Local example text for the Explore intake.

These phrases are guidance. They are not market facts, verified data, or engine inputs.
"""

from __future__ import annotations

import re

SUGGESTION_NOTE = (
    "Examples only. Selecting a suggestion fills the field as a user-supplied assumption. "
    "It does not affect the engine result, a recommend-against flag, demand evidence, "
    "or investor readiness."
)

SUGGESTION_FIELDS = ("stage", "products", "customers", "competition")

_GENERAL = {
    "stage": [
        "Idea",
        "Concept",
        "Startup",
        "Early revenue",
        "Operating",
        "Expanding",
    ],
    "products": [
        "The main product or service you would sell first",
        "A second offer you might add later",
    ],
    "customers": [
        "The person or business most likely to pay first",
        "A nearby or online group you would serve",
    ],
    "competition": [
        "The closest alternative a customer would choose instead",
        "A larger option in the same category",
    ],
}

# Match phrases are matched on word boundaries. Longer phrases win.
_INDUSTRIES: dict[str, dict[str, object]] = {
    "restaurant": {
        "match": ["restaurant", "cafe", "coffee shop", "diner", "food service", "bakery"],
        "stage": ["Idea", "Concept", "Startup", "Early revenue", "Operating", "Expanding"],
        "products": {
            "idea": ["A short sample menu of lunch plates"],
            "startup": ["Counter service with a fixed lunch menu"],
            "operating": ["The current lunch and dinner menu"],
            "expanding": ["The same menu offered at a second location"],
            "default": ["Lunch and dinner service for guests on site"],
        },
        "customers": {
            "idea": ["People nearby who would try a first menu"],
            "startup": ["Nearby workers and residents for the opening weeks"],
            "operating": ["Current weekday lunch guests"],
            "expanding": ["Guests who already visit, plus a new neighborhood"],
            "default": ["Nearby residents and weekday lunch guests"],
        },
        "competition": {
            "default": ["Other independent restaurants a guest could choose instead"],
        },
    },
    "retail": {
        "match": ["retail", "boutique", "store"],
        "stage": ["Idea", "Concept", "Startup", "Early revenue", "Operating", "Expanding"],
        "products": {
            "default": ["A small set of goods on the shelf"],
            "idea": ["A first assortment you would test with nearby shoppers"],
            "expanding": ["The same goods offered in a second shop"],
        },
        "customers": {"default": ["Nearby shoppers who buy this kind of good"]},
        "competition": {"default": ["Other local shops selling a similar good"]},
    },
    "professional": {
        "match": ["professional services", "consulting", "accounting", "legal services", "law firm"],
        "stage": ["Idea", "Concept", "Startup", "Early revenue", "Operating", "Expanding"],
        "products": {"default": ["A fixed-scope professional engagement"]},
        "customers": {"default": ["Local businesses that hire this kind of help"]},
        "competition": {"default": ["Other local firms a client could hire instead"]},
    },
    "construction": {
        "match": ["construction", "contractor", "trades", "plumbing", "electrical contractor"],
        "stage": ["Idea", "Startup", "Early revenue", "Operating", "Expanding"],
        "products": {"default": ["A quoted trade job for a local property"]},
        "customers": {"default": ["Property owners who hire this trade"]},
        "competition": {"default": ["Other local contractors a customer could call"]},
    },
    "software": {
        "match": ["software", "saas", "technology"],
        "stage": ["Idea", "Prototype", "Beta", "Early revenue", "Operating"],
        "products": {
            "idea": ["A sketched workflow you would test with a few users"],
            "startup": ["A hosted software subscription for a named workflow"],
            "default": ["A hosted software subscription for a named workflow"],
        },
        "customers": {"default": ["Teams that would pay for this workflow"]},
        "competition": {"default": ["Other software a buyer could subscribe to instead"]},
    },
    "lodging": {
        "match": ["lodging", "hotel", "motel", "inn", "short term rental"],
        "stage": ["Idea", "Startup", "Early revenue", "Operating", "Expanding"],
        "products": {"default": ["Nightly rooms for short stays"]},
        "customers": {"default": ["Travelers who need a short stay in this place"]},
        "competition": {"default": ["Other places to stay a traveler could book"]},
    },
    "healthcare": {
        "match": ["healthcare", "clinic", "dental", "medical practice"],
        "stage": ["Idea", "Startup", "Early revenue", "Operating", "Expanding"],
        "products": {"default": ["An appointment-based clinical visit"]},
        "customers": {"default": ["Patients who would book this kind of visit"]},
        "competition": {"default": ["Other clinics a patient could visit instead"]},
    },
    "manufacturing": {
        "match": ["manufacturing", "factory", "production"],
        "stage": ["Idea", "Prototype", "Startup", "Early revenue", "Operating", "Expanding"],
        "products": {"default": ["A made-to-order production run"]},
        "customers": {"default": ["Businesses that would order this product"]},
        "competition": {"default": ["Other makers a buyer could order from"]},
    },
    "education": {
        "match": ["education", "training", "tutoring", "school"],
        "stage": ["Idea", "Concept", "Startup", "Early revenue", "Operating", "Expanding"],
        "products": {"default": ["A scheduled class or training session"]},
        "customers": {"default": ["Learners who would enroll in this class"]},
        "competition": {"default": ["Other classes a learner could take instead"]},
    },
    "personal": {
        "match": ["personal services", "salon", "barber", "fitness studio", "gym"],
        "stage": ["Idea", "Startup", "Early revenue", "Operating", "Expanding"],
        "products": {"default": ["An appointment for a personal service"]},
        "customers": {"default": ["Nearby clients who book this service"]},
        "competition": {"default": ["Other local providers a client could book"]},
    },
}


def suggestions_for(industry: str, stage: str = "") -> dict[str, list[str]]:
    """Example phrases for the four guided fields. Unknown industries use the general list."""
    record = _match_industry(industry)
    bucket = _stage_bucket(stage)
    if record is None:
        return {field: list(_GENERAL[field]) for field in SUGGESTION_FIELDS}
    chosen: dict[str, list[str]] = {}
    for field in SUGGESTION_FIELDS:
        value = record[field]
        if isinstance(value, list):
            chosen[field] = list(value)
        else:
            groups = value if isinstance(value, dict) else {}
            picked = groups.get(bucket) or groups.get("default") or []
            chosen[field] = [str(item) for item in picked]
    return chosen


def _match_industry(industry: str) -> dict[str, object] | None:
    folded = _words(industry)
    if not folded:
        return None
    padded = f" {folded} "
    best_length = 0
    best: dict[str, object] | None = None
    for record in _INDUSTRIES.values():
        phrases = record.get("match")
        if not isinstance(phrases, list):
            continue
        for phrase in phrases:
            needle = f" {_words(str(phrase))} "
            if needle.strip() and needle in padded and len(needle) > best_length:
                best_length = len(needle)
                best = record
    return best


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

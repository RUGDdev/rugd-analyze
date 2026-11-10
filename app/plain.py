"""Short explanations for people new to the terms.

The precise term stays visible. Learn more holds the tighter definition.
These notes do not calculate a figure, clear a flag, or grant investor-ready status.
"""

from __future__ import annotations

from html import escape

TERMS: dict[str, dict[str, str]] = {
    "recommendation": {
        "term": "Recommendation",
        "plain": "The engine's draft answer about whether to go ahead. It is still a draft.",
        "precise": "The stored engine recommendation. A hard recommend-against flag keeps the gate recommendation at do-not-proceed.",
    },
    "insufficient_demand_evidence": {
        "term": "INSUFFICIENT_DEMAND_EVIDENCE",
        "plain": "The file does not yet have proof that customers will buy. That block stays until a verified demand record is saved.",
        "precise": "Recommend-against flag. A customer yes, a note, or market text does not clear it. Clearing it does not approve the file or make it investor-ready.",
    },
    "investor_readiness": {
        "term": "Investor readiness",
        "plain": "Whether this file is ready to show an investor. On this prototype it stays internal until every existing gate and an authorized review are in place.",
        "precise": "Investor Readiness Gate status. Internal is not investor-ready. This note does not change the gate.",
    },
    "recommend_against": {
        "term": "Recommend-against flag",
        "plain": "A hard stop from the engine. While one is active, the gate stays Blocked and the gate recommendation stays do-not-proceed.",
        "precise": "The engine flag list. The indicative band is forced to Blocked. The stored engine recommendation is not rewritten by this note.",
    },
    "dscr": {
        "term": "DSCR",
        "plain": "How many times the business's cash covers its loan payment. Below 1 means the cash does not cover that payment.",
        "precise": "Debt service coverage ratio from the engine: cash flow before debt service divided by the debt payment. This note does not recalculate it.",
    },
    "sources_and_uses": {
        "term": "Sources and uses",
        "plain": "Where the opening money comes from and what it is spent on. Sources are the money in. Uses are the costs.",
        "precise": "The engine's startup sources-and-uses table. Figures appear only when the engine calculated them. Missing inputs stay blank.",
    },
    "indicative_score": {
        "term": "Indicative assessment",
        "plain": "A reading aid with three parts: market, money, and stewardship. It is not a pass/fail grade, and a hard stop overrides it.",
        "precise": "Indicative assessment — market validity, financial viability, and stewardship readiness. Does not override engine flags or human review. No feasibility score is calculated.",
    },
    "market_snapshot": {
        "term": "Market snapshot",
        "plain": "A labeled look at the area and industry. On this prototype it is a demonstration unless a public extract was requested. It is not proof of customers.",
        "precise": "Market observations do not clear INSUFFICIENT_DEMAND_EVIDENCE or any other recommend-against flag, and they do not grant investor-ready status.",
    },
}


def term_note(key: str) -> str:
    """Visible term, one plain sentence, and a Learn more definition."""
    item = TERMS[key]
    return (
        '<details class="plain">'
        f"<summary><strong>{escape(item['term'])}.</strong> {escape(item['plain'])} "
        '<span class="muted">Learn more</span></summary>'
        f"<p>{escape(item['precise'])}</p>"
        "<p class=\"muted\">This explanation does not change an engine number, clear a flag, "
        "set human_review_approved, or grant investor-ready status.</p>"
        "</details>"
    )

"""Short explanations for people new to the terms.

Each note answers three questions in plain words: what it means, why it matters, and what to do.
The tighter definition sits behind "Learn more". These notes do not calculate a figure, clear a
flag, or grant investor-ready status.
"""

from __future__ import annotations

from html import escape

TERMS: dict[str, dict[str, str]] = {
    "recommendation": {
        "term": "Draft recommendation",
        "plain": "RUGD's first answer on whether to go ahead. It is a draft until a person reviews it.",
        "matters": "It tells you where you stand right now, not where you could end up.",
        "todo": "Read what is missing, then work through the next steps on the page.",
        "precise": "The stored engine recommendation. A hard recommend-against flag keeps it at do-not-proceed.",
    },
    "insufficient_demand_evidence": {
        "term": "Not enough evidence of customer demand",
        "plain": "There is no documented proof yet that customers will buy.",
        "matters": "Lenders and investors look for this first. Until it is on file, the assessment cannot move forward.",
        "todo": "Save real evidence, such as signed commitments, pre-orders, deposits, or documented sales, in Research.",
        "precise": "Stored as INSUFFICIENT_DEMAND_EVIDENCE. A customer's yes, a note, or market text does not clear it. Clearing it would not approve the file or make it ready to show investors.",
    },
    "investor_readiness": {
        "term": "Ready to show investors",
        "plain": "Whether the file is complete enough to share with an investor. Today it is marked not ready.",
        "matters": "Showing investors too early can cost you credibility.",
        "todo": "Finish the open items, including customer evidence, and ask for an authorized review.",
        "precise": "Stored as the Investor Readiness Gate status. Internal means not ready to show investors. This note does not change the gate.",
    },
    "recommend_against": {
        "term": "Serious concern on file",
        "plain": "A problem big enough to stop the assessment from moving forward.",
        "matters": "While one is on file, the result stays at not ready to go ahead.",
        "todo": "Open the concern, read what would address it, and follow the next step.",
        "precise": "A recommend-against flag from the engine. The preliminary evaluation is held at Blocked. This note does not rewrite the stored recommendation.",
    },
    "dscr": {
        "term": "Loan coverage (DSCR)",
        "plain": "How many times the cash the business keeps covers its yearly loan payments.",
        "matters": "Below 1.00× the cash does not cover the loan. Lenders often want about 1.25× or more.",
        "todo": "If it is low, test lower costs, higher sales, a smaller project, or more of your own money in Improve.",
        "precise": "Debt service coverage ratio from the engine: cash flow before debt service divided by the debt payment. This note does not recalculate it.",
    },
    "sources_and_uses": {
        "term": "Sources and uses of money",
        "plain": "Where the opening money comes from, and what it is spent on.",
        "matters": "The two sides must match. A gap means the project is not fully funded.",
        "todo": "Check that each cost is realistic and that you can show where each dollar comes from.",
        "precise": "The engine's startup sources-and-uses table. Figures appear only when the engine calculated them. Missing inputs stay blank.",
    },
    "indicative_score": {
        "term": "Preliminary business evaluation",
        "plain": "A first look at market demand, financial strength, and long-term sustainability.",
        "matters": "It shows where the idea is strong and where it needs work. It is not a grade and not an approval.",
        "todo": "Use it to choose what to improve first. A serious open concern keeps the result at not yet ready.",
        "precise": "Market demand, financial strength, and long-term sustainability. It does not override a serious concern on file or a human review. No feasibility score is calculated.",
    },
    "market_snapshot": {
        "term": "Market snapshot",
        "plain": "A labeled look at the area and industry. On this version it is a demonstration unless you asked for a public extract.",
        "matters": "It gives background. It is not proof that customers will buy from you.",
        "todo": "Use it to guide questions, then collect your own evidence.",
        "precise": "Market observations do not clear INSUFFICIENT_DEMAND_EVIDENCE or any other recommend-against flag, and they do not grant investor-ready status.",
    },
}


def term_note(key: str) -> str:
    """The term, one plain sentence, and the rest on request."""
    item = TERMS[key]
    return (
        '<details class="plain">'
        f"<summary><strong>{escape(item['term'])}.</strong> {escape(item['plain'])} "
        '<span class="muted">Learn more</span></summary>'
        f"<p><strong>Why it matters.</strong> {escape(item['matters'])}</p>"
        f"<p><strong>What to do.</strong> {escape(item['todo'])}</p>"
        '<details class="techref"><summary>Exact definition (technical)</summary>'
        f"<p>{escape(item['precise'])}</p></details>"
        "</details>"
    )

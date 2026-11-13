"""Plain-English wording for customer pages.

This module only translates what is already stored. It never changes a flag, a score, a gate, a
recommendation, a review status, or a figure. The original codes stay in the stored result and in
exports. Pages show the plain words first and keep the exact code in a collapsed technical reference.

Nothing here clears a flag or marks anything approved. A finding that reads "needs evidence" stays
that way until the real requirement is met and an authorized review says otherwise.
"""

from __future__ import annotations

from dataclasses import dataclass
import re
from html import escape
from typing import Any

from scoring import rules

# ---------------------------------------------------------------------------
# Gate, band, and the official summary words
# ---------------------------------------------------------------------------

GATE_LABEL = {
    "Blocked": "Important information still needed",
    "Open": "No hard stop on file",
    "Not run": "Not evaluated yet",
}
GATE_MEANING = {
    "Blocked": "Something essential, such as proof that customers will buy, is still missing. Until it is on file, this assessment cannot move forward.",
    "Open": "No serious concern is recorded right now. That is not an approval, and a person still has to review the file.",
}
BAND_LABEL = {
    "Blocked": "Assessment not yet ready",
    "Strong": "Strong preliminary result",
    "Conditional": "Promising, with conditions",
    "Weak": "Needs substantial work",
    "Not run": "Not evaluated yet",
}
BAND_MEANING = {
    "Blocked": "The missing information above has to be dealt with before this evaluation can say more.",
    "Strong": "The three parts of the preliminary evaluation look strong so far. It does not replace evidence or a review.",
    "Conditional": "Some parts look promising and others still need support.",
    "Weak": "One or more parts need substantial work before this idea is ready for outside review.",
}
RECOMMENDATION_LABEL = {
    "do-not-proceed": "Not ready to go ahead (draft)",
    "conditional": "Possible, with conditions (draft)",
    "go": "Ready to go ahead (draft)",
}
READINESS_LABEL = {
    "internal": "Not ready to show investors",
    "investor-ready": "Ready to show investors",
}
REVIEW_LABEL = {
    "pending": "Waiting for an authorized review",
    "approved": "Reviewed and approved",
    "rejected": "Reviewed and not approved",
}
PRELIMINARY = "Preliminary business evaluation"
PRELIMINARY_PARTS = "Market demand, financial strength, and long-term sustainability"
PRELIMINARY_NOTE = (
    "A first look at three things: market demand, financial strength, and long-term sustainability. "
    "It is a reading aid, not a grade, and it does not replace evidence or a review."
)


def gate_label(status: str) -> str:
    return GATE_LABEL.get(status, status or GATE_LABEL["Not run"])


def band_label(band: str) -> str:
    return BAND_LABEL.get(band, band or BAND_LABEL["Not run"])


def recommendation_label(value: str) -> str:
    key = str(value or "").strip()
    return RECOMMENDATION_LABEL.get(key, key.replace("-", " ").capitalize() if key else "Not evaluated yet")


def readiness_label(value: str) -> str:
    key = str(value or "").strip()
    return READINESS_LABEL.get(key, key.replace("-", " ").capitalize() if key else "Not evaluated yet")


def review_label(value: str) -> str:
    key = str(value or "").strip()
    return REVIEW_LABEL.get(key, key.replace("_", " ").capitalize() if key else "Waiting for an authorized review")


def score_words(line: str) -> str:
    """The stored score line, said plainly. RUGD still gives no overall feasibility score."""
    text = str(line or "").strip()
    if not text or text.lower().startswith("not calculated"):
        return "No overall score. RUGD does not give one yet."
    return text


# ---------------------------------------------------------------------------
# Findings: one entry per stored flag
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Finding:
    title: str
    found: str
    matters: str
    todo: str
    links: tuple[tuple[str, str], ...]  # (button label, path after /assessments/<id>)


_RESEARCH = ("Save evidence in Research", "/intelligence")
_EXPLORE = ("Update your answers in Explore", "")
_CHECKLIST = ("See the evidence checklist", "/results")

FINDINGS: dict[str, Finding] = {
    rules.FLAG_DEMAND: Finding(
        "Not enough evidence of customer demand",
        "RUGD found no documented proof yet that customers will buy.",
        "Lenders and investors look for proof of demand before anything else. Without it, the assessment cannot move forward.",
        "Collect real evidence: signed commitments, pre-orders, deposits, or documented sales from an existing business. Then save it.",
        (_RESEARCH, ("Evidence checklist", "/results#evidence-checklist")),
    ),
    rules.FLAG_DEMAND_UNVERIFIED: Finding(
        "Demand is your own statement so far",
        "You said customers want this, but nothing independent backs it up yet.",
        "A claim without a source is treated as an assumption, so it cannot settle the demand question.",
        "Add a source people can check: a signed letter, a survey, a waitlist, or sales records.",
        (_RESEARCH,),
    ),
    rules.FLAG_OPERATOR: Finding(
        "Operator capacity looks too thin for this plan",
        "Your answers say the people running this do not have enough capacity for the scope proposed.",
        "Plans that outgrow the team tend to stall or lose money.",
        "Narrow the scope, or add management or staff, then update your answer.",
        (_EXPLORE,),
    ),
    rules.FLAG_REGULATORY: Finding(
        "An unresolved legal or regulatory issue is recorded",
        "Your answers include a regulatory or liability problem that is still open.",
        "Unresolved permits, licenses, or liability can stop an opening or add large costs.",
        "Resolve the issue, or get advice from a professional, then update your answer.",
        (_EXPLORE,),
    ),
    rules.FLAG_EXTRACTION: Finding(
        "The plan takes money out without putting any back in",
        "Your answers say profits would be taken out with nothing set aside to reinvest.",
        "A business that is not reinvested in becomes fragile over time.",
        "Describe how the business will be maintained and grown, then update your answer.",
        (_EXPLORE,),
    ),
    rules.FLAG_OPERATOR_GAP: Finding(
        "We do not know yet whether the team can run this",
        "You have not said whether the people running this can handle the scope.",
        "Operator capacity is one of the first things a reviewer checks.",
        "Answer the question about who will run the business.",
        (_EXPLORE,),
    ),
    rules.FLAG_REGULATORY_GAP: Finding(
        "Permits, licenses, and legal risks have not been checked",
        "You have not said whether any regulatory or liability issue is open.",
        "A missed permit or liability issue can be expensive to fix later.",
        "List the licenses and permits you need and whether any problem is open.",
        (_EXPLORE,),
    ),
    rules.FLAG_STEWARDSHIP_GAP: Finding(
        "Long-term care of the business has not been described",
        "You have not said how profits would be reinvested in the business.",
        "Reinvestment shows the business can last and is not only a short-term payout.",
        "Say how you would reinvest in equipment, people, or reserves.",
        (_EXPLORE,),
    ),
    rules.FLAG_FINANCIALS_UNMEASURED: Finding(
        "Costs and revenue are still estimates",
        "The money figures are your own estimates, not quotes or measurements.",
        "Estimates can be far off. Quotes and records make the results far more reliable.",
        "Replace the main estimates with contractor quotes, supplier prices, or real sales records.",
        (("Update your numbers in Explore", ""), ("Check against benchmarks", "/benchmarks")),
    ),
    rules.FLAG_NEGATIVE_OR_MARGINAL_CASH_FLOW: Finding(
        "The business does not earn enough yet under your numbers",
        "After costs, the business keeps little or no cash in both a normal and a weaker year.",
        "Without spare cash, loan payments and surprises cannot be covered.",
        "Test higher sales or lower costs, and see which changes close the gap.",
        (("Test revenue in the worksheet", "/revenue-worksheet"), ("Try changes in Improve", "/improve")),
    ),
    rules.FLAG_NO_GROSS_MARGIN: Finding(
        "Prices do not leave anything after direct costs",
        "The numbers show no money left after the direct cost of what you sell.",
        "Break-even sales cannot be worked out until each sale leaves something over.",
        "Check your prices and your cost of goods, then update them.",
        (_EXPLORE,),
    ),
}


def humanize(code: str) -> str:
    """A readable fallback for a code with no written finding."""
    words = str(code or "").replace("_", " ").strip().lower()
    return words.capitalize() if words else "Not stated"


def finding(code: str) -> Finding:
    found = FINDINGS.get(str(code))
    if found:
        return found
    label = humanize(code)
    return Finding(label, f"{label}.", "It is recorded on this assessment.", "Review it with your adviser.", (_EXPLORE,))


def title_of(code: str) -> str:
    return finding(code).title


def links_for(code: str, assessment_id: str) -> list[tuple[str, str]]:
    return [(label, f"/assessments/{assessment_id}{suffix}") for label, suffix in finding(code).links]


def tech_ref(*codes: str) -> str:
    """The exact stored codes, collapsed. They stay available to advisers and reviewers."""
    seen = [str(code) for code in codes if code]
    if not seen:
        return ""
    items = "".join(f"<li><code>{escape(code)}</code></li>" for code in seen)
    return (
        '<details class="techref"><summary>Technical reference</summary>'
        f"<p>The exact codes stored on this assessment, for your adviser or a reviewer.</p><ul>{items}</ul></details>"
    )


def official_line(result: dict[str, Any] | None) -> str:
    """One plain sentence for the stored official result. The codes sit in a collapsed reference."""
    result = result or {}
    if not result.get("engine_ran"):
        return "RUGD has not analyzed this business yet."
    blocking = [str(flag) for flag in result.get("blocking_flags") or []]
    parts = [recommendation_label(str(result.get("recommendation") or ""))]
    if blocking:
        parts.append(" and ".join(title_of(flag).lower() for flag in blocking[:2]).capitalize())
    parts.append(readiness_label(str(result.get("readiness_status") or "")))
    parts.append(review_label(str(result.get("human_review_status") or "pending")))
    return ". ".join(parts) + "."


# ---------------------------------------------------------------------------
# Field names that appear in saved text
# ---------------------------------------------------------------------------

FIELD_LABELS = {
    "total_project_cost": "Total project cost",
    "construction_cost": "Construction cost",
    "equipment": "Equipment",
    "soft_costs": "Soft costs (design, permits, fees)",
    "preopening_working_capital": "Cash set aside before opening",
    "contingency": "Contingency (a safety margin)",
    "debt": "Borrowed money",
    "equity": "Your own and investors' money",
    "total_sources": "Total sources of money",
    "annual_debt_service": "Loan payments per year",
    "monthly_debt_service": "Loan payment per month",
    "startup_base_revenue": "Typical-year sales",
    "startup_downside_revenue": "Weaker-year sales",
    "startup_base_dscr": "Loan coverage, typical year",
    "startup_downside_dscr": "Loan coverage, weaker year",
    "startup_break_even_revenue": "Sales needed to break even",
    "base_monthly_contribution": "Money left after direct costs, typical month",
    "base_monthly_cash_flow": "Cash left after all costs, typical month",
    "downside_monthly_revenue": "Sales in a weaker month",
    "downside_monthly_contribution": "Money left after direct costs, weaker month",
    "downside_monthly_cash_flow": "Cash left after all costs, weaker month",
    "break_even_monthly_revenue": "Monthly sales needed to break even",
    "months_to_break_even_base": "Months to earn back the starting money",
    "human_review_approved": "Authorized review approved",
    "investor_ready": "Ready to show investors",
    "revenue_trailing_12m": "Documented sales from an existing business (last 12 months)",
    "verified_revenue_trailing_12m": "Documented sales from an existing business (last 12 months)",
    "demand_evidence": "Evidence of customer demand",
    "inputs_are_measured": "Figures come from quotes or records",
}


def field_label(key: str) -> str:
    return FIELD_LABELS.get(str(key), humanize(key))


def humanize_lines(text: str) -> str:
    """Replace a leading ``field_name:`` with its plain label at the start of a line. Display only."""
    out = []
    for line in str(text).splitlines():
        head, sep, tail = line.partition(": ")
        if sep and head in FIELD_LABELS:
            if tail in ("true", "false"):
                tail = "Yes" if tail == "true" else "No"
            if "dscr" in head:
                tail = re.sub(r"^(-?)\$(\d[\d,]*(?:\.\d+)?)", r"\1\2×", tail)
            # "key: value. Label. Copied from the stored projection." repeats the label. Keep the value only.
            tail = re.sub(r"^(.*?)\. [A-Z][^.]*\. Copied from the stored projection\.$", r"\1.", tail)
            tail = tail.replace("Copied from the stored projection.", "Taken from your saved results.")
            out.append(_plain_phrases(f"{FIELD_LABELS[head]}: {tail}"))
        else:
            out.append(_plain_phrases(_plain_codes(line)))
    return "\n".join(out)


_PHRASES = (
    ("human_review_approved remains false", "No authorized review has approved this assessment"),
    ("Recommend-against flag still active", "Serious concern still open"),
    ("The deterministic draft recommendation", "The draft recommendation"),
    ("Demand provenance", "Where the demand figure came from:"),
    ("Calculated by the engine", "Calculated by RUGD"),
    ("Stored engine result.", "Saved results."),
    ("Engine flags:", "Open concerns:"),
    ("none stored on the financial result", "none on the financial result"),
    ("the stored engine result", "the saved results"),
    ("stored engine result", "saved results"),
    ("The engine does not return", "RUGD does not return"),
    ("Copied from the stored result", "Taken from your saved results"),
    ("Copied from the stored projection", "Taken from your saved results"),
)


def _plain_phrases(line: str) -> str:
    for old, new in _PHRASES:
        line = line.replace(old, new)
    return line


_CODE = re.compile(r"\b(" + "|".join(sorted(map(re.escape, FINDINGS), key=len, reverse=True)) + r")\b")


_KEY = re.compile(r"\b(" + "|".join(sorted(map(re.escape, FIELD_LABELS), key=len, reverse=True)) + r")\b")


def _plain_codes(line: str) -> str:
    """Swap a known flag code inside a sentence for its plain title. Display only."""
    line = _CODE.sub(lambda match: FINDINGS[match.group(1)].title, line)
    return _KEY.sub(lambda match: FIELD_LABELS[match.group(1)].lower() if match.start() else FIELD_LABELS[match.group(1)], line)


# ---------------------------------------------------------------------------
# Contextual explanations: what it means, why it matters, what to do
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Explanation:
    term: str
    means: str
    matters: str
    todo: str
    more: str = ""
    link: tuple[str, str] = ("", "")  # (label, path after /assessments/<id>)


EXPLANATIONS: dict[str, Explanation] = {
    "demand_evidence": Explanation(
        "Evidence of customer demand",
        "Proof that real people or businesses will pay for what you sell.",
        "Without it, everything else is a guess, and lenders and investors will not go further.",
        "Gather signed commitments, pre-orders, deposits, a paid waitlist, or documented sales, then save them in Research.",
        "A friend saying it sounds good, or a general market statistic, is not proof of demand for your business.",
        ("Save evidence in Research", "/intelligence"),
    ),
    "preliminary": Explanation(
        PRELIMINARY,
        "A first look at market demand, financial strength, and long-term sustainability.",
        "It helps you see where the idea is strong and where it needs work.",
        "Use it to pick what to improve first. It does not replace evidence or a review.",
        "It is not a grade and not an approval. A serious open concern keeps the result at not yet ready.",
    ),
    "important_info": Explanation(
        "Important information still needed",
        "Something essential is missing, usually proof that customers will buy.",
        "Until it is on file, the assessment cannot move forward, however good the numbers look.",
        "Open the next step below and add what is missing.",
        "Adding information does not unlock the result by itself. The requirement has to be truly met and then reviewed by an authorized person.",
    ),
    "not_ready": Explanation(
        "Assessment not yet ready",
        "The preliminary evaluation cannot say more until the missing information is dealt with.",
        "It stops a polished-looking number from hiding a real gap.",
        "Start with the first item under What to do next.",
    ),
    "break_even": Explanation(
        "Break-even",
        "The sales you need each month or year just to pay all costs and the loan.",
        "If your expected sales are below it, the business loses money.",
        "Compare it with your expected sales, then test ways to raise sales or cut costs.",
        "",
        ("Test revenue in the worksheet", "/revenue-worksheet"),
    ),
    "dscr": Explanation(
        "Loan coverage (DSCR)",
        "How many times the cash the business keeps covers its yearly loan payments.",
        "Below 1.00× the cash does not cover the loan. Lenders usually want about 1.25× or more.",
        "If it is low, test lower costs, higher sales, a smaller project, or more of your own money.",
        "",
        ("Try changes in Improve", "/improve"),
    ),
    "contingency": Explanation(
        "Contingency",
        "A safety margin added to costs for surprises.",
        "Costs nearly always run over, and a margin keeps a small overrun from becoming a crisis.",
        "Keep the default unless you have a quote or a reason to change it.",
    ),
    "working_capital": Explanation(
        "Working capital",
        "Cash kept on hand to pay bills before sales catch up.",
        "Many new businesses fail because they run out of cash, not because they lack customers.",
        "Estimate several months of expenses and enter them as cash set aside.",
        "",
        ("Update your numbers in Explore", ""),
    ),
    "equity": Explanation(
        "Your own and investors' money",
        "The part of the project paid for with your money or investors' money, not borrowed money.",
        "Lenders expect you to share the risk.",
        "Check how much you can really put in, and have a bank statement or commitment ready.",
    ),
    "benchmark": Explanation(
        "Benchmark",
        "A typical figure for similar businesses, such as average spending per customer.",
        "It shows whether your assumptions are realistic.",
        "Compare each of your key numbers with a source you can name.",
        "A benchmark is context. It does not prove your own numbers.",
        ("Open Benchmarks", "/benchmarks"),
    ),
    "scenario": Explanation(
        "Scenario",
        "A what-if version of your plan, such as fewer seats or a lower build cost.",
        "It shows which changes would help most before you spend money.",
        "Try one change at a time, then compare the results side by side.",
        "A scenario is a projection. It is not approved and does not change the saved assessment.",
        ("Open Improve", "/improve"),
    ),
    "placeholder": Explanation(
        "Placeholder",
        "A standard starting number used when you have not entered your own.",
        "It lets the page show a result, but it is not a fact about your business.",
        "Replace it with a quote, a lender term, or a measurement.",
        "",
        ("Update your numbers in Explore", ""),
    ),
    "recommendation": Explanation(
        "Draft recommendation",
        "RUGD's current reading of whether to go ahead, based only on what is saved.",
        "It tells you whether the idea is ready to move forward or still needs work.",
        "Read what is still open, then work through the next steps.",
        "It is a draft. It changes only when real evidence is added and the file is re-analyzed and reviewed.",
    ),
    "human_review": Explanation(
        "Human review",
        "A person with authority reads the file and records a decision.",
        "No software result is final until someone accountable has checked it.",
        "Nothing is needed from you except complete, honest information.",
        "Only an authorized reviewer can record this. Customers cannot approve their own file.",
    ),
    "investor_ready": Explanation(
        "Ready to show investors",
        "Whether the file is complete enough to share with investors.",
        "Sharing too early can cost you credibility.",
        "Finish the open items first, including customer evidence and a review.",
        "Today it stays marked not ready until every requirement is met and an authorized review is recorded.",
    ),
    "revenue_trailing_12m": Explanation(
        "Documented sales from an existing business",
        "Sales from the last 12 months that you can back up with records, such as bank deposits or tax filings.",
        "Real sales are the strongest proof that customers will pay.",
        "Enter the total only if you have records to show.",
    ),
}


def explain(key: str, assessment_id: str = "") -> str:
    """A "?" control: one plain sentence up front, the rest on request. It never changes a result."""
    item = EXPLANATIONS[key]
    link = ""
    if item.link[0] and assessment_id:
        link = f'<p><a href="/assessments/{escape(assessment_id)}{escape(item.link[1])}">{escape(item.link[0])}</a></p>'
    more = f'<p class="muted">{escape(item.more)}</p>' if item.more else ""
    return (
        '<details class="dh">'
        f'<summary aria-label="About {escape(item.term)}"><span aria-hidden="true">?</span></summary>'
        f'<div class="dh-body"><p class="dh-title">{escape(item.term)}</p>'
        f"<p><strong>What it means.</strong> {escape(item.means)}</p>"
        f"<p><strong>Why it matters.</strong> {escape(item.matters)}</p>"
        f"<p><strong>What to do.</strong> {escape(item.todo)}</p>"
        f"{more}{link}</div></details>"
    )

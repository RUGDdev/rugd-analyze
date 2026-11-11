"""Pitch decks copied from a saved business plan. Edits do not recalculate figures."""

from __future__ import annotations

from typing import Any

NOT_STORED = "Not stored. This deck does not fill this in."
ASSEMBLED = "Assembled from the saved business plan. This is not a live adviser response."
DISCLAIMER = (
    "This presentation is a draft summary of the saved plan. "
    "Financing approval, investor readiness, verified demand, and a guaranteed return are not established."
)
NARRATIVE_LIMIT = 4000

AUDIENCES = {
    "investor": "Investor presentation",
    "lender": "Bank or lender financing presentation",
    "partner": "Strategic partnership presentation",
    "overview": "General business overview",
}

# Included kinds are the useful default length. Every other kind stays in the deck and can be restored.
_INCLUDED = {
    "investor": {
        "intro",
        "opportunity",
        "problem",
        "solution",
        "customers",
        "competition",
        "revenue",
        "financials",
        "scenarios",
        "capital",
        "growth",
        "funding",
        "next",
    },
    "lender": {"intro", "capital", "financials", "break_even", "scenarios", "operations", "funding", "next"},
    "partner": {"intro", "opportunity", "products", "operations", "funding", "next"},
    "overview": {"intro", "products", "customers", "operations", "financials", "next"},
}

_KINDS = (
    ("intro", "Business introduction", False),
    ("opportunity", "Executive opportunity", True),
    ("problem", "Problem or unmet need", True),
    ("solution", "Proposed solution", True),
    ("products", "Products and services", True),
    ("customers", "Target customers and market", True),
    ("competition", "Competition and differentiation", True),
    ("revenue", "Business and revenue model", True),
    ("marketing", "Marketing and customer acquisition", True),
    ("operations", "Operations and management", True),
    ("financials", "Financial performance", True),
    ("break_even", "Break-even analysis", True),
    ("capital", "Capital requirements and use of funds", True),
    ("scenarios", "Financial scenarios and risks", True),
    ("growth", "Growth strategy", True),
    ("durable", "Durable Value considerations", True),
    ("funding", "Funding or partnership proposition", True),
    ("next", "Next steps", False),
)

_USE_KEYS = (
    ("construction_cost", "Construction"),
    ("equipment", "Equipment"),
    ("soft_costs", "Soft costs"),
    ("preopening_working_capital", "Pre-opening working capital"),
    ("contingency", "Contingency"),
)


def build_deck_document(plan: dict[str, Any], *, audience: str) -> dict[str, Any]:
    """Copy one saved plan into a deck. Later changes to the plan do not change this copy."""
    if audience not in AUDIENCES:
        raise ValueError("Choose an audience before generating a pitch deck.")
    document = plan.get("document") if isinstance(plan.get("document"), dict) else {}
    snapshot = document.get("snapshot") if isinstance(document.get("snapshot"), dict) else {}
    graphics = snapshot.get("graphics") if isinstance(snapshot.get("graphics"), dict) else {}
    figures = extract_figures(document)
    slides = [
        _slide(kind, title, optional, audience=audience, document=document, figures=figures)
        for kind, title, optional in _KINDS
    ]
    return {
        "plan_id": str(plan.get("id") or ""),
        "plan_title": str(plan.get("title") or "Business plan"),
        "audience": audience,
        "audience_label": AUDIENCES[audience],
        "business_name": str(snapshot.get("business_name") or "Assessment"),
        "stage": str(document.get("stage") or ""),
        "figures": figures,
        "graphics": {key: str(graphics.get(key) or "") for key in ("revenue", "break_even", "comparison", "allocation", "trend")},
        "slides": slides,
        "narrative_source": ASSEMBLED,
        "disclaimer": DISCLAIMER,
    }


def extract_figures(document: dict[str, Any]) -> dict[str, Any]:
    """Read numbers already stored on the plan. This does not run the engine."""
    snapshot = document.get("snapshot") if isinstance(document.get("snapshot"), dict) else {}
    assumptions = snapshot.get("assumptions") if isinstance(snapshot.get("assumptions"), list) else []
    results = snapshot.get("base_results") if isinstance(snapshot.get("base_results"), list) else []
    revenue = _amount_after(assumptions, "Projected monthly base revenue:")
    fixed = _amount_after(assumptions, "Monthly fixed costs:")
    break_even = _amount_after(results, "break_even_monthly_revenue:")
    gap = round(revenue - break_even, 2) if revenue is not None and break_even is not None else None
    uses = _uses(document)
    return {
        "assumed_revenue": revenue,
        "fixed_costs": fixed,
        "initial_capital": _amount_after(assumptions, "Initial capital:"),
        "base_contribution": _amount_after(results, "base_monthly_contribution:"),
        "base_cash_flow": _amount_after(results, "base_monthly_cash_flow:"),
        "downside_revenue": _amount_after(results, "downside_monthly_revenue:"),
        "downside_contribution": _amount_after(results, "downside_monthly_contribution:"),
        "downside_cash_flow": _amount_after(results, "downside_monthly_cash_flow:"),
        "break_even": break_even,
        "revenue_gap": gap,
        "uses": uses,
        "debt_service": _debt_service(document),
        "stage": str(document.get("stage") or ""),
    }


def edited_deck(document: dict[str, Any], form: dict[str, str]) -> list[dict[str, Any]]:
    """Apply narrative, inclusion, and order from the form. Copied figures stay as they are."""
    current = document.get("slides") if isinstance(document.get("slides"), list) else []
    slides = []
    for item in current:
        if not isinstance(item, dict):
            continue
        slide = dict(item)
        key = f"narrative_{slide.get('id')}"
        if key in form:
            text = str(form.get(key) or "").strip()
            if len(text) > NARRATIVE_LIMIT:
                raise ValueError(f"A slide narrative is limited to {NARRATIVE_LIMIT} characters. The deck was not changed.")
            slide["narrative"] = text or NOT_STORED
        if slide.get("optional"):
            slide["included"] = form.get(f"include_{slide.get('id')}") == "1"
        else:
            slide["included"] = True
        slides.append(slide)
    move = str(form.get("move") or "")
    if ":" in move:
        slide_id, direction = move.split(":", 1)
        _move(slides, slide_id, direction)
    return slides


def included_slides(document: dict[str, Any]) -> list[dict[str, Any]]:
    slides = document.get("slides") if isinstance(document.get("slides"), list) else []
    return [slide for slide in slides if isinstance(slide, dict) and slide.get("included")]


def _slide(
    kind: str,
    title: str,
    optional: bool,
    *,
    audience: str,
    document: dict[str, Any],
    figures: dict[str, Any],
) -> dict[str, Any]:
    narrative, facts, chart = _content(kind, audience, document, figures)
    return {
        "id": kind,
        "kind": kind,
        "title": _title(kind, title, audience),
        "narrative": narrative,
        "facts": facts,
        "chart": chart,
        "included": kind in _INCLUDED[audience],
        "optional": optional,
    }


def _title(kind: str, title: str, audience: str) -> str:
    if kind != "funding":
        return title
    if audience == "lender":
        return "Financing request"
    if audience == "partner":
        return "Partnership proposition"
    if audience == "overview":
        return "What this overview covers"
    return "Funding proposition"


def _content(
    kind: str,
    audience: str,
    document: dict[str, Any],
    figures: dict[str, Any],
) -> tuple[str, list[str], str | None]:
    sections = document.get("sections") if isinstance(document.get("sections"), dict) else {}
    snapshot = document.get("snapshot") if isinstance(document.get("snapshot"), dict) else {}
    name = str(snapshot.get("business_name") or "This business")
    if kind == "intro":
        return (
            f"{name}. {AUDIENCES[audience]}. {_purpose(audience)} {DISCLAIMER}",
            _lines(snapshot, "business_overview")[:4],
            None,
        )
    if kind == "opportunity":
        return (_section(sections, "executive_summary"), _lines(snapshot, "objective"), None)
    if kind == "problem":
        return (
            _first_present(snapshot, "evidence_gaps", "market_and_customers"),
            _lines(snapshot, "evidence_gaps"),
            None,
        )
    if kind == "solution":
        return (_section(sections, "products_services"), _lines(snapshot, "business_overview")[:3], None)
    if kind == "products":
        return (_section(sections, "products_services"), [], None)
    if kind == "customers":
        facts = _lines(snapshot, "market_and_customers")
        narrative = _section_or_facts(None, facts)
        if not any("Not available" not in line and "Not stored" not in line for line in facts):
            narrative = NOT_STORED + " Market size is not stored."
        return (narrative, facts, None)
    if kind == "competition":
        return (
            NOT_STORED + " Competitive facts are not stored.",
            ["Competitive facts are not stored. None were added."],
            None,
        )
    if kind == "revenue":
        return (_section_or_facts(sections.get("executive_summary"), _lines(snapshot, "assumptions")), _lines(snapshot, "assumptions"), None)
    if kind == "marketing":
        return (_section(sections, "marketing"), [], None)
    if kind == "operations":
        management = _section(sections, "management")
        operations = _section(sections, "operations")
        return (f"{operations}\n\n{management}", [], None)
    if kind == "financials":
        return (
            "These figures are copied from the saved plan. Monthly revenue and fixed costs are customer-supplied assumptions. "
            "Contribution and cash flow come from the stored engine result. No expense total is shown.",
            _money_facts(figures),
            "cash",
        )
    if kind == "break_even":
        return (_break_even_sentence(figures), _break_even_facts(figures), "break_even")
    if kind == "capital":
        return _capital_content(document, figures)
    if kind == "scenarios":
        return (
            "Base and Downside use the saved plan. Base revenue is the entered assumption. "
            "Downside revenue, contribution, and cash flow come from the stored engine result.",
            _scenario_facts(figures) + _lines(snapshot, "risk_indicators"),
            "comparison",
        )
    if kind == "growth":
        return (_section(sections, "growth"), [], None)
    if kind == "durable":
        return (_section(sections, "durable_value"), ["Educational guidance. This is not a DVT evaluation and it is not a score."], None)
    if kind == "funding":
        return (_funding(audience, figures), _funding_facts(audience, figures), None)
    actions = document.get("actions") if isinstance(document.get("actions"), list) else []
    if actions:
        narrative = "\n".join(
            f"{item.get('status') or 'open'}: {item.get('title') or 'Action'}" for item in actions if isinstance(item, dict)
        )
    else:
        narrative = _section(sections, "implementation")
    return (narrative + "\n\n" + DISCLAIMER, [], None)


def _purpose(audience: str) -> str:
    if audience == "investor":
        return "The emphasis is the growth opportunity, differentiation, revenue model, financial scenarios, capital need, and investment risks."
    if audience == "lender":
        return "The emphasis is the capital requirement, cash flow, repayment where a debt-service figure is stored, assumptions, and risks."
    if audience == "partner":
        return "The emphasis is the business opportunity, the operating model, and partnership objectives stored on the plan."
    return "The emphasis is the concept, products, customers, operations, financial highlights, and next steps."


def _funding(audience: str, figures: dict[str, Any]) -> str:
    capital = _money(figures.get("initial_capital"), "Initial capital")
    debt = _money(figures.get("debt_service"), "Monthly debt service")
    if audience == "lender":
        return (
            f"{capital} {debt} Repayment capacity is discussed from the stored cash flow and the stored debt service. "
            f"A missing debt-service figure stays missing. {DISCLAIMER}"
        )
    if audience == "partner":
        return (
            "Partnership objectives are limited to what the saved plan states. "
            f"Mutual benefits are not added. {capital} {DISCLAIMER}"
        )
    if audience == "overview":
        return f"This overview does not request funding. {capital} {DISCLAIMER}"
    return (
        f"{capital} The funding proposition uses the stored capital figures and the saved plan. "
        f"An investment return is not stated. {DISCLAIMER}"
    )


def _funding_facts(audience: str, figures: dict[str, Any]) -> list[str]:
    facts = [_money(figures.get("initial_capital"), "Initial capital"), _money(figures.get("base_cash_flow"), "Base monthly cash flow")]
    if audience == "lender":
        facts.append(_money(figures.get("debt_service"), "Monthly debt service"))
    return facts


def _capital_content(document: dict[str, Any], figures: dict[str, Any]) -> tuple[str, list[str], str | None]:
    if figures.get("stage") == "existing":
        return (
            "Startup capital requirements are not part of this existing or expanding business. No allocation was added.",
            ["Startup capital requirements are not part of this existing or expanding business."],
            None,
        )
    uses = figures.get("uses") if isinstance(figures.get("uses"), list) else []
    if not uses:
        return (
            "Startup capital allocation is not drawn. The required sources and uses are not stored. No category was added.",
            ["Startup capital allocation is not drawn."],
            None,
        )
    facts = [f"{item['label']}: {item['amount']}. Copied from the stored projection." for item in uses]
    return ("Use of funds is limited to the stored sources and uses. No extra category was added.", facts, "allocation")


def _break_even_sentence(figures: dict[str, Any]) -> str:
    revenue = figures.get("assumed_revenue")
    break_even = figures.get("break_even")
    gap = figures.get("revenue_gap")
    if revenue is None or break_even is None or gap is None:
        return "Break-even revenue or entered monthly revenue is not stored, so the difference is not shown."
    if gap > 0:
        relation = f"The entered monthly revenue is {gap} above the calculated break-even revenue."
    elif gap < 0:
        relation = f"The entered monthly revenue is {abs(gap)} below the calculated break-even revenue."
    else:
        relation = "The entered monthly revenue equals the calculated break-even revenue."
    return (
        f"Entered monthly revenue is {revenue}. Calculated break-even revenue is {break_even}. "
        f"The difference is {gap}. This difference is entered revenue minus the stored break-even. "
        f"It is not a separate engine output. {relation}"
    )


def _break_even_facts(figures: dict[str, Any]) -> list[str]:
    return [
        _money(figures.get("assumed_revenue"), "Entered monthly revenue"),
        _money(figures.get("break_even"), "Calculated break-even revenue"),
        _money(figures.get("revenue_gap"), "Revenue difference"),
    ]


def _money_facts(figures: dict[str, Any]) -> list[str]:
    return [
        _money(figures.get("assumed_revenue"), "Monthly revenue"),
        _money(figures.get("base_contribution"), "Monthly contribution"),
        _money(figures.get("fixed_costs"), "Monthly fixed costs"),
        "The engine does not return a separate expense total. No expense total is shown.",
        _money(figures.get("base_cash_flow"), "Monthly cash flow"),
        _money(figures.get("downside_cash_flow"), "Downside monthly cash flow"),
    ]


def _scenario_facts(figures: dict[str, Any]) -> list[str]:
    return [
        "Base " + _money(figures.get("assumed_revenue"), "revenue"),
        "Downside " + _money(figures.get("downside_revenue"), "revenue"),
        "Base " + _money(figures.get("base_contribution"), "contribution"),
        "Downside " + _money(figures.get("downside_contribution"), "contribution"),
        "Base " + _money(figures.get("base_cash_flow"), "cash flow"),
        "Downside " + _money(figures.get("downside_cash_flow"), "cash flow"),
    ]


def _money(value: Any, label: str) -> str:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return f"{label}: {NOT_STORED}"
    if value == 0:
        return f"{label}: 0. Stored as zero."
    return f"{label}: {value}."


def _section(sections: dict[str, Any], key: str) -> str:
    text = str(sections.get(key) or "").strip()
    if not text or text.startswith("Not written"):
        return NOT_STORED
    return text


def _section_or_facts(text: Any, facts: list[str]) -> str:
    cleaned = str(text or "").strip()
    if cleaned and not cleaned.startswith("Not written") and cleaned != NOT_STORED:
        return cleaned
    present = [line for line in facts if "Not available" not in line and "Not stored" not in line and "Missing" not in line]
    if present:
        return "\n".join(present[:4])
    return NOT_STORED


def _first_present(snapshot: dict[str, Any], *keys: str) -> str:
    for key in keys:
        lines = [line for line in _lines(snapshot, key) if "Not available" not in line and "Not stored" not in line]
        if lines:
            return "\n".join(lines[:4])
    return NOT_STORED


def _lines(snapshot: dict[str, Any], key: str) -> list[str]:
    values = snapshot.get(key)
    if isinstance(values, list) and values:
        return [str(item) for item in values]
    return [NOT_STORED]


def _amount_after(lines: list[Any], prefix: str) -> float | None:
    for line in lines:
        text = str(line)
        if not text.startswith(prefix):
            continue
        rest = text[len(prefix):].strip()
        lowered = rest.lower()
        if lowered.startswith("missing") or lowered.startswith("not "):
            return None
        token = rest.split()[0].rstrip(".") if rest else ""
        try:
            return float(token)
        except ValueError:
            return None
    return None


def _uses(document: dict[str, Any]) -> list[dict[str, Any]]:
    if str(document.get("stage") or "") == "existing":
        return []
    projection = document.get("projection") if isinstance(document.get("projection"), dict) else None
    if not isinstance(projection, dict) or not projection.get("calculated"):
        return []
    uses = projection.get("sources_and_uses") if isinstance(projection.get("sources_and_uses"), dict) else {}
    use_lines = uses.get("uses") if isinstance(uses.get("uses"), dict) else {}
    rows = []
    for key, label in _USE_KEYS:
        item = use_lines.get(key) if isinstance(use_lines.get(key), dict) else None
        amount = item.get("amount") if isinstance(item, dict) else None
        if isinstance(amount, bool) or not isinstance(amount, (int, float)):
            continue
        rows.append({"key": key, "label": label, "amount": float(amount)})
    return rows


def _debt_service(document: dict[str, Any]) -> float | None:
    projection = document.get("projection") if isinstance(document.get("projection"), dict) else None
    if not isinstance(projection, dict) or not projection.get("calculated"):
        return None
    uses = projection.get("sources_and_uses") if isinstance(projection.get("sources_and_uses"), dict) else {}
    sources = uses.get("sources") if isinstance(uses.get("sources"), dict) else {}
    item = sources.get("monthly_debt_service")
    if isinstance(item, dict):
        amount = item.get("amount")
        if isinstance(amount, (int, float)) and not isinstance(amount, bool):
            return float(amount)
    return None


def _move(slides: list[dict[str, Any]], slide_id: str, direction: str) -> None:
    index = next((position for position, slide in enumerate(slides) if slide.get("id") == slide_id), None)
    if index is None:
        return
    if direction == "earlier" and index > 0:
        slides[index - 1], slides[index] = slides[index], slides[index - 1]
    if direction == "later" and index < len(slides) - 1:
        slides[index + 1], slides[index] = slides[index], slides[index + 1]

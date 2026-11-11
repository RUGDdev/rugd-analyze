"""Adviser replies and proposals. A reply does not write an assessment, a plan, or a deck."""

from __future__ import annotations

from typing import Any

DETERMINISTIC = "Deterministic adviser. No live model was called."
LIVE = "Live adviser reply. This is not a deterministic fallback."
FALLBACK = "The configured adviser could not be reached. No live reply was invented."
NOT_SAVED = "This suggestion is not part of the saved plan or deck until you approve it."


def ask_adviser(
    context: dict[str, Any],
    question: str,
    analyst: Any,
) -> dict[str, Any]:
    """Answer from the assembled context. The assessment record is not an argument that gets mutated."""
    asked = " ".join(str(question or "").split()).strip()[:500]
    if not asked:
        return {
            "text": "Ask a question about this saved assessment. A blank question was not sent.",
            "source": "deterministic",
            "usage": {},
            "proposal": None,
        }
    source = "deterministic"
    usage: dict[str, Any] = {}
    if analyst.__class__.__name__ == "ExternalAnalyst" and getattr(analyst, "uses_network", False):
        try:
            text = str(analyst.complete_context(context, asked)).strip()
            if not text:
                raise ValueError("empty analyst response")
            source = "live"
            raw_usage = getattr(analyst, "last_usage", {})
            usage = dict(raw_usage) if isinstance(raw_usage, dict) else {}
            text = f"{LIVE}\n{text}"
        except Exception:
            text = f"{FALLBACK}\n{_deterministic(context, asked)}"
            source = "fallback"
    else:
        label = str(getattr(analyst, "label", "") or "")
        prefix = FALLBACK if label.startswith("Fallback:") else DETERMINISTIC
        text = f"{prefix}\n{_deterministic(context, asked)}"
        source = "fallback" if label.startswith("Fallback:") else "deterministic"
    return {
        "text": text[:4000],
        "source": source,
        "usage": usage,
        "proposal": _proposal(asked, context),
    }


def _deterministic(context: dict[str, Any], question: str) -> str:
    folded = question.lower()
    facts = context.get("customer_facts") if isinstance(context.get("customer_facts"), dict) else {}
    assumptions = context.get("unverified_assumptions") if isinstance(context.get("unverified_assumptions"), dict) else {}
    calculations = context.get("verified_calculations") if isinstance(context.get("verified_calculations"), dict) else {}
    official = context.get("official_conclusion") if isinstance(context.get("official_conclusion"), dict) else {}
    lines = [
        f"You asked: {question}",
        "Already saved: " + (", ".join(f"{key}" for key in facts) if facts else "no Explore note is stored beyond the business name."),
    ]
    if any(word in folded for word in ("cash", "break", "financial", "revenue", "downside", "contribution")):
        if calculations:
            lines.append(
                "Stored engine figures: "
                + "; ".join(f"{key} {calculations[key]}" for key in calculations)
                + ". These are the saved calculations. This reply does not replace them."
            )
        else:
            lines.append("No stored engine figure is available. This reply does not invent one.")
        if assumptions:
            lines.append(
                "Customer-supplied assumptions: "
                + "; ".join(f"{key} {assumptions[key]}" for key in assumptions)
                + "."
            )
    if any(word in folded for word in ("missing", "evidence", "market", "demand", "gap")):
        flags = [str(item) for item in (context.get("risk_flags") or [])]
        missing = [str(item) for item in (context.get("missing_evidence") or [])]
        if flags:
            lines.append("Recommend-against flags still stored: " + "; ".join(flags) + ". This reply does not clear them.")
        else:
            lines.append("No recommend-against flag is listed on the stored result.")
        if missing:
            lines.append("Missing items already listed: " + "; ".join(missing[:6]) + ".")
        lines.append("Market size is not treated as verified. This reply does not add a market figure.")
    research = context.get("research") if isinstance(context.get("research"), dict) else {}
    projects = research.get("projects") if isinstance(research.get("projects"), list) else []
    if projects and any(word in folded for word in ("research", "competitor", "pulse", "market", "evidence", "source")):
        lines.append(str(research.get("label") or "Saved research is separate from the engine result."))
        for project in projects[:2]:
            if not isinstance(project, dict):
                continue
            findings = project.get("evidence") if isinstance(project.get("evidence"), list) else []
            if findings and isinstance(findings[0], dict):
                lines.append(
                    f"Sourced record ({findings[0].get('class_label')}): {findings[0].get('finding')} "
                    f"Limitation: {findings[0].get('limitations') or 'not recorded'}."
                )
            else:
                lines.append(f"Research project {project.get('title')} has no saved evidence.")
        lines.append(
            "Interpretation is separate from a sourced fact. Saved research does not clear a recommend-against flag "
            "or change a stored calculation."
        )
        for project in projects[:2]:
            if not isinstance(project, dict):
                continue
            for line in (project.get("comparison") or [])[:3]:
                lines.append("Saved comparison: " + str(line))
        if any(isinstance(project, dict) and project.get("comparison") for project in projects):
            lines.append("This comparison quotes saved records. It does not add a source, a statistic, or a finding.")
        if any(
            "Retrieved public source" in str(finding.get("class_label") or "")
            for project in projects
            if isinstance(project, dict)
            for finding in (project.get("evidence") or [])
            if isinstance(finding, dict)
        ):
            lines.append(
                "A retrieved public figure is cited from its source record. It is not a market-size conclusion, "
                "and an older measurement period is incomplete for a current decision."
            )
            if any(
                "not an enacted requirement" in str(finding.get("finding") or "")
                for project in projects
                if isinstance(project, dict)
                for finding in (project.get("evidence") or [])
                if isinstance(finding, dict)
            ):
                lines.append("A proposed rule or a notice is not an enacted requirement.")
    if "plan" in folded or "deck" in folded or "slide" in folded or "report" in folded or "action" in folded:
        lines.append(_workflow_line(folded, context))
    recommendation = official.get("recommendation")
    lines.append(
        f"Stored recommendation: {recommendation}. "
        f"Investor readiness: {official.get('readiness_status')}. "
        "human_review_approved stays false. This reply does not grant financing approval or investor-ready status."
    )
    return "\n".join(lines)


def _workflow_line(folded: str, context: dict[str, Any]) -> str:
    plans = context.get("plans") if isinstance(context.get("plans"), list) else []
    decks = context.get("decks") if isinstance(context.get("decks"), list) else []
    actions = context.get("actions") if isinstance(context.get("actions"), list) else []
    if "deck" in folded or "slide" in folded:
        if decks:
            return f"A saved pitch deck is available ({decks[0].get('title')}). Slide wording can be proposed for review. {NOT_SAVED}"
        return f"No pitch deck is saved for this assessment. {NOT_SAVED}"
    if "action" in folded or "report" in folded:
        if actions:
            shown = "; ".join(f"{item.get('title')} ({item.get('status')})" for item in actions[:4] if isinstance(item, dict))
            return f"Open actions already stored: {shown}. This reply does not close an action or clear a flag."
        return "No action is stored. A flag stays in place until the assessment itself changes."
    if plans:
        return f"A saved business plan is available ({plans[0].get('title')}). A narrative suggestion stays a proposal. {NOT_SAVED}"
    return f"No business plan is saved yet. {NOT_SAVED}"


def _proposal(question: str, context: dict[str, Any]) -> dict[str, Any] | None:
    folded = question.lower()
    wants_plan = "plan" in folded and any(word in folded for word in ("improve", "suggest", "narrative", "rewrite", "proposal"))
    wants_deck = any(word in folded for word in ("deck", "slide")) and any(
        word in folded for word in ("improve", "suggest", "narrative", "wording", "proposal")
    )
    if not wants_plan and not wants_deck:
        return None
    facts = context.get("customer_facts") if isinstance(context.get("customer_facts"), dict) else {}
    concept = str(facts.get("concept") or "").strip()
    name = str(facts.get("business_name") or "This business")
    basis = concept or "No concept is stored. This proposal does not invent one."
    if wants_deck:
        decks = context.get("decks") if isinstance(context.get("decks"), list) else []
        target = str(decks[0].get("id") or "") if decks and isinstance(decks[0], dict) else ""
        kind = "deck"
        text = (
            f"{name}. Suggested slide wording from the saved concept: {basis} "
            "Audience wording can be edited after you approve. "
            "This does not state financing approval, verified demand, or a return."
        )
    else:
        plans = context.get("plans") if isinstance(context.get("plans"), list) else []
        target = str(plans[0].get("id") or "") if plans and isinstance(plans[0], dict) else ""
        kind = "plan"
        text = (
            f"{name}. Suggested plan narrative from the saved concept: {basis} "
            "Missing evidence stays missing. This does not change a stored figure or the recommendation."
        )
    research = context.get("research") if isinstance(context.get("research"), dict) else {}
    projects = research.get("projects") if isinstance(research.get("projects"), list) else []
    if projects and isinstance(projects[0], dict):
        findings = projects[0].get("evidence") if isinstance(projects[0].get("evidence"), list) else []
        if findings and isinstance(findings[0], dict):
            text += (
                " Reviewed research, not a new figure: "
                + str(findings[0].get("class_label") or "Evidence")
                + ". "
                + str(findings[0].get("finding") or "")
            )
    return {"kind": kind, "status": "review", "target_id": target, "text": text[:2000]}

"""Guided Explore conversation. Answers are saved only after the customer approves them."""

from __future__ import annotations

from typing import Any

QUESTIONS: tuple[tuple[str, str, str], ...] = (
    ("business_name", "What should we call this business?", "Business name"),
    ("concept", "In a sentence, what are you considering?", "Business concept"),
    ("industry", "What industry is this?", "Industry"),
    ("market", "Do you have a location or market in mind?", "Geographic market"),
    ("products", "What would you sell or provide?", "Products and services"),
    ("customers", "Who is the customer?", "Target customers"),
    ("revenue_model", "How would this business make money?", "Revenue model"),
    ("competition", "Who else could the customer choose?", "Competition"),
)

ALLOWED_FIELDS = frozenset(key for key, _question, _label in QUESTIONS)
PLACEHOLDER_NAMES = frozenset({"", "untitled", "new draft"})
PROVIDER_UNAVAILABLE = (
    "The configured adviser could not be reached. No live reply was invented. "
    "Your words are still waiting for approval below."
)

THEMES: dict[str, tuple[str, str]] = {
    "start-business": (
        "Build for Tomorrow",
        "A new venture asks what has to be true before money is spent.",
    ),
    "evaluate-idea": (
        "Earn Trust",
        "An idea still needs evidence that a customer will pay.",
    ),
    "existing-business": (
        "Embrace Accountability",
        "An existing business can name which figures are measured and which are still blank.",
    ),
    "improve-profitability": (
        "Embrace Accountability",
        "A margin question starts with the figures the engine can calculate, not a guessed result.",
    ),
    "business-plan": (
        "Build for Tomorrow",
        "A plan is useful after the blank fields and the evidence gaps are named.",
    ),
    "research-market": (
        "Adapt and Innovate",
        "Market Intelligence can show a labeled source. A typed place is still an assumption.",
    ),
    "expansion": (
        "Build for Tomorrow",
        "An expansion asks what new capacity and capital would be required.",
    ),
    "prepare-investment": (
        "Earn Trust",
        "Preparing for investment does not grant investor-ready status.",
    ),
    "prepare-sale": (
        "Steward for the Next Generation",
        "A sale or exit question is saved here. The 0.1 engine does not score that purpose.",
    ),
    "durable-value": (
        "Leave It Stronger",
        "Durable Value on this screen is educational guidance, not a DVT evaluation.",
    ),
    "monitor": (
        "Adapt and Innovate",
        "Monitoring is not active. No scheduled job has retrieved a current finding.",
    ),
}


def _messages(profile: dict[str, Any]) -> list[dict[str, str]]:
    stored = profile.get("adviser_messages")
    if not isinstance(stored, list):
        return []
    clean: list[dict[str, str]] = []
    for item in stored:
        if not isinstance(item, dict):
            continue
        role = "customer" if item.get("role") == "customer" else "adviser"
        text = " ".join(str(item.get("text") or "").split()).strip()
        if text:
            clean.append({"role": role, "text": text[:2000]})
    return clean[-40:]


def _add(profile: dict[str, Any], role: str, text: str) -> None:
    messages = _messages(profile)
    messages.append({"role": role, "text": " ".join(str(text).split()).strip()[:2000]})
    profile["adviser_messages"] = messages[-40:]


def field_is_blank(profile: dict[str, Any], key: str) -> bool:
    value = str(profile.get(key) or "").strip()
    if key == "business_name" and value.lower() in PLACEHOLDER_NAMES:
        return True
    return value == ""


def next_question(profile: dict[str, Any]) -> tuple[str, str, str] | None:
    for key, question, label in QUESTIONS:
        if field_is_blank(profile, key):
            return key, question, label
    return None


def start_conversation(profile: dict[str, Any], objective_label: str) -> dict[str, Any]:
    """Ask the first unanswered question. Nothing is treated as verified."""
    if _messages(profile):
        return profile
    profile["adviser_messages"] = []
    profile["human_review_approved"] = False
    nxt = next_question(profile)
    if nxt is None:
        _add(profile, "adviser", "The notes already on this draft are listed below.")
        return profile
    key, question, label = nxt
    profile["adviser_pending"] = {"field": key, "question": question, "label": label}
    _add(
        profile,
        "adviser",
        f"{question} Deterministic guidance, no live model. Nothing is saved until you approve it.",
    )
    return profile


def receive_answer(profile: dict[str, Any], text: str) -> dict[str, Any]:
    """Store the customer words and a proposal. The profile field stays unchanged."""
    cleaned = " ".join(str(text or "").split()).strip()[:500]
    if not cleaned:
        return profile
    if profile.get("adviser_proposal"):
        _add(profile, "adviser", "Approve or discard the answer already waiting. This reply did not replace it.")
        return profile
    pending = profile.get("adviser_pending")
    if not isinstance(pending, dict) or pending.get("field") not in ALLOWED_FIELDS:
        nxt = next_question(profile)
        if nxt is None:
            _add(profile, "customer", cleaned)
            _add(
                profile,
                "adviser",
                "The notes for this draft are already saved. Run Analyze when you want a calculation. This reply does not calculate a figure.",
            )
            return profile
        key, question, label = nxt
        pending = {"field": key, "question": question, "label": label}
        profile["adviser_pending"] = pending
    _add(profile, "customer", cleaned)
    profile["adviser_proposal"] = {
        "field": pending["field"],
        "label": pending["label"],
        "value": cleaned,
    }
    _add(
        profile,
        "adviser",
        (
            f"Save this as {pending['label']}: {cleaned}? "
            "This is a user-supplied assumption. It does not clear a flag or run the engine."
        ),
    )
    profile["human_review_approved"] = False
    return profile


def apply_proposal(profile: dict[str, Any]) -> dict[str, Any]:
    """Write the approved text into one allowed field."""
    proposal = profile.get("adviser_proposal")
    if not isinstance(proposal, dict):
        return profile
    field = str(proposal.get("field") or "")
    value = " ".join(str(proposal.get("value") or "").split()).strip()[:500]
    if field not in ALLOWED_FIELDS or not value:
        profile["adviser_proposal"] = None
        return profile
    profile[field] = value
    profile["adviser_proposal"] = None
    profile["adviser_pending"] = None
    profile["human_review_approved"] = False
    _add(
        profile,
        "adviser",
        f"Saved {proposal.get('label') or field}. This did not clear a flag and did not run the engine.",
    )
    nxt = next_question(profile)
    if nxt is None:
        _add(
            profile,
            "adviser",
            "The notes for this draft are saved. Continue to Analyze when you want the engine to calculate. This reply does not calculate a figure.",
        )
        return profile
    key, question, label = nxt
    profile["adviser_pending"] = {"field": key, "question": question, "label": label}
    _add(profile, "adviser", question)
    return profile


def discard_proposal(profile: dict[str, Any]) -> dict[str, Any]:
    if not profile.get("adviser_proposal"):
        return profile
    profile["adviser_proposal"] = None
    profile["human_review_approved"] = False
    _add(profile, "adviser", "That answer was not saved. You can reply again.")
    return profile


def note_provider_failure(profile: dict[str, Any]) -> dict[str, Any]:
    _add(profile, "adviser", PROVIDER_UNAVAILABLE)
    return profile


def note_provider_reply(profile: dict[str, Any], lines: list[str]) -> dict[str, Any]:
    text = " ".join(str(line) for line in lines if str(line).strip())
    if text:
        _add(profile, "adviser", text[:2000])
    return profile

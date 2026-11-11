"""Server-side context for the adviser. It copies authorized facts and does not calculate."""

from __future__ import annotations

import json
from typing import Any

from app.analyst import MAX_HISTORY_MESSAGES, MAX_USER_CHARS
from app.export import _without_secrets

_FACT_KEYS = (
    "business_name",
    "concept",
    "industry",
    "market",
    "products",
    "customers",
    "revenue_model",
    "competition",
    "stage",
    "venture_path",
)
_ASSUMPTION_KEYS = (
    "projected_monthly_revenue_base",
    "monthly_fixed_costs",
    "initial_capital",
    "gross_margin_pct",
    "downside_multiplier",
)
_CALCULATION_KEYS = (
    "base_monthly_contribution",
    "base_monthly_cash_flow",
    "downside_monthly_revenue",
    "downside_monthly_contribution",
    "downside_monthly_cash_flow",
    "break_even_monthly_revenue",
)


def build_adviser_context(
    record: dict[str, Any],
    *,
    plans: list[dict[str, Any]] | None = None,
    decks: list[dict[str, Any]] | None = None,
    actions: list[dict[str, Any]] | None = None,
    recent_messages: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Labeled context for one authorized assessment. Other customers' data is not accepted here."""
    profile = _without_secrets(record.get("profile") or {})
    if not isinstance(profile, dict):
        profile = {}
    result = record.get("result") if isinstance(record.get("result"), dict) else {}
    financial = result.get("financial") if isinstance(result.get("financial"), dict) else {}
    facts = {
        key: str(profile.get(key)).strip()
        for key in _FACT_KEYS
        if str(profile.get(key) or record.get(key) or "").strip()
    }
    if record.get("business_name") and "business_name" not in facts:
        facts["business_name"] = str(record.get("business_name"))
    assumptions = {
        key: profile.get(key)
        for key in _ASSUMPTION_KEYS
        if str(profile.get(key) or "").strip()
    }
    calculations = {
        key: financial.get(key)
        for key in _CALCULATION_KEYS
        if isinstance(financial.get(key), (int, float)) and not isinstance(financial.get(key), bool)
    }
    missing = [str(item) for item in (result.get("missing") or [])][:8]
    flags = [str(item) for item in (result.get("blocking_flags") or [])][:8]
    context = {
        "assessment_id": str(record.get("id") or ""),
        "customer_facts": facts,
        "unverified_assumptions": assumptions,
        "verified_calculations": calculations,
        "missing_evidence": missing,
        "risk_flags": flags,
        "official_conclusion": {
            "recommendation": result.get("recommendation"),
            "readiness_status": result.get("readiness_status"),
            "human_review_approved": bool(result.get("human_review_approved")),
            "score_line": result.get("score_line"),
            "engine_ran": bool(result.get("engine_ran")),
        },
        "plans": [
            {"id": str(item.get("id") or ""), "title": str(item.get("title") or "Business plan")}
            for item in (plans or [])[:3]
            if isinstance(item, dict)
        ],
        "decks": [
            {"id": str(item.get("id") or ""), "title": str(item.get("title") or "Pitch deck")}
            for item in (decks or [])[:3]
            if isinstance(item, dict)
        ],
        "actions": [
            {
                "title": str(item.get("title") or "Action"),
                "status": str(item.get("status") or "open"),
            }
            for item in (actions or [])[:6]
            if isinstance(item, dict)
        ],
        "recent_messages": [
            {
                "role": "customer" if item.get("role") == "customer" else "adviser",
                "text": str(item.get("text") or "")[:300],
            }
            for item in (recent_messages or [])[-MAX_HISTORY_MESSAGES:]
            if isinstance(item, dict) and str(item.get("text") or "").strip()
        ],
        "ai_suggestions": "Suggestions in the conversation are not saved facts until the customer approves them.",
    }
    encoded = json.dumps(context, default=str)
    if len(encoded) > MAX_USER_CHARS:
        context["recent_messages"] = context["recent_messages"][-2:]
        context["actions"] = context["actions"][:2]
    return context

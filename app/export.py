"""Local JSON export of saved assessments. Session secrets are omitted."""

from __future__ import annotations

from typing import Any

from app.store import BASELINE_ID

_SECRET_PARTS = ("token", "passphrase", "password", "secret", "cookie")


def export_assessment(record: dict[str, Any]) -> dict[str, Any]:
    """Copy one saved assessment. This does not run the engine or change the record."""
    return {
        "kind": "rugd-assessment-export",
        "official_baseline": _is_baseline(record),
        "assessment": _assessment_body(record),
    }


_OBSERVATION_FIELDS = (
    "source",
    "geographic_coverage",
    "industry_classification",
    "measurement_period",
    "retrieval_date",
    "limitations",
    "measure",
    "value",
)
_PACKAGE_DISCLAIMER = (
    "Local prototype. Not production security. This package is a draft research export. "
    "It does not grant investor-ready status. It does not clear a recommend-against flag "
    "and it does not set human_review_approved."
)
_TIER_DISCLAIMERS = {
    "explore": "Explore is a limited view. This package does not add a score.",
    "analyze": "Analyze includes the engine result and the research sections already derived from it. This package does not add a score.",
    "validate": "Validate can request review. This package is not an approval and it cannot set human_review_approved.",
    "partner": "Partner monitoring is not active. Hypothetical monitoring text is a demonstration.",
}


def export_research_package(
    record: dict[str, Any],
    result: dict[str, Any] | None = None,
    *,
    market: dict[str, Any] | None = None,
    analyst_lines: list[str] | None = None,
) -> dict[str, Any]:
    """Copy a shareable research package. This does not run the engine or change the record."""
    stored = result if result is not None else (record.get("result") or {})
    if not isinstance(stored, dict):
        stored = {}
    tier = str(record.get("tier") or "explore")
    if tier not in _TIER_DISCLAIMERS:
        tier = "explore"
    if analyst_lines is None:
        from app.analyst import DemonstrationAnalyst

        analyst_lines = DemonstrationAnalyst().explain(record, stored if stored else None)
    market_view = market if isinstance(market, dict) else {}
    blocking = [str(flag) for flag in stored.get("blocking_flags") or []]
    gap_flags = [str(flag) for flag in stored.get("gap_flags") or []]
    missing = [str(item) for item in stored.get("missing") or []]
    evidence_gaps = []
    if "INSUFFICIENT_DEMAND_EVIDENCE" in blocking:
        evidence_gaps.append("INSUFFICIENT_DEMAND_EVIDENCE is an active engine flag.")
    evidence_gaps.extend(f"Engine gap flag: {flag}." for flag in gap_flags)
    evidence_gaps.extend(f"Engine missing field: {item}" for item in missing)
    if not evidence_gaps:
        evidence_gaps.append("The engine did not list a gap flag or a missing field on this result.")
    assumptions = []
    intake = stored.get("intake") if isinstance(stored.get("intake"), dict) else {}
    for item in intake.get("assumptions") or []:
        if isinstance(item, dict):
            assumptions.append(
                {
                    "key": item.get("key"),
                    "value": item.get("value"),
                    "source": item.get("source"),
                    "rationale": item.get("rationale"),
                }
            )
    payload = {
        "kind": "rugd-research-package",
        "prototype_disclaimer": _PACKAGE_DISCLAIMER,
        "tier": tier,
        "tier_disclaimer": _TIER_DISCLAIMERS[tier],
        "does_not_clear_recommend_against_flags": True,
        "does_not_set_human_review_approved": True,
        "assessment_summary": {
            "id": record.get("id"),
            "business_name": record.get("business_name"),
            "purpose": record.get("purpose"),
            "tier": tier,
            "read_only": bool(record.get("read_only")),
            "hypothetical": bool(record.get("hypothetical")),
            "pilot_label": record.get("pilot_label"),
            "human_review_approved": record.get("human_review_approved") is True,
            "recommendation": stored.get("recommendation"),
            "readiness_status": stored.get("readiness_status"),
            "human_review_status": stored.get("human_review_status"),
            "engine_ran": bool(stored.get("engine_ran")),
        },
        "engine_results": {
            "engine_ran": bool(stored.get("engine_ran")),
            "model_version": stored.get("model_version"),
            "recommendation": stored.get("recommendation"),
            "score_line": stored.get("score_line"),
            "human_review_status": stored.get("human_review_status"),
            "human_review_approved": stored.get("human_review_approved") is True,
            "is_final": stored.get("is_final") is True,
            "readiness_status": stored.get("readiness_status"),
            "blocking_flags": blocking,
            "gap_flags": gap_flags,
            "missing": missing,
            "demand": stored.get("demand"),
            "view_summary": stored.get("view_summary"),
            "financial": stored.get("financial"),
            "projection": stored.get("projection"),
            "assumptions": assumptions,
        },
        "flags": {"blocking_flags": blocking, "gap_flags": gap_flags},
        "evidence_gaps": evidence_gaps,
        "market": {
            "status": str(market_view.get("status") or ""),
            "label": str(market_view.get("label") or ""),
            "observations": _observation_rows(market_view.get("observations")),
            "synthetic_observations": _observation_rows(market_view.get("synthetic_observations")),
            "does_not_clear_recommend_against_flags": True,
        },
        "analyst_explanation": [str(line) for line in analyst_lines],
    }
    return _without_secrets(payload)


def research_package_markdown(package: dict[str, Any]) -> str:
    """Render the research package as Markdown. The package is already free of session secrets."""
    summary = package.get("assessment_summary") or {}
    engine = package.get("engine_results") or {}
    lines = [
        f"# Research package: {summary.get('business_name') or 'Untitled'}",
        "",
        str(package.get("prototype_disclaimer") or ""),
        "",
        f"Tier: {package.get('tier') or 'explore'}. {package.get('tier_disclaimer') or ''}",
        "",
        "## Assessment summary",
        "",
        f"- Recommendation: {summary.get('recommendation')}",
        f"- Investor readiness: {summary.get('readiness_status')}",
        f"- Human review status: {summary.get('human_review_status')}",
        f"- human_review_approved: {str(bool(summary.get('human_review_approved'))).lower()}",
        "",
        "## Engine results",
        "",
        f"- Engine ran: {str(bool(engine.get('engine_ran'))).lower()}",
        f"- Model: {engine.get('model_version')}",
        f"- Score line: {engine.get('score_line')}",
        "",
        "## Flags",
        "",
    ]
    flags = package.get("flags") or {}
    lines.extend(f"- Blocking flag: {flag}" for flag in flags.get("blocking_flags") or [])
    lines.extend(f"- Gap flag: {flag}" for flag in flags.get("gap_flags") or [])
    if not flags.get("blocking_flags") and not flags.get("gap_flags"):
        lines.append("- No flag is listed on this result.")
    lines.extend(["", "## Evidence gaps", ""])
    lines.extend(f"- {item}" for item in package.get("evidence_gaps") or [])
    lines.extend(["", "## Market observations", ""])
    market = package.get("market") or {}
    lines.append(str(market.get("label") or "No market provider label is attached."))
    lines.append("")
    observations = list(market.get("observations") or []) + list(market.get("synthetic_observations") or [])
    if not observations:
        lines.append("No market observation is attached. No market fact is invented.")
    for item in observations:
        lines.extend(
            [
                f"- {item.get('measure')}: {item.get('value')}",
                f"  - Source: {item.get('source')}",
                f"  - Geographic coverage: {item.get('geographic_coverage')}",
                f"  - Classification: {item.get('industry_classification')}",
                f"  - Measurement period: {item.get('measurement_period')}",
                f"  - Retrieval date: {item.get('retrieval_date')}",
                f"  - Limitations: {item.get('limitations')}",
            ]
        )
    lines.extend(["", "These market figures do not clear a recommend-against flag.", "", "## Analyst explanation", ""])
    explanation = package.get("analyst_explanation") or []
    if explanation:
        lines.extend(f"- {line}" for line in explanation)
    else:
        lines.append("- Analyst explanation is not available.")
    lines.extend(
        [
            "",
            "## Limitations",
            "",
            str(package.get("prototype_disclaimer") or ""),
            "Customer-entered values remain user-supplied assumptions. This export does not change the stored assessment.",
            "",
        ]
    )
    return "\n".join(lines)


def _observation_rows(rows: Any) -> list[dict[str, str]]:
    if not isinstance(rows, list):
        return []
    copied = []
    for item in rows:
        if not isinstance(item, dict):
            continue
        copied.append({field: "" if item.get(field) is None else str(item.get(field)) for field in _OBSERVATION_FIELDS})
    return copied


def export_drafts(records: list[dict[str, Any]]) -> dict[str, Any]:
    """Copy every saved assessment except the official baseline."""
    drafts = [_assessment_body(record) for record in records if not _is_baseline(record)]
    return {
        "kind": "rugd-draft-export",
        "official_baseline_included": False,
        "drafts": drafts,
    }


def _is_baseline(record: dict[str, Any]) -> bool:
    return bool(record.get("read_only") or record.get("id") == BASELINE_ID)


def _assessment_body(record: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": record.get("id"),
        "business_name": record.get("business_name"),
        "purpose": record.get("purpose"),
        "tier": record.get("tier"),
        "read_only": bool(record.get("read_only")),
        "hypothetical": bool(record.get("hypothetical")),
        "pilot_label": record.get("pilot_label"),
        "profile": _without_secrets(record.get("profile")),
        "intake": _without_secrets(record.get("intake")),
        "result": _without_secrets(record.get("result")),
        "human_review_approved": record.get("human_review_approved") is True,
        "created_at": record.get("created_at"),
        "updated_at": record.get("updated_at"),
    }


def _without_secrets(value: Any) -> Any:
    if isinstance(value, dict):
        cleaned = {}
        for key, item in value.items():
            if _secret_key(str(key)):
                continue
            cleaned[key] = _without_secrets(item)
        return cleaned
    if isinstance(value, list):
        return [_without_secrets(item) for item in value]
    return value


def _secret_key(key: str) -> bool:
    lowered = key.lower().replace("-", "_")
    if lowered in {"session_id", "rugd_reviewer", "rugd_session"}:
        return True
    return any(part in lowered for part in _SECRET_PARTS)

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
    if lowered in {"session_id", "rugd_reviewer"}:
        return True
    return any(part in lowered for part in _SECRET_PARTS)

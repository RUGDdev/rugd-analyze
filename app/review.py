"""Reviewer-only approval. This is a local prototype gate, not production authentication."""

from __future__ import annotations

from typing import Any

from app.analysis import analyze_intake, analyze_record
from app.store import (
    BASELINE_ID,
    get_assessment,
    latest_approval,
    record_approval,
    save_result,
)

LOCAL_REVIEWER_GATE = "local-prototype-reviewer"
APPROVAL_NOTE = (
    "Reviewer approval recorded. It does not clear recommend-against flags, "
    "does not change the draft recommendation, and does not grant investor-ready."
)


class ReviewError(PermissionError):
    """The reviewer gate refused the action."""


def approve_assessment(
    connection: Any,
    assessment_id: str,
    *,
    reviewer_identity: str,
    reviewer_gate: str,
) -> dict[str, Any]:
    """Record approval and refresh the stored result. Customer forms cannot call this."""
    if reviewer_gate != LOCAL_REVIEWER_GATE:
        raise ReviewError("Reviewer gate refused. This is not a customer approval control.")
    identity = reviewer_identity.strip()
    if not identity:
        raise ValueError("A reviewer identity is required.")
    record = get_assessment(connection, assessment_id)
    if record is None:
        raise KeyError(assessment_id)
    if record["read_only"] or record["id"] == BASELINE_ID:
        raise ReviewError("The official baseline cannot be approved from this prototype.")
    pending = analyze_record(record)
    if not pending.get("engine_ran") or not pending.get("intake"):
        raise ReviewError("Analyze did not produce an engine result to approve.")
    approval = record_approval(
        connection,
        assessment_id,
        reviewer_identity=identity,
        note=APPROVAL_NOTE,
    )
    result = _with_approval(pending, approval)
    save_result(connection, assessment_id, result.get("intake"), result)
    return result


def result_with_stored_approval(record: dict[str, Any], pending: dict[str, Any], connection: Any) -> dict[str, Any]:
    """Reapply a stored reviewer approval after a customer analysis. Baseline stays unapproved."""
    if record.get("read_only") or record.get("id") == BASELINE_ID:
        return pending
    approval = latest_approval(connection, record["id"])
    if approval is None or not pending.get("engine_ran") or not pending.get("intake"):
        return pending
    return _with_approval(pending, approval)


def _with_approval(pending: dict[str, Any], approval: dict[str, Any]) -> dict[str, Any]:
    created = str(approval.get("approved_at") or "2026-11-07")
    result = analyze_intake(
        pending["intake"],
        as_of_date=created[:10],
        human_review="approved",
        approval=approval,
    )
    result["investor_summary_written"] = False
    result["is_final"] = False
    result["audit"]["investor_summary_written"] = False
    result["audit"]["is_final"] = False
    result["audit"]["approvals"] = [approval]
    return result

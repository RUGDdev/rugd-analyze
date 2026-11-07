"""Prototype reviewer session and approval. This is not production authentication."""

from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone
from typing import Any

from app.analysis import analyze_intake, analyze_record
from app.store import (
    BASELINE_ID,
    end_reviewer_session,
    get_assessment,
    get_reviewer_session,
    latest_approval,
    load_reviewer_session,
    record_approval,
    save_result,
    start_reviewer_session,
)

PROTOTYPE_REVIEWER_IDENTITY = "Local prototype reviewer"
PROTOTYPE_REVIEWER_PASSPHRASE = "local-prototype-reviewer"
LOCAL_REVIEWER_GATE = PROTOTYPE_REVIEWER_PASSPHRASE
AUTHENTICATION_METHOD = "local-session"
SESSION_LIFETIME_HOURS = 4
SESSION_LIFETIME_SECONDS = SESSION_LIFETIME_HOURS * 60 * 60
APPROVAL_NOTE = (
    "Reviewer approval recorded by a local-session reviewer. "
    "It does not clear recommend-against flags, "
    "does not change the draft recommendation, and does not grant investor-ready."
)


class ReviewError(PermissionError):
    """The reviewer gate refused the action."""


def open_reviewer_session(
    connection: Any,
    *,
    reviewer_identity: str,
    reviewer_passphrase: str,
) -> dict[str, Any]:
    """Open a local reviewer session. The passphrase is a prototype constant, not a user password store."""
    identity = reviewer_identity.strip()
    if identity != PROTOTYPE_REVIEWER_IDENTITY or reviewer_passphrase != PROTOTYPE_REVIEWER_PASSPHRASE:
        raise ReviewError("Reviewer sign-in refused. This is not a customer approval control.")
    created = datetime.now(timezone.utc).replace(microsecond=0)
    expires = created + timedelta(hours=SESSION_LIFETIME_HOURS)
    return start_reviewer_session(
        connection,
        token=secrets.token_urlsafe(32),
        reviewer_identity=identity,
        authentication_method=AUTHENTICATION_METHOD,
        expires_at=expires.isoformat(),
    )


def session_from_token(connection: Any, token: str) -> dict[str, Any] | None:
    """Return a session only when the stored token is present and unexpired."""
    return get_reviewer_session(connection, token)


def reviewer_session_state(connection: Any, token: str) -> dict[str, Any]:
    """Describe the cookie for the reviewer screen. An expired or missing token is not active."""
    if not token:
        return {"state": "signed-out", "active": False}
    loaded = load_reviewer_session(connection, token)
    if loaded is None or loaded.get("role") != "reviewer":
        return {"state": "signed-out", "active": False}
    active = get_reviewer_session(connection, token)
    if active is None:
        return {
            "state": "expired",
            "active": False,
            "reviewer_identity": loaded.get("reviewer_identity"),
            "authentication_method": loaded.get("authentication_method"),
        }
    return active


def close_reviewer_session(connection: Any, token: str) -> None:
    """Delete the stored token. The caller also clears the cookie."""
    end_reviewer_session(connection, token)


def approve_assessment(
    connection: Any,
    assessment_id: str,
    *,
    session: dict[str, Any],
) -> dict[str, Any]:
    """Record approval after re-checking the stored session. Customer forms cannot call this."""
    current = get_reviewer_session(connection, str(session.get("token") or ""))
    if (
        current is None
        or current.get("role") != "reviewer"
        or current.get("authentication_method") != AUTHENTICATION_METHOD
        or current.get("reviewer_identity") != PROTOTYPE_REVIEWER_IDENTITY
    ):
        raise ReviewError(
            "Reviewer session is missing, expired, or signed out. This is not a customer approval control."
        )
    identity = str(current["reviewer_identity"])
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
        authentication_method=AUTHENTICATION_METHOD,
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

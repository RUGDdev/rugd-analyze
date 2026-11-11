"""Local account sessions and reviewer approval. This is not production authentication."""

from __future__ import annotations

import secrets
from typing import Any

from app.accounts import AccountError, authenticate_user, session_expiry
from app.analysis import analyze_intake, analyze_record
from app.store import (
    BASELINE_ID,
    end_reviewer_session,
    end_user_sessions,
    get_account_session,
    get_assessment,
    get_reviewer_session,
    latest_approval,
    load_reviewer_session,
    record_approval,
    record_reviewer_event,
    save_result,
    start_reviewer_session,
)

AUTHENTICATION_METHOD = "local-account"
SESSION_LIFETIME_HOURS = 4
SESSION_LIFETIME_SECONDS = SESSION_LIFETIME_HOURS * 60 * 60
SESSION_COOKIE = "rugd_session"
APPROVAL_NOTE = (
    "Reviewer approval recorded for a local account. "
    "It does not clear recommend-against flags, "
    "does not change the draft recommendation, and does not grant investor-ready."
)


class ReviewError(PermissionError):
    """The reviewer gate refused the action."""


def open_account_session(
    connection: Any,
    *,
    email: str,
    password: str,
) -> dict[str, Any]:
    """Open a session for a local account. A customer session cannot approve."""
    try:
        user = authenticate_user(connection, email=email, password=password)
    except AccountError as exc:
        raise ReviewError(str(exc)) from exc
    end_user_sessions(connection, str(user["id"]))
    session = start_reviewer_session(
        connection,
        token=secrets.token_urlsafe(32),
        reviewer_identity=str(user["email"]),
        authentication_method=AUTHENTICATION_METHOD,
        expires_at=session_expiry(),
        user_id=str(user["id"]),
        role=str(user["role"]),
    )
    record_reviewer_event(
        connection,
        action="sign-in",
        reviewer_identity=str(user["email"]),
        session_token=session["token"],
        authentication_method=AUTHENTICATION_METHOD,
        note="Local account sign-in. This does not change an assessment.",
    )
    return session


def session_from_token(connection: Any, token: str) -> dict[str, Any] | None:
    """Return a session only when the stored token is present and unexpired."""
    return get_reviewer_session(connection, token)


def reviewer_session_state(connection: Any, token: str) -> dict[str, Any]:
    """Describe the cookie. A customer session stays visible and cannot approve."""
    if not token:
        return {"state": "signed-out", "active": False, "role": ""}
    loaded = load_reviewer_session(connection, token)
    if loaded is None:
        return {"state": "signed-out", "active": False, "role": ""}
    active = get_account_session(connection, token)
    if active is None:
        return {
            "state": "expired",
            "active": False,
            "role": loaded.get("role") or "",
            "reviewer_identity": loaded.get("reviewer_identity"),
            "authentication_method": loaded.get("authentication_method"),
        }
    return active


def close_reviewer_session(connection: Any, token: str) -> None:
    """Record sign-out, then delete the stored token. The caller also clears the cookie."""
    loaded = load_reviewer_session(connection, token)
    if loaded is not None:
        record_reviewer_event(
            connection,
            action="sign-out",
            reviewer_identity=str(loaded.get("reviewer_identity") or ""),
            session_token=token,
            authentication_method=str(loaded.get("authentication_method") or ""),
            note="Local account sign-out. This does not change an assessment.",
        )
    end_reviewer_session(connection, token)


def approve_assessment(
    connection: Any,
    assessment_id: str,
    *,
    session: dict[str, Any],
) -> dict[str, Any]:
    """Record approval after re-checking the stored session. Customer forms cannot call this."""
    current = get_account_session(connection, str(session.get("token") or ""))
    if current is None or current.get("authentication_method") != AUTHENTICATION_METHOD:
        raise ReviewError(
            "Reviewer session is missing, expired, or signed out. This is not a customer approval control."
        )
    if current.get("role") != "reviewer":
        raise ReviewError("This account cannot approve. A customer role is not a reviewer.")
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
    record_reviewer_event(
        connection,
        action="approve",
        reviewer_identity=identity,
        session_token=str(current["token"]),
        authentication_method=AUTHENTICATION_METHOD,
        assessment_id=assessment_id,
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

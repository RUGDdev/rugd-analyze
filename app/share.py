"""Read-only share links. A link cannot edit an assessment or approve it."""

from __future__ import annotations

import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from app.store import (
    create_share_link,
    get_assessment,
    get_share_by_token_hash,
    get_share_link,
    list_share_links,
    revoke_share_link,
    session_storage_key,
)

SHARE_LIFETIMES = {
    "24h": 24,
    "7d": 24 * 7,
    "until-revoked": None,
}


class ShareError(PermissionError):
    """The share link was refused. The message does not include the token."""


def can_manage_share(session: dict[str, Any] | None, record: dict[str, Any]) -> bool:
    """An assessment owner or a reviewer may create and revoke a link."""
    if not session or not session.get("active"):
        return False
    if session.get("authentication_method") != "local-account":
        return False
    if session.get("role") == "reviewer":
        return True
    if session.get("role") != "customer":
        return False
    owner = str(record.get("owner_user_id") or "")
    user_id = str(session.get("user_id") or "")
    return bool(owner) and owner == user_id


def issue_share_link(
    connection: Any,
    record: dict[str, Any],
    session: dict[str, Any],
    lifetime: str,
    *,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Store a hashed token. The raw token is returned once and is not written to SQLite."""
    if not can_manage_share(session, record):
        raise ShareError("Only the assessment owner or a reviewer can create a read-only link.")
    if lifetime not in SHARE_LIFETIMES:
        raise ShareError("Choose a 24-hour, 7-day, or until-revoked link.")
    current = _utc(now)
    hours = SHARE_LIFETIMES[lifetime]
    expires_at = None if hours is None else _stamp(current + timedelta(hours=hours))
    raw = secrets.token_urlsafe(32)
    share_id = str(uuid.uuid4())
    create_share_link(
        connection,
        share_id=share_id,
        token_hash=session_storage_key(raw),
        assessment_id=str(record["id"]),
        created_by=str(session.get("user_id") or ""),
        created_at=_stamp(current),
        expires_at=expires_at,
    )
    return {
        "id": share_id,
        "token": raw,
        "path": f"/share/{raw}",
        "expires_at": expires_at,
        "assessment_id": record["id"],
    }


def revoke_share(
    connection: Any,
    record: dict[str, Any],
    session: dict[str, Any],
    share_id: str,
    *,
    now: datetime | None = None,
) -> None:
    if not can_manage_share(session, record):
        raise ShareError("Only the assessment owner or a reviewer can revoke a read-only link.")
    link = get_share_link(connection, share_id)
    if link is None or link["assessment_id"] != record["id"]:
        raise ShareError("That share link was not found.")
    revoke_share_link(connection, share_id, _stamp(_utc(now)))


def open_share(connection: Any, token: str, *, now: datetime | None = None) -> dict[str, Any]:
    """Return the assessment for a live link. This does not change the assessment."""
    current = _utc(now)
    link = get_share_by_token_hash(connection, session_storage_key(token)) if token else None
    if link is None:
        raise ShareError("This link is not valid.")
    if link["revoked_at"]:
        raise ShareError("This link has been revoked.")
    if link["expires_at"]:
        try:
            expires = datetime.fromisoformat(link["expires_at"])
        except ValueError as exc:
            raise ShareError("This link is not valid.") from exc
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=timezone.utc)
        if expires <= current:
            raise ShareError("This link has expired.")
    record = get_assessment(connection, link["assessment_id"])
    if record is None:
        raise ShareError("This link is not valid.")
    return record


def active_share_links(connection: Any, assessment_id: str) -> list[dict[str, Any]]:
    return [item for item in list_share_links(connection, assessment_id) if not item["revoked_at"]]


def _utc(now: datetime | None) -> datetime:
    current = now or datetime.now(timezone.utc)
    if current.tzinfo is None:
        return current.replace(tzinfo=timezone.utc)
    return current.astimezone(timezone.utc)


def _stamp(value: datetime) -> str:
    return value.astimezone(timezone.utc).replace(microsecond=0).isoformat()

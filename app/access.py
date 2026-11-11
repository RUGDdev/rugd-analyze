"""Who may read or change an assessment.

Customer files stay with that customer or a reviewer. The official baseline and the
seeded restaurant demonstrations stay readable because they are prototype records.
Ordinary customers and visitors cannot change those demonstrations. The baseline
stays read-only. An unclaimed draft has no owner. It is not assigned and it is
not deleted. Only a reviewer can open it.
"""

from __future__ import annotations

from typing import Any

from app.store import BASELINE_ID, RESTAURANT_ID, RESTAURANT_VERIFIED_ID

PUBLIC_IDS = frozenset({BASELINE_ID, RESTAURANT_ID, RESTAURANT_VERIFIED_ID})

DENIAL = "This assessment is not available to this session."


def is_public_record(record: dict[str, Any]) -> bool:
    """A prototype record shipped with the app, not a customer-owned file."""
    if record.get("read_only"):
        return True
    return str(record.get("id") or "") in PUBLIC_IDS


def may_read(session: dict[str, Any] | None, record: dict[str, Any]) -> bool:
    if is_public_record(record):
        return True
    if _reviewer(session):
        return True
    owner = str(record.get("owner_user_id") or "")
    if not owner:
        return False
    return _customer_owns(session, owner)


def may_write(session: dict[str, Any] | None, record: dict[str, Any]) -> bool:
    if record.get("read_only") or str(record.get("id") or "") == BASELINE_ID:
        return False
    if _reviewer(session):
        return True
    if is_public_record(record):
        return False
    owner = str(record.get("owner_user_id") or "")
    if not owner:
        return False
    return _customer_owns(session, owner)


def may_save_report(session: dict[str, Any] | None, record: dict[str, Any]) -> bool:
    """A signed-in reader may store a report snapshot. The assessment row stays as it is."""
    return _signed_in(session) and may_read(session, record)


def may_see_attachment(
    session: dict[str, Any] | None,
    record: dict[str, Any],
    created_by: str,
) -> bool:
    """Saved reports and actions follow the assessment, and stay with their author on a public record."""
    if not may_read(session, record):
        return False
    if _reviewer(session):
        return True
    if not _signed_in(session):
        return False
    if _customer_owns(session, str(record.get("owner_user_id") or "")):
        return True
    return str(session.get("user_id") or "") == str(created_by or "")


def visible_records(
    session: dict[str, Any] | None,
    records: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    return [record for record in records if may_read(session, record)]


def _signed_in(session: dict[str, Any] | None) -> bool:
    return bool(
        session
        and session.get("active")
        and session.get("authentication_method") == "local-account"
        and session.get("user_id")
    )


def _reviewer(session: dict[str, Any] | None) -> bool:
    return _signed_in(session) and session.get("role") == "reviewer"


def _customer_owns(session: dict[str, Any] | None, owner: str) -> bool:
    return bool(
        _signed_in(session)
        and session.get("role") == "customer"
        and str(session.get("user_id") or "") == owner
    )

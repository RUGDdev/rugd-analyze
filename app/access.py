"""Who may read or change an assessment.

Customer files stay with that customer or a reviewer. The official baseline and the
seeded restaurant demonstrations stay readable because they are prototype records,
not a customer's file. An unclaimed draft has no owner. It is not assigned to a
signed-in customer, and it is not deleted.
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
        return not _signed_in(session)
    return _customer_owns(session, owner)


def may_write(session: dict[str, Any] | None, record: dict[str, Any]) -> bool:
    if record.get("read_only") or str(record.get("id") or "") == BASELINE_ID:
        return False
    if is_public_record(record):
        return True
    if _reviewer(session):
        return True
    owner = str(record.get("owner_user_id") or "")
    if not owner:
        return not _signed_in(session)
    return _customer_owns(session, owner)


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

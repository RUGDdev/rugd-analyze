"""Stored email preferences for the local pilot.

The preference is a record on the account. Delivery uses the existing mail
path: the server log when SMTP_HOST is unset, or SMTP when it is set.
A notice goes only to the owner of that assessment, and only when that owner
turned the event on. Verification and password-reset mail are separate and
stay available. A notice does not approve an assessment, lift a concern, change
a role, or approve the assessment.
"""

from __future__ import annotations

from typing import Any

EVENTS: tuple[tuple[str, str, str], ...] = (
    (
        "assessment_shared",
        "Assessment shared",
        "A read-only link was created for an assessment this account owns.",
    ),
    (
        "review_requested",
        "Review requested",
        "A review was requested on an assessment this account owns.",
    ),
    (
        "review_recorded",
        "Review recorded",
        "A reviewer recorded a decision on an assessment this account owns.",
    ),
)


def preferences_from_form(form: dict[str, str]) -> dict[str, bool]:
    """Read the known checkboxes. An absent box is off. Unknown fields are ignored."""
    return {key: form.get(f"pref_{key}") == "1" for key, _label, _detail in EVENTS}


def normalize_preferences(raw: Any) -> dict[str, bool]:
    """Keep only the known events. Anything else, including an approval field, is dropped."""
    data = raw if isinstance(raw, dict) else {}
    return {key: data.get(key) is True for key, _label, _detail in EVENTS}


def notify_owner(connection: Any, record: dict[str, Any], event: str) -> bool:
    """Mail the owner when that account opted in. No token is included."""
    known = {key for key, _label, _detail in EVENTS}
    if event not in known:
        return False
    user_id = str(record.get("owner_user_id") or "")
    if not user_id:
        return False
    from app.store import get_user_by_id

    user = get_user_by_id(connection, user_id)
    if user is None:
        return False
    preferences = user.get("notification_preferences") or {}
    if preferences.get(event) is not True:
        return False
    email = str(user.get("email") or "")
    if not email:
        return False
    subject, body = _message(event, str(record.get("business_name") or "This assessment"))
    from app.mail import deliver

    deliver(email, subject, body)
    return True


def _message(event: str, name: str) -> tuple[str, str]:
    if event == "assessment_shared":
        return (
            "RUGD Analyze: a read-only link was created",
            (
                f"{name}: a read-only link was created. The link cannot edit the assessment or approve it. "
                "This notice does not approve the assessment or lift a serious concern."
            ),
        )
    if event == "review_requested":
        return (
            "RUGD Analyze: a review was requested",
            (
                f"{name}: a review was requested. This notice does not approve the assessment, "
                "lift a serious concern, or approve the assessment."
            ),
        )
    return (
        "RUGD Analyze: a review was recorded",
        (
            f"{name}: a reviewer recorded a decision. That decision does not by itself clear a "
            "serious concern or grant investor-ready status. "
            "This notice does not approve the assessment."
        ),
    )

"""Local email and password accounts for the pilot. This is not production authentication.

Self-registration creates a customer. The first reviewer is created from
RUGD_BOOTSTRAP_REVIEWER_EMAIL and RUGD_BOOTSTRAP_REVIEWER_PASSWORD when no
reviewer exists. Later reviewers are created by a signed-in reviewer.
"""

from __future__ import annotations

import hashlib
import os
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from app.store import (
    count_users_with_role,
    create_user,
    get_user_by_email,
    record_reviewer_event,
)

BOOTSTRAP_EMAIL_VARIABLE = "RUGD_BOOTSTRAP_REVIEWER_EMAIL"
BOOTSTRAP_PASSWORD_VARIABLE = "RUGD_BOOTSTRAP_REVIEWER_PASSWORD"

ROLES = frozenset({"customer", "reviewer"})
MIN_PASSWORD_LENGTH = 8
_SCRYPT_N = 2**14
_SCRYPT_R = 8
_SCRYPT_P = 1
_SCRYPT_DKLEN = 32
_DUMMY_HASH = ""


class AccountError(ValueError):
    """Registration or login was refused. The message does not include a password."""


def hash_password(password: str, *, salt: bytes | None = None) -> str:
    """Return a scrypt hash. The password itself is not stored."""
    if salt is None:
        salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(
        password.encode("utf-8"),
        salt=salt,
        n=_SCRYPT_N,
        r=_SCRYPT_R,
        p=_SCRYPT_P,
        dklen=_SCRYPT_DKLEN,
    )
    return f"scrypt${_SCRYPT_N}${_SCRYPT_R}${_SCRYPT_P}${salt.hex()}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        scheme, n_text, r_text, p_text, salt_hex, digest_hex = stored.split("$")
        if scheme != "scrypt":
            return False
        expected = bytes.fromhex(digest_hex)
        check = hashlib.scrypt(
            password.encode("utf-8"),
            salt=bytes.fromhex(salt_hex),
            n=int(n_text),
            r=int(r_text),
            p=int(p_text),
            dklen=len(expected),
        )
    except (TypeError, ValueError):
        return False
    return secrets.compare_digest(check, expected)


def normalize_email(email: str) -> str:
    cleaned = email.strip().lower()
    if len(cleaned) > 254 or cleaned.count("@") != 1 or any(char.isspace() for char in cleaned):
        raise AccountError("Enter an email address.")
    local, domain = cleaned.split("@")
    if not local or "." not in domain or domain.startswith(".") or domain.endswith("."):
        raise AccountError("Enter an email address.")
    return cleaned


def register_account(
    connection: Any,
    *,
    email: str,
    password: str,
) -> dict[str, Any]:
    """Create a customer account. This path cannot create or promote a reviewer."""
    return _create_account(connection, email=email, password=password, role="customer")


def bootstrap_reviewer(
    connection: Any,
    *,
    email: str,
    password: str,
) -> dict[str, Any] | None:
    """Create the first reviewer when none exists. An existing account is left unchanged."""
    if count_users_with_role(connection, "reviewer") > 0:
        return None
    try:
        normalized = normalize_email(email)
    except AccountError:
        return None
    if get_user_by_email(connection, normalized) is not None:
        return None
    try:
        _check_password(password)
    except AccountError:
        return None
    return _create_account(connection, email=normalized, password=password, role="reviewer")


def bootstrap_reviewer_from_environment(connection: Any) -> dict[str, Any] | None:
    """Read the bootstrap variables. Missing values and an existing reviewer do nothing."""
    email = os.environ.get(BOOTSTRAP_EMAIL_VARIABLE, "").strip()
    password = os.environ.get(BOOTSTRAP_PASSWORD_VARIABLE, "")
    if not email or not password:
        return None
    return bootstrap_reviewer(connection, email=email, password=password)


def create_reviewer_account(
    connection: Any,
    *,
    email: str,
    password: str,
    session: dict[str, Any],
) -> dict[str, Any]:
    """Create another reviewer. The caller must already be a signed-in reviewer."""
    if (
        not session.get("active")
        or session.get("role") != "reviewer"
        or session.get("authentication_method") != "local-account"
    ):
        raise AccountError("A customer account cannot create a reviewer.")
    existing = None
    try:
        existing = get_user_by_email(connection, normalize_email(email))
    except AccountError:
        existing = None
    if existing is not None:
        raise AccountError("An account with that email is already registered.")
    created = _create_account(connection, email=email, password=password, role="reviewer")
    record_reviewer_event(
        connection,
        action="create-reviewer",
        reviewer_identity=str(session.get("reviewer_identity") or ""),
        session_token=str(session.get("token") or ""),
        authentication_method=str(session.get("authentication_method") or ""),
        note=(
            f"Created reviewer account {created['email']}. "
            "This does not change an assessment, clear a flag, or set human_review_approved."
        ),
    )
    return created


def _create_account(
    connection: Any,
    *,
    email: str,
    password: str,
    role: str,
) -> dict[str, Any]:
    if role not in ROLES:
        raise AccountError("Role must be customer or reviewer.")
    normalized = normalize_email(email)
    _check_password(password)
    try:
        user = create_user(
            connection,
            user_id=str(uuid.uuid4()),
            email=normalized,
            password_hash=hash_password(password),
            role=role,
        )
    except ValueError as exc:
        raise AccountError(str(exc)) from exc
    return public_user(user)


def _check_password(password: str) -> None:
    if len(password) < MIN_PASSWORD_LENGTH:
        raise AccountError("Use a password of at least 8 characters.")
    if len(password) > 200:
        raise AccountError("That password is too long.")


def authenticate_user(connection: Any, *, email: str, password: str) -> dict[str, Any]:
    """Return the account when the email and password match. A miss reveals neither field."""
    try:
        normalized = normalize_email(email)
    except AccountError:
        _burn_password_check(password)
        raise AccountError("Email or password was not accepted.") from None
    user = get_user_by_email(connection, normalized)
    stored = user["password_hash"] if user is not None else _dummy_hash()
    if user is None or not verify_password(password, stored):
        raise AccountError("Email or password was not accepted.")
    if user["role"] not in ROLES:
        raise AccountError("Email or password was not accepted.")
    return public_user(user)


def public_user(user: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": user["id"],
        "email": user["email"],
        "role": user["role"],
        "created_at": user["created_at"],
    }


def session_expiry() -> str:
    created = datetime.now(timezone.utc).replace(microsecond=0)
    return (created + timedelta(hours=4)).isoformat()


def _dummy_hash() -> str:
    global _DUMMY_HASH
    if not _DUMMY_HASH:
        _DUMMY_HASH = hash_password("local-pilot-dummy-password")
    return _DUMMY_HASH


def _burn_password_check(password: str) -> None:
    verify_password(password, _dummy_hash())

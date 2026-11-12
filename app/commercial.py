"""Local plan definitions, usage meters, and a mock billing event log.

No price, card number, or payment provider is stored. A simulated plan is not a
paid subscription. With RUGD_BILLING_SIMULATION unset, a signed event is recorded
and does not change access. The disabled billing hook in app.future stays disabled.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import re
import sqlite3
from datetime import datetime, timezone
from html import escape
from typing import Any

from app.public_retrieval import account_batch_limit
from app.store import get_user_by_id, record_audit_event

PLAN_IDS = ("explore", "analyze", "validate", "partner")
_EXPLORE = frozenset({"explore", "draft"})
_ANALYZE = _EXPLORE | frozenset({"analyze", "research", "adviser", "report", "plan", "deck"})
_VALIDATE = _ANALYZE | frozenset({"validate"})
_PARTNER = _VALIDATE | frozenset({"partner"})
PLAN_FEATURES = {
    "explore": _EXPLORE,
    "analyze": _ANALYZE,
    "validate": _VALIDATE,
    "partner": _PARTNER,
}
PILOT_FEATURES = _PARTNER
KINDS = frozenset({"upgrade", "downgrade", "cancel", "renew"})
_EVENT_ID = re.compile(r"^[A-Za-z0-9_-]{8,80}$")
_FORBIDDEN = frozenset({"card", "card_number", "pan", "cvv", "cvc", "payment_method"})
_MAX_BODY = 4000


class CommercialError(RuntimeError):
    """A rejected billing event reduced to a category."""

    def __init__(self, category: str) -> None:
        self.category = category
        super().__init__(f"billing event rejected: {category}")


def simulation_enabled() -> bool:
    """True only when this process is explicitly running the local billing simulation."""
    return os.environ.get("RUGD_BILLING_SIMULATION", "").strip() == "1"


def webhook_secret() -> str:
    return os.environ.get("RUGD_BILLING_WEBHOOK_SECRET", "")


def ai_quota() -> int:
    return _configured_limit("RUGD_AI_REPLY_QUOTA", 40, 1, 500)


def retrieval_quota() -> int:
    return _configured_limit("RUGD_RETRIEVAL_QUOTA", account_batch_limit(), 1, 40)


def _configured_limit(name: str, default: int, low: int, high: int) -> int:
    raw = os.environ.get(name, "").strip()
    if not raw.isdigit():
        return default
    value = int(raw)
    if value < low or value > high:
        return default
    return value


def current_period() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m")


def account_access(connection: sqlite3.Connection, user_id: str) -> dict[str, Any]:
    """Effective access. The included pilot keeps every current prototype feature."""
    row = _entitlement(connection, user_id)
    if row is not None and row["status"] == "simulated_active" and row["plan_id"] in PLAN_FEATURES:
        plan_id = str(row["plan_id"])
        return {
            "plan_id": plan_id,
            "status": "simulated_active",
            "paid": False,
            "simulated": True,
            "features": PLAN_FEATURES[plan_id],
            "label": f"Simulated {plan_id}",
        }
    return {
        "plan_id": "pilot",
        "status": "included",
        "paid": False,
        "simulated": False,
        "features": PILOT_FEATURES,
        "label": "Included local pilot",
    }


def allows(connection: sqlite3.Connection, user_id: str, feature: str) -> bool:
    if not user_id:
        return True
    return feature in account_access(connection, user_id)["features"]


def meter_status(connection: sqlite3.Connection, user_id: str, meter: str) -> dict[str, int | bool]:
    quota = ai_quota() if meter == "ai_reply" else retrieval_quota()
    used = _used(connection, user_id, meter)
    return {"used": used, "quota": quota, "allowed": used < quota}


def meter_open(connection: sqlite3.Connection, user_id: str, meter: str) -> bool:
    return bool(meter_status(connection, user_id, meter)["allowed"])


def record_use(connection: sqlite3.Connection, user_id: str, meter: str) -> None:
    """Count one account-level use. A new project or session does not reset it."""
    if not user_id or meter not in {"ai_reply", "public_retrieval"}:
        return
    period = current_period()
    connection.execute(
        """
        INSERT INTO usage_meters (user_id, meter, period, used)
        VALUES (?, ?, ?, 1)
        ON CONFLICT(user_id, meter, period) DO UPDATE SET used = used + 1
        """,
        (user_id, meter, period),
    )
    connection.commit()


def usage_summary(connection: sqlite3.Connection, user_id: str) -> dict[str, Any]:
    access = account_access(connection, user_id)
    events = [
        {
            "event_id": str(row["event_id"]),
            "kind": str(row["kind"]),
            "plan_id": str(row["plan_id"]),
            "applied": bool(row["applied"]),
            "detail": str(row["detail"]),
        }
        for row in connection.execute(
            """
            SELECT event_id, kind, plan_id, applied, detail
            FROM billing_events
            WHERE user_id = ?
            ORDER BY received_at, event_id
            """,
            (user_id,),
        )
    ]
    return {
        "access": access,
        "ai_reply": meter_status(connection, user_id, "ai_reply"),
        "public_retrieval": meter_status(connection, user_id, "public_retrieval"),
        "events": events,
    }


def sign_body(body: bytes, secret: str) -> str:
    return hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()


def verify_signature(body: bytes, signature: str) -> bool:
    secret = webhook_secret()
    presented = (signature or "").strip()
    if not secret or not presented:
        return False
    return hmac.compare_digest(sign_body(body, secret), presented)


def accept_webhook(connection: sqlite3.Connection, body: bytes, signature: str) -> dict[str, Any]:
    """Verify a mock provider body and record the event. A bad signature is not stored."""
    if len(body) > _MAX_BODY or not verify_signature(body, signature):
        raise CommercialError("signature")
    try:
        payload = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise CommercialError("not_allowed") from exc
    if not isinstance(payload, dict) or _forbidden(payload):
        raise CommercialError("not_allowed")
    return apply_event(connection, payload)


def apply_event(connection: sqlite3.Connection, payload: dict[str, Any]) -> dict[str, Any]:
    event_id = str(payload.get("event_id") or "")
    user_id = str(payload.get("user_id") or "")
    kind = str(payload.get("kind") or "")
    plan_id = str(payload.get("plan_id") or "")
    sequence = payload.get("sequence")
    if (
        not _EVENT_ID.fullmatch(event_id)
        or not _EVENT_ID.fullmatch(user_id)
        or kind not in KINDS
        or plan_id not in PLAN_FEATURES
        or not isinstance(sequence, int)
        or isinstance(sequence, bool)
        or sequence < 1
        or sequence > 1_000_000
    ):
        raise CommercialError("not_allowed")
    existing = _event(connection, event_id)
    if existing is not None:
        return {"category": "duplicate", "applied": bool(existing["applied"])}
    if get_user_by_id(connection, user_id) is None:
        _store_event(connection, event_id, user_id, kind, plan_id, sequence, False, "unknown_account")
        return {"category": "unknown_account", "applied": False}
    if not simulation_enabled():
        _store_event(connection, event_id, user_id, kind, plan_id, sequence, False, "billing_disabled")
        _audit(connection, user_id, "billing_disabled")
        return {"category": "billing_disabled", "applied": False}
    current = _entitlement(connection, user_id)
    last_sequence = int(current["sequence"]) if current is not None else 0
    if sequence <= last_sequence:
        _store_event(connection, event_id, user_id, kind, plan_id, sequence, False, "out_of_order")
        _audit(connection, user_id, "out_of_order")
        return {"category": "out_of_order", "applied": False}
    status = "simulated_canceled" if kind == "cancel" else "simulated_active"
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    try:
        connection.execute(
            """
            INSERT INTO account_entitlements (user_id, plan_id, status, sequence, updated_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                plan_id = excluded.plan_id,
                status = excluded.status,
                sequence = excluded.sequence,
                updated_at = excluded.updated_at
            """,
            (user_id, plan_id, status, sequence, now),
        )
        _insert_event(connection, event_id, user_id, kind, plan_id, sequence, True, kind)
        connection.commit()
    except sqlite3.IntegrityError:
        connection.rollback()
        return {"category": "duplicate", "applied": False}
    _audit(connection, user_id, f"{kind}:{plan_id}")
    return {"category": "applied", "applied": True}


def usage_page(connection: sqlite3.Connection, user_id: str) -> str:
    from app.pages import layout

    summary = usage_summary(connection, user_id)
    access = summary["access"]
    ai = summary["ai_reply"]
    retrieval = summary["public_retrieval"]
    rows = "".join(
        "<li>"
        f"{escape(item['kind'])} {escape(item['plan_id'])}: "
        f"{'recorded and applied in simulation' if item['applied'] else 'recorded and not applied'} "
        f"({escape(item['detail'])})"
        "</li>"
        for item in summary["events"]
    ) or "<li>No billing events are stored for this account.</li>"
    body = f"""
<h1>Usage</h1>
<p>Plan: {escape(str(access['label']))}. This is not a paid subscription. No charge is created. A simulated plan does not grant investor-ready status.</p>
<p>The plans named for this pilot are Explore, Analyze, Validate, and Partner. Prices, contracts, and a payment provider are not set. The included local pilot keeps the access this prototype already offers.</p>
<ul>
<li>Adviser replies this month: {int(ai['used'])} of {int(ai['quota'])}. The count stays with this account. A new session does not reset it.</li>
<li>Public retrievals this month: {int(retrieval['used'])} of {int(retrieval['quota'])}. The count stays with this account. A new project does not reset it.</li>
</ul>
<h2>Billing events</h2>
<ul>{rows}</ul>
<p class="muted">Production billing is disabled. A mock event is not a real entitlement. Billing hooks remain disabled and create no charge.</p>
"""
    return layout("Usage", body, active="/settings")


def _forbidden(value: Any) -> bool:
    if isinstance(value, dict):
        return any(str(key).lower() in _FORBIDDEN or _forbidden(item) for key, item in value.items())
    if isinstance(value, list):
        return any(_forbidden(item) for item in value)
    return False


def _entitlement(connection: sqlite3.Connection, user_id: str) -> sqlite3.Row | None:
    return connection.execute(
        "SELECT user_id, plan_id, status, sequence FROM account_entitlements WHERE user_id = ?",
        (user_id,),
    ).fetchone()


def _event(connection: sqlite3.Connection, event_id: str) -> sqlite3.Row | None:
    return connection.execute(
        "SELECT event_id, applied, detail FROM billing_events WHERE event_id = ?",
        (event_id,),
    ).fetchone()


def _used(connection: sqlite3.Connection, user_id: str, meter: str) -> int:
    row = connection.execute(
        "SELECT used FROM usage_meters WHERE user_id = ? AND meter = ? AND period = ?",
        (user_id, meter, current_period()),
    ).fetchone()
    return int(row["used"]) if row is not None else 0


def _store_event(
    connection: sqlite3.Connection,
    event_id: str,
    user_id: str,
    kind: str,
    plan_id: str,
    sequence: int,
    applied: bool,
    detail: str,
) -> None:
    try:
        _insert_event(connection, event_id, user_id, kind, plan_id, sequence, applied, detail)
        connection.commit()
    except sqlite3.IntegrityError:
        connection.rollback()


def _insert_event(
    connection: sqlite3.Connection,
    event_id: str,
    user_id: str,
    kind: str,
    plan_id: str,
    sequence: int,
    applied: bool,
    detail: str,
) -> None:
    connection.execute(
        """
        INSERT INTO billing_events (
            event_id, user_id, kind, plan_id, sequence, received_at, applied, detail
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            event_id,
            user_id,
            kind,
            plan_id,
            sequence,
            datetime.now(timezone.utc).isoformat(timespec="seconds"),
            1 if applied else 0,
            detail[:120],
        ),
    )


def _audit(connection: sqlite3.Connection, user_id: str, detail: str) -> None:
    record_audit_event(
        connection,
        action="billing_event",
        actor_id=user_id,
        session_token="",
        detail=detail[:120],
    )

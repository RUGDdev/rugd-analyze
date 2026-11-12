"""Advisory records kept apart from the assessment profile.

Saved scenarios, suggestion decisions, customer-cited benchmarks, and the proposed
revenue worksheet live here. None of them is an assumption the official engine
reads. Every query is scoped to one assessment id that the caller has already
authorized.
"""

from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import datetime, timezone
from typing import Any

KINDS = ("scenario", "decision", "benchmark_entry", "revenue_worksheet")
_LIMITS = {"scenario": 12, "decision": 300, "benchmark_entry": 40, "revenue_worksheet": 1}
_KEYED = {"decision", "revenue_worksheet"}
MAX_PAYLOAD_CHARS = 24_000


class AdvisoryLimit(ValueError):
    """The record is too large or the saved count is at its limit."""


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _row(row: sqlite3.Row) -> dict[str, Any]:
    try:
        payload = json.loads(row["payload_json"] or "{}")
    except json.JSONDecodeError:
        payload = {}
    return {
        "id": row["id"],
        "assessment_id": row["assessment_id"],
        "created_by": row["created_by"],
        "kind": row["kind"],
        "key": row["record_key"],
        "title": row["title"],
        "payload": payload if isinstance(payload, dict) else {},
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def list_records(connection: sqlite3.Connection, assessment_id: str, kind: str) -> list[dict[str, Any]]:
    rows = connection.execute(
        """
        SELECT * FROM advisory_records
        WHERE assessment_id = ? AND kind = ?
        ORDER BY created_at, id
        """,
        (assessment_id, kind),
    ).fetchall()
    return [_row(row) for row in rows]


def get_record(connection: sqlite3.Connection, assessment_id: str, record_id: str) -> dict[str, Any] | None:
    row = connection.execute(
        "SELECT * FROM advisory_records WHERE id = ? AND assessment_id = ?",
        (record_id, assessment_id),
    ).fetchone()
    return None if row is None else _row(row)


def save_record(
    connection: sqlite3.Connection,
    *,
    assessment_id: str,
    created_by: str,
    kind: str,
    payload: dict[str, Any],
    title: str = "",
    record_key: str = "",
) -> dict[str, Any]:
    """Insert a record. A keyed kind replaces the earlier record with the same key."""
    if kind not in KINDS:
        raise ValueError(f"unknown advisory kind: {kind}")
    text = json.dumps(payload, sort_keys=True)
    if len(text) > MAX_PAYLOAD_CHARS:
        raise AdvisoryLimit("This record is too large to save.")
    now = _now()
    if kind in _KEYED and record_key:
        existing = connection.execute(
            "SELECT id, created_at FROM advisory_records WHERE assessment_id = ? AND kind = ? AND record_key = ?",
            (assessment_id, kind, record_key),
        ).fetchone()
        if existing is not None:
            connection.execute(
                "UPDATE advisory_records SET payload_json = ?, title = ?, updated_at = ?, created_by = ? WHERE id = ?",
                (text, title[:160], now, created_by, existing["id"]),
            )
            connection.commit()
            stored = get_record(connection, assessment_id, existing["id"])
            assert stored is not None
            return stored
    count = connection.execute(
        "SELECT COUNT(*) FROM advisory_records WHERE assessment_id = ? AND kind = ?",
        (assessment_id, kind),
    ).fetchone()[0]
    if count >= _LIMITS[kind]:
        raise AdvisoryLimit(f"This assessment already has the most saved {kind.replace('_', ' ')} records allowed.")
    record_id = str(uuid.uuid4())
    connection.execute(
        """
        INSERT INTO advisory_records (
            id, assessment_id, created_by, kind, record_key, title, payload_json, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (record_id, assessment_id, created_by, kind, record_key[:120], title[:160], text, now, now),
    )
    connection.commit()
    stored = get_record(connection, assessment_id, record_id)
    assert stored is not None
    return stored


def update_payload(
    connection: sqlite3.Connection, assessment_id: str, record_id: str, payload: dict[str, Any]
) -> dict[str, Any] | None:
    text = json.dumps(payload, sort_keys=True)
    if len(text) > MAX_PAYLOAD_CHARS:
        raise AdvisoryLimit("This record is too large to save.")
    connection.execute(
        "UPDATE advisory_records SET payload_json = ?, updated_at = ? WHERE id = ? AND assessment_id = ?",
        (text, _now(), record_id, assessment_id),
    )
    connection.commit()
    return get_record(connection, assessment_id, record_id)


def delete_record(connection: sqlite3.Connection, assessment_id: str, record_id: str) -> bool:
    cursor = connection.execute(
        "DELETE FROM advisory_records WHERE id = ? AND assessment_id = ?",
        (record_id, assessment_id),
    )
    connection.commit()
    return cursor.rowcount > 0


def decisions(connection: sqlite3.Connection, assessment_id: str) -> dict[str, dict[str, Any]]:
    """Latest decision for each suggestion id."""
    return {item["key"]: item["payload"] for item in list_records(connection, assessment_id, "decision")}

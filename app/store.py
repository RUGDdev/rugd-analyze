"""Local SQLite drafts for RUGD Analyze. data/ is gitignored."""

from __future__ import annotations

import hashlib
import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DB = ROOT / "data" / "analyze.sqlite"
SAMPLE = ROOT / "intake" / "samples" / "rugd_intelligence.json"

BASELINE_ID = "rugd-intelligence-baseline"
RESTAURANT_ID = "hypothetical-restaurant"
RESTAURANT_VERIFIED_ID = "hypothetical-restaurant-verified-demand"
HYPOTHETICAL_DEMO_LABEL = "Hypothetical demonstration — not a real assessment."
VERIFIED_DEMO_LABEL = (
    "Verified-demand demonstration — not a real assessment. Not the official baseline."
)
# App labels only. Scoring and the 0.1 engine do not read these names.
NAMED_PILOT_NAMES = frozenset({"Bunny Hive", "The Bunny Hive", "Small Town Pub"})
NAMED_PILOT_LABEL = (
    "Named-pilot draft. Not a completed assessment. "
    "Only RUGD Intelligence is the official baseline."
)
CUSTOMER_DRAFT_LABEL = "Customer draft. Not a completed assessment."
_EMPTY_PILOT_FIELDS = (
    "concept",
    "industry",
    "market",
    "stage",
    "products",
    "customers",
    "competition",
    "demand_evidence",
    "verified_record_source",
    "verified_revenue_trailing_12m",
    "verified_demand_evidence",
    "verified_demand_rationale",
    "operator_capacity_adequate",
    "unresolved_regulatory_or_liability",
    "extraction_without_reinvestment",
    "construction_cost",
    "equipment",
    "soft_costs",
    "preopening_working_capital",
    "seats",
    "average_ticket",
    "weekday_occupancy",
    "weekend_occupancy",
    "operating_days",
    "annual_fixed_costs",
    "contribution_margin",
    "initial_capital",
    "monthly_fixed_costs",
    "gross_margin_pct",
    "projected_monthly_revenue_base",
    "evidence_notes",
)

FORBIDDEN_PROFILE_KEYS = frozenset(
    {"human_review_approved", "is_final", "investor_ready", "source"}
)


def connect(path: Path = DEFAULT_DB) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS assessments (
            id TEXT PRIMARY KEY,
            business_name TEXT NOT NULL,
            purpose TEXT NOT NULL,
            tier TEXT NOT NULL,
            read_only INTEGER NOT NULL,
            hypothetical INTEGER NOT NULL,
            pilot_label TEXT NOT NULL,
            profile_json TEXT NOT NULL,
            intake_json TEXT,
            result_json TEXT,
            review_requested INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS review_approvals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            assessment_id TEXT NOT NULL,
            reviewer_identity TEXT NOT NULL,
            approved_at TEXT NOT NULL,
            note TEXT NOT NULL,
            authentication_method TEXT NOT NULL DEFAULT 'local-prototype-gate'
        )
        """
    )
    approval_columns = {
        row[1] for row in connection.execute("PRAGMA table_info(review_approvals)")
    }
    if "authentication_method" not in approval_columns:
        connection.execute(
            "ALTER TABLE review_approvals ADD COLUMN authentication_method TEXT NOT NULL DEFAULT 'local-prototype-gate'"
        )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS reviewer_sessions (
            token TEXT PRIMARY KEY,
            reviewer_identity TEXT NOT NULL,
            role TEXT NOT NULL,
            authentication_method TEXT NOT NULL,
            created_at TEXT NOT NULL,
            expires_at TEXT NOT NULL
        )
        """
    )
    session_columns = {
        row[1] for row in connection.execute("PRAGMA table_info(reviewer_sessions)")
    }
    if "expires_at" not in session_columns:
        connection.execute("ALTER TABLE reviewer_sessions ADD COLUMN expires_at TEXT")
        connection.execute(
            "UPDATE reviewer_sessions SET expires_at = created_at WHERE expires_at IS NULL"
        )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS reviewer_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            action TEXT NOT NULL,
            assessment_id TEXT,
            reviewer_identity TEXT NOT NULL,
            recorded_at TEXT NOT NULL,
            authentication_method TEXT,
            session_id TEXT NOT NULL,
            note TEXT NOT NULL
        )
        """
    )
    return connection


def seed(connection: sqlite3.Connection) -> None:
    if get_assessment(connection, BASELINE_ID) is None:
        intake = json.loads(SAMPLE.read_text(encoding="utf-8"))
        profile = {
            "business_name": intake["business_name"],
            "purpose": intake["engagement_type"],
            "tier": "analyze",
            "concept": intake.get("description", ""),
            "industry": "",
            "market": "",
            "stage": "Pilot baseline",
            "read_only_note": (
                "Official 0.1 baseline. This screen does not edit the sample file."
            ),
        }
        _insert(
            connection,
            assessment_id=BASELINE_ID,
            business_name=intake["business_name"],
            purpose=intake["engagement_type"],
            tier="analyze",
            read_only=True,
            hypothetical=False,
            pilot_label="Official baseline. Not a completed customer study.",
            profile=profile,
            intake=intake,
        )
    _ensure_restaurant_demo(connection, verified_demand=False)
    _ensure_restaurant_demo(connection, verified_demand=True)


def restaurant_demonstration_profile(*, verified_demand: bool) -> dict[str, Any]:
    """Shared hypothetical restaurant figures. Demand stays unanswered unless verified_demand is set.

    A verified demonstration is not marked hypothetical, because a hypothetical
    demonstration does not apply a verified demand record.
    """
    name = (
        "Hypothetical Restaurant — verified demand demonstration"
        if verified_demand
        else "Hypothetical Restaurant Startup"
    )
    concept = (
        "Hypothetical demonstration — not a real assessment. "
        "Seat, ticket, occupancy, and cost-build figures are invented for the Explore-to-Analyze path. "
        "They are not market research and not a real operating business. "
    )
    if verified_demand:
        concept += (
            "This variant adds a verified demand_evidence record under the documented rule. "
            "Clearing that flag does not approve the assessment or make it investor-ready."
        )
    else:
        concept += "Demand evidence is left unanswered, so the insufficient-demand flag stays on."
    profile = blank_profile(
        business_name=name,
        purpose="startup_feasibility",
        tier="explore",
    )
    profile.update(
        {
            "concept": concept,
            "industry": "Restaurant",
            "stage": "Idea",
            "market": "Unspecified demonstration market",
            "products": "Hypothetical lunch and dinner service.",
            "customers": "Hypothetical neighborhood diners.",
            "competition": "Not researched. Placeholder for the demonstration.",
            "demand_evidence": "",
            "construction_cost": "100000",
            "equipment": "35000",
            "soft_costs": "15000",
            "preopening_working_capital": "20000",
            "seats": "48",
            "average_ticket": "28",
            "weekday_occupancy": "0.45",
            "weekend_occupancy": "0.70",
            "operating_days": "312",
            "contribution_margin": "0.35",
            "annual_fixed_costs": "240000",
            "initial_capital": "180000",
            "monthly_fixed_costs": "18000",
            "gross_margin_pct": "0.58",
            "projected_monthly_revenue_base": "42000",
            "inputs_are_measured": False,
            "hypothetical": not verified_demand,
        }
    )
    if verified_demand:
        profile.update(
            {
                "verified_record_source": "verified",
                "verified_demand_evidence": "true",
                "verified_revenue_trailing_12m": "",
                "verified_demand_rationale": (
                    "Demonstration of the documented rule: boolean demand_evidence true "
                    "with source verified and a rationale. Not market research and not a real customer file."
                ),
            }
        )
    return profile


def _ensure_restaurant_demo(connection: sqlite3.Connection, *, verified_demand: bool) -> None:
    assessment_id = RESTAURANT_VERIFIED_ID if verified_demand else RESTAURANT_ID
    profile = restaurant_demonstration_profile(verified_demand=verified_demand)
    label = VERIFIED_DEMO_LABEL if verified_demand else HYPOTHETICAL_DEMO_LABEL
    current = get_assessment(connection, assessment_id)
    if current is None:
        _insert(
            connection,
            assessment_id=assessment_id,
            business_name=profile["business_name"],
            purpose=profile["purpose"],
            tier="explore",
            read_only=False,
            hypothetical=not verified_demand,
            pilot_label=label,
            profile=profile,
            intake=None,
        )
        return
    if current["read_only"] or current["id"] == BASELINE_ID:
        return
    if verified_demand or str((current.get("profile") or {}).get("seats") or "").strip():
        return
    now = _now()
    connection.execute(
        """
        UPDATE assessments
        SET business_name = ?, purpose = ?, tier = ?, hypothetical = ?, pilot_label = ?,
            profile_json = ?, intake_json = NULL, result_json = NULL, updated_at = ?
        WHERE id = ?
        """,
        (
            profile["business_name"],
            profile["purpose"],
            "explore",
            1,
            label,
            json.dumps(profile),
            now,
            assessment_id,
        ),
    )
    connection.commit()


def blank_profile(*, business_name: str, purpose: str, tier: str) -> dict[str, Any]:
    return {
        "business_name": business_name,
        "purpose": purpose,
        "tier": tier,
        "concept": "",
        "industry": "",
        "market": "",
        "stage": "",
        "products": "",
        "customers": "",
        "competition": "",
        "demand_evidence": "",
        "verified_record_source": "",
        "verified_revenue_trailing_12m": "",
        "verified_demand_evidence": "",
        "verified_demand_rationale": "",
        "operator_capacity_adequate": "",
        "unresolved_regulatory_or_liability": "",
        "extraction_without_reinvestment": "",
        "construction_cost": "",
        "equipment": "",
        "soft_costs": "",
        "preopening_working_capital": "",
        "contingency_pct": "0.10",
        "debt_share": "0.70",
        "annual_interest_rate": "0.08",
        "amortization_years": "20",
        "seats": "",
        "average_ticket": "",
        "weekday_occupancy": "",
        "weekend_occupancy": "",
        "operating_days": "",
        "annual_fixed_costs": "",
        "contribution_margin": "",
        "downside_multiplier": "0.6",
        "initial_capital": "",
        "monthly_fixed_costs": "",
        "gross_margin_pct": "",
        "projected_monthly_revenue_base": "",
        "inputs_are_measured": False,
        "hypothetical": False,
        "evidence_notes": "",
    }


def label_for_new_assessment(business_name: str) -> str:
    """Choose a display label. This does not score the draft or edit the baseline."""
    if business_name.strip() in NAMED_PILOT_NAMES:
        return NAMED_PILOT_LABEL
    return CUSTOMER_DRAFT_LABEL


def is_named_pilot(record: dict[str, Any]) -> bool:
    if record.get("read_only") or record.get("id") == BASELINE_ID:
        return False
    return record.get("pilot_label") == NAMED_PILOT_LABEL


def named_pilot_is_empty(record: dict[str, Any]) -> bool:
    profile = record.get("profile") or {}
    return all(not str(profile.get(key) or "").strip() for key in _EMPTY_PILOT_FIELDS)


def create_assessment(
    connection: sqlite3.Connection,
    *,
    business_name: str,
    purpose: str,
    tier: str,
    pilot_label: str = "Customer draft. Not a completed assessment.",
    hypothetical: bool = False,
) -> str:
    profile = blank_profile(business_name=business_name, purpose=purpose, tier=tier)
    profile["hypothetical"] = hypothetical
    assessment_id = uuid.uuid4().hex
    _insert(
        connection,
        assessment_id=assessment_id,
        business_name=business_name,
        purpose=purpose,
        tier=tier,
        read_only=False,
        hypothetical=hypothetical,
        pilot_label=pilot_label,
        profile=profile,
        intake=None,
    )
    return assessment_id


def list_assessments(connection: sqlite3.Connection) -> list[dict[str, Any]]:
    rows = connection.execute(
        "SELECT * FROM assessments ORDER BY updated_at DESC"
    ).fetchall()
    return [_attach_approval(connection, _public_row(row)) for row in rows]


def get_assessment(connection: sqlite3.Connection, assessment_id: str) -> dict[str, Any] | None:
    row = connection.execute(
        "SELECT * FROM assessments WHERE id = ?", (assessment_id,)
    ).fetchone()
    if row is None:
        return None
    return _attach_approval(connection, _public_row(row))


def save_profile(
    connection: sqlite3.Connection, assessment_id: str, profile: dict[str, Any]
) -> dict[str, Any]:
    current = get_assessment(connection, assessment_id)
    if current is None:
        raise KeyError(assessment_id)
    if current["read_only"]:
        raise PermissionError("This assessment is read-only.")
    clean = {key: value for key, value in profile.items() if key not in FORBIDDEN_PROFILE_KEYS}
    clean["human_review_approved"] = False
    if current["hypothetical"]:
        clean["hypothetical"] = True
    tier = clean.get("tier") or current["tier"]
    if tier not in ("explore", "analyze", "validate", "partner"):
        tier = current["tier"]
    clean["tier"] = tier
    now = _now()
    connection.execute(
        """
        UPDATE assessments
        SET business_name = ?, purpose = ?, tier = ?, hypothetical = ?,
            profile_json = ?, updated_at = ?
        WHERE id = ?
        """,
        (
            str(clean.get("business_name") or current["business_name"]),
            str(clean.get("purpose") or current["purpose"]),
            tier,
            1 if clean.get("hypothetical") is True else 0,
            json.dumps(clean),
            now,
            assessment_id,
        ),
    )
    connection.commit()
    saved = get_assessment(connection, assessment_id)
    assert saved is not None
    return saved


def save_result(
    connection: sqlite3.Connection,
    assessment_id: str,
    intake: dict[str, Any] | None,
    result: dict[str, Any],
) -> None:
    connection.execute(
        """
        UPDATE assessments
        SET intake_json = ?, result_json = ?, updated_at = ?
        WHERE id = ?
        """,
        (
            None if intake is None else json.dumps(intake),
            json.dumps(result),
            _now(),
            assessment_id,
        ),
    )
    connection.commit()


def request_review(connection: sqlite3.Connection, assessment_id: str) -> dict[str, Any]:
    current = get_assessment(connection, assessment_id)
    if current is None:
        raise KeyError(assessment_id)
    connection.execute(
        "UPDATE assessments SET review_requested = 1, updated_at = ? WHERE id = ?",
        (_now(), assessment_id),
    )
    connection.commit()
    saved = get_assessment(connection, assessment_id)
    assert saved is not None
    return saved


def _insert(
    connection: sqlite3.Connection,
    *,
    assessment_id: str,
    business_name: str,
    purpose: str,
    tier: str,
    read_only: bool,
    hypothetical: bool,
    pilot_label: str,
    profile: dict[str, Any],
    intake: dict[str, Any] | None,
) -> None:
    now = _now()
    connection.execute(
        """
        INSERT INTO assessments (
            id, business_name, purpose, tier, read_only, hypothetical, pilot_label,
            profile_json, intake_json, result_json, review_requested, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, NULL, 0, ?, ?)
        """,
        (
            assessment_id,
            business_name,
            purpose,
            tier,
            1 if read_only else 0,
            1 if hypothetical else 0,
            pilot_label,
            json.dumps(profile),
            None if intake is None else json.dumps(intake),
            now,
            now,
        ),
    )
    connection.commit()


def record_approval(
    connection: sqlite3.Connection,
    assessment_id: str,
    *,
    reviewer_identity: str,
    note: str,
    authentication_method: str,
) -> dict[str, Any]:
    approved_at = _now()
    connection.execute(
        """
        INSERT INTO review_approvals (
            assessment_id, reviewer_identity, approved_at, note, authentication_method
        )
        VALUES (?, ?, ?, ?, ?)
        """,
        (assessment_id, reviewer_identity, approved_at, note, authentication_method),
    )
    connection.commit()
    approval = latest_approval(connection, assessment_id)
    assert approval is not None
    return approval


def _approval_from_row(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "assessment_id": row["assessment_id"],
        "reviewer_identity": row["reviewer_identity"],
        "approved_at": row["approved_at"],
        "action": "approve",
        "authentication_method": row["authentication_method"],
        "note": row["note"],
    }


def latest_approval(connection: sqlite3.Connection, assessment_id: str) -> dict[str, Any] | None:
    row = connection.execute(
        """
        SELECT assessment_id, reviewer_identity, approved_at, note, authentication_method
        FROM review_approvals
        WHERE assessment_id = ?
        ORDER BY id DESC
        LIMIT 1
        """,
        (assessment_id,),
    ).fetchone()
    if row is None:
        return None
    return _approval_from_row(row)


def list_approvals(connection: sqlite3.Connection, assessment_id: str) -> list[dict[str, Any]]:
    rows = connection.execute(
        """
        SELECT assessment_id, reviewer_identity, approved_at, note, authentication_method
        FROM review_approvals
        WHERE assessment_id = ?
        ORDER BY id
        """,
        (assessment_id,),
    ).fetchall()
    return [_approval_from_row(row) for row in rows]


def session_public_id(token: str) -> str:
    """Short hash for audit display. The raw session token stays out of the trail."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()[:12]


def record_reviewer_event(
    connection: sqlite3.Connection,
    *,
    action: str,
    reviewer_identity: str,
    session_token: str,
    authentication_method: str | None,
    assessment_id: str | None = None,
    note: str = "",
) -> dict[str, Any]:
    recorded_at = _now()
    session_id = session_public_id(session_token)
    connection.execute(
        """
        INSERT INTO reviewer_events (
            action, assessment_id, reviewer_identity, recorded_at,
            authentication_method, session_id, note
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            action,
            assessment_id,
            reviewer_identity,
            recorded_at,
            authentication_method,
            session_id,
            note,
        ),
    )
    connection.commit()
    row = connection.execute(
        """
        SELECT action, assessment_id, reviewer_identity, recorded_at,
               authentication_method, session_id, note
        FROM reviewer_events
        WHERE id = last_insert_rowid()
        """
    ).fetchone()
    assert row is not None
    return _event_from_row(row)


def list_reviewer_events(
    connection: sqlite3.Connection,
    assessment_id: str | None = None,
) -> list[dict[str, Any]]:
    if assessment_id is None:
        rows = connection.execute(
            """
            SELECT action, assessment_id, reviewer_identity, recorded_at,
                   authentication_method, session_id, note
            FROM reviewer_events
            ORDER BY id
            """
        ).fetchall()
    else:
        rows = connection.execute(
            """
            SELECT action, assessment_id, reviewer_identity, recorded_at,
                   authentication_method, session_id, note
            FROM reviewer_events
            WHERE assessment_id IS NULL OR assessment_id = ?
            ORDER BY id
            """,
            (assessment_id,),
        ).fetchall()
    return [_event_from_row(row) for row in rows]


def session_activity(connection: sqlite3.Connection) -> dict[str, str | None]:
    return {
        "last_sign_in": _latest_event_time(connection, "sign-in"),
        "last_sign_out": _latest_event_time(connection, "sign-out"),
    }


def _latest_event_time(connection: sqlite3.Connection, action: str) -> str | None:
    row = connection.execute(
        """
        SELECT recorded_at FROM reviewer_events
        WHERE action = ?
        ORDER BY id DESC
        LIMIT 1
        """,
        (action,),
    ).fetchone()
    if row is None:
        return None
    return row["recorded_at"]


def _event_from_row(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "action": row["action"],
        "assessment_id": row["assessment_id"],
        "reviewer_identity": row["reviewer_identity"],
        "recorded_at": row["recorded_at"],
        "authentication_method": row["authentication_method"],
        "session_id": row["session_id"],
        "note": row["note"],
    }


def start_reviewer_session(
    connection: sqlite3.Connection,
    *,
    token: str,
    reviewer_identity: str,
    authentication_method: str,
    expires_at: str,
) -> dict[str, Any]:
    created_at = _now()
    connection.execute(
        """
        INSERT INTO reviewer_sessions (
            token, reviewer_identity, role, authentication_method, created_at, expires_at
        )
        VALUES (?, ?, 'reviewer', ?, ?, ?)
        """,
        (token, reviewer_identity, authentication_method, created_at, expires_at),
    )
    connection.commit()
    session = get_reviewer_session(connection, token)
    assert session is not None
    return session


def load_reviewer_session(connection: sqlite3.Connection, token: str) -> dict[str, Any] | None:
    if not token:
        return None
    row = connection.execute(
        """
        SELECT token, reviewer_identity, role, authentication_method, created_at, expires_at
        FROM reviewer_sessions
        WHERE token = ?
        """,
        (token,),
    ).fetchone()
    if row is None:
        return None
    return {
        "token": row["token"],
        "reviewer_identity": row["reviewer_identity"],
        "role": row["role"],
        "authentication_method": row["authentication_method"],
        "created_at": row["created_at"],
        "expires_at": row["expires_at"],
    }


def get_reviewer_session(connection: sqlite3.Connection, token: str) -> dict[str, Any] | None:
    loaded = load_reviewer_session(connection, token)
    if loaded is None or loaded["role"] != "reviewer":
        return None
    remaining = _remaining_seconds(loaded.get("expires_at"))
    if remaining is None or remaining <= 0:
        return None
    loaded["remaining_seconds"] = remaining
    loaded["state"] = "signed-in"
    loaded["active"] = True
    return loaded


def end_reviewer_session(connection: sqlite3.Connection, token: str) -> None:
    if not token:
        return
    connection.execute("DELETE FROM reviewer_sessions WHERE token = ?", (token,))
    connection.commit()


def _remaining_seconds(expires_at: str | None) -> int | None:
    if not expires_at:
        return None
    try:
        expires = datetime.fromisoformat(expires_at)
    except ValueError:
        return None
    if expires.tzinfo is None:
        expires = expires.replace(tzinfo=timezone.utc)
    return int((expires - datetime.now(timezone.utc)).total_seconds())


def _attach_approval(connection: sqlite3.Connection, record: dict[str, Any]) -> dict[str, Any]:
    approval = None if record["read_only"] else latest_approval(connection, record["id"])
    record["review_approval"] = approval
    record["human_review_approved"] = approval is not None
    return record


def _public_row(row: sqlite3.Row) -> dict[str, Any]:
    profile = json.loads(row["profile_json"])
    profile.pop("human_review_approved", None)
    intake = json.loads(row["intake_json"]) if row["intake_json"] else None
    result = json.loads(row["result_json"]) if row["result_json"] else None
    return {
        "id": row["id"],
        "business_name": row["business_name"],
        "purpose": row["purpose"],
        "tier": row["tier"],
        "read_only": bool(row["read_only"]),
        "hypothetical": bool(row["hypothetical"]),
        "pilot_label": row["pilot_label"],
        "profile": profile,
        "intake": intake,
        "result": result,
        "review_requested": bool(row["review_requested"]),
        "human_review_approved": False,
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()

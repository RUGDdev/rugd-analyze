"""Local SQLite drafts for RUGD Analyze. data/ is gitignored."""

from __future__ import annotations

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
    if get_assessment(connection, RESTAURANT_ID) is None:
        profile = blank_profile(
            business_name="Hypothetical Restaurant Startup",
            purpose="startup_feasibility",
            tier="explore",
        )
        profile.update(
            {
                "concept": (
                    "Hypothetical demonstration for the Explore-to-Analyze journey. "
                    "Not market research and not a real operating business."
                ),
                "industry": "Restaurant",
                "stage": "Idea",
                "market": "Unspecified demonstration market",
                "construction_cost": "100000",
                "hypothetical": True,
            }
        )
        _insert(
            connection,
            assessment_id=RESTAURANT_ID,
            business_name=profile["business_name"],
            purpose=profile["purpose"],
            tier="explore",
            read_only=False,
            hypothetical=True,
            pilot_label="Hypothetical. Every figure the customer did not type is a labeled demonstration value.",
            profile=profile,
            intake=None,
        )


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
    return [_public_row(row) for row in rows]


def get_assessment(connection: sqlite3.Connection, assessment_id: str) -> dict[str, Any] | None:
    row = connection.execute(
        "SELECT * FROM assessments WHERE id = ?", (assessment_id,)
    ).fetchone()
    if row is None:
        return None
    return _public_row(row)


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
    saved["human_review_approved"] = False
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

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
RESTAURANT_VERIFIED_ID = "hypothetical-restaurant-verified-demand"
BASELINE_PROFILE_ID = "business-profile-rugd-intelligence-baseline"
RESTAURANT_PROFILE_ID = "business-profile-hypothetical-restaurant"
RESTAURANT_VERIFIED_PROFILE_ID = "business-profile-hypothetical-restaurant-verified-demand"
ISOLATION_BASELINE = "baseline"
ISOLATION_PILOT = "pilot"
ISOLATION_CUSTOMER = "customer"
_STABLE_PROFILE_IDS = {
    BASELINE_ID: BASELINE_PROFILE_ID,
    RESTAURANT_ID: RESTAURANT_PROFILE_ID,
    RESTAURANT_VERIFIED_ID: RESTAURANT_VERIFIED_PROFILE_ID,
}
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
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            email TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS reviewer_sessions (
            token TEXT PRIMARY KEY,
            reviewer_identity TEXT NOT NULL,
            role TEXT NOT NULL,
            authentication_method TEXT NOT NULL,
            created_at TEXT NOT NULL,
            expires_at TEXT NOT NULL,
            user_id TEXT
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
    if "user_id" not in session_columns:
        connection.execute("ALTER TABLE reviewer_sessions ADD COLUMN user_id TEXT")
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
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS guidance_notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            assessment_id TEXT NOT NULL,
            pillar_id TEXT NOT NULL,
            note TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
        """
    )
    assessment_columns = {
        row[1] for row in connection.execute("PRAGMA table_info(assessments)")
    }
    if "business_profile_id" not in assessment_columns:
        connection.execute("ALTER TABLE assessments ADD COLUMN business_profile_id TEXT")
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS business_profiles (
            id TEXT PRIMARY KEY,
            display_name TEXT NOT NULL,
            industry TEXT NOT NULL,
            geography TEXT NOT NULL,
            stage TEXT NOT NULL,
            isolation TEXT NOT NULL,
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
    _ensure_restaurant_demo(connection, verified_demand=False)
    _ensure_restaurant_demo(connection, verified_demand=True)
    ensure_business_profiles(connection)
    from app.accounts import bootstrap_reviewer_from_environment

    bootstrap_reviewer_from_environment(connection)


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
    business_profile_id: str | None = None,
    from_link: bool = False,
) -> str:
    profile = blank_profile(business_name=business_name, purpose=purpose, tier=tier)
    profile["hypothetical"] = hypothetical
    if business_profile_id:
        business = get_business_profile(connection, business_profile_id)
        if business is None:
            raise KeyError(business_profile_id)
        if business["isolation"] == ISOLATION_BASELINE:
            raise PermissionError(
                "The official baseline profile cannot be linked to a draft."
            )
        if business["isolation"] == ISOLATION_PILOT and not from_link:
            raise PermissionError(
                "Named-pilot and demonstration profiles stay isolated."
            )
        profile["business_name"] = business["display_name"]
        profile["industry"] = business["industry"]
        profile["market"] = business["geography"]
        profile["stage"] = business["stage"]
        business_name = business["display_name"] or business_name
    else:
        business_profile_id = create_business_profile(
            connection,
            display_name=business_name,
            industry="",
            geography="",
            stage="",
            isolation=_isolation_for_new(business_name, pilot_label, hypothetical),
        )
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
        business_profile_id=business_profile_id,
    )
    return assessment_id


def create_linked_assessment(
    connection: sqlite3.Connection,
    assessment_id: str,
    *,
    tier: str,
    purpose: str | None = None,
) -> str:
    """Open another tier for the same business. Core fields are copied. Evidence is not."""
    source = get_assessment(connection, assessment_id)
    if source is None:
        raise KeyError(assessment_id)
    if source["read_only"] or source["id"] == BASELINE_ID:
        raise PermissionError(
            "The official baseline profile cannot be linked to a draft."
        )
    if not source.get("business_profile_id"):
        raise PermissionError("This draft has no business profile.")
    business = get_business_profile(connection, source["business_profile_id"])
    if business is None or business["isolation"] == ISOLATION_BASELINE:
        raise PermissionError(
            "The official baseline profile cannot be linked to a draft."
        )
    selected = tier if tier in ("explore", "analyze", "validate", "partner") else source["tier"]
    return create_assessment(
        connection,
        business_name=str(business["display_name"] or source["business_name"]),
        purpose=purpose or source["purpose"],
        tier=selected,
        pilot_label=source["pilot_label"],
        hypothetical=bool(source["hypothetical"]),
        business_profile_id=source["business_profile_id"],
        from_link=True,
    )


def list_assessments(connection: sqlite3.Connection) -> list[dict[str, Any]]:
    rows = connection.execute(
        "SELECT * FROM assessments ORDER BY updated_at DESC"
    ).fetchall()
    return [
        _attach_business_profile(connection, _attach_approval(connection, _public_row(row)))
        for row in rows
    ]


def get_assessment(connection: sqlite3.Connection, assessment_id: str) -> dict[str, Any] | None:
    row = connection.execute(
        "SELECT * FROM assessments WHERE id = ?", (assessment_id,)
    ).fetchone()
    if row is None:
        return None
    return _attach_business_profile(connection, _attach_approval(connection, _public_row(row)))


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
    _sync_shared_profile(connection, current, clean, now)
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


def list_guidance_notes(
    connection: sqlite3.Connection, assessment_id: str
) -> list[dict[str, Any]]:
    """Educational notes only. They are not copied into the engine result."""
    from app.durable_value import pillar_by_id

    rows = connection.execute(
        """
        SELECT pillar_id, note, created_at
        FROM guidance_notes
        WHERE assessment_id = ?
        ORDER BY id
        """,
        (assessment_id,),
    ).fetchall()
    notes = []
    for row in rows:
        pillar = pillar_by_id(row["pillar_id"])
        notes.append(
            {
                "pillar_id": row["pillar_id"],
                "pillar_title": pillar["title"] if pillar else row["pillar_id"],
                "note": row["note"],
                "created_at": row["created_at"],
                "authoritative": False,
            }
        )
    return notes


def save_guidance_note(
    connection: sqlite3.Connection,
    assessment_id: str,
    pillar_id: str,
    note: str,
) -> list[dict[str, Any]]:
    """Store one educational note. The assessment row, including its result, stays as it was."""
    from app.durable_value import pillar_by_id

    current = get_assessment(connection, assessment_id)
    if current is None:
        raise KeyError(assessment_id)
    if current["read_only"] or current["id"] == BASELINE_ID:
        raise PermissionError(
            "Educational notes cannot be stored on the official baseline."
        )
    pillar = pillar_by_id(str(pillar_id or "").strip())
    if pillar is None:
        raise ValueError("Choose one of the seven educational pillars.")
    text = " ".join(str(note or "").split())
    if not text:
        raise ValueError("An educational note needs text.")
    text = text[:1000]
    columns = (
        "business_name, purpose, tier, read_only, hypothetical, pilot_label, "
        "profile_json, intake_json, result_json, review_requested"
    )
    before = connection.execute(
        f"SELECT {columns} FROM assessments WHERE id = ?",
        (assessment_id,),
    ).fetchone()
    connection.execute(
        """
        INSERT INTO guidance_notes (assessment_id, pillar_id, note, created_at)
        VALUES (?, ?, ?, ?)
        """,
        (assessment_id, pillar["id"], text, _now()),
    )
    after = connection.execute(
        f"SELECT {columns} FROM assessments WHERE id = ?",
        (assessment_id,),
    ).fetchone()
    if tuple(before) != tuple(after):
        connection.rollback()
        raise RuntimeError("An educational note must not change the assessment.")
    connection.commit()
    return list_guidance_notes(connection, assessment_id)


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


def create_business_profile(
    connection: sqlite3.Connection,
    *,
    display_name: str,
    industry: str,
    geography: str,
    stage: str,
    isolation: str,
    profile_id: str | None = None,
) -> str:
    if isolation not in (ISOLATION_BASELINE, ISOLATION_PILOT, ISOLATION_CUSTOMER):
        raise ValueError("Unknown business profile isolation.")
    profile_id = profile_id or uuid.uuid4().hex
    now = _now()
    connection.execute(
        """
        INSERT INTO business_profiles (
            id, display_name, industry, geography, stage, isolation, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            profile_id,
            str(display_name or "Untitled").strip() or "Untitled",
            str(industry or ""),
            str(geography or ""),
            str(stage or ""),
            isolation,
            now,
            now,
        ),
    )
    connection.commit()
    return profile_id


def get_business_profile(
    connection: sqlite3.Connection, profile_id: str
) -> dict[str, Any] | None:
    row = connection.execute(
        "SELECT * FROM business_profiles WHERE id = ?",
        (profile_id,),
    ).fetchone()
    if row is None:
        return None
    return _profile_row(row)


def list_business_profiles(
    connection: sqlite3.Connection, *, isolation: str | None = None
) -> list[dict[str, Any]]:
    if isolation:
        rows = connection.execute(
            "SELECT * FROM business_profiles WHERE isolation = ? ORDER BY display_name",
            (isolation,),
        ).fetchall()
    else:
        rows = connection.execute(
            "SELECT * FROM business_profiles ORDER BY display_name"
        ).fetchall()
    return [_profile_row(row) for row in rows]


def assessments_for_profile(
    connection: sqlite3.Connection, profile_id: str
) -> list[dict[str, Any]]:
    rows = connection.execute(
        """
        SELECT id, business_name, tier, read_only
        FROM assessments
        WHERE business_profile_id = ?
        ORDER BY created_at
        """,
        (profile_id,),
    ).fetchall()
    return [
        {
            "id": row["id"],
            "business_name": row["business_name"],
            "tier": row["tier"],
            "read_only": bool(row["read_only"]),
        }
        for row in rows
    ]


def ensure_business_profiles(connection: sqlite3.Connection) -> None:
    """Give each existing assessment its own profile. Does not rewrite intake or results."""
    rows = connection.execute(
        """
        SELECT id, business_name, pilot_label, read_only, hypothetical, profile_json, business_profile_id
        FROM assessments
        """
    ).fetchall()
    for row in rows:
        if row["business_profile_id"]:
            continue
        profile = json.loads(row["profile_json"])
        isolation = _isolation_for_row(row)
        profile_id = _STABLE_PROFILE_IDS.get(row["id"])
        if profile_id and get_business_profile(connection, profile_id) is None:
            create_business_profile(
                connection,
                display_name=row["business_name"],
                industry=str(profile.get("industry") or ""),
                geography=str(profile.get("market") or profile.get("geographic_market") or ""),
                stage=str(profile.get("stage") or ""),
                isolation=isolation,
                profile_id=profile_id,
            )
        elif profile_id is None:
            profile_id = create_business_profile(
                connection,
                display_name=row["business_name"],
                industry=str(profile.get("industry") or ""),
                geography=str(profile.get("market") or profile.get("geographic_market") or ""),
                stage=str(profile.get("stage") or ""),
                isolation=isolation,
            )
        connection.execute(
            "UPDATE assessments SET business_profile_id = ? WHERE id = ? AND business_profile_id IS NULL",
            (profile_id, row["id"]),
        )
    connection.commit()


def _isolation_for_new(business_name: str, pilot_label: str, hypothetical: bool) -> str:
    if business_name.strip() in NAMED_PILOT_NAMES or pilot_label == NAMED_PILOT_LABEL:
        return ISOLATION_PILOT
    if hypothetical or "demonstration" in pilot_label.lower():
        return ISOLATION_PILOT
    return ISOLATION_CUSTOMER


def _isolation_for_row(row: sqlite3.Row) -> str:
    if row["id"] == BASELINE_ID or row["read_only"]:
        return ISOLATION_BASELINE
    if row["id"] in (RESTAURANT_ID, RESTAURANT_VERIFIED_ID):
        return ISOLATION_PILOT
    return _isolation_for_new(
        str(row["business_name"] or ""),
        str(row["pilot_label"] or ""),
        bool(row["hypothetical"]),
    )


def _sync_shared_profile(
    connection: sqlite3.Connection,
    current: dict[str, Any],
    clean: dict[str, Any],
    now: str,
) -> None:
    """Copy identity, industry, geography, and stage to the shared profile and its other drafts."""
    profile_id = current.get("business_profile_id")
    if not profile_id:
        return
    business = get_business_profile(connection, profile_id)
    if business is None or business["isolation"] == ISOLATION_BASELINE:
        return
    display_name = str(clean.get("business_name") or current["business_name"])
    industry = str(clean.get("industry") or "")
    geography = str(clean.get("market") or clean.get("geographic_market") or "")
    stage = str(clean.get("stage") or "")
    connection.execute(
        """
        UPDATE business_profiles
        SET display_name = ?, industry = ?, geography = ?, stage = ?, updated_at = ?
        WHERE id = ? AND isolation != ?
        """,
        (display_name, industry, geography, stage, now, profile_id, ISOLATION_BASELINE),
    )
    others = connection.execute(
        """
        SELECT id, profile_json, read_only
        FROM assessments
        WHERE business_profile_id = ? AND id != ?
        """,
        (profile_id, current["id"]),
    ).fetchall()
    for other in others:
        if other["read_only"] or other["id"] == BASELINE_ID:
            continue
        payload = json.loads(other["profile_json"])
        payload["business_name"] = display_name
        payload["industry"] = industry
        payload["market"] = geography
        payload["stage"] = stage
        connection.execute(
            """
            UPDATE assessments
            SET business_name = ?, profile_json = ?
            WHERE id = ? AND read_only = 0
            """,
            (display_name, json.dumps(payload), other["id"]),
        )


def _profile_row(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "id": row["id"],
        "display_name": row["display_name"],
        "industry": row["industry"],
        "geography": row["geography"],
        "stage": row["stage"],
        "isolation": row["isolation"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


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
    business_profile_id: str | None = None,
) -> None:
    now = _now()
    connection.execute(
        """
        INSERT INTO assessments (
            id, business_name, purpose, tier, read_only, hypothetical, pilot_label,
            profile_json, intake_json, result_json, review_requested, created_at, updated_at,
            business_profile_id
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, NULL, 0, ?, ?, ?)
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
            business_profile_id,
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


def session_storage_key(token: str) -> str:
    """Hash stored for a session cookie. The raw token is not written to SQLite."""
    from app.config import session_storage_key as configured_key

    return configured_key(token)


def session_public_id(token: str) -> str:
    """Short hash for audit display. The raw session token stays out of the trail."""
    return session_storage_key(token)[:12]


def create_user(
    connection: sqlite3.Connection,
    *,
    user_id: str,
    email: str,
    password_hash: str,
    role: str,
) -> dict[str, Any]:
    created_at = _now()
    try:
        connection.execute(
            """
            INSERT INTO users (id, email, password_hash, role, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (user_id, email, password_hash, role, created_at),
        )
        connection.commit()
    except sqlite3.IntegrityError as exc:
        connection.rollback()
        raise ValueError("An account with that email is already registered.") from exc
    user = get_user_by_email(connection, email)
    assert user is not None
    return user


def count_users_with_role(connection: sqlite3.Connection, role: str) -> int:
    row = connection.execute(
        "SELECT COUNT(*) AS n FROM users WHERE role = ?",
        (role,),
    ).fetchone()
    return int(row["n"])


def get_user_by_email(connection: sqlite3.Connection, email: str) -> dict[str, Any] | None:
    row = connection.execute(
        """
        SELECT id, email, password_hash, role, created_at
        FROM users
        WHERE email = ?
        """,
        (email,),
    ).fetchone()
    if row is None:
        return None
    return {
        "id": row["id"],
        "email": row["email"],
        "password_hash": row["password_hash"],
        "role": row["role"],
        "created_at": row["created_at"],
    }


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
    user_id: str = "",
    role: str = "reviewer",
) -> dict[str, Any]:
    created_at = _now()
    connection.execute(
        """
        INSERT INTO reviewer_sessions (
            token, reviewer_identity, role, authentication_method, created_at, expires_at, user_id
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            session_storage_key(token),
            reviewer_identity,
            role,
            authentication_method,
            created_at,
            expires_at,
            user_id,
        ),
    )
    connection.commit()
    session = get_account_session(connection, token)
    assert session is not None
    return session


def load_reviewer_session(connection: sqlite3.Connection, token: str) -> dict[str, Any] | None:
    if not token:
        return None
    row = connection.execute(
        """
        SELECT reviewer_identity, role, authentication_method, created_at, expires_at, user_id
        FROM reviewer_sessions
        WHERE token = ?
        """,
        (session_storage_key(token),),
    ).fetchone()
    if row is None:
        return None
    return {
        "token": token,
        "reviewer_identity": row["reviewer_identity"],
        "role": row["role"],
        "authentication_method": row["authentication_method"],
        "created_at": row["created_at"],
        "expires_at": row["expires_at"],
        "user_id": row["user_id"] or "",
    }


def get_account_session(connection: sqlite3.Connection, token: str) -> dict[str, Any] | None:
    """Return an unexpired session for any local role. The raw token stays in memory only."""
    loaded = load_reviewer_session(connection, token)
    if loaded is None:
        return None
    remaining = _remaining_seconds(loaded.get("expires_at"))
    if remaining is None or remaining <= 0:
        return None
    loaded["remaining_seconds"] = remaining
    loaded["state"] = "signed-in"
    loaded["active"] = True
    return loaded


def get_reviewer_session(connection: sqlite3.Connection, token: str) -> dict[str, Any] | None:
    loaded = get_account_session(connection, token)
    if loaded is None or loaded["role"] != "reviewer":
        return None
    return loaded


def end_reviewer_session(connection: sqlite3.Connection, token: str) -> None:
    if not token:
        return
    connection.execute(
        "DELETE FROM reviewer_sessions WHERE token = ?",
        (session_storage_key(token),),
    )
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
        "business_profile_id": row["business_profile_id"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def _attach_business_profile(
    connection: sqlite3.Connection, record: dict[str, Any]
) -> dict[str, Any]:
    profile_id = record.get("business_profile_id")
    record["business_profile"] = (
        get_business_profile(connection, profile_id) if profile_id else None
    )
    record["linked_assessments"] = (
        assessments_for_profile(connection, profile_id) if profile_id else []
    )
    return record


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()

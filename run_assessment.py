"""
Run one RUGD assessment from an intake JSON file through the financial engine,
the scoring rules, and the report template.

Architecture § High-Level Components — intake, deterministic analysis, rule
scoring, templated report, and an audit record.
Architecture § Autonomy Boundaries — no new APIs, no weight changes, and no
final recommendation without a person.
Pilot scope § In-Scope — manual human review remains the approval step.

The report date is intake `as_of_date` or an explicit --date. This script does
not read the system clock.
"""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from engine.financial import FinancialInputs, result_to_dict, run_financials
from engine.startup_projection import format_projection, record_for_intake, worksheet_errors
from scoring.industry_benchmarks import audit_record
from scoring.rules import (
    METHODOLOGY_VERSION,
    MODEL_VERSION,
    NEXT_ACTIONS,
    REF_MARGIN,
    Recommendation,
    assessment_investor_readiness,
    build_recommendation,
    report_context,
)

ROOT = Path(__file__).resolve().parent
TEMPLATE_PATH = ROOT / "reports" / "template.md"
DEFAULT_INTAKE = ROOT / "intake" / "samples" / "rugd_intelligence.json"
ENGAGEMENT_TYPES = (
    "startup_feasibility",
    "expansion_feasibility",
    "operational_diagnostic",
)
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
PLACEHOLDERS = {
    "engagement_type": "engagement\\_type",
    "business_name": "business\\_name",
    "date": "date",
    "executive_summary": "executive\\_summary",
    "recommendation": "recommendation",
    "review_status": "review\\_status",
    "verified_data": "verified\\_data",
    "assumptions_list": "assumptions\\_list",
    "base_monthly_contribution": "base\\_monthly\\_contribution",
    "base_monthly_cash_flow": "base\\_monthly\\_cash\\_flow",
    "downside_monthly_cash_flow": "downside\\_monthly\\_cash\\_flow",
    "break_even_monthly_revenue": "break\\_even\\_monthly\\_revenue",
    "months_to_recover_initial_capital": "months\\_to\\_recover\\_initial\\_capital",
    "engine_flags": "engine\\_flags",
    "overall_score": "overall\\_score",
    "financial_notes": "financial\\_notes",
    "reasonableness_check": "reasonableness\\_check",
    "startup_capital": "startup\\_capital",
    "risks": "risks",
    "stewardship": "stewardship",
    "next_actions": "next\\_actions",
    "investor_readiness_status": "investor\\_readiness\\_status",
    "human_review_approved": "human\\_review\\_approved",
    "investor_readiness_conditions": "investor\\_readiness\\_conditions",
}

RUNNER_ASSUMPTIONS = (
    "The report date is the intake as_of_date or the --date argument. The runner does not read the system clock.",
    "Intake checks cover the fields this pilot uses. A full JSON Schema draft-2020-12 library is not a project dependency.",
    "Output files are written only under the project root.",
)


@dataclass(frozen=True)
class AssessmentArtifacts:
    report_path: Path
    audit_path: Path
    recommendation: Recommendation
    financial_result: dict[str, Any] | None
    report_text: str


def run_assessment(
    intake_path: Path,
    output_path: Path | None = None,
    *,
    as_of_date: str | None = None,
    template_path: Path = TEMPLATE_PATH,
) -> AssessmentArtifacts:
    intake_path = resolve_intake_path(intake_path)
    intake = load_intake(intake_path)
    errors = validate_intake(intake)
    if errors:
        raise ValueError("Intake failed validation:\n- " + "\n- ".join(errors))
    report_date = resolve_date(intake, as_of_date)
    financial = _run_engine(intake)
    financial_flags = list(financial["flags"]) if financial is not None else []
    recommendation = build_recommendation(intake, financial_flags, financial)
    readiness = assessment_investor_readiness(intake, recommendation, financial)
    startup_record = record_for_intake(
        intake, human_review_approved=readiness.human_review_approved
    )
    context = report_context(
        intake,
        recommendation,
        financial,
        as_of_date=report_date,
        extra_method_assumptions=RUNNER_ASSUMPTIONS,
    )
    context["startup_capital"] = format_projection(startup_record)
    template = template_path.read_text(encoding="utf-8")
    report_text = render_template(template, context)
    destination = output_path or default_output_path(str(intake["business_name"]))
    report_file = confine(destination)
    audit_file = confine(audit_path_for(report_file))
    report_file.parent.mkdir(parents=True, exist_ok=True)
    report_file.write_text(report_text, encoding="utf-8")
    audit = {
        "methodology_version": METHODOLOGY_VERSION,
        "model_version": MODEL_VERSION,
        "methodology_refs": [
            "Methodology § Core Principles — evidence hierarchy",
            "Methodology § Scoring Approach",
            "Methodology § Output Requirements",
            "Methodology § Investor Readiness Gate",
            "Architecture § High-Level Components",
            "Architecture § Technical Constraints for Pilot",
            "Pilot scope § In-Scope",
        ],
        "intake_path": str(intake_path),
        "as_of_date": report_date,
        "intake": intake,
        "financial_result": financial,
        "recommendation": {
            "draft_recommendation": recommendation.draft_recommendation,
            "is_final": recommendation.is_final,
            "requires_human_review": recommendation.requires_human_review,
            "human_review_status": recommendation.human_review_status,
            "blocking_flags": list(recommendation.blocking_flags),
            "gap_flags": list(recommendation.gap_flags),
            "notices": list(recommendation.notices),
            "engine_flags": list(recommendation.engine_flags),
            "overall_feasibility_score": recommendation.overall_feasibility_score,
            "score_note": recommendation.score_note,
            "method_assumptions": list(recommendation.method_assumptions)
            + list(RUNNER_ASSUMPTIONS),
            "ai_interpretations_noted": list(recommendation.ai_interpretations_noted),
            "next_actions": list(recommendation.next_actions),
            "criteria": [
                {
                    "criterion_id": item.criterion_id,
                    "status": item.status,
                    "flag": item.flag,
                    "methodology_ref": item.methodology_ref,
                    "evidence": item.evidence,
                }
                for item in recommendation.criteria
            ],
        },
        "investor_readiness": {
            "status": readiness.status,
            "human_review_approved": readiness.human_review_approved,
            "dscr_minimum": readiness.dscr_minimum,
            "conditions": [
                {"name": item.name, "passed": item.passed, "detail": item.detail}
                for item in readiness.conditions
            ],
        },
        "human_review": {
            "required": True,
            "status": "pending",
            "is_final": False,
            "recorded_by": None,
        },
        "ai_contributions": _ai_contributions(intake),
        "secondary_industry_benchmarks": audit_record(),
        "startup_capital": startup_record,
    }
    audit_file.write_text(json.dumps(audit, indent=2), encoding="utf-8")
    return AssessmentArtifacts(
        report_path=report_file,
        audit_path=audit_file,
        recommendation=recommendation,
        financial_result=financial,
        report_text=report_text,
    )


def load_intake(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("intake JSON must be an object")
    return payload


def validate_intake(intake: dict[str, Any]) -> list[str]:
    """Subset of intake/schema.json enforced without an external schema library."""
    errors: list[str] = []
    if not isinstance(intake, dict):
        return ["intake must be an object"]
    engagement = intake.get("engagement_type")
    if engagement not in ENGAGEMENT_TYPES:
        errors.append(
            "engagement_type must be one of " + ", ".join(ENGAGEMENT_TYPES)
        )
    name = intake.get("business_name")
    if not isinstance(name, str) or not name.strip():
        errors.append("business_name must be a non-empty string")
    if "description" in intake and not isinstance(intake["description"], str):
        errors.append("description must be a string")
    if "as_of_date" in intake and intake["as_of_date"] is not None:
        if not isinstance(intake["as_of_date"], str) or not DATE_RE.match(
            intake["as_of_date"]
        ):
            errors.append("as_of_date must be YYYY-MM-DD")
    errors.extend(_validate_verified(intake.get("verified_data")))
    errors.extend(_validate_assumptions(intake.get("assumptions")))
    if "financial_inputs" in intake and intake["financial_inputs"] is not None:
        errors.extend(_validate_financial(intake["financial_inputs"]))
    errors.extend(worksheet_errors(intake.get("startup_capital")))
    return errors


def resolve_date(intake: dict[str, Any], explicit: str | None) -> str:
    if explicit is not None:
        if not DATE_RE.match(explicit):
            raise ValueError("--date must be YYYY-MM-DD")
        return explicit
    stored = intake.get("as_of_date")
    if isinstance(stored, str) and DATE_RE.match(stored):
        return stored
    raise ValueError(
        "as_of_date is missing. Pass --date YYYY-MM-DD. The runner does not read the system clock."
    )


def render_template(template: str, context: dict[str, str]) -> str:
    rendered = template
    for key, token in PLACEHOLDERS.items():
        if key not in context:
            raise ValueError(f"report context missing {key}")
        rendered = rendered.replace("{{" + token + "}}", context[key])
    if "{{" in rendered:
        raise ValueError("report template still contains an unfilled placeholder")
    return rendered


def confine(path: Path) -> Path:
    """Resolve path under the project root. Relative paths are anchored at the root, not the shell cwd."""
    anchored = path if path.is_absolute() else ROOT / path
    resolved = anchored.resolve()
    root = ROOT.resolve()
    if resolved != root and root not in resolved.parents:
        raise ValueError(f"path must stay inside {root}")
    return resolved


def resolve_intake_path(path: Path) -> Path:
    if path.is_file():
        return path
    candidate = ROOT / path
    if candidate.is_file():
        return candidate
    return path


def default_output_path(business_name: str) -> Path:
    return ROOT / "reports" / "output" / f"{_slug(business_name)}-draft.md"


# Methodology § Investor Readiness Gate — a one-page summary is written only
# when the gate status is investor-ready and human_review_approved is true.
# Pilot scope — Investor Readiness Gate (status flag and one-page summary only).
_SUMMARY_FINANCIAL_FIELDS = (
    "base_monthly_contribution",
    "base_monthly_cash_flow",
    "downside_monthly_revenue",
    "downside_monthly_contribution",
    "downside_monthly_cash_flow",
    "break_even_monthly_revenue",
    "dscr_downside",
)


def write_investor_summary(
    intake: dict[str, Any],
    recommendation: Recommendation,
    financial_result: dict[str, Any] | None,
    *,
    human_review_approved: bool = False,
    output_path: Path | None = None,
) -> Path:
    """Write a one-page investor summary, or refuse without creating a file.

    Methodology § Investor Readiness Gate. The file is written only when the
    gate status is investor-ready and human_review_approved is explicitly true.
    """
    destination = output_path or (
        ROOT
        / "reports"
        / "output"
        / f"{_slug(str(intake.get('business_name', 'assessment')))}-investor-summary.md"
    )
    resolved = confine(destination)
    if human_review_approved is not True:
        raise ValueError("Investor summary refused: human_review_approved is not true.")
    readiness = assessment_investor_readiness(
        intake,
        recommendation,
        financial_result,
        human_review="approved",
    )
    if readiness.status != "investor-ready" or readiness.human_review_approved is not True:
        raise ValueError(f"Investor summary refused: status is {readiness.status}.")
    resolved.parent.mkdir(parents=True, exist_ok=True)
    resolved.write_text(
        _investor_summary_text(intake, recommendation, financial_result),
        encoding="utf-8",
    )
    return resolved


def _investor_summary_text(
    intake: dict[str, Any],
    recommendation: Recommendation,
    financial_result: dict[str, Any] | None,
) -> str:
    score = recommendation.overall_feasibility_score
    score_line = "not computed" if score is None else str(score)
    stewardship = next(
        item
        for item in recommendation.criteria
        if item.criterion_id == "stewardship_extraction"
    )
    sections = [
        "## Recommendation and score",
        f"Recommendation: {recommendation.draft_recommendation}",
        f"Score: {score_line}",
        "",
        "## Evidence labels",
        _evidence_labels(intake),
        "",
        "## Base and downside financials",
        _engine_financial_lines(financial_result),
        "",
        "## Key risks and mitigations",
        _summary_risks(recommendation),
        "",
        "## Stewardship observations",
        f"Status: {stewardship.status}. {stewardship.evidence}",
        "",
    ]
    return "\n".join(sections)


def _summary_risks(recommendation: Recommendation) -> str:
    lines = []
    for item in recommendation.criteria:
        if item.status in ("triggered", "gap") and item.flag:
            lines.append(
                f"- {item.flag} ({item.status}). Mitigation: {NEXT_ACTIONS[item.flag]}"
            )
    for notice in recommendation.notices:
        lines.append(f"- {notice} (engine notice). {REF_MARGIN}")
    return "\n".join(lines) if lines else "- No automatic flags."


def _evidence_labels(intake: dict[str, Any]) -> str:
    verified = intake.get("verified_data") or {}
    lines = []
    if isinstance(verified, dict):
        for key in ("revenue_trailing_12m", "current_cash", "headcount", "evidence_notes"):
            label = "not supplied" if verified.get(key) is None else "verified"
            lines.append(f"- {key}: {label}")
    for item in intake.get("assumptions") or []:
        if isinstance(item, dict) and "key" in item and "source" in item:
            lines.append(f"- {item['key']}: {item['source']}")
    return "\n".join(lines) if lines else "- No evidence labels supplied."


def _engine_financial_lines(financial_result: dict[str, Any] | None) -> str:
    if not isinstance(financial_result, dict):
        return "- No engine result supplied."
    lines = []
    for key in _SUMMARY_FINANCIAL_FIELDS:
        if key not in financial_result or financial_result[key] is None:
            lines.append(f"- {key}: not supplied by the engine")
            continue
        value = financial_result[key]
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            lines.append(f"- {key}: not supplied by the engine")
            continue
        decimals = 4 if key == "dscr_downside" else 2
        lines.append(f"- {key}: {value:.{decimals}f}")
    return "\n".join(lines)


def audit_path_for(report_file: Path) -> Path:
    stem = report_file.stem
    if stem.endswith("-draft"):
        stem = stem[: -len("-draft")] + "-audit"
    else:
        stem = stem + "-audit"
    return report_file.with_name(stem + ".json")


def _run_engine(intake: dict[str, Any]) -> dict[str, Any] | None:
    financial = intake.get("financial_inputs")
    if not isinstance(financial, dict):
        return None
    multiplier = financial.get("downside_revenue_multiplier", 0.6)
    inputs = FinancialInputs(
        initial_capital=financial["initial_capital"],
        monthly_fixed_costs=financial["monthly_fixed_costs"],
        gross_margin_pct=financial["gross_margin_pct"],
        projected_monthly_revenue_base=financial["projected_monthly_revenue_base"],
        downside_revenue_multiplier=multiplier,
    )
    return result_to_dict(run_financials(inputs))


def _validate_verified(verified: Any) -> list[str]:
    if verified is None:
        return []
    if not isinstance(verified, dict):
        return ["verified_data must be an object"]
    errors = []
    for key in ("revenue_trailing_12m", "current_cash"):
        if key in verified:
            errors.extend(_optional_number(f"verified_data.{key}", verified[key], minimum=0))
    if "headcount" in verified:
        value = verified["headcount"]
        if value is not None and (
            isinstance(value, bool) or not isinstance(value, int) or value < 0
        ):
            errors.append("verified_data.headcount must be an integer >= 0 or null")
    if "evidence_notes" in verified and not isinstance(verified["evidence_notes"], str):
        errors.append("verified_data.evidence_notes must be a string")
    return errors


def _validate_assumptions(assumptions: Any) -> list[str]:
    if not isinstance(assumptions, list):
        return ["assumptions must be a list"]
    errors = []
    for index, item in enumerate(assumptions):
        if not isinstance(item, dict):
            errors.append(f"assumptions[{index}] must be an object")
            continue
        for field in ("key", "value", "source", "rationale"):
            if field not in item:
                errors.append(f"assumptions[{index}] missing {field}")
        if "key" in item and (not isinstance(item["key"], str) or not item["key"].strip()):
            errors.append(f"assumptions[{index}].key must be a non-empty string")
        if "source" in item and item["source"] not in (
            "user",
            "verified",
            "ai_interpretation",
        ):
            errors.append(f"assumptions[{index}].source is not allowed")
        if "rationale" in item and not isinstance(item["rationale"], str):
            errors.append(f"assumptions[{index}].rationale must be a string")
    return errors


def _validate_financial(financial: Any) -> list[str]:
    if not isinstance(financial, dict):
        return ["financial_inputs must be an object"]
    errors = []
    required = (
        "initial_capital",
        "monthly_fixed_costs",
        "gross_margin_pct",
        "projected_monthly_revenue_base",
    )
    for key in required:
        if key not in financial:
            errors.append(f"financial_inputs.{key} is required")
            continue
        upper = 1 if key == "gross_margin_pct" else None
        errors.extend(
            _required_number(f"financial_inputs.{key}", financial[key], minimum=0, maximum=upper)
        )
    if "downside_revenue_multiplier" in financial:
        errors.extend(
            _required_number(
                "financial_inputs.downside_revenue_multiplier",
                financial["downside_revenue_multiplier"],
                minimum=0,
            )
        )
    if "inputs_are_measured" in financial and not isinstance(
        financial["inputs_are_measured"], bool
    ):
        errors.append("financial_inputs.inputs_are_measured must be a boolean")
    return errors


def _optional_number(
    label: str, value: Any, *, minimum: float | None = None
) -> list[str]:
    if value is None:
        return []
    return _required_number(label, value, minimum=minimum)


def _required_number(
    label: str,
    value: Any,
    *,
    minimum: float | None = None,
    maximum: float | None = None,
) -> list[str]:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return [f"{label} must be a number"]
    if isinstance(value, float) and not math.isfinite(value):
        return [f"{label} must be finite"]
    if minimum is not None and value < minimum:
        return [f"{label} must be >= {minimum}"]
    if maximum is not None and value > maximum:
        return [f"{label} must be <= {maximum}"]
    return []


def _ai_contributions(intake: dict[str, Any]) -> list[str]:
    lines = [
        "Risk, stewardship, and next-action prose is assembled by scoring/rules.py. Dimension scores were not generated."
    ]
    for item in intake.get("assumptions", []):
        if isinstance(item, dict) and item.get("source") == "ai_interpretation":
            lines.append(
                f"Intake assumption {item.get('key')} is source ai_interpretation."
            )
    return lines


def _slug(name: str) -> str:
    cleaned = "".join(char.lower() if char.isalnum() else "-" for char in name)
    while "--" in cleaned:
        cleaned = cleaned.replace("--", "-")
    return cleaned.strip("-") or "assessment"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run a RUGD draft assessment.")
    parser.add_argument("intake", nargs="?", default=str(DEFAULT_INTAKE))
    parser.add_argument("--output", default=None)
    parser.add_argument("--date", default=None)
    args = parser.parse_args(argv)
    try:
        artifacts = run_assessment(
            Path(args.intake),
            Path(args.output) if args.output else None,
            as_of_date=args.date,
        )
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"Assessment was not written: {exc}", file=sys.stderr)
        return 2
    draft = artifacts.recommendation.draft_recommendation
    print(f"Draft recommendation: {draft}")
    print("Human review: pending. No final recommendation was issued.")
    print(f"Report: {artifacts.report_path}")
    print(f"Audit: {artifacts.audit_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Replaceable analyst. No external AI service is configured."""

from __future__ import annotations

import copy
from typing import Any, Protocol


class Analyst(Protocol):
    label: str

    def explain(self, record: dict[str, Any], result: dict[str, Any] | None) -> list[str]:
        """Explain a copy of the engine result. Implementations must not mutate it."""


class DemonstrationAnalyst:
    """Rule-based stand-in used when no external analyst API is configured."""

    label = "Demonstration Analyst. No external AI service is connected."

    def explain(self, record: dict[str, Any], result: dict[str, Any] | None) -> list[str]:
        safe_record = copy.deepcopy(record)
        safe_result = copy.deepcopy(result) if result is not None else None
        return _explain(safe_record, safe_result)


def get_analyst() -> DemonstrationAnalyst:
    """Replacement point for a future analyst. No external API is configured."""
    return DemonstrationAnalyst()


def explain(record: dict[str, Any], result: dict[str, Any] | None) -> list[str]:
    return get_analyst().explain(record, result)


def _explain(record: dict[str, Any], result: dict[str, Any] | None) -> list[str]:
    lines = [
        DemonstrationAnalyst.label,
        "This analyst can explain the current assessment. It cannot change engine results, clear a recommend-against flag, approve review, or mark a recommendation final.",
    ]
    if record.get("hypothetical"):
        lines.append("This file is a hypothetical demonstration. Do not treat its figures as verified evidence.")
    if record.get("read_only"):
        lines.append(
            "The RUGD Intelligence baseline is read-only. Its draft remains do-not-proceed until measured evidence and an authorized review change it."
        )
    if not result or not result.get("engine_ran"):
        lines.append("Analyze has not produced an engine result for this draft yet.")
        return lines
    for item in result.get("missing") or []:
        lines.append(str(item))
    recommendation = result.get("recommendation")
    if recommendation:
        lines.append(f"The deterministic draft recommendation is {recommendation}. It is not final.")
    summary = result.get("view_summary") or {}
    if summary:
        lines.append(
            "INSUFFICIENT_DEMAND_EVIDENCE is "
            f"{summary.get('insufficient_demand_evidence', 'present')}. "
            f"Demand evidence status is {summary.get('demand_status', 'uncleared')}."
        )
        lines.append(f"Human review status is {summary.get('human_review_status', 'pending')}.")
    elif (result.get("demand") or {}).get("status"):
        lines.append(
            f"Demand evidence status is {result['demand']['status']}. "
            "The analyst cannot clear that flag."
        )
    for row in (result.get("demand") or {}).get("provenance") or []:
        lines.append(f"Demand provenance {row.get('field')}: {row.get('provenance')}.")
    for flag in result.get("blocking_flags") or []:
        lines.append(f"Recommend-against flag still active: {flag}.")
    for flag in result.get("gap_flags") or []:
        lines.append(f"Evidence gap still open: {flag}. The analyst cannot close it.")
    lines.extend(_explain_financial(result.get("financial")))
    lines.extend(_explain_projection(result.get("projection")))
    if result.get("readiness_status"):
        lines.append(
            f"Investor readiness is {result['readiness_status']}. "
            "The analyst cannot change the Investor Readiness Gate."
        )
    if not result.get("blocking_flags") and result.get("gap_flags"):
        lines.append("Open evidence gaps remain. A silent or incomplete intake cannot become a go recommendation.")
    if result.get("human_review_approved") is True:
        lines.append(
            "human_review_approved is true on this stored result. "
            "The analyst did not set it and cannot change investor readiness."
        )
    else:
        lines.append("human_review_approved remains false. This explanation is not evidence and is not final.")
    return lines


def _explain_financial(financial: dict[str, Any] | None) -> list[str]:
    if not financial:
        return ["Monthly engine output is absent. The analyst does not invent monthly cash flow."]
    return [
        "Monthly base cash flow from the engine is "
        f"{financial.get('base_monthly_cash_flow')}.",
        "Monthly downside cash flow from the engine is "
        f"{financial.get('downside_monthly_cash_flow')}.",
    ]


def _explain_projection(projection: dict[str, Any] | None) -> list[str]:
    if not projection or not projection.get("calculated"):
        return [
            "The engine did not calculate sources and uses for this assessment. "
            "The analyst does not supply a cost or a DSCR."
        ]
    uses = (projection.get("sources_and_uses") or {}).get("uses") or {}
    sources = (projection.get("sources_and_uses") or {}).get("sources") or {}
    views = projection.get("views") or {}
    base = views.get("base") or {}
    downside = views.get("downside") or {}
    return [
        "Sources and uses from the engine: total project cost is "
        f"{_amount(uses.get('total_project_cost'))}. "
        f"Debt is {_amount(sources.get('debt'))}. "
        f"Equity is {_amount(sources.get('equity'))}.",
        "Base case from the engine: revenue "
        f"{base.get('revenue')}, cash flow before debt service "
        f"{base.get('cash_flow_before_debt_service')}, DSCR {_dscr(base.get('dscr'))}.",
        "Downside case from the engine: revenue "
        f"{downside.get('revenue')}, cash flow before debt service "
        f"{downside.get('cash_flow_before_debt_service')}, DSCR {_dscr(downside.get('dscr'))}.",
    ]


def _amount(value: Any) -> Any:
    if isinstance(value, dict):
        return value.get("amount")
    return value


def _dscr(value: Any) -> Any:
    if value is None:
        return "undefined"
    return value

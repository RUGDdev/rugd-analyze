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
    if result.get("readiness_status"):
        lines.append(
            f"Investor readiness is {result['readiness_status']}. "
            "The analyst cannot change the Investor Readiness Gate."
        )
    if not result.get("blocking_flags") and result.get("gap_flags"):
        lines.append("Open evidence gaps remain. A silent or incomplete intake cannot become a go recommendation.")
    lines.append("human_review_approved remains false. This explanation is not evidence and is not final.")
    return lines

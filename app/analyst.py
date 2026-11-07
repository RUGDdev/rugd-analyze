"""Rule-based Demonstration Analyst. No external AI service is called."""

from __future__ import annotations

from typing import Any

LABEL = "Demonstration Analyst. No external AI service is connected."


def explain(record: dict[str, Any], result: dict[str, Any] | None) -> list[str]:
    lines = [
        LABEL,
        "This analyst can explain the current assessment. It cannot change engine results, clear a recommend-against flag, approve review, or mark a recommendation final.",
    ]
    if record.get("hypothetical"):
        lines.append("This file is a hypothetical demonstration. Do not treat its figures as verified evidence.")
    if record.get("read_only"):
        lines.append("The RUGD Intelligence baseline is read-only. Its draft remains do-not-proceed until measured evidence and an authorized review change it.")
    if not result or not result.get("engine_ran"):
        lines.append("Analyze has not produced an engine result for this draft yet.")
        return lines
    for item in result.get("missing") or []:
        lines.append(item)
    recommendation = result.get("recommendation")
    if recommendation:
        lines.append(f"The deterministic draft recommendation is {recommendation}. It is not final.")
    demand = result.get("demand") or {}
    if demand.get("status"):
        lines.append(
            f"Demand evidence status is {demand['status']}. "
            "The analyst cannot clear that flag."
        )
    for flag in result.get("blocking_flags") or []:
        lines.append(f"Recommend-against flag still active: {flag}.")
    if result.get("readiness_status"):
        lines.append(
            f"Investor readiness is {result['readiness_status']}. "
            "A purchased review would not set human_review_approved."
        )
    if not result.get("blocking_flags") and result.get("gap_flags"):
        lines.append("Open evidence gaps remain. A silent or incomplete intake cannot become a go recommendation.")
    return lines

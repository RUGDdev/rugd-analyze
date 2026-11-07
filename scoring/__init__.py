"""Methodology scoring and draft recommendations. Human review stays outside this package."""

from scoring.rules import (
    METHODOLOGY_VERSION,
    MODEL_VERSION,
    InvestorReadiness,
    Recommendation,
    build_recommendation,
    evaluate_flags,
    investor_readiness_gate,
    recommendation_to_dict,
    report_context,
)

__all__ = [
    "METHODOLOGY_VERSION",
    "MODEL_VERSION",
    "InvestorReadiness",
    "Recommendation",
    "build_recommendation",
    "evaluate_flags",
    "investor_readiness_gate",
    "recommendation_to_dict",
    "report_context",
]

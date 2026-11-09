"""Disabled seams for later owner decisions.

None of these functions turn a feature on. Environment variables cannot enable
them. Replacing a function requires a written owner decision in DECISIONS.md.
They do not clear a recommend-against flag, set human_review_approved, or
calculate a score.
"""

from __future__ import annotations

from typing import Any

SCORING_MESSAGE = "Not calculated — methodology pending approval."

_DECISIONS = (
    {
        "id": "production_authentication",
        "title": "Production authentication provider",
        "status": "disabled",
        "message": (
            "No production identity provider is connected. Local email and password accounts "
            "exist for this pilot and are not production authentication."
        ),
        "owner_input": (
            "Name the provider, whether it is local accounts, OAuth, or an external identity provider, "
            "and where account records will live. Confirm a customer account cannot set human_review_approved, "
            "and that reviewer approval still cannot clear a flag or grant investor-ready by itself."
        ),
    },
    {
        "id": "scoring_methodology",
        "title": "Scoring methodology",
        "status": "disabled",
        "message": SCORING_MESSAGE,
        "owner_input": (
            "Approve the score definition and its weights in writing. Confirm the score does not replace "
            "a recommend-against flag or the Investor Readiness Gate, and that it cannot clear "
            "INSUFFICIENT_DEMAND_EVIDENCE or set human_review_approved."
        ),
    },
    {
        "id": "deployment",
        "title": "Deployment settings",
        "status": "disabled",
        "message": "Public deployment is disabled. The local server stays on 127.0.0.1.",
        "owner_input": (
            "Name the host, port, operator, and whether the app may leave 127.0.0.1. Include TLS and the domain. "
            "Confirm a deployed app does not overwrite the official baseline files."
        ),
    },
    {
        "id": "billing",
        "title": "Billing hooks",
        "status": "disabled",
        "message": "Billing is not active. No charge is created.",
        "owner_input": (
            "Name the payment provider, the products, and the prices. Confirm a payment cannot clear a flag, "
            "approve a review, or set investor-ready."
        ),
    },
)


def production_auth_provider() -> dict[str, Any]:
    """The replacement point for a future identity provider. It returns no provider."""
    return {"enabled": False, "provider": None, "status": "disabled"}


def scoring_methodology() -> dict[str, Any]:
    """The replacement point for an approved score. It returns no score."""
    return {"enabled": False, "score": None, "status": "disabled", "message": SCORING_MESSAGE}


def deployment_settings() -> dict[str, Any]:
    """The replacement point for a public host. The running server does not read it."""
    return {
        "enabled": False,
        "status": "disabled",
        "bind_host": "127.0.0.1",
        "public_deployment": False,
    }


def billing_hooks() -> dict[str, Any]:
    """The replacement point for a payment call. It creates no charge."""
    return {"enabled": False, "provider": None, "charge": None, "status": "disabled"}


def future_status() -> dict[str, Any]:
    """Read-only status for the four disabled seams."""
    return {
        "enabled": False,
        "decisions": [dict(item) for item in _DECISIONS],
        "authentication": production_auth_provider(),
        "scoring": scoring_methodology(),
        "deployment": deployment_settings(),
        "billing": billing_hooks(),
    }

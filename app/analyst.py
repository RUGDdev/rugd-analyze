"""Replaceable analyst. External providers are optional and fail closed to the demonstration."""

from __future__ import annotations

import copy
import json
import os
import urllib.error
import urllib.request
from typing import Any, Callable, Protocol

from app.export import _without_secrets

SAFETY_PROMPT = (
    "You are the RUGD analyst. Explain only the assessment summary you are given. "
    "You must not change financial numbers, clear recommend-against flags, set human_review_approved, "
    "or change investor readiness. You must not invent market research or evidence. "
    "If a figure is absent, say it was not calculated. Your reply is an explanation, not a decision."
)

_PROVIDERS = {
    "claude": {
        "key": "ANTHROPIC_API_KEY",
        "url": "https://api.anthropic.com/v1/messages",
        "model": "claude-sonnet-4-5",
    },
    "openai": {
        "key": "OPENAI_API_KEY",
        "url": "https://api.openai.com/v1/chat/completions",
        "model": "gpt-4.1-mini",
    },
    "grok": {
        "key": "XAI_API_KEY",
        "url": "https://api.x.ai/v1/chat/completions",
        "model": "grok-3",
    },
}
_ALIASES = {
    "claude": "claude",
    "anthropic": "claude",
    "openai": "openai",
    "chatgpt": "openai",
    "grok": "grok",
    "xai": "grok",
}
Transport = Callable[[str, dict[str, str], dict[str, Any]], dict[str, Any]]


ASSISTANCE_LABEL = (
    "Assistance only. This reply cannot change numbers, clear a recommend-against flag, "
    "set human_review_approved, or grant investor-ready status."
)

STARTER_QUESTIONS = (
    "What does my score mean?",
    "Why is demand evidence missing?",
    "What should I do next?",
    "What should I work on next?",
    "What does the recommendation mean?",
    "What does this gate mean?",
    "Am I investor-ready?",
    "How is this different from a business plan?",
)

AGENT_WORKFLOW = (
    ("intake", "Intake guidance"),
    ("gaps", "Gap identification"),
    ("results", "Results explanation"),
    ("next", "Next-step recommendation"),
)


class Analyst(Protocol):
    label: str

    def explain(self, record: dict[str, Any], result: dict[str, Any] | None) -> list[str]:
        """Explain a copy of the engine result. Implementations must not mutate it."""


class DemonstrationAnalyst:
    """Rule-based stand-in used when no external analyst API is configured."""

    label = "Demonstration Analyst. No external AI service is connected."
    uses_network = False

    def explain(self, record: dict[str, Any], result: dict[str, Any] | None) -> list[str]:
        safe_record = copy.deepcopy(record)
        safe_result = copy.deepcopy(result) if result is not None else None
        return _explain(safe_record, safe_result)

    def reply(
        self,
        record: dict[str, Any],
        result: dict[str, Any] | None,
        question: str,
        market_notes: list[str] | None = None,
    ) -> list[str]:
        safe_record = copy.deepcopy(record)
        safe_result = copy.deepcopy(result) if result is not None else None
        return [ASSISTANCE_LABEL, self.label, *_grounded_reply(safe_record, safe_result, question, market_notes)]


class FallbackAnalyst:
    """Labeled Demonstration Analyst used when a provider was requested but cannot run."""

    uses_network = False

    def __init__(self, reason: str) -> None:
        self.label = f"Fallback: Demonstration Analyst. {reason}"

    def explain(self, record: dict[str, Any], result: dict[str, Any] | None) -> list[str]:
        return [self.label, *DemonstrationAnalyst().explain(record, result)]

    def reply(
        self,
        record: dict[str, Any],
        result: dict[str, Any] | None,
        question: str,
        market_notes: list[str] | None = None,
    ) -> list[str]:
        lines = DemonstrationAnalyst().reply(record, result, question, market_notes)
        if lines and lines[0] == ASSISTANCE_LABEL:
            return [ASSISTANCE_LABEL, self.label, *lines[1:]]
        return [ASSISTANCE_LABEL, self.label, *lines]


class ExternalAnalyst:
    """Optional provider call. A failed call falls back and does not edit the engine result."""

    uses_network = True

    def __init__(self, provider: str, api_key: str, model: str, transport: Transport | None = None) -> None:
        self.provider = provider
        self.label = (
            f"External analyst ({provider}). Not the Demonstration Analyst. "
            "This explanation cannot change engine results, flags, approval, or investor readiness."
        )
        self._api_key = api_key
        self._model = model
        self._transport = transport or _post_json

    def explain(self, record: dict[str, Any], result: dict[str, Any] | None) -> list[str]:
        safe_record = copy.deepcopy(record)
        safe_result = copy.deepcopy(result) if result is not None else None
        try:
            text = self._complete(_summary(safe_record, safe_result)).strip()
            if not text:
                raise ValueError("empty analyst response")
        except Exception:
            fallback = FallbackAnalyst("The external analyst call failed.")
            return fallback.explain(record, result)
        lines = [self.label, SAFETY_PROMPT]
        lines.extend(line.strip() for line in text.splitlines() if line.strip())
        return lines

    def reply(
        self,
        record: dict[str, Any],
        result: dict[str, Any] | None,
        question: str,
        market_notes: list[str] | None = None,
    ) -> list[str]:
        safe_record = copy.deepcopy(record)
        safe_result = copy.deepcopy(result) if result is not None else None
        summary = _summary(safe_record, safe_result)
        summary["question"] = str(question or "")[:500]
        summary["market_notes"] = [str(item) for item in (market_notes or [])]
        try:
            text = self._complete(summary).strip()
            if not text:
                raise ValueError("empty analyst response")
        except Exception:
            fallback = FallbackAnalyst("The external analyst call failed.")
            return fallback.reply(record, result, question, market_notes)
        lines = [ASSISTANCE_LABEL, self.label, SAFETY_PROMPT]
        lines.extend(line.strip() for line in text.splitlines() if line.strip())
        return lines

    def _complete(self, summary: dict[str, Any]) -> str:
        spec = _PROVIDERS[self.provider]
        user = json.dumps(summary, default=str)
        if self.provider == "claude":
            payload = {
                "model": self._model,
                "max_tokens": 800,
                "system": SAFETY_PROMPT,
                "messages": [{"role": "user", "content": user}],
            }
            headers = {
                "content-type": "application/json",
                "x-api-key": self._api_key,
                "anthropic-version": "2023-06-01",
            }
        else:
            payload = {
                "model": self._model,
                "messages": [
                    {"role": "system", "content": SAFETY_PROMPT},
                    {"role": "user", "content": user},
                ],
            }
            headers = {
                "content-type": "application/json",
                "authorization": f"Bearer {self._api_key}",
            }
        response = self._transport(spec["url"], headers, payload)
        return _response_text(self.provider, response)


def agent_workflow(record: dict[str, Any], *, surface: str = "intake") -> dict[str, Any]:
    """Name the assistance stage for this file. Reading it does not write a result."""
    record = record or {}
    result = record.get("result") if isinstance(record.get("result"), dict) else {}
    ran = bool(result.get("engine_ran"))
    flags = [str(flag) for flag in result.get("blocking_flags") or []]
    missing = [str(item) for item in result.get("missing") or []]
    assessment_id = str(record.get("id") or "")
    if not ran:
        current = "intake"
        action = "Save the draft, then run Analyze. This suggestion does not run the engine."
        href = f"/assessments/{assessment_id}#intake" if surface == "results" else "#intake"
        link_label = "Open the intake fields"
        questions = ("What should I do next?", "What evidence is still missing?")
    elif surface == "results":
        current = "results"
        if flags:
            action = (
                f"Read the active recommend-against flag {flags[0]}. "
                "This suggestion does not clear it."
            )
        else:
            action = "Read the stored recommendation. This suggestion does not change it."
        href = "#results-lead"
        link_label = "Read the stored result"
        questions = ("Explain this result", "What should I do next?")
    else:
        current = "gaps"
        if missing:
            action = (
                "The engine already lists missing items on this draft. "
                "This suggestion does not fill them."
            )
        elif flags:
            action = (
                f"Recommend-against flag {flags[0]} is still active. "
                "This suggestion does not clear it."
            )
        else:
            action = "Read the stored result. This suggestion does not change it."
        href = f"#evidence-checklist-{assessment_id}"
        link_label = "Open the evidence checklist"
        questions = ("What evidence is still missing?", "Explain this result")
    return {
        "stages": AGENT_WORKFLOW,
        "current": current,
        "action": action,
        "href": href,
        "link_label": link_label,
        "questions": questions,
    }


def get_analyst(environ: Any | None = None, transport: Transport | None = None) -> Any:
    """Return the configured analyst. A missing key or unknown provider falls back."""
    env = os.environ if environ is None else environ
    raw = str(env.get("ANALYST_PROVIDER") or "").strip().lower()
    if raw in {"", "demo", "demonstration", "none"}:
        return DemonstrationAnalyst()
    provider = _ALIASES.get(raw)
    if provider is None:
        return FallbackAnalyst("The selected analyst provider is not available.")
    api_key = str(env.get(_PROVIDERS[provider]["key"]) or "").strip()
    if not api_key:
        return FallbackAnalyst("No API key is configured.")
    model = str(env.get("ANALYST_MODEL") or "").strip() or _PROVIDERS[provider]["model"]
    return ExternalAnalyst(provider, api_key, model, transport=transport)


def explain(
    record: dict[str, Any],
    result: dict[str, Any] | None,
    *,
    environ: Any | None = None,
    transport: Transport | None = None,
) -> list[str]:
    return get_analyst(environ=environ, transport=transport).explain(record, result)


def answer(
    record: dict[str, Any],
    result: dict[str, Any] | None,
    question: str,
    *,
    environ: Any | None = None,
    transport: Transport | None = None,
    market_notes: list[str] | None = None,
) -> list[str]:
    """Answer one question from the current assessment. Nothing is saved."""
    lines = get_analyst(environ=environ, transport=transport).reply(
        record,
        result,
        question,
        market_notes,
    )
    if not lines or lines[0] != ASSISTANCE_LABEL:
        return [ASSISTANCE_LABEL, *lines]
    return lines


def _grounded_reply(
    record: dict[str, Any],
    result: dict[str, Any] | None,
    question: str,
    market_notes: list[str] | None,
) -> list[str]:
    """Sentences drawn from this assessment. No figure is invented."""
    asked = " ".join(str(question or "").split()).strip()
    folded = asked.lower()
    lines = [
        f"You asked: {asked or 'a question about this assessment.'}",
    ]
    if record.get("read_only"):
        lines.append(
            "This is the official baseline. Its draft stays do-not-proceed until the intake itself "
            "and an authorized review change it. This reply does not change the intake."
        )
    if "different" in folded or "business plan" in folded:
        lines.append(
            "RUGD keeps a hard recommend-against flag in force. A business-plan narrative, "
            "an indicative number, and a market example do not clear that flag or grant investor-ready status. "
            "When a public extract is requested, Market Intelligence shows the source and the period. "
            "This reply does not change the recommendation."
        )
    if not result or not result.get("engine_ran"):
        lines.append(
            "Analyze has not been run yet. Save the draft, then run Analyze. "
            "This reply does not run the engine and does not fill a blank field."
        )
        lines.append("Return to the intake on this draft. Blank fields stay blank.")
        return lines
    flags = [str(flag) for flag in result.get("blocking_flags") or []]
    if "score" in folded:
        lines.append(f"The feasibility score line is {result.get('score_line')}.")
        lines.extend(_indicative_reading(result))
    if "demand" in folded:
        if "INSUFFICIENT_DEMAND_EVIDENCE" in flags:
            lines.append(
                "Demand evidence is missing because INSUFFICIENT_DEMAND_EVIDENCE is still active. "
                "The engine needs a verified demand record: source verified, a rationale, and a true demand claim "
                "or trailing revenue above zero. This reply does not create that record and does not clear the flag."
            )
        else:
            lines.append(
                "INSUFFICIENT_DEMAND_EVIDENCE is not in the active recommend-against flags on this stored result. "
                "This reply does not change that list."
            )
    if "explain" in folded:
        lines.append(
            f"The stored recommendation is {result.get('recommendation')}. "
            f"Investor readiness is {result.get('readiness_status')}. "
            "This reply explains the stored result and does not change it."
        )
        lines.extend(_indicative_reading(result))
    if "evidence" in folded or "missing" in folded:
        missing = [str(item) for item in result.get("missing") or []]
        if missing:
            shown = "; ".join(missing[:6])
            lines.append(
                f"The engine already lists these missing items: {shown}. "
                "This reply does not fill them and does not clear a flag."
            )
        if flags:
            listed = "; ".join(flags)
            lines.append(
                f"Recommend-against flags still active: {listed}. This reply does not clear them."
            )
        elif not missing:
            lines.append(
                "No recommend-against flag is listed on this stored result. "
                "This reply does not add or remove one."
            )
    if "next" in folded or "what should i do" in folded:
        missing = [str(item) for item in result.get("missing") or []]
        if missing:
            shown = "; ".join(missing[:6])
            lines.append(
                f"Next, the engine already lists these missing items: {shown}. "
                "Entering them is your edit on the draft. This reply does not write them."
            )
        elif "INSUFFICIENT_DEMAND_EVIDENCE" in flags:
            lines.append(
                "Next, gather verified demand evidence and save it on the draft. "
                "This reply does not clear the flag."
            )
        else:
            lines.append(
                "Next, read the recommend-against flags and the evidence checklist on this file. "
                "This reply does not close them."
            )
    if "gate" in folded:
        lines.extend(_indicative_reading(result))
        lines.append(
            "In everyday words: a blocked gate means a hard recommend-against flag is still active, "
            "so the recommendation stays do-not-proceed. An open gate is not investor-ready. "
            "This reply does not change the gate."
        )
    if "recommend" in folded:
        lines.append(
            f"The stored recommendation is {result.get('recommendation')}. "
            "A hard recommend-against flag keeps the gate at do-not-proceed. "
            "This reply does not change the recommendation."
        )
    if "investor" in folded:
        lines.append(
            f"Investor readiness on this stored result is {result.get('readiness_status')}. "
            "Asking a question does not set human_review_approved and does not grant investor-ready status."
        )
    if "market" in folded:
        notes = [str(item) for item in (market_notes or []) if str(item).strip()]
        if notes:
            lines.append(
                "Market observations already attached to this question, as observations only: "
                + "; ".join(notes[:4])
                + ". They do not clear a flag."
            )
        else:
            lines.append(
                "No market observation is stored on this engine result. "
                "The Market Intelligence page is a labeled demonstration unless a public extract was requested. "
                "This reply does not add a market figure."
            )
    lines.append(
        f"Stored recommendation: {result.get('recommendation')}. "
        f"Investor readiness: {result.get('readiness_status')}. "
        f"human_review_approved: {str(bool(result.get('human_review_approved'))).lower()}."
    )
    for flag in flags:
        lines.append(f"Recommend-against flag still active: {flag}.")
    if not flags:
        lines.append("No recommend-against flag is listed on this stored result. This reply does not add or remove one.")
    return lines


def _indicative_reading(result: dict[str, Any]) -> list[str]:
    from app.indicative_score import indicative_score

    score = indicative_score(copy.deepcopy(result))
    return [
        (
            f"Indicative gate status is {score.get('gate_status')}, band {score.get('band')}, "
            f"gate recommendation {score.get('gate_recommendation')}. "
            "A recommend-against flag forces Blocked and do-not-proceed. "
            "The indicative number does not replace the feasibility line."
        )
    ]


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


def _summary(record: dict[str, Any], result: dict[str, Any] | None) -> dict[str, Any]:
    """Assessment summary for a provider. Secret keys are removed before the call."""
    engine_result = _without_secrets(result) if result is not None else None
    if isinstance(engine_result, dict):
        engine_result.pop("report_markdown", None)
    return {
        "business_name": record.get("business_name"),
        "purpose": record.get("purpose"),
        "tier": record.get("tier"),
        "hypothetical": bool(record.get("hypothetical")),
        "read_only": bool(record.get("read_only")),
        "pilot_label": record.get("pilot_label"),
        "profile": _without_secrets(record.get("profile") or {}),
        "engine_result": engine_result,
    }


def _response_text(provider: str, payload: dict[str, Any]) -> str:
    if provider == "claude":
        parts = payload.get("content") or []
        texts = [
            str(item.get("text"))
            for item in parts
            if isinstance(item, dict) and item.get("text")
        ]
        if not texts:
            raise ValueError("empty analyst response")
        return "\n".join(texts)
    choices = payload.get("choices") or []
    if not choices or not isinstance(choices[0], dict):
        raise ValueError("empty analyst response")
    message = choices[0].get("message") or {}
    content = message.get("content") if isinstance(message, dict) else None
    if not content:
        raise ValueError("empty analyst response")
    return str(content)


def _post_json(url: str, headers: dict[str, str], payload: dict[str, Any]) -> dict[str, Any]:
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.URLError as exc:
        raise RuntimeError("analyst provider request failed") from exc

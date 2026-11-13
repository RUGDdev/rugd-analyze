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
        "model": "claude-sonnet-5-5",
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
MAX_OUTPUT_TOKENS = 600
MAX_USER_CHARS = 12000
MAX_REPLY_CHARS = 4000
REQUEST_TIMEOUT_SECONDS = 20
MAX_HISTORY_MESSAGES = 6


ASSISTANCE_LABEL = (
    "Assistance only. It cannot change numbers, lift a concern, or approve anything."
)

# Internal text. It goes to the provider as the system message and is never shown to a customer.
_INTERNAL_MARKERS = (
    "you are the rugd analyst",
    "explain only the assessment summary you are given",
    "your reply is an explanation, not a decision",
)


def customer_lines(text: str) -> list[str]:
    """Split a provider reply into display lines and drop any echo of the internal prompt."""
    lines: list[str] = []
    for raw in str(text or "").splitlines():
        line = raw.strip()
        if not line:
            continue
        folded = line.lower()
        if any(marker in folded for marker in _INTERNAL_MARKERS):
            continue
        lines.append(line)
    return lines

STARTER_QUESTIONS = (
    "What does my score mean?",
    "Why is demand evidence missing?",
    "What should I do next?",
    "What should I work on next?",
    "What does the recommendation mean?",
    "Why does it say important information is still needed?",
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
        self.label = f"External analyst ({provider}). Not the Demonstration Analyst."
        self._api_key = api_key
        self._model = model
        self._transport = transport or _post_json
        self.last_usage: dict[str, Any] = {}
        self.last_error_category = ""

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
        return [self.label, *customer_lines(text)]

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
        return [ASSISTANCE_LABEL, self.label, *customer_lines(text)]

    def _complete(self, summary: dict[str, Any]) -> str:
        spec = _PROVIDERS[self.provider]
        user = json.dumps(summary, default=str)
        if len(user) > MAX_USER_CHARS:
            user = user[:MAX_USER_CHARS]
        if self.provider == "claude":
            payload = {
                "model": self._model,
                "max_tokens": MAX_OUTPUT_TOKENS,
                "system": SAFETY_PROMPT,
                "messages": [{"role": "user", "content": user}],
            }
            # Sonnet 5.5 thinks by default, and thinking tokens count against max_tokens.
            # Without tools, between_tools returns text only. Older overrides omit the field.
            if self._model == "claude-sonnet-5-5":
                payload["thinking"] = {"type": "between_tools"}
            headers = {
                "content-type": "application/json",
                "x-api-key": self._api_key,
                "anthropic-version": "2026-10-21",
            }
        else:
            payload = {
                "model": self._model,
                "max_tokens": MAX_OUTPUT_TOKENS,
                "messages": [
                    {"role": "system", "content": SAFETY_PROMPT},
                    {"role": "user", "content": user},
                ],
            }
            headers = {
                "content-type": "application/json",
                "authorization": f"Bearer {self._api_key}",
            }
        try:
            response = self._transport(spec["url"], headers, payload)
        except ProviderCallError as exc:
            self.last_error_category = exc.category
            raise
        except TimeoutError:
            self.last_error_category = "timeout"
            raise
        except Exception:
            self.last_error_category = "unavailable"
            raise
        self.last_error_category = ""
        self.last_usage = _usage(response)
        return _response_text(self.provider, response)[:MAX_REPLY_CHARS]

    def complete_context(self, context: dict[str, Any], question: str) -> str:
        """One bounded provider call. A failure is left for the caller to handle. There is no retry."""
        history = context.get("recent_messages") if isinstance(context.get("recent_messages"), list) else []
        packet = {
            "context": {key: value for key, value in context.items() if key != "recent_messages"},
            "recent_messages": [
                item for item in history[:MAX_HISTORY_MESSAGES] if isinstance(item, dict)
            ],
            "question": str(question or "")[:500],
        }
        return self._complete(packet)


def _plain_title(code: str) -> str:
    from app import wording

    return wording.title_of(code)


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
        action = "Save the draft, then run Analyze to see what RUGD finds."
        href = f"/assessments/{assessment_id}#intake" if surface == "results" else "#intake"
        link_label = "Open the intake fields"
        questions = (
            "What should I do next?",
            "What evidence is still missing?",
            "What should I work on next?",
        )
    elif surface == "results":
        current = "results"
        if flags:
            action = (
                f"Start with the main open concern: {_plain_title(flags[0]).lower()}. "
                "Reading about it does not resolve it."
            )
        else:
            action = "Read the saved recommendation and the next steps."
        href = "#results-lead"
        link_label = "Read the saved result"
        questions = (
            "Explain this result",
            "What should I do next?",
            "Why does it say important information is still needed?",
        )
    else:
        current = "gaps"
        if missing:
            action = (
                "RUGD already lists the missing items on this draft. "
                "This suggestion does not fill them in."
            )
        elif flags:
            action = (
                f"Still open: {_plain_title(flags[0]).lower()}. "
                "This suggestion does not resolve it."
            )
        else:
            action = "Read the stored result. This suggestion does not change it."
        href = f"#evidence-checklist-{assessment_id}"
        link_label = "Open the evidence checklist"
        questions = (
            "What evidence is still missing?",
            "Explain this result",
            "What should I do next?",
        )
    name = str(record.get("business_name") or "this draft")
    return {
        "stages": AGENT_WORKFLOW,
        "current": current,
        "welcome": (
            f"Welcome. This adviser is reading {name}. "
            "It can point to a gap, explain a stored result, and suggest a next step."
        ),
        "action": action,
        "href": href,
        "link_label": link_label,
        "questions": questions,
    }


def provider_status(environ: Any | None = None) -> dict[str, Any]:
    """Report configuration without calling a provider or returning a credential."""
    env = os.environ if environ is None else environ
    raw = str(env.get("ANALYST_PROVIDER") or "").strip().lower()
    if raw in {"", "demo", "demonstration", "none"}:
        return {
            "provider": "",
            "mode": "deterministic",
            "credential_present": False,
            "adapter_implemented": True,
            "live_connectivity": "unverified",
            "max_output_tokens": MAX_OUTPUT_TOKENS,
            "timeout_seconds": REQUEST_TIMEOUT_SECONDS,
        }
    provider = _ALIASES.get(raw)
    if provider is None:
        return {
            "provider": raw,
            "mode": "fallback",
            "credential_present": False,
            "adapter_implemented": False,
            "live_connectivity": "unverified",
            "max_output_tokens": MAX_OUTPUT_TOKENS,
            "timeout_seconds": REQUEST_TIMEOUT_SECONDS,
        }
    present = bool(str(env.get(_PROVIDERS[provider]["key"]) or "").strip())
    return {
        "provider": provider,
        "mode": "configured" if present else "fallback",
        "credential_present": present,
        "adapter_implemented": True,
        "live_connectivity": "unverified",
        "max_output_tokens": MAX_OUTPUT_TOKENS,
        "timeout_seconds": REQUEST_TIMEOUT_SECONDS,
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
    """Sentences drawn from this assessment, in a supportive adviser's voice. No figure is invented."""
    from app import wording

    asked = " ".join(str(question or "").split()).strip()
    folded = asked.lower()
    lines = [
        f"You asked: {asked or 'a question about this assessment.'}",
    ]
    if record.get("read_only"):
        lines.append(
            "This is the official RUGD Intelligence baseline. It still needs real evidence of customer demand "
            "and an authorized review before its draft recommendation can change. Nothing I say changes that."
        )
    if "different" in folded or "business plan" in folded:
        lines.append(
            "A business plan tells your story. RUGD checks whether the evidence behind the story is there. "
            "A well-written plan, a preliminary evaluation, or a market example cannot stand in for proof that customers will buy, "
            "and none of them makes a business ready to show investors. "
            "When you ask for a public market extract, Market Intelligence shows its source and period."
        )
    if not result or not result.get("engine_ran"):
        lines.append(
            "RUGD has not analyzed this business yet. Save your answers, then run Analyze, and I can walk you through what it finds. "
            "This reply does not run the analysis, and I will not fill in a blank for you."
        )
        lines.append("Return to the intake on this draft and complete what you know. A blank stays blank.")
        return lines
    flags = [str(flag) for flag in result.get("blocking_flags") or []]
    if "score" in folded:
        lines.append(
            f"The saved score line reads: {result.get('score_line')}. "
            "In plain terms, RUGD does not give one overall feasibility score yet."
        )
        lines.extend(_indicative_reading(result))
    if "demand" in folded:
        if "INSUFFICIENT_DEMAND_EVIDENCE" in flags:
            lines.append(
                "Customer demand is the missing piece. RUGD has no documented proof yet that customers will buy. "
                "What helps is real evidence: signed commitments, pre-orders, deposits, or documented sales from an existing business, "
                "saved as verified evidence in Research. Telling me it is true is not enough, and this reply does not lift the concern."
            )
        else:
            lines.append(
                "No demand-evidence concern is on file for this assessment right now. "
                "This reply does not add or remove one."
            )
    if "explain" in folded:
        lines.append(
            f"Where things stand: {wording.recommendation_label(str(result.get('recommendation') or '')).lower()}, "
            f"and {wording.readiness_label(str(result.get('readiness_status') or '')).lower()}. "
            "That is a draft reading of what is saved. Explaining it does not change it."
        )
        lines.extend(_indicative_reading(result))
    if "evidence" in folded or "missing" in folded:
        missing = [str(item) for item in result.get("missing") or []]
        if missing:
            shown = "; ".join(item.rstrip(". ") for item in missing[:6])
            lines.append(
                f"These items are still missing: {shown}. "
                "You fill them in on the draft. I will not fill them in for you."
            )
        if flags:
            listed = "; ".join(wording.title_of(flag) for flag in flags)
            lines.append(f"Still open: {listed}. Nothing I say closes them.")
        elif not missing:
            lines.append("Nothing is listed as missing on this saved result. This reply does not add or remove anything.")
    if "next" in folded or "what should i do" in folded:
        missing = [str(item) for item in result.get("missing") or []]
        if missing:
            shown = "; ".join(item.rstrip(". ") for item in missing[:6])
            lines.append(
                f"A good next step is to enter the missing items: {shown}. "
                "Those are your edits on the draft. I will not write them in for you, and this reply does not lift the concern."
            )
        elif "INSUFFICIENT_DEMAND_EVIDENCE" in flags:
            lines.append(
                "A good next step is to gather evidence that customers will buy, such as signed commitments, deposits, or documented sales, "
                "and save it in Research. This reply does not lift the concern; real evidence and an authorized review do."
            )
        else:
            lines.append(
                "A good next step is to read what is still open and work through the evidence checklist on this file. "
                "This reply does not close anything."
            )
    if "gate" in folded or "important information" in folded:
        lines.extend(_indicative_reading(result))
        lines.append(
            "\"Important information still needed\" means something essential, usually proof that customers will buy, is missing. "
            "Until it is on file, the draft stays at not ready to go ahead, and a result that is not blocked is still not ready to show investors. "
            "This reply does not change that."
        )
    if "recommend" in folded:
        lines.append(
            f"RUGD's draft recommendation is: {wording.recommendation_label(str(result.get('recommendation') or '')).lower()}. "
            "A serious concern on file keeps it there. This reply does not change the recommendation."
        )
    if "investor" in folded:
        lines.append(
            f"Right now the file is marked: {wording.readiness_label(str(result.get('readiness_status') or '')).lower()}. "
            "Asking a question does not approve anything and does not grant investor-ready status."
        )
    if "market" in folded:
        notes = [str(item) for item in (market_notes or []) if str(item).strip()]
        if notes:
            lines.append(
                "Market observations already attached to this question, as observations only: "
                + "; ".join(notes[:4])
                + ". They do not lift a concern."
            )
        else:
            lines.append(
                "No market observation is saved on this result. "
                "The Market Intelligence page is a labeled demonstration unless a public extract was requested. "
                "This reply does not add a market figure."
            )
    lines.append(
        f"Where things stand: {wording.recommendation_label(str(result.get('recommendation') or '')).lower()}; "
        f"{wording.readiness_label(str(result.get('readiness_status') or '')).lower()}; "
        f"{wording.review_label('approved' if result.get('human_review_approved') else 'pending').lower()}."
    )
    for flag in flags:
        lines.append(f"Still open: {wording.title_of(flag)}.")
    if not flags:
        lines.append("No serious concern is listed on this saved result. This reply does not add or remove one.")
    return lines


def _indicative_reading(result: dict[str, Any]) -> list[str]:
    from app import wording
    from app.indicative_score import indicative_score

    score = indicative_score(copy.deepcopy(result))
    return [
        (
            f"The preliminary business evaluation reads: {wording.gate_label(str(score.get('gate_status')))}, "
            f"{wording.band_label(str(score.get('band'))).lower()}. "
            "A serious concern on file holds it there, whatever the numbers say. "
            "It is a reading aid and does not replace the saved recommendation."
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


def _usage(payload: dict[str, Any]) -> dict[str, Any]:
    """Token counts from a provider body. Credentials are not part of this object."""
    raw = payload.get("usage") if isinstance(payload.get("usage"), dict) else {}
    usage: dict[str, Any] = {}
    for source, target in (
        ("input_tokens", "input_tokens"),
        ("output_tokens", "output_tokens"),
        ("prompt_tokens", "input_tokens"),
        ("completion_tokens", "output_tokens"),
    ):
        value = raw.get(source)
        if isinstance(value, int) and not isinstance(value, bool):
            usage[target] = value
    return usage


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


class ProviderCallError(RuntimeError):
    """A failed provider call reduced to a category. The response body is not kept."""

    def __init__(self, category: str) -> None:
        self.category = category
        super().__init__(f"analyst provider request failed: {category}")


def provider_error_category(exc: BaseException) -> str:
    """Name the failure without the response body, the URL, or a credential."""
    if isinstance(exc, TimeoutError):
        return "timeout"
    if isinstance(exc, urllib.error.HTTPError):
        code = int(getattr(exc, "code", 0) or 0)
        if code in {401, 403, 404, 429}:
            return f"http_{code}"
        if code == 408:
            return "timeout"
        if code == 400:
            return "http_400"
        if 500 <= code <= 599:
            return "http_5xx"
        return "http_error"
    if isinstance(exc, urllib.error.URLError):
        reason = getattr(exc, "reason", exc)
        if isinstance(reason, TimeoutError):
            return "timeout"
        text = str(reason).lower()
        if "timed out" in text:
            return "timeout"
        if "getaddrinfo" in text or "name or service not known" in text or "nodename nor servname" in text:
            return "dns"
        if "certificate" in text or "tls" in text or "ssl" in text:
            return "tls"
        return "connection"
    return "unavailable"


def _post_json(url: str, headers: dict[str, str], payload: dict[str, Any]) -> dict[str, Any]:
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT_SECONDS) as response:
            return json.loads(response.read().decode("utf-8"))
    except TimeoutError as exc:
        raise ProviderCallError("timeout") from exc
    except urllib.error.URLError as exc:
        raise ProviderCallError(provider_error_category(exc)) from exc

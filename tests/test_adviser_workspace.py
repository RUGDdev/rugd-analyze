"""The adviser explains stored context and cannot change an official result."""

from __future__ import annotations

import hashlib
import os
import tempfile
import threading
import unittest
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

import app.server as server_module
from app.access import DENIAL
from app.adviser_context import build_adviser_context
from app.adviser_workspace import ask_adviser
from app.analyst import (
    MAX_OUTPUT_TOKENS,
    MAX_USER_CHARS,
    SAFETY_PROMPT,
    ExternalAnalyst,
    get_analyst,
    provider_status,
)
from app.server import make_server
from app.store import (
    BASELINE_ID,
    SAMPLE,
    connect,
    create_assessment,
    get_assessment,
    get_business_plan,
    insert_business_plan,
    seed,
)
from app.plan import build_plan_document
from engine.financial import FinancialInputs, result_to_dict, run_financials
from tests.session_cookie import open_customer

_ENV = (
    "ANALYST_PROVIDER",
    "ANALYST_MODEL",
    "ANTHROPIC_API_KEY",
    "OPENAI_API_KEY",
    "XAI_API_KEY",
)


class TestAdviserWorkspace(unittest.TestCase):
    def setUp(self) -> None:
        self._saved = {key: os.environ.get(key) for key in _ENV}
        for key in _ENV:
            os.environ.pop(key, None)
        self._transport = server_module.analyst_transport
        server_module.analyst_transport = None

    def tearDown(self) -> None:
        for key, value in self._saved.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        server_module.analyst_transport = self._transport

    def test_provider_status_and_missing_credentials_do_not_call_out(self) -> None:
        demo = provider_status({})
        self.assertEqual(demo["mode"], "deterministic")
        self.assertFalse(demo["credential_present"])
        self.assertEqual(demo["live_connectivity"], "unverified")
        self.assertIsInstance(get_analyst(environ={}), type(get_analyst()))
        missing = provider_status({"ANALYST_PROVIDER": "claude"})
        self.assertEqual(missing["mode"], "fallback")
        self.assertEqual(missing["provider"], "claude")
        self.assertFalse(missing["credential_present"])
        self.assertTrue(missing["adapter_implemented"])
        self.assertEqual(missing["live_connectivity"], "unverified")
        fallback = get_analyst(environ={"ANALYST_PROVIDER": "claude"})
        self.assertIn("No API key is configured.", fallback.label)
        unknown = provider_status({"ANALYST_PROVIDER": "made-up"})
        self.assertFalse(unknown["adapter_implemented"])
        configured = provider_status({"ANALYST_PROVIDER": "openai", "OPENAI_API_KEY": "sk-live-secret"})
        self.assertEqual(configured["mode"], "configured")
        self.assertTrue(configured["credential_present"])
        self.assertNotIn("sk-live-secret", str(configured))
        self.assertEqual(configured["live_connectivity"], "unverified")

    def test_claude_openai_and_grok_adapters_parse_mocked_responses(self) -> None:
        record = {"business_name": "Harbor Books", "profile": {"token": "raw-session-token"}}
        result = _result()
        seen = []

        def claude(url: str, headers: dict[str, str], payload: dict[str, object]) -> dict[str, object]:
            seen.append(url)
            self.assertEqual(payload["max_tokens"], MAX_OUTPUT_TOKENS)
            self.assertEqual(payload["system"], SAFETY_PROMPT)
            self.assertNotIn("raw-session-token", str(payload))
            self.assertNotIn("claude-secret", str(payload))
            return {
                "content": [{"text": "Stored cash flow stays the engine figure."}],
                "usage": {"input_tokens": 12, "output_tokens": 4},
            }

        analyst = get_analyst(
            environ={"ANALYST_PROVIDER": "claude", "ANTHROPIC_API_KEY": "claude-secret"},
            transport=claude,
        )
        self.assertIsInstance(analyst, ExternalAnalyst)
        text = analyst.complete_context(build_adviser_context(record | {"result": result}), "What is cash flow?")
        self.assertIn("api.anthropic.com", seen[0])
        self.assertIn("engine figure", text)
        self.assertEqual(analyst.last_usage, {"input_tokens": 12, "output_tokens": 4})
        self.assertNotIn("claude-secret", text)

        def openai(url: str, headers: dict[str, str], payload: dict[str, object]) -> dict[str, object]:
            seen.append(url)
            self.assertIn("Bearer openai-secret", headers["authorization"])
            self.assertEqual(payload["max_tokens"], MAX_OUTPUT_TOKENS)
            self.assertNotIn("openai-secret", str(payload))
            return {"choices": [{"message": {"content": "OpenAI mock reply."}}], "usage": {"prompt_tokens": 3, "completion_tokens": 2}}

        openai_analyst = get_analyst(
            environ={"ANALYST_PROVIDER": "chatgpt", "OPENAI_API_KEY": "openai-secret"},
            transport=openai,
        )
        openai_text = openai_analyst.complete_context({"customer_facts": {"business_name": "Harbor Books"}}, "Explain")
        self.assertIn("api.openai.com", seen[-1])
        self.assertEqual(openai_text, "OpenAI mock reply.")
        self.assertEqual(openai_analyst.last_usage["input_tokens"], 3)

        def grok(url: str, headers: dict[str, str], payload: dict[str, object]) -> dict[str, object]:
            seen.append(url)
            self.assertIn(SAFETY_PROMPT, str(payload["messages"]))
            raise TimeoutError("timed out")

        grok_analyst = get_analyst(
            environ={"ANALYST_PROVIDER": "xai", "XAI_API_KEY": "xai-secret"},
            transport=grok,
        )
        calls = {"n": 0}

        def counting(url: str, headers: dict[str, str], payload: dict[str, object]) -> dict[str, object]:
            calls["n"] += 1
            self.assertIn("api.x.ai", url)
            self.assertLessEqual(len(str(payload["messages"][1]["content"])), MAX_USER_CHARS)
            raise TimeoutError("timed out")

        grok_analyst._transport = counting
        context = build_adviser_context(record | {"result": result})
        context["recent_messages"] = [{"role": "customer", "text": "x" * 5000} for _ in range(20)]
        outcome = ask_adviser(context, "What is the stored cash flow?", grok_analyst)
        self.assertEqual(calls["n"], 1)
        self.assertEqual(outcome["source"], "fallback")
        self.assertIn("could not be reached", outcome["text"])
        self.assertIn(str(result["financial"]["base_monthly_cash_flow"]), outcome["text"])
        self.assertEqual(result["recommendation"], "do-not-proceed")

    def test_context_keeps_figures_and_names_missing_evidence(self) -> None:
        expected = result_to_dict(run_financials(FinancialInputs(10000, 400, 0.5, 1000, 0.6)))
        record = {
            "id": "harbor",
            "business_name": "Harbor Books",
            "profile": {
                "business_name": "Harbor Books",
                "concept": "A neighborhood bookstore.",
                "industry": "Retail",
                "projected_monthly_revenue_base": 1000,
                "token": "hide-me",
            },
            "result": {
                **_result(),
                "financial": expected,
                "missing": ["Demand evidence"],
            },
        }
        before = expected["base_monthly_cash_flow"]
        context = build_adviser_context(
            record,
            plans=[{"id": "plan-1", "title": "Harbor plan"}],
            decks=[{"id": "deck-1", "title": "Harbor deck"}],
            actions=[{"title": "Collect demand evidence", "status": "open"}],
        )
        self.assertEqual(context["verified_calculations"]["base_monthly_cash_flow"], before)
        self.assertEqual(context["customer_facts"]["concept"], "A neighborhood bookstore.")
        self.assertNotIn("hide-me", str(context))
        self.assertIn("INSUFFICIENT_DEMAND_EVIDENCE", context["risk_flags"])
        self.assertIn("Demand evidence", context["missing_evidence"])
        reply = ask_adviser(context, "What cash flow and missing market evidence are stored?", get_analyst(environ={}))
        self.assertEqual(reply["source"], "deterministic")
        self.assertIn("No outside AI service was used", reply["text"])
        self.assertIn(str(before), reply["text"])
        self.assertIn("INSUFFICIENT_DEMAND_EVIDENCE", reply["text"])
        self.assertIn("Market size is not treated as verified", reply["text"])
        self.assertIsNone(reply["proposal"])
        self.assertEqual(record["result"]["financial"]["base_monthly_cash_flow"], before)
        proposal = ask_adviser(context, "Suggest a plan narrative improvement.", get_analyst(environ={}))
        self.assertEqual(proposal["proposal"]["status"], "review")
        self.assertEqual(proposal["proposal"]["target_id"], "plan-1")
        self.assertIn("neighborhood bookstore", proposal["proposal"]["text"])
        self.assertNotIn("investor-ready", proposal["proposal"]["text"])

    def test_http_conversation_persists_and_stays_private(self) -> None:
        directory = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        database = Path(directory.name) / "analyze.sqlite"
        connection = connect(database)
        seed(connection)
        server = make_server(database, port=0)
        calls = {"n": 0}

        def transport(url: str, headers: dict[str, str], payload: dict[str, object]) -> dict[str, object]:
            calls["n"] += 1
            return {"choices": [{"message": {"content": "Mock live reply."}}]}

        server_module.analyst_transport = transport
        os.environ["ANALYST_PROVIDER"] = "openai"
        os.environ["OPENAI_API_KEY"] = "sk-browser-secret"
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        base = f"http://127.0.0.1:{server.server_address[1]}"
        try:
            cookie, user_id = open_customer(connection, base)
            other, _other_id = open_customer(connection, base)
            sample_before = hashlib.sha256(SAMPLE.read_bytes()).hexdigest()
            expected = result_to_dict(run_financials(FinancialInputs(10000, 400, 0.5, 1000, 0.6)))
            assessment_id = create_assessment(
                connection,
                business_name="Harbor Books",
                purpose="startup_feasibility",
                tier="explore",
                owner_user_id=user_id,
            )
            analyzed = _raw(
                base + f"/assessments/{assessment_id}/analyze",
                {
                    "business_name": "Harbor Books",
                    "concept": "A neighborhood bookstore.",
                    "initial_capital": "10000",
                    "monthly_fixed_costs": "400",
                    "gross_margin_pct": "0.5",
                    "projected_monthly_revenue_base": "1000",
                    "downside_multiplier": "0.6",
                },
                cookie,
            )
            self.assertEqual(analyzed[0], 303)
            record = get_assessment(connection, assessment_id)
            assert record is not None
            plan = insert_business_plan(
                connection,
                assessment_id=assessment_id,
                created_by=user_id,
                title="Harbor plan",
                document=build_plan_document(record),
            )
            sections_before = plan["document"]["sections"]
            home = _get(base + "/adviser", cookie)
            self.assertEqual(home[0], 200)
            self.assertIn("Harbor Books", home[1])
            self.assertIn("has not verified a live connection", home[1])
            self.assertNotIn("sk-browser-secret", home[1])
            opened = _get(base + f"/assessments/{assessment_id}/advice", cookie)
            self.assertEqual(calls["n"], 0)
            self.assertIn(str(expected["base_monthly_cash_flow"]), opened[1])
            self.assertIn("INSUFFICIENT_DEMAND_EVIDENCE", opened[1])
            asked = _raw(
                base + f"/assessments/{assessment_id}/advice",
                {"question": "What is the stored cash flow? <script>alert(1)</script>"},
                cookie,
            )
            self.assertEqual(asked[0], 303)
            self.assertEqual(calls["n"], 1)
            path = asked[2].get("Location") or ""
            page = _get(base + path, cookie)
            self.assertEqual(calls["n"], 1)
            self.assertIn("Mock live reply.", page[1])
            self.assertIn("&lt;script&gt;alert(1)&lt;/script&gt;", page[1])
            self.assertNotIn("<script>alert(1)</script>", page[1])
            self.assertNotIn("sk-browser-secret", page[1])
            proposed = _raw(
                base + path.split("?", 1)[0],
                {"question": "Suggest a plan narrative improvement."},
                cookie,
            )
            self.assertEqual(proposed[0], 303)
            review = _get(base + (proposed[2].get("Location") or ""), cookie)
            self.assertIn("Proposal for review", review[1])
            self.assertIn("neighborhood bookstore", review[1])
            self.assertIn("Approve and save", review[1])
            conversation_id = path.split("?", 1)[0].rstrip("/").rsplit("/", 1)[-1]
            rejected_plan = get_business_plan(connection, plan["id"])
            assert rejected_plan is not None
            _raw(
                base + f"/assessments/{assessment_id}/advice/{conversation_id}/decision",
                {"decision": "reject"},
                cookie,
            )
            after_reject = get_business_plan(connection, plan["id"])
            assert after_reject is not None
            self.assertNotIn("adviser_suggestion", after_reject["document"])
            self.assertEqual(after_reject["document"]["sections"], sections_before)
            stored = get_assessment(connection, assessment_id)
            assert stored is not None and stored["result"] is not None
            self.assertEqual(stored["result"]["financial"]["base_monthly_cash_flow"], expected["base_monthly_cash_flow"])
            self.assertEqual(stored["result"]["recommendation"], "do-not-proceed")
            self.assertFalse(stored["human_review_approved"])
            asked_again = _raw(
                base + f"/assessments/{assessment_id}/advice/{conversation_id}",
                {"question": "Suggest a plan narrative improvement."},
                cookie,
            )
            self.assertEqual(asked_again[0], 303)
            approved = _raw(
                base + f"/assessments/{assessment_id}/advice/{conversation_id}/decision",
                {"decision": "approve"},
                cookie,
            )
            self.assertEqual(approved[0], 303)
            saved = get_business_plan(connection, plan["id"])
            assert saved is not None
            self.assertIn("neighborhood bookstore", saved["document"].get("adviser_suggestion") or "")
            self.assertEqual(saved["document"]["sections"], sections_before)
            self.assertEqual(saved["document"]["snapshot"], rejected_plan["document"]["snapshot"])
            reloaded = _get(base + f"/assessments/{assessment_id}/advice/{conversation_id}", cookie)
            self.assertIn("Approved suggestions", reloaded[1])
            self.assertIn("neighborhood bookstore", reloaded[1])
            denied = _get(base + f"/assessments/{assessment_id}/advice/{conversation_id}", other)
            self.assertEqual(denied[0], 403)
            self.assertIn(DENIAL, denied[1])
            self.assertNotIn("Harbor Books", denied[1])
            self.assertNotIn("neighborhood bookstore", denied[1])
            self.assertNotIn("Mock live reply.", denied[1])
            self.assertEqual(_raw(base + f"/assessments/{assessment_id}/advice/{conversation_id}/decision", {"decision": "approve"}, other)[0], 403)
            baseline = _raw(base + f"/assessments/{BASELINE_ID}/advice", {"question": "Suggest a plan narrative."}, cookie)
            self.assertEqual(baseline[0], 403)
            official = get_assessment(connection, BASELINE_ID)
            assert official is not None
            self.assertIsNone(official.get("result"))
            self.assertFalse(official["human_review_approved"])
            from app.analysis import analyze_record

            checked = analyze_record(official)
            self.assertEqual(checked["recommendation"], "do-not-proceed")
            self.assertIn("INSUFFICIENT_DEMAND_EVIDENCE", checked["blocking_flags"])
            self.assertEqual(checked["readiness_status"], "internal")
            self.assertFalse(checked["human_review_approved"])
            self.assertIsNone(get_assessment(connection, BASELINE_ID).get("result"))
            self.assertEqual(hashlib.sha256(SAMPLE.read_bytes()).hexdigest(), sample_before)
            index = _get(base + "/adviser", other)
            self.assertNotIn("Harbor Books", index[1])
        finally:
            connection.close()
            server.shutdown()
            directory.cleanup()


def _result() -> dict:
    return {
        "engine_ran": True,
        "recommendation": "do-not-proceed",
        "blocking_flags": ["INSUFFICIENT_DEMAND_EVIDENCE"],
        "gap_flags": [],
        "missing": [],
        "readiness_status": "internal",
        "human_review_approved": False,
        "is_final": False,
        "score_line": "Not calculated — methodology pending approval.",
        "financial": {"base_monthly_cash_flow": 100.0},
    }


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def _raw(url: str, form: dict[str, str], cookie: str) -> tuple[int, str, dict[str, str]]:
    request = urllib.request.Request(
        url,
        data=urllib.parse.urlencode(form).encode(),
        headers={"Cookie": cookie},
        method="POST",
    )
    try:
        response = urllib.request.build_opener(_NoRedirect).open(request)
        code = response.status
        body = response.read().decode("utf-8", "replace")
        headers = dict(response.headers)
    except urllib.error.HTTPError as exc:
        code = exc.code
        body = exc.read().decode("utf-8", "replace")
        headers = dict(exc.headers)
    return code, body, headers


def _get(url: str, cookie: str) -> tuple[int, str]:
    request = urllib.request.Request(url, headers={"Cookie": cookie})
    try:
        response = urllib.request.urlopen(request)
        return response.status, response.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode("utf-8", "replace")


if __name__ == "__main__":
    unittest.main()

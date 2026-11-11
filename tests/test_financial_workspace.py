"""Live financial previews and saved business plans stay outside the official result."""

from __future__ import annotations

import hashlib
import re
import tempfile
import threading
import unittest
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from app.access import DENIAL
from app.charts import render_financial_graphics
from app.plan import build_plan_document, edited_sections, plan_markdown
from app.preview import calculate_preview, preview_markup
from app.review import SESSION_COOKIE
from app.server import make_server
from app.store import BASELINE_ID, SAMPLE, connect, create_assessment, get_assessment, seed
from engine.financial import FinancialInputs, result_to_dict, run_financials
from engine.startup_projection import record_for_intake
from tests.session_cookie import open_customer

PASSWORD = "workspace-pass-1"


class TestFinancialWorkspace(unittest.TestCase):
    def test_preview_matches_the_engine_and_leaves_blanks_blank(self) -> None:
        expected = result_to_dict(run_financials(FinancialInputs(10000, 400, 0.5, 1000, 0.6)))
        preview = calculate_preview(
            {
                "initial_capital": "10000",
                "monthly_fixed_costs": "400",
                "gross_margin_pct": "0.5",
                "projected_monthly_revenue_base": "1000",
                "downside_multiplier": "0.6",
            }
        )
        financial = preview["financial"]
        assert financial is not None
        self.assertEqual(financial["base_monthly_cash_flow"], expected["base_monthly_cash_flow"])
        self.assertEqual(financial["base_monthly_contribution"], expected["base_monthly_contribution"])
        self.assertEqual(financial["break_even_monthly_revenue"], expected["break_even_monthly_revenue"])
        self.assertEqual(financial["downside_monthly_cash_flow"], expected["downside_monthly_cash_flow"])
        blank = calculate_preview({"initial_capital": "", "monthly_fixed_costs": "0"})
        self.assertIsNone(blank["financial"])
        self.assertFalse(blank["monthly_issues"])
        invalid = calculate_preview({"projected_monthly_revenue_base": "abc", "gross_margin_pct": "2"})
        self.assertIsNone(invalid["financial"])
        self.assertTrue(invalid["monthly_issues"])
        zero = calculate_preview(
            {
                "initial_capital": "10000",
                "monthly_fixed_costs": "0",
                "gross_margin_pct": "0.5",
                "projected_monthly_revenue_base": "1000",
                "downside_multiplier": "0.6",
            }
        )
        assert zero["financial"] is not None
        self.assertEqual(
            zero["financial"]["base_monthly_cash_flow"],
            result_to_dict(run_financials(FinancialInputs(10000, 0, 0.5, 1000, 0.6)))["base_monthly_cash_flow"],
        )

    def test_startup_preview_uses_the_projection_and_skips_a_partial_worksheet(self) -> None:
        fields = {
            "construction_cost": "100000",
            "seats": "20",
            "average_ticket": "15",
            "weekday_occupancy": "0.4",
            "weekend_occupancy": "0.6",
            "operating_days": "300",
            "contribution_margin": "0.6",
        }
        preview = calculate_preview(fields)
        expected = record_for_intake(
            {
                "startup_capital": {
                    "construction_cost": 100000.0,
                    "seats": 20.0,
                    "average_ticket": 15.0,
                    "weekday_occupancy": 0.4,
                    "weekend_occupancy": 0.6,
                    "operating_days": 300.0,
                    "contribution_margin": 0.6,
                    "verified": {key: False for key in fields},
                }
            },
            human_review_approved=False,
        )
        assert preview["projection"] is not None
        self.assertEqual(
            preview["projection"]["sources_and_uses"]["uses"]["total_project_cost"]["amount"],
            expected["sources_and_uses"]["uses"]["total_project_cost"]["amount"],
        )
        self.assertFalse(preview["projection"]["human_review_approved"])
        self.assertFalse(preview["projection"]["investor_ready"])
        self.assertEqual(
            preview["projection"]["views"]["base"]["revenue"],
            expected["views"]["base"]["revenue"],
        )
        partial = calculate_preview({"construction_cost": "100000", "seats": ""})
        self.assertIsNone(partial["projection"])
        refused = calculate_preview({**fields, "seats": "abc"})
        self.assertIsNone(refused["projection"])
        self.assertTrue(refused["startup_issues"])

    def test_plan_edit_does_not_replace_copied_figures(self) -> None:
        record = {
            "id": "plan-unit",
            "business_name": "Plan Cafe",
            "updated_at": "2026-11-11T00:00:00+00:00",
            "profile": {
                "business_name": "Plan Cafe",
                "concept": "",
                "customer_objective": "start-business",
                "initial_capital": "10000",
                "monthly_fixed_costs": "400",
                "gross_margin_pct": "0.5",
                "projected_monthly_revenue_base": "1000",
                "downside_multiplier": "0.6",
            },
            "result": {
                "engine_ran": True,
                "recommendation": "do-not-proceed",
                "blocking_flags": ["INSUFFICIENT_DEMAND_EVIDENCE"],
                "gap_flags": [],
                "readiness_status": "internal",
                "human_review_status": "pending",
                "human_review_approved": False,
                "score_line": "Not calculated — methodology pending approval.",
                "financial": result_to_dict(run_financials(FinancialInputs(10000, 400, 0.5, 1000, 0.6))),
            },
            "scenarios": {},
        }
        document = build_plan_document(record)
        self.assertIn("Not written. This section was left blank.", document["sections"]["executive_summary"])
        self.assertIn("No Downside scenario is saved.", document["snapshot"]["downside_scenario"])
        cash = document["snapshot"]["base_results"]
        self.assertTrue(any("base_monthly_cash_flow: 100.0" in line for line in cash))
        sections = edited_sections(
            document,
            {
                "executive_summary": "Weekday neighbors are the first customers to ask.",
                "base_monthly_cash_flow": "1",
                "human_review_approved": "true",
            },
        )
        self.assertEqual(sections["executive_summary"], "Weekday neighbors are the first customers to ask.")
        self.assertNotIn("base_monthly_cash_flow", sections)
        self.assertTrue(any("base_monthly_cash_flow: 100.0" in line for line in document["snapshot"]["base_results"]))

    def test_graphics_keep_missing_distinct_from_zero_and_skip_a_trend(self) -> None:
        expected = result_to_dict(run_financials(FinancialInputs(10000, 400, 0.5, 1000, 0.6)))
        drawn = render_financial_graphics(
            expected,
            assumed_revenue=1000,
            assumed_fixed_costs=400,
            projection=None,
            preview=True,
        )
        self.assertIn('data-revenue-gap="200.0"', drawn["break_even"])
        self.assertIn("above the calculated break-even revenue", drawn["break_even"])
        self.assertIn('data-assumption-value="1000.0"', drawn["revenue"])
        self.assertIn('data-engine-value="-100.0"', drawn["revenue"])
        self.assertIn('fill="#27323B"', drawn["revenue"])
        self.assertIn("Base", drawn["comparison"])
        self.assertIn("Downside", drawn["comparison"])
        self.assertIn("-100.0. Calculated by the engine.", drawn["comparison"])
        self.assertIn("No category was added.", drawn["allocation"])
        self.assertNotIn("<svg", drawn["allocation"])
        self.assertIn("A trend line is not drawn.", drawn["trend"])
        self.assertNotIn("<svg", drawn["trend"])
        blank = render_financial_graphics(None, assumed_revenue=None, assumed_fixed_costs=0, projection=None, preview=True)
        self.assertIn("Monthly revenue: Missing.", blank["revenue"])
        self.assertNotIn("Monthly revenue: 0.", blank["revenue"])
        self.assertIn("Monthly fixed costs: 0. Customer-supplied assumption.", blank["revenue"])
        self.assertIn("The difference is not shown", blank["break_even"])
        partial = preview_markup({"construction_cost": "100000", "seats": ""})
        self.assertIn("No category was added.", partial)
        self.assertNotIn('data-chart="capital-allocation"><h3>Startup capital allocation</h3><svg', partial)

    def test_existing_business_plan_omits_startup_capital(self) -> None:
        record = {
            "id": "existing-1",
            "business_name": "Main Street Books",
            "profile": {"venture_path": "existing", "concept": "A neighborhood bookstore.", "business_name": "Main Street Books"},
            "result": None,
        }
        document = build_plan_document(record, actions=[{"title": "Confirm weekend sales", "status": "open", "description": ""}])
        self.assertEqual(document["stage"], "existing")
        self.assertIn("Confirm weekend sales", document["sections"]["implementation"])
        self.assertIn("not a DVT evaluation", document["sections"]["durable_value"])
        exported = plan_markdown(document, title="Main Street Books business plan")
        self.assertIn("Startup capital requirements are not part of this existing or expanding business.", exported)
        self.assertIn("This is not a live adviser response.", exported)
        self.assertNotIn("construction_cost:", exported)
        self.assertIn("## Executive Summary", exported)
        self.assertIn("## Implementation Priorities and Next Steps", exported)

    def test_http_preview_and_plan_keep_the_saved_result(self) -> None:
        directory = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        connection = connect(Path(directory.name) / "analyze.sqlite")
        seed(connection)
        sample_before = hashlib.sha256(SAMPLE.read_bytes()).hexdigest()
        server = make_server(Path(directory.name) / "analyze.sqlite", port=0)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        base = f"http://127.0.0.1:{server.server_address[1]}"
        try:
            cookie, user_id = open_customer(connection, base)
            other, _other_id = open_customer(connection, base)
            assessment_id = create_assessment(
                connection,
                business_name="Workspace Cafe",
                purpose="startup_feasibility",
                tier="analyze",
                owner_user_id=user_id,
            )
            draft = self._get(base + f"/assessments/{assessment_id}", cookie)
            self.assertIn('id="financial-workspace"', draft[1])
            self.assertIn("Update preview", draft[1])
            self.assertIn("finance-workspace", draft[1])

            waiting = self._raw(
                base + f"/assessments/{assessment_id}/preview",
                {"preview_fragment": "1", "initial_capital": ""},
                cookie,
            )
            self.assertEqual(waiting[0], 200)
            self.assertIn("not treated as zero", waiting[1])
            self.assertNotIn("base_monthly_cash_flow:", waiting[1])
            self.assertNotIn("do-not-proceed", waiting[1])
            self.assertIsNone(get_assessment(connection, assessment_id)["result"])

            refused = self._raw(
                base + f"/assessments/{assessment_id}/preview",
                {
                    "preview_fragment": "1",
                    "initial_capital": "10000",
                    "monthly_fixed_costs": "400",
                    "gross_margin_pct": "0.5",
                    "projected_monthly_revenue_base": "abc",
                    "downside_multiplier": "0.6",
                },
                cookie,
            )
            self.assertEqual(refused[0], 200)
            self.assertIn("not a finite number", refused[1])
            self.assertNotIn("base_monthly_cash_flow:", refused[1])
            self.assertIsNone(get_assessment(connection, assessment_id)["result"])

            expected = result_to_dict(run_financials(FinancialInputs(10000, 400, 0.5, 1000, 0.6)))
            shown = self._raw(
                base + f"/assessments/{assessment_id}/preview",
                {
                    "preview_fragment": "1",
                    "initial_capital": "10000",
                    "monthly_fixed_costs": "400",
                    "gross_margin_pct": "0.5",
                    "projected_monthly_revenue_base": "1000",
                    "downside_multiplier": "0.6",
                    "construction_cost": "100000",
                    "seats": "20",
                    "average_ticket": "15",
                    "weekday_occupancy": "0.4",
                    "weekend_occupancy": "0.6",
                    "operating_days": "300",
                    "contribution_margin": "0.6",
                },
                cookie,
            )
            self.assertEqual(shown[0], 200)
            self.assertIn("Preview. These figures were calculated", shown[1])
            self.assertIn(f"base_monthly_cash_flow: {expected['base_monthly_cash_flow']}", shown[1])
            self.assertIn('data-chart="preview-revenue"', shown[1])
            self.assertIn('data-chart="preview-cash-flow"', shown[1])
            self.assertIn('data-chart="preview-break-even"', shown[1])
            self.assertIn('data-chart="preview-capital"', shown[1])
            self.assertIn("startup_base_revenue:", shown[1])
            self.assertIn("Not saved.", shown[1])
            self.assertIn('data-revenue-gap="200.0"', shown[1])
            self.assertIn("Base and Downside", shown[1])
            self.assertIn('data-chart="capital-allocation"', shown[1])
            self.assertIn("construction_cost:", shown[1])
            self.assertIn("A trend line is not drawn.", shown[1])
            self.assertNotIn("do-not-proceed", shown[1])
            self.assertIsNone(get_assessment(connection, assessment_id)["result"])
            echoed = self._raw(
                base + f"/assessments/{assessment_id}/preview",
                {
                    "business_name": "Workspace Cafe",
                    "initial_capital": "10000",
                    "monthly_fixed_costs": "400",
                    "gross_margin_pct": "0.5",
                    "projected_monthly_revenue_base": "1000",
                    "downside_multiplier": "0.6",
                },
                cookie,
            )
            self.assertEqual(echoed[0], 200)
            self.assertIn('value="1000"', echoed[1])
            self.assertIn(f"base_monthly_cash_flow: {expected['base_monthly_cash_flow']}", echoed[1])
            self.assertIsNone(get_assessment(connection, assessment_id)["result"])
            self.assertNotEqual(get_assessment(connection, assessment_id)["profile"].get("projected_monthly_revenue_base"), "1000")

            blocked = self._raw(
                base + f"/assessments/{assessment_id}/preview",
                {"preview_fragment": "1", "human_review_approved": "true"},
                cookie,
            )
            self.assertEqual(blocked[0], 403)

            fields = {
                "initial_capital": "10000",
                "monthly_fixed_costs": "400",
                "gross_margin_pct": "0.5",
                "projected_monthly_revenue_base": "1000",
                "downside_multiplier": "0.6",
                "concept": "A neighborhood cafe",
                "construction_cost": "100000",
                "seats": "20",
                "average_ticket": "15",
                "weekday_occupancy": "0.4",
                "weekend_occupancy": "0.6",
                "operating_days": "300",
                "contribution_margin": "0.6",
            }
            ran = self._raw(base + f"/assessments/{assessment_id}/analyze", fields, cookie)
            self.assertEqual(ran[0], 303)
            stored = get_assessment(connection, assessment_id)
            assert stored is not None and stored["result"] is not None
            self.assertEqual(stored["result"]["financial"]["base_monthly_cash_flow"], expected["base_monthly_cash_flow"])
            self.assertEqual(stored["result"]["recommendation"], "do-not-proceed")
            self.assertIn("INSUFFICIENT_DEMAND_EVIDENCE", stored["result"]["blocking_flags"])
            self.assertFalse(stored["human_review_approved"])
            capital_before = stored["result"]["projection"]["sources_and_uses"]["uses"]["total_project_cost"]["amount"]

            later = self._raw(
                base + f"/assessments/{assessment_id}/preview",
                {
                    "preview_fragment": "1",
                    "initial_capital": "10000",
                    "monthly_fixed_costs": "400",
                    "gross_margin_pct": "0.5",
                    "projected_monthly_revenue_base": "800",
                    "downside_multiplier": "0.6",
                },
                cookie,
            )
            self.assertEqual(later[0], 200)
            changed = result_to_dict(run_financials(FinancialInputs(10000, 400, 0.5, 800, 0.6)))
            self.assertIn(f"base_monthly_cash_flow: {changed['base_monthly_cash_flow']}", later[1])
            untouched = get_assessment(connection, assessment_id)
            assert untouched is not None and untouched["result"] is not None
            self.assertEqual(untouched["result"]["financial"]["base_monthly_cash_flow"], expected["base_monthly_cash_flow"])
            self.assertEqual(
                untouched["result"]["projection"]["sources_and_uses"]["uses"]["total_project_cost"]["amount"],
                capital_before,
            )
            self.assertEqual(untouched["result"]["recommendation"], "do-not-proceed")

            created = self._raw(base + f"/assessments/{assessment_id}/plans", {}, cookie)
            self.assertEqual(created[0], 303)
            listing = self._get(base + f"/assessments/{assessment_id}/plans?saved=1", cookie)
            self.assertIn("Business plan saved.", listing[1])
            self.assertIn("Workspace Cafe business plan", listing[1])
            plan_path = re.findall(r'href="(/assessments/[^"]+/plans/[0-9a-f-]+)"', listing[1])[0]
            page = self._get(base + plan_path, cookie)
            self.assertEqual(page[0], 200)
            self.assertIn("A neighborhood cafe", page[1])
            self.assertIn(f"base_monthly_cash_flow: {expected['base_monthly_cash_flow']}", page[1])
            self.assertIn(f"total_project_cost: {capital_before}", page[1])
            self.assertIn("startup_base_revenue:", page[1])
            self.assertNotIn("Startup base revenue: Not available.", page[1])
            self.assertIn("do-not-proceed", page[1])
            self.assertIn("human_review_approved: false", page[1])
            self.assertIn("Save plan", page[1])
            self.assertIn("Export", page[1])
            self.assertIn("Financial Analysis and Projections", page[1])
            self.assertIn("Propose narrative", page[1])
            self.assertIn('data-chart="capital-allocation"', page[1])
            self.assertIn("A trend line is not drawn.", page[1])
            self.assertIn("Assembled from the saved assessment.", page[1])
            proposed = self._raw(base + plan_path + "/propose", {}, cookie)
            self.assertEqual(proposed[0], 200)
            self.assertIn("No live adviser is configured.", proposed[1])
            self.assertIn("A neighborhood cafe", proposed[1])
            self.assertNotIn("Live adviser proposal", proposed[1])

            saved = self._raw(
                base + plan_path,
                {
                    "executive_summary": "Ask weekday neighbors before buying equipment.",
                    "base_monthly_cash_flow": "1",
                },
                cookie,
            )
            self.assertEqual(saved[0], 303)
            edited = self._get(base + plan_path, cookie)
            self.assertIn("Ask weekday neighbors before buying equipment.", edited[1])
            self.assertIn(f"base_monthly_cash_flow: {expected['base_monthly_cash_flow']}", edited[1])
            after_edit = get_assessment(connection, assessment_id)
            assert after_edit is not None and after_edit["result"] is not None
            self.assertEqual(after_edit["result"]["recommendation"], "do-not-proceed")
            self.assertFalse(after_edit["human_review_approved"])
            self.assertIn("INSUFFICIENT_DEMAND_EVIDENCE", after_edit["result"]["blocking_flags"])

            exported = self._get(base + plan_path + "/export", cookie)
            self.assertEqual(exported[0], 200)
            self.assertIn("Ask weekday neighbors before buying equipment.", exported[1])
            self.assertIn(f"base_monthly_cash_flow: {expected['base_monthly_cash_flow']}", exported[1])
            printed = self._get(base + plan_path + "/print", cookie)
            self.assertIn("print-view", printed[1])
            self.assertIn("Ask weekday neighbors before buying equipment.", printed[1])

            fields["projected_monthly_revenue_base"] = "800"
            again = self._raw(base + f"/assessments/{assessment_id}/analyze", fields, cookie)
            self.assertEqual(again[0], 303)
            still = self._get(base + plan_path, cookie)
            self.assertIn(f"base_monthly_cash_flow: {expected['base_monthly_cash_flow']}", still[1])
            second = self._raw(base + f"/assessments/{assessment_id}/plans", {}, cookie)
            self.assertEqual(second[0], 303)
            history = self._get(base + "/history", cookie)
            self.assertEqual(history[1].count("Workspace Cafe business plan"), 2)
            latest = self._get(base + f"/assessments/{assessment_id}/plans", cookie)
            plan_pages = [
                self._get(base + path, cookie)[1]
                for path in dict.fromkeys(re.findall(r'href="(/assessments/[^"]+/plans/[0-9a-f-]+)"', latest[1]))
            ]
            self.assertEqual(len(plan_pages), 2)
            self.assertTrue(any(f"base_monthly_cash_flow: {expected['base_monthly_cash_flow']}" in page for page in plan_pages))
            self.assertTrue(any(f"base_monthly_cash_flow: {changed['base_monthly_cash_flow']}" in page for page in plan_pages))

            for cookie_value in (other, ""):
                denied = self._get(base + plan_path, cookie_value)
                self.assertEqual(denied[0], 403)
                self.assertIn(DENIAL, denied[1])
                self.assertNotIn("Workspace Cafe", denied[1])
                self.assertNotIn("weekday neighbors", denied[1])
                preview_denied = self._raw(
                    base + f"/assessments/{assessment_id}/preview",
                    {"preview_fragment": "1", "projected_monthly_revenue_base": "1000"},
                    cookie_value,
                )
                self.assertEqual(preview_denied[0], 403)
                self.assertNotIn("Workspace Cafe", preview_denied[1])
            self.assertNotIn("Workspace Cafe", self._get(base + "/plans", "")[1])
            self.assertNotIn("Workspace Cafe", self._get(base + "/history", other)[1])

            baseline_before = get_assessment(connection, BASELINE_ID)
            assert baseline_before is not None
            baseline_preview = self._raw(
                base + f"/assessments/{BASELINE_ID}/preview",
                {
                    "preview_fragment": "1",
                    "initial_capital": "10000",
                    "monthly_fixed_costs": "400",
                    "gross_margin_pct": "0.5",
                    "projected_monthly_revenue_base": "1000",
                    "downside_multiplier": "0.6",
                },
                cookie,
            )
            self.assertEqual(baseline_preview[0], 200)
            baseline_plan = self._raw(base + f"/assessments/{BASELINE_ID}/plans", {}, cookie)
            self.assertEqual(baseline_plan[0], 303)
            baseline_after = get_assessment(connection, BASELINE_ID)
            assert baseline_after is not None
            self.assertEqual(baseline_after["result"], baseline_before["result"])
            self.assertFalse(baseline_after["human_review_approved"])
            self.assertEqual(hashlib.sha256(SAMPLE.read_bytes()).hexdigest(), sample_before)
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=3)
            connection.close()
            directory.cleanup()

    def _get(self, url: str, cookie: str = "") -> tuple[int, str]:
        headers = {"Cookie": cookie} if cookie else {}
        request = urllib.request.Request(url, headers=headers)
        try:
            with urllib.request.urlopen(request) as response:
                return response.status, response.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            return exc.code, exc.read().decode("utf-8")

    def _raw(self, url: str, fields: dict[str, str], cookie: str = "") -> tuple[int, str, dict[str, str]]:
        class NoRedirect(urllib.request.HTTPRedirectHandler):
            def redirect_request(self, req, fp, code, msg, headers, newurl):
                return None

        headers = {"Cookie": cookie} if cookie else {}
        opener = urllib.request.build_opener(NoRedirect)
        request = urllib.request.Request(
            url,
            data=urllib.parse.urlencode(fields).encode(),
            method="POST",
            headers=headers,
        )
        try:
            response = opener.open(request)
        except urllib.error.HTTPError as exc:
            return exc.code, exc.read().decode("utf-8"), dict(exc.headers)
        return response.status, response.read().decode("utf-8"), dict(response.headers)

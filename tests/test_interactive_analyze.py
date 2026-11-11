"""Interactive Analyze uses the engine's numbers and keeps a bad entry out of the draft."""

import hashlib
import tempfile
import threading
import unittest
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from app.accounts import register_account
from app.charts import finite_number, reading_lines, series, CASH_FLOW_KEYS
from app.inputs import field_state, monthly_problems
from app.server import make_server
from app.store import BASELINE_ID, SAMPLE, connect, create_assessment, get_assessment, seed
from engine.financial import FinancialInputs, run_financials

OWNER = "analyze-owner@pilot.example"
OTHER = "analyze-other@pilot.example"
PASSWORD = "analyze-pass-1"


class TestInteractiveAnalyze(unittest.TestCase):
    def test_blank_is_not_zero_and_text_is_refused(self) -> None:
        self.assertEqual(field_state(""), "missing")
        self.assertEqual(field_state("0"), "zero")
        self.assertEqual(field_state("0.0"), "zero")
        self.assertEqual(field_state("abc"), "invalid")
        self.assertEqual(monthly_problems({"projected_monthly_revenue_base": ""}), [])
        refused = monthly_problems({"projected_monthly_revenue_base": "abc", "initial_capital": "0"})
        self.assertIn("Projected monthly base revenue is not a finite number.", refused[0])
        self.assertTrue(monthly_problems({"gross_margin_pct": "1.2"})[0].startswith("Gross margin"))

    def test_chart_points_match_the_engine_and_do_not_add_an_expense(self) -> None:
        expected = run_financials(
            FinancialInputs(
                initial_capital=10000,
                monthly_fixed_costs=400,
                gross_margin_pct=0.5,
                projected_monthly_revenue_base=1000,
                downside_revenue_multiplier=0.6,
            )
        )
        financial = {
            "base_monthly_cash_flow": expected.base_monthly_cash_flow,
            "downside_monthly_cash_flow": expected.downside_monthly_cash_flow,
            "downside_monthly_revenue": expected.downside_monthly_revenue,
            "break_even_monthly_revenue": expected.break_even_monthly_revenue,
        }
        points = series(financial, CASH_FLOW_KEYS)
        self.assertEqual(points[0]["value"], expected.base_monthly_cash_flow)
        self.assertEqual(points[0]["source"], "engine")
        lines = reading_lines(financial, live=False)
        self.assertIn("Demonstration reading. No live model was called.", lines[0])
        self.assertIn(f"base_monthly_cash_flow: {expected.base_monthly_cash_flow}. Calculated by the engine.", lines)
        self.assertIn("The engine does not return a separate expense total. No expense amount is drawn.", lines)
        self.assertIsNone(finite_number(True))

    def test_customer_saves_runs_recalculates_and_another_customer_cannot_change_it(self) -> None:
        directory = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        connection = connect(Path(directory.name) / "analyze.sqlite")
        seed(connection)
        sample_before = hashlib.sha256(SAMPLE.read_bytes()).hexdigest()
        owner = register_account(connection, email=OWNER, password=PASSWORD)
        register_account(connection, email=OTHER, password=PASSWORD)
        assessment_id = create_assessment(
            connection,
            business_name="Chart Cafe",
            purpose="startup_feasibility",
            tier="analyze",
            owner_user_id=owner["id"],
        )
        server = make_server(Path(directory.name) / "analyze.sqlite", port=0)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        base = f"http://127.0.0.1:{server.server_address[1]}"
        try:
            cookie = self._login(base, OWNER)
            draft = self._get(base + f"/assessments/{assessment_id}", cookie)
            self.assertIn("Missing. This blank is not treated as zero.", draft)
            self.assertIn('id="saved-explore-context"', draft)
            self.assertIn("not entered", draft)
            refused = self._raw(
                base + f"/assessments/{assessment_id}/analyze",
                {"projected_monthly_revenue_base": "abc"},
                cookie,
            )
            self.assertEqual(refused[0], 400)
            self.assertIn("not a finite number", refused[1])
            self.assertIn("engine was not run", refused[1])
            untouched = get_assessment(connection, assessment_id)
            assert untouched is not None
            self.assertEqual(untouched["profile"]["projected_monthly_revenue_base"], "")
            self.assertIsNone(untouched["result"])

            fields = {
                "initial_capital": "10000",
                "monthly_fixed_costs": "0",
                "gross_margin_pct": "0.5",
                "projected_monthly_revenue_base": "1000",
                "downside_multiplier": "0.6",
            }
            saved = self._raw(base + f"/assessments/{assessment_id}/save", fields, cookie)
            self.assertEqual(saved[0], 303)
            reloaded = self._get(base + f"/assessments/{assessment_id}", cookie)
            self.assertIn('value="1000"', reloaded)
            self.assertIn('value="0"', reloaded)
            self.assertIn("Entered as zero.", reloaded)
            stored = get_assessment(connection, assessment_id)
            assert stored is not None
            self.assertEqual(stored["profile"]["projected_monthly_revenue_base"], "1000")
            self.assertEqual(stored["profile"]["monthly_fixed_costs"], "0")
            self.assertIsNone(stored["result"])

            first = run_financials(
                FinancialInputs(10000, 0, 0.5, 1000, 0.6)
            )
            ran = self._raw(base + f"/assessments/{assessment_id}/analyze", fields, cookie)
            self.assertEqual(ran[0], 303)
            calculated = get_assessment(connection, assessment_id)
            assert calculated is not None and calculated["result"] is not None
            financial = calculated["result"]["financial"]
            self.assertEqual(financial["base_monthly_cash_flow"], first.base_monthly_cash_flow)
            self.assertEqual(financial["break_even_monthly_revenue"], first.break_even_monthly_revenue)
            self.assertIn("INSUFFICIENT_DEMAND_EVIDENCE", calculated["result"]["blocking_flags"])
            self.assertFalse(calculated["human_review_approved"])
            page = self._get(base + f"/assessments/{assessment_id}/results", cookie)
            self.assertIn(f'data-engine-value="{first.base_monthly_cash_flow}"', page)
            self.assertIn(f'data-engine-value="{first.break_even_monthly_revenue}"', page)
            self.assertIn("No expense amount is drawn.", page)
            self.assertIn("Demonstration reading. No live model was called.", page)

            revised = dict(fields)
            revised["projected_monthly_revenue_base"] = "800"
            revised["monthly_fixed_costs"] = "400"
            second = run_financials(FinancialInputs(10000, 400, 0.5, 800, 0.6))
            self.assertNotEqual(second.base_monthly_cash_flow, first.base_monthly_cash_flow)
            again = self._raw(base + f"/assessments/{assessment_id}/analyze", revised, cookie)
            self.assertEqual(again[0], 303)
            updated = get_assessment(connection, assessment_id)
            assert updated is not None and updated["result"] is not None
            self.assertEqual(updated["result"]["financial"]["base_monthly_cash_flow"], second.base_monthly_cash_flow)
            redrawn = self._get(base + f"/assessments/{assessment_id}/results", cookie)
            self.assertIn(f'data-engine-value="{second.base_monthly_cash_flow}"', redrawn)
            self.assertNotIn(f'data-engine-value="{first.base_monthly_cash_flow}"', redrawn)

            downside = self._raw(
                base + f"/assessments/{assessment_id}/scenarios",
                {"case": "downside"},
                cookie,
            )
            self.assertEqual(downside[0], 303)
            compared = get_assessment(connection, assessment_id)
            assert compared is not None
            alternative = compared["scenarios"]["alternative"]["metrics"]["monthly_cash_flow"]
            self.assertEqual(
                alternative,
                compared["scenarios"]["alternative"]["metrics"]["monthly_cash_flow"],
            )
            self.assertIsNotNone(alternative)
            self.assertNotEqual(compared["result"]["recommendation"], None)
            chart = self._get(base + f"/assessments/{assessment_id}/results", cookie)
            self.assertIn(f'data-engine-value="{alternative}"', chart)
            self.assertEqual(compared["result"]["financial"]["base_monthly_cash_flow"], second.base_monthly_cash_flow)
            self.assertFalse(compared["human_review_approved"])

            other = self._login(base, OTHER)
            blocked = self._raw(
                base + f"/assessments/{assessment_id}/analyze",
                {"projected_monthly_revenue_base": "1"},
                other,
            )
            self.assertEqual(blocked[0], 403)
            self.assertIn("not available to this session", blocked[1])
            self.assertNotIn("Chart Cafe", blocked[1])
            after_block = get_assessment(connection, assessment_id)
            assert after_block is not None and after_block["result"] is not None
            self.assertEqual(
                after_block["result"]["financial"]["base_monthly_cash_flow"],
                second.base_monthly_cash_flow,
            )
            self.assertEqual(after_block["profile"]["projected_monthly_revenue_base"], "800")

            baseline = self._get(base + f"/assessments/{BASELINE_ID}/results")
            self.assertIn("do-not-proceed", baseline)
            self.assertIn("INSUFFICIENT_DEMAND_EVIDENCE", baseline)
            official = get_assessment(connection, BASELINE_ID)
            assert official is not None
            self.assertFalse(official["human_review_approved"])
            self.assertEqual(hashlib.sha256(SAMPLE.read_bytes()).hexdigest(), sample_before)
            self.assertIsNone(official["result"])
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=3)
            connection.close()
            directory.cleanup()

    def _login(self, base: str, email: str) -> str:
        status, _body, headers = self._raw(base + "/login", {"email": email, "password": PASSWORD})
        self.assertEqual(status, 303)
        return (headers.get("Set-Cookie") or "").split(";", 1)[0]

    def _get(self, url: str, cookie: str = "") -> str:
        headers = {"Cookie": cookie} if cookie else {}
        request = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(request) as response:
            return response.read().decode("utf-8")

    def _raw(
        self,
        url: str,
        fields: dict[str, str],
        cookie: str = "",
    ) -> tuple[int, str, dict[str, str]]:
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

"""Saved reports and action items stay with the assessment owner."""

import hashlib
import tempfile
import threading
import unittest
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from app.access import DENIAL
from app.accounts import register_account
from app.report_snapshot import build_report_snapshot
from app.review import SESSION_COOKIE
from app.server import make_server
from app.store import BASELINE_ID, SAMPLE, connect, create_assessment, get_assessment, save_profile, seed
from engine.financial import FinancialInputs, result_to_dict, run_financials

OWNER = "reports-owner@pilot.example"
OTHER = "reports-other@pilot.example"
PASSWORD = "reports-pass-1"


class TestReportsAndActions(unittest.TestCase):
    def test_missing_snapshot_does_not_invent_zero(self) -> None:
        directory = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        connection = connect(Path(directory.name) / "analyze.sqlite")
        seed(connection)
        assessment_id = create_assessment(
            connection,
            business_name="Blank Cafe",
            purpose="startup_feasibility",
            tier="analyze",
            owner_user_id="owner",
        )
        record = get_assessment(connection, assessment_id)
        assert record is not None
        snapshot = build_report_snapshot(record)
        assumptions = " ".join(snapshot["assumptions"])
        self.assertIn("Missing. This blank is not stored as zero.", assumptions)
        self.assertNotIn("Initial capital: 0", assumptions)
        self.assertEqual(snapshot["base_results"], ["Not calculated. Analyze has not been run."])
        self.assertEqual(snapshot["downside_scenario"], ["No Downside scenario is saved."])
        self.assertIn("Not calculated. Analyze has not been run.", snapshot["recommendation"])
        connection.close()
        directory.cleanup()

    def test_http_saves_reports_actions_and_hides_them_from_other_customers(self) -> None:
        directory = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        connection = connect(Path(directory.name) / "analyze.sqlite")
        seed(connection)
        sample_before = hashlib.sha256(SAMPLE.read_bytes()).hexdigest()
        owner = register_account(connection, email=OWNER, password=PASSWORD)
        register_account(connection, email=OTHER, password=PASSWORD)
        assessment_id = create_assessment(
            connection,
            business_name="Report Cafe",
            purpose="startup_feasibility",
            tier="analyze",
            owner_user_id=owner["id"],
        )
        profile = dict(get_assessment(connection, assessment_id)["profile"])
        profile.update(
            {
                "concept": "A small cafe",
                "industry": "Restaurant",
                "market": "Harbor",
                "customers": "Neighbors",
                "customer_objective": "start-business",
                "initial_capital": "10000",
                "monthly_fixed_costs": "400",
                "gross_margin_pct": "0.5",
                "projected_monthly_revenue_base": "1000",
                "downside_multiplier": "0.6",
            }
        )
        save_profile(connection, assessment_id, profile)
        expected = result_to_dict(run_financials(FinancialInputs(10000, 400, 0.5, 1000, 0.6)))
        server = make_server(Path(directory.name) / "analyze.sqlite", port=0)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        base = f"http://127.0.0.1:{server.server_address[1]}"
        try:
            cookie = self._login(base, OWNER)
            other = self._login(base, OTHER)
            analyzed = self._raw(
                base + f"/assessments/{assessment_id}/analyze",
                {
                    "initial_capital": "10000",
                    "monthly_fixed_costs": "400",
                    "gross_margin_pct": "0.5",
                    "projected_monthly_revenue_base": "1000",
                    "downside_multiplier": "0.6",
                },
                cookie,
            )
            self.assertEqual(analyzed[0], 303)
            downside = self._raw(
                base + f"/assessments/{assessment_id}/scenarios",
                {"case": "downside"},
                cookie,
            )
            self.assertEqual(downside[0], 303)
            first = self._raw(base + f"/assessments/{assessment_id}/reports", {}, cookie)
            self.assertEqual(first[0], 303)
            report_path = first[2].get("Location") or ""
            page = self._get(base + report_path, cookie)
            self.assertEqual(page[0], 200)
            self.assertIn("Report saved.", page[1])
            self.assertIn("Report Cafe", page[1])
            self.assertIn("Start a Business", page[1])
            self.assertIn("Neighbors", page[1])
            self.assertIn(f"base_monthly_cash_flow: {expected['base_monthly_cash_flow']}", page[1])
            self.assertIn(f'data-engine-value="{expected["base_monthly_cash_flow"]}"', page[1])
            self.assertIn("No expense amount is drawn.", page[1])
            self.assertIn("Saved Downside scenario.", page[1])
            self.assertIn("INSUFFICIENT_DEMAND_EVIDENCE", page[1])
            self.assertIn("human_review_approved: false", page[1])
            self.assertIn("do-not-proceed", page[1])
            exported = self._get(base + report_path.split("?", 1)[0] + "/export", cookie)
            self.assertEqual(exported[0], 200)
            self.assertIn(f"base_monthly_cash_flow: {expected['base_monthly_cash_flow']}", exported[1])
            printed = self._get(base + report_path.split("?", 1)[0] + "/print", cookie)
            self.assertEqual(printed[0], 200)
            self.assertIn("print-view", printed[1])
            self.assertIn(f"base_monthly_cash_flow: {expected['base_monthly_cash_flow']}", printed[1])

            changed = {
                "initial_capital": "10000",
                "monthly_fixed_costs": "400",
                "gross_margin_pct": "0.5",
                "projected_monthly_revenue_base": "800",
                "downside_multiplier": "0.6",
            }
            rerun = self._raw(base + f"/assessments/{assessment_id}/analyze", changed, cookie)
            self.assertEqual(rerun[0], 303)
            second = self._raw(base + f"/assessments/{assessment_id}/reports", {}, cookie)
            self.assertEqual(second[0], 303)
            kept = self._get(base + report_path.split("?", 1)[0], cookie)
            self.assertIn(f"base_monthly_cash_flow: {expected['base_monthly_cash_flow']}", kept[1])
            later = result_to_dict(run_financials(FinancialInputs(10000, 400, 0.5, 800, 0.6)))
            new_page = self._get(base + (second[2].get("Location") or ""), cookie)
            self.assertIn(f"base_monthly_cash_flow: {later['base_monthly_cash_flow']}", new_page[1])
            self.assertNotEqual(expected["base_monthly_cash_flow"], later["base_monthly_cash_flow"])

            history = self._get(base + "/history", cookie)
            self.assertEqual(history[0], 200)
            self.assertIn("Report Cafe", history[1])
            self.assertIn("A stored engine result is available.", history[1])
            self.assertEqual(history[1].count("Report Cafe report"), 2)

            created = self._raw(
                base + f"/assessments/{assessment_id}/actions",
                {"description": "Call three customers", "status": "open"},
                cookie,
            )
            self.assertEqual(created[0], 303)
            actions = self._get(base + f"/assessments/{assessment_id}/actions", cookie)
            self.assertIn("Call three customers", actions[1])
            self.assertIn("Create action from INSUFFICIENT_DEMAND_EVIDENCE", actions[1])
            from_flag = self._raw(
                base + f"/assessments/{assessment_id}/actions",
                {
                    "source_flag": "INSUFFICIENT_DEMAND_EVIDENCE",
                    "description": "Follow up on INSUFFICIENT_DEMAND_EVIDENCE. Completing this action does not clear the flag.",
                    "status": "open",
                },
                cookie,
            )
            self.assertEqual(from_flag[0], 303)
            current = get_assessment(connection, assessment_id)
            assert current is not None
            self.assertIn("INSUFFICIENT_DEMAND_EVIDENCE", current["result"]["blocking_flags"])
            action_id = ""
            for item in actions[1].split('action="/assessments/')[1:]:
                if "/actions/" in item:
                    action_id = item.split("/actions/", 1)[1].split('"', 1)[0]
                    break
            self.assertTrue(action_id)
            edited = self._raw(
                base + f"/assessments/{assessment_id}/actions/{action_id}",
                {"description": "Call five customers", "status": "completed"},
                cookie,
            )
            self.assertEqual(edited[0], 303)
            finished = self._get(base + f"/assessments/{assessment_id}/actions", cookie)
            self.assertIn("Call five customers", finished[1])
            self.assertIn("Completed", finished[1])
            stored = get_assessment(connection, assessment_id)
            assert stored is not None
            self.assertEqual(stored["result"]["recommendation"], "do-not-proceed")
            self.assertIn("INSUFFICIENT_DEMAND_EVIDENCE", stored["result"]["blocking_flags"])
            self.assertFalse(stored["human_review_approved"])
            again = self._get(base + "/history", cookie)
            self.assertIn("completed", again[1])

            for cookie_value in ("", other):
                for path in (
                    f"/assessments/{assessment_id}/reports",
                    report_path.split("?", 1)[0],
                    report_path.split("?", 1)[0] + "/export",
                    f"/assessments/{assessment_id}/actions",
                ):
                    denied = self._get(base + path, cookie_value)
                    self.assertEqual(denied[0], 403, path)
                    self.assertIn(DENIAL, denied[1])
                    self.assertNotIn("Report Cafe", denied[1])
                    self.assertNotIn("Call five customers", denied[1])
                blocked = self._raw(
                    base + f"/assessments/{assessment_id}/actions",
                    {"description": "Take over", "status": "completed"},
                    cookie_value,
                )
                self.assertEqual(blocked[0], 403)
                self.assertNotIn("Report Cafe", blocked[1])
            stranger_history = self._get(base + "/history", other)
            self.assertNotIn("Report Cafe", stranger_history[1])
            stranger_reports = self._get(base + "/reports", "")
            self.assertNotIn("Report Cafe", stranger_reports[1])

            baseline_before = get_assessment(connection, BASELINE_ID)
            assert baseline_before is not None
            baseline_report = self._raw(base + f"/assessments/{BASELINE_ID}/reports", {}, cookie)
            self.assertEqual(baseline_report[0], 303)
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

    def _login(self, base: str, email: str) -> str:
        status, _body, headers = self._raw(base + "/login", {"email": email, "password": PASSWORD})
        self.assertEqual(status, 303)
        cookie = (headers.get("Set-Cookie") or "").split(";", 1)[0]
        self.assertTrue(cookie.startswith(SESSION_COOKIE + "="))
        return cookie

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

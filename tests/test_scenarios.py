"""Saved scenarios stay beside the official result and do not change its gates."""

import copy
import hashlib
import json
import tempfile
import threading
import unittest
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from app.analysis import analyze_record
from app.pages import results_page
from app.scenarios import DISCLAIMER, update_scenarios
from app.server import make_server
from app.store import (
    BASELINE_ID,
    SAMPLE,
    connect,
    create_assessment,
    get_assessment,
    save_profile,
    save_result,
    save_scenarios,
    seed,
)

ROOT = Path(__file__).resolve().parent.parent
DRAFT_REPORT = ROOT / "reports" / "output" / "rugd-intelligence-draft.md"


class TestScenarioComparison(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.db = Path(self.directory.name) / "analyze.sqlite"
        self.connection = connect(self.db)
        seed(self.connection)
        self.assessment_id = create_assessment(
            self.connection,
            business_name="Scenario Cafe",
            purpose="startup_feasibility",
            tier="analyze",
        )
        record = get_assessment(self.connection, self.assessment_id)
        assert record is not None
        profile = dict(record["profile"])
        profile.update(
            {
                "initial_capital": "10000",
                "monthly_fixed_costs": "400",
                "gross_margin_pct": "0.5",
                "projected_monthly_revenue_base": "1000",
                "downside_multiplier": "0.6",
            }
        )
        save_profile(self.connection, self.assessment_id, profile)

    def tearDown(self) -> None:
        self.connection.close()
        self.directory.cleanup()

    def test_alternative_case_does_not_change_flags_or_the_baseline(self) -> None:
        sample_before = hashlib.sha256(SAMPLE.read_bytes()).hexdigest()
        report_before = hashlib.sha256(DRAFT_REPORT.read_bytes()).hexdigest()
        record = get_assessment(self.connection, self.assessment_id)
        assert record is not None
        result = analyze_record(record)
        save_result(self.connection, self.assessment_id, result.get("intake"), result)
        official = get_assessment(self.connection, self.assessment_id)
        assert official is not None
        stored = json.dumps(official["result"], sort_keys=True)
        self.assertEqual(official["result"]["recommendation"], "do-not-proceed")
        self.assertIn("INSUFFICIENT_DEMAND_EVIDENCE", official["result"]["blocking_flags"])
        self.assertNotIn("NEGATIVE_OR_MARGINAL_CASH_FLOW", official["result"]["blocking_flags"])
        self.assertFalse(official["human_review_approved"])

        untouched = copy.deepcopy(official)
        downside = update_scenarios(official, "downside")
        self.assertEqual(official["result"], untouched["result"])
        self.assertEqual(official["profile"], untouched["profile"])
        self.assertFalse(downside["affects_official_recommendation"])
        self.assertFalse(downside["clears_hard_gates"])
        self.assertFalse(downside["sets_human_review_approved"])
        self.assertEqual(downside["base"]["metrics"]["monthly_cash_flow"], 100.0)
        self.assertEqual(downside["alternative"]["kind"], "downside")
        self.assertEqual(downside["alternative"]["metrics"]["monthly_cash_flow"], -100.0)
        self.assertFalse(downside["alternative"]["changes_recommendation"])
        self.assertFalse(downside["alternative"]["clears_hard_gates"])
        self.assertNotIn("recommendation", downside["alternative"])
        self.assertNotIn("blocking_flags", downside["alternative"])

        save_scenarios(self.connection, self.assessment_id, downside)
        after = get_assessment(self.connection, self.assessment_id)
        assert after is not None
        self.assertEqual(json.dumps(after["result"], sort_keys=True), stored)
        self.assertEqual(after["result"]["recommendation"], "do-not-proceed")
        self.assertEqual(
            after["result"]["blocking_flags"],
            official["result"]["blocking_flags"],
        )
        self.assertFalse(after["human_review_approved"])
        self.assertNotIn("human_review_approved", after["scenarios"]["alternative"])
        upside = update_scenarios(after, "upside")
        self.assertEqual(upside["alternative"]["kind"], "upside")
        self.assertGreater(
            upside["alternative"]["metrics"]["monthly_cash_flow"],
            upside["base"]["metrics"]["monthly_cash_flow"],
        )
        self.assertEqual(json.dumps(after["result"], sort_keys=True), stored)

        page = results_page(after, after["result"])
        self.assertIn("Scenario comparison", page)
        self.assertIn(DISCLAIMER, page)
        self.assertIn("<th>Base</th>", page)
        self.assertIn("<th>Downside</th>", page)
        self.assertIn("Official recommendation:</strong> do-not-proceed", page)
        self.assertIn("INSUFFICIENT_DEMAND_EVIDENCE", page)
        self.assertIn("This comparison did not clear them.", page)
        self.assertIn("100.0", page)
        self.assertIn("-100.0", page)

        baseline = get_assessment(self.connection, BASELINE_ID)
        assert baseline is not None
        intake_before = json.dumps(baseline["intake"], sort_keys=True)
        baseline_result = analyze_record(baseline)
        save_result(self.connection, BASELINE_ID, baseline.get("intake"), baseline_result)
        analyzed = get_assessment(self.connection, BASELINE_ID)
        assert analyzed is not None
        baseline_stored = json.dumps(analyzed["result"], sort_keys=True)
        self.assertEqual(analyzed["result"]["recommendation"], "do-not-proceed")
        self.assertIn("INSUFFICIENT_DEMAND_EVIDENCE", analyzed["result"]["blocking_flags"])
        save_scenarios(self.connection, BASELINE_ID, update_scenarios(analyzed, "downside"))
        baseline_after = get_assessment(self.connection, BASELINE_ID)
        assert baseline_after is not None
        self.assertEqual(json.dumps(baseline_after["result"], sort_keys=True), baseline_stored)
        self.assertEqual(json.dumps(baseline_after["intake"], sort_keys=True), intake_before)
        self.assertEqual(baseline_after["result"]["recommendation"], "do-not-proceed")
        self.assertIn("INSUFFICIENT_DEMAND_EVIDENCE", baseline_after["result"]["blocking_flags"])
        self.assertFalse(baseline_after["human_review_approved"])
        shown = results_page(baseline_after, baseline_after["result"])
        self.assertIn("Official recommendation:</strong> do-not-proceed", shown)
        self.assertIn("INSUFFICIENT_DEMAND_EVIDENCE", shown)
        self.assertEqual(hashlib.sha256(SAMPLE.read_bytes()).hexdigest(), sample_before)
        self.assertEqual(hashlib.sha256(DRAFT_REPORT.read_bytes()).hexdigest(), report_before)

    def test_http_comparison_leaves_the_official_result_in_place(self) -> None:
        sample_before = hashlib.sha256(SAMPLE.read_bytes()).hexdigest()
        empty_id = create_assessment(
            self.connection,
            business_name="Scenario Empty",
            purpose="startup_feasibility",
            tier="analyze",
        )
        record = get_assessment(self.connection, self.assessment_id)
        assert record is not None
        result = analyze_record(record)
        save_result(self.connection, self.assessment_id, result.get("intake"), result)
        stored = json.dumps(get_assessment(self.connection, self.assessment_id)["result"], sort_keys=True)
        server = make_server(self.db, port=0)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        host, port = server.server_address
        base = f"http://{host}:{port}"
        from tests.session_cookie import claim, open_customer

        cookie, user_id = open_customer(self.connection, base)
        claim(self.connection, empty_id, user_id)
        claim(self.connection, self.assessment_id, user_id)
        try:
            refused = urllib.request.Request(
                base + f"/assessments/{empty_id}/scenarios",
                data=b"case=downside",
                method="POST",
                headers={"Cookie": cookie},
            )
            with self.assertRaises(urllib.error.HTTPError) as blocked:
                urllib.request.urlopen(refused)
            self.assertEqual(blocked.exception.code, 400)
            self.assertIsNone(get_assessment(self.connection, empty_id)["result"])

            page = _post(
                base + f"/assessments/{self.assessment_id}/scenarios",
                urllib.parse.urlencode({"case": "downside"}).encode("utf-8"),
                cookie,
            )
            self.assertIn("Scenario comparison", page)
            self.assertIn("<th>Base</th>", page)
            self.assertIn("<th>Downside</th>", page)
            self.assertIn("Official recommendation:</strong> do-not-proceed", page)
            self.assertIn("INSUFFICIENT_DEMAND_EVIDENCE", page)
            self.assertIn("human_review_approved:</strong> false", page)
            current = get_assessment(self.connection, self.assessment_id)
            assert current is not None
            self.assertEqual(json.dumps(current["result"], sort_keys=True), stored)
            self.assertEqual(current["scenarios"]["alternative"]["kind"], "downside")
            self.assertEqual(current["result"]["recommendation"], "do-not-proceed")
            self.assertFalse(current["human_review_approved"])

            replaced = _post(
                base + f"/assessments/{self.assessment_id}/scenarios",
                urllib.parse.urlencode({"case": "upside"}).encode("utf-8"),
                cookie,
            )
            self.assertIn("<th>Upside</th>", replaced)
            self.assertNotIn("<th>Downside</th>", replaced)
            self.assertIn("Official recommendation:</strong> do-not-proceed", replaced)
            updated = get_assessment(self.connection, self.assessment_id)
            assert updated is not None
            self.assertEqual(updated["scenarios"]["alternative"]["kind"], "upside")
            self.assertEqual(json.dumps(updated["result"], sort_keys=True), stored)
            self.assertIn("INSUFFICIENT_DEMAND_EVIDENCE", updated["result"]["blocking_flags"])

            approval = urllib.request.Request(
                base + f"/assessments/{self.assessment_id}/scenarios",
                data=b"case=downside&human_review_approved=true",
                method="POST",
            )
            with self.assertRaises(urllib.error.HTTPError) as denied:
                urllib.request.urlopen(approval)
            self.assertEqual(denied.exception.code, 403)
            final = get_assessment(self.connection, self.assessment_id)
            assert final is not None
            self.assertEqual(final["scenarios"]["alternative"]["kind"], "upside")
            self.assertEqual(json.dumps(final["result"], sort_keys=True), stored)
            self.assertFalse(final["human_review_approved"])
            self.assertEqual(hashlib.sha256(SAMPLE.read_bytes()).hexdigest(), sample_before)
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)


def _post(url: str, body: bytes, cookie: str = "") -> str:
    headers = {"Cookie": cookie} if cookie else {}
    request = urllib.request.Request(url, data=body, method="POST", headers=headers)
    with urllib.request.urlopen(request) as response:
        return response.read().decode("utf-8")


if __name__ == "__main__":
    unittest.main()

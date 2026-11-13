"""A fictional local pilot case. The figures are assumptions, not verified evidence."""

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

from app.accounts import register_account
from app.server import make_server
from app.store import SAMPLE, connect, get_assessment, seed, set_email_verified

BUSINESS = "Harbor Lane Coffee"


class TestPilotJourney(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.database = Path(self.directory.name) / "analyze.sqlite"
        self.connection = connect(self.database)
        seed(self.connection)
        self.server = make_server(self.database, port=0)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base = f"http://127.0.0.1:{self.server.server_address[1]}"
        self.sample = hashlib.sha256(SAMPLE.read_bytes()).hexdigest()

    def tearDown(self) -> None:
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=5)
        self.connection.close()
        self.directory.cleanup()

    def test_fictional_startup_can_be_saved_and_resumed(self) -> None:
        email = "harbor-lane@pilot.example"
        user = register_account(self.connection, email=email, password="session-pass-1")
        set_email_verified(self.connection, user["id"])
        cookie = self._login(email)
        created = self._post(
            "/assessments",
            {"business_name": BUSINESS, "venture_path": "startup", "purpose": "startup_feasibility"},
            cookie,
        )
        self.assertEqual(created[0], 303)
        assessment_path = created[2]["Location"]
        assessment_id = assessment_path.rstrip("/").rsplit("/", 1)[-1]
        draft = self._get(assessment_path, cookie)
        self.assertEqual(draft[0], 200)
        self.assertIn('id="journey-nav"', draft[1])
        self.assertIn("enter 0.55 for 55%", draft[1])
        self.assertIn(BUSINESS, draft[1])
        analyzed = self._post(
            f"/assessments/{assessment_id}/analyze",
            {
                "business_name": BUSINESS,
                "concept": "A fictional neighborhood coffee startup used only to exercise the local pilot.",
                "industry": "Restaurant",
                "market": "Colbert County, Alabama",
                "seats": "24",
                "average_ticket": "8",
                "weekday_occupancy": "0.45",
                "weekend_occupancy": "0.70",
                "operating_days": "360",
                "construction_cost": "90000",
                "contribution_margin": "0.62",
                "initial_capital": "180000",
                "monthly_fixed_costs": "12000",
                "gross_margin_pct": "0.62",
                "projected_monthly_revenue_base": "28000",
                "downside_multiplier": "0.70",
            },
            cookie,
        )
        self.assertEqual(analyzed[0], 303)
        results = self._get(analyzed[2]["Location"], cookie)
        self.assertEqual(results[0], 200)
        self.assertIn("INSUFFICIENT_DEMAND_EVIDENCE", results[1])
        self.assertIn("do-not-proceed", results[1])
        self.assertIn("human_review_approved", results[1])
        project = self._post(
            f"/assessments/{assessment_id}/intelligence",
            {"op": "create_project", "title": "Neighborhood demand notes", "objective": "demand", "geography": "Colbert County"},
            cookie,
        )
        self.assertEqual(project[0], 303)
        research = self._get(project[2]["Location"], cookie)
        self.assertIn("Neighborhood demand notes", research[1])
        self.assertNotIn("verified market research", research[1].lower())
        plan = self._post(f"/assessments/{assessment_id}/plans", {}, cookie)
        self.assertEqual(plan[0], 303)
        plans = self._get(f"/assessments/{assessment_id}/plans", cookie)
        plan_ids = re.findall(r'href="/assessments/[^"]+/plans/([0-9a-f-]+)"', plans[1])
        self.assertTrue(plan_ids)
        deck = self._post(
            f"/assessments/{assessment_id}/decks",
            {"plan_id": plan_ids[0], "audience": "investor"},
            cookie,
        )
        self.assertEqual(deck[0], 303)
        decks = self._get(f"/assessments/{assessment_id}/decks", cookie)
        deck_ids = re.findall(r'href="/assessments/[^"]+/decks/([0-9a-f-]+)"', decks[1])
        self.assertTrue(deck_ids)
        pptx = self._get(f"/assessments/{assessment_id}/decks/{deck_ids[0]}/pptx", cookie)
        pdf = self._get(f"/assessments/{assessment_id}/decks/{deck_ids[0]}/pdf", cookie)
        self.assertEqual(pptx[0], 200)
        self.assertTrue(pptx[1].startswith("PK"))
        self.assertEqual(pdf[0], 200)
        self.assertTrue(pdf[1].startswith("%PDF"))
        report = self._post(f"/assessments/{assessment_id}/reports", {}, cookie)
        self.assertEqual(report[0], 303)
        saved_report = self._get(report[2]["Location"].split("?", 1)[0], cookie)
        self.assertIn(BUSINESS, saved_report[1])
        action = self._post(
            f"/assessments/{assessment_id}/actions",
            {"description": "Ask five nearby offices whether they would visit on a weekday", "status": "open"},
            cookie,
        )
        self.assertEqual(action[0], 303)
        actions = self._get(f"/assessments/{assessment_id}/actions", cookie)
        self.assertIn("Ask five nearby offices", actions[1])
        advice = self._post(
            f"/assessments/{assessment_id}/advice",
            {"question": "What evidence is still missing?"},
            cookie,
        )
        self.assertEqual(advice[0], 303)
        conversation = self._get(advice[2]["Location"].split("?", 1)[0], cookie)
        self.assertIn("Built-in adviser", conversation[1])
        self.assertIn("No outside AI service was used", conversation[1])
        self._post("/logout", {}, cookie)
        signed_out = self._get("/", "")
        self.assertIn("Welcome to RUGD Intelligence", signed_out[1])
        self.assertNotIn(BUSINESS, signed_out[1])
        returned = self._login(email)
        resumed = self._get(assessment_path, returned)
        self.assertEqual(resumed[0], 200)
        self.assertIn(BUSINESS, resumed[1])
        self.assertIn("28000", resumed[1])
        other = register_account(self.connection, email="other-lane@pilot.example", password="session-pass-1")
        set_email_verified(self.connection, other["id"])
        outsider = self._login("other-lane@pilot.example")
        denied = self._get(assessment_path, outsider)
        self.assertEqual(denied[0], 403)
        self.assertNotIn(BUSINESS, denied[1])
        record = get_assessment(self.connection, assessment_id)
        assert record is not None
        self.assertFalse(record["human_review_approved"])
        self.assertEqual(hashlib.sha256(SAMPLE.read_bytes()).hexdigest(), self.sample)

    def _login(self, email: str) -> str:
        status, _body, headers = self._open(
            "/login",
            urllib.parse.urlencode({"email": email, "password": "session-pass-1"}).encode(),
            {},
        )
        self.assertEqual(status, 303)
        return (headers.get("Set-Cookie") or "").split(";", 1)[0]

    def _get(self, path: str, cookie: str) -> tuple[int, str]:
        request = urllib.request.Request(self.base + path, headers={"Cookie": cookie} if cookie else {})
        try:
            response = urllib.request.urlopen(request)
        except urllib.error.HTTPError as exc:
            response = exc
        try:
            status = response.status if hasattr(response, "status") else response.code
            return status, response.read().decode("utf-8", "replace")
        finally:
            response.close()

    def _post(self, path: str, form: dict[str, str], cookie: str) -> tuple[int, str, dict[str, str]]:
        return self._open(path, urllib.parse.urlencode(form).encode(), {"Cookie": cookie})

    def _open(self, path: str, data: bytes, headers: dict[str, str]) -> tuple[int, str, dict[str, str]]:
        class NoRedirect(urllib.request.HTTPRedirectHandler):
            def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: ARG002
                try:
                    fp.close()
                except Exception:
                    pass
                return None

        request = urllib.request.Request(self.base + path, data=data, headers=headers, method="POST")
        try:
            response = urllib.request.build_opener(NoRedirect).open(request)
        except urllib.error.HTTPError as exc:
            response = exc
        try:
            status = response.status if hasattr(response, "status") else response.code
            body = response.read().decode("utf-8", "replace")
            return status, body, dict(response.headers)
        finally:
            response.close()


if __name__ == "__main__":
    unittest.main()

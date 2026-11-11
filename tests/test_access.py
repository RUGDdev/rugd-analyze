"""Customer files stay with the customer. An unclaimed draft is not given away."""

import hashlib
import tempfile
import threading
import unittest
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from app.access import DENIAL, may_read, may_write
from app.accounts import bootstrap_reviewer, register_account
from app.review import SESSION_COOKIE, open_account_session
from app.server import make_server
from app.store import BASELINE_ID, RESTAURANT_ID, SAMPLE, connect, create_assessment, get_assessment, seed

OWNER_EMAIL = "access-owner@pilot.example"
OTHER_EMAIL = "access-other@pilot.example"
REVIEWER_EMAIL = "access-reviewer@pilot.example"
PASSWORD = "access-pass-1"


class TestAssessmentAccess(unittest.TestCase):
    def test_rules_keep_an_unclaimed_draft_unassigned(self) -> None:
        owned = {"owner_user_id": "owner-1", "id": "draft", "read_only": False}
        unclaimed = {"owner_user_id": "", "id": "old-draft", "read_only": False}
        customer = {
            "active": True,
            "authentication_method": "local-account",
            "role": "customer",
            "user_id": "owner-1",
        }
        stranger = dict(customer)
        stranger["user_id"] = "owner-2"
        reviewer = dict(customer)
        reviewer["role"] = "reviewer"
        signed_out = {"active": False, "role": ""}
        self.assertTrue(may_read(customer, owned))
        self.assertTrue(may_write(customer, owned))
        self.assertFalse(may_read(stranger, owned))
        self.assertFalse(may_write(stranger, owned))
        self.assertFalse(may_read(signed_out, owned))
        self.assertTrue(may_read(reviewer, owned))
        self.assertFalse(may_read(stranger, unclaimed))
        self.assertFalse(may_write(stranger, unclaimed))
        self.assertFalse(may_read(signed_out, unclaimed))
        self.assertFalse(may_write(signed_out, unclaimed))
        self.assertTrue(may_read(reviewer, unclaimed))
        self.assertTrue(may_write(reviewer, unclaimed))
        self.assertFalse(may_write(reviewer, {"id": BASELINE_ID, "read_only": True, "owner_user_id": ""}))
        demo = {"id": RESTAURANT_ID, "read_only": False, "owner_user_id": ""}
        self.assertTrue(may_read(signed_out, demo))
        self.assertFalse(may_write(signed_out, demo))
        self.assertFalse(may_write(customer, demo))
        self.assertTrue(may_write(reviewer, demo))

    def test_http_hides_another_customers_draft_and_leaves_unclaimed_rows(self) -> None:
        directory = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        connection = connect(Path(directory.name) / "analyze.sqlite")
        seed(connection)
        sample_before = hashlib.sha256(SAMPLE.read_bytes()).hexdigest()
        owner = register_account(connection, email=OWNER_EMAIL, password=PASSWORD)
        register_account(connection, email=OTHER_EMAIL, password=PASSWORD)
        bootstrap_reviewer(connection, email=REVIEWER_EMAIL, password=PASSWORD)
        owned_id = create_assessment(
            connection,
            business_name="Private Cafe",
            purpose="startup_feasibility",
            tier="analyze",
            owner_user_id=owner["id"],
        )
        current = get_assessment(connection, owned_id)
        assert current is not None
        from app.store import save_profile, save_result
        from app.analysis import analyze_record

        profile = dict(current["profile"])
        profile.update(
            {
                "initial_capital": "10000",
                "monthly_fixed_costs": "400",
                "gross_margin_pct": "0.5",
                "projected_monthly_revenue_base": "1000",
            }
        )
        save_profile(connection, owned_id, profile)
        analyzed = analyze_record(get_assessment(connection, owned_id))
        save_result(connection, owned_id, analyzed.get("intake"), analyzed)
        unclaimed_id = create_assessment(
            connection,
            business_name="Unclaimed Draft",
            purpose="startup_feasibility",
            tier="explore",
        )
        server = make_server(Path(directory.name) / "analyze.sqlite", port=0)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        base = f"http://127.0.0.1:{server.server_address[1]}"
        try:
            owner_cookie = self._login(base, OWNER_EMAIL)
            other_cookie = self._login(base, OTHER_EMAIL)
            reviewer_cookie = self._login(base, REVIEWER_EMAIL)
            own_page = self._get(base + f"/assessments/{owned_id}/results", owner_cookie)
            self.assertEqual(own_page[0], 200)
            self.assertIn("Private Cafe", own_page[1])
            self.assertIn("base_monthly_cash_flow", own_page[1])

            for cookie in ("", other_cookie):
                for path in (
                    f"/assessments/{owned_id}",
                    f"/assessments/{owned_id}/results",
                    f"/assessments/{owned_id}/export",
                    f"/assessments/{owned_id}/report",
                    f"/assessments/{owned_id}/audit",
                ):
                    denied = self._get(base + path, cookie)
                    self.assertEqual(denied[0], 403, path)
                    self.assertIn(DENIAL, denied[1])
                    self.assertNotIn("Private Cafe", denied[1])
                    self.assertNotIn("base_monthly_cash_flow", denied[1])
                changed = self._raw(
                    base + f"/assessments/{owned_id}/save",
                    {"projected_monthly_revenue_base": "1", "business_name": "Taken Cafe"},
                    cookie,
                )
                self.assertEqual(changed[0], 403)
                self.assertNotIn("Private Cafe", changed[1])
                scenario = self._raw(
                    base + f"/assessments/{owned_id}/scenarios",
                    {"case": "downside"},
                    cookie,
                )
                self.assertEqual(scenario[0], 403)
                self.assertNotIn("Private Cafe", scenario[1])

            reviewed = self._get(base + f"/assessments/{owned_id}/results", reviewer_cookie)
            self.assertEqual(reviewed[0], 200)
            self.assertIn("Private Cafe", reviewed[1])

            stranger_list = self._get(base + "/explore", other_cookie)
            self.assertEqual(stranger_list[0], 200)
            self.assertNotIn("Private Cafe", stranger_list[1])
            self.assertNotIn("Unclaimed Draft", stranger_list[1])
            owner_list = self._get(base + "/reports", owner_cookie)
            self.assertIn("Private Cafe", owner_list[1])
            self.assertNotIn("Unclaimed Draft", owner_list[1])

            unclaimed = self._get(base + f"/assessments/{unclaimed_id}")
            self.assertEqual(unclaimed[0], 403)
            self.assertNotIn("Unclaimed Draft", unclaimed[1])
            unclaimed_post = self._raw(
                base + f"/assessments/{unclaimed_id}/save",
                {"business_name": "Claimed Draft"},
                "",
            )
            self.assertEqual(unclaimed_post[0], 403)
            self.assertNotIn("Unclaimed Draft", unclaimed_post[1])
            for path in ("/explore", "/analyze", "/market", "/reports", "/actions", "/history", "/assessments/export"):
                listed = self._get(base + path)
                self.assertEqual(listed[0], 200, path)
                self.assertNotIn("Unclaimed Draft", listed[1], path)
            hidden = self._get(base + f"/assessments/{unclaimed_id}", other_cookie)
            self.assertEqual(hidden[0], 403)
            self.assertNotIn("Unclaimed Draft", hidden[1])
            kept = get_assessment(connection, unclaimed_id)
            assert kept is not None
            self.assertFalse(kept.get("owner_user_id"))
            self.assertEqual(kept["business_name"], "Unclaimed Draft")
            reviewer_unclaimed = self._get(base + f"/assessments/{unclaimed_id}", reviewer_cookie)
            self.assertEqual(reviewer_unclaimed[0], 200)
            self.assertIn("Unclaimed Draft", reviewer_unclaimed[1])
            restaurant = get_assessment(connection, RESTAURANT_ID)
            assert restaurant is not None
            restaurant_name = restaurant["business_name"]
            for cookie in ("", other_cookie):
                demo_write = self._raw(
                    base + f"/assessments/{RESTAURANT_ID}/save",
                    {"business_name": "Taken Restaurant"},
                    cookie,
                )
                self.assertEqual(demo_write[0], 403)
                self.assertNotIn("Taken Restaurant", demo_write[1])
                self.assertNotIn(restaurant_name, demo_write[1])
            kept_demo = get_assessment(connection, RESTAURANT_ID)
            assert kept_demo is not None
            self.assertEqual(kept_demo["business_name"], restaurant_name)
            ghost = self._raw(
                base + "/assessments",
                {"business_name": "Ghost Cafe", "purpose": "startup_feasibility", "tier": "explore"},
                "",
            )
            self.assertEqual(ghost[0], 403)
            self.assertIn("Sign in to create a draft", ghost[1])
            self.assertNotIn("Ghost Cafe", ghost[1])

            stored = get_assessment(connection, owned_id)
            assert stored is not None
            self.assertEqual(stored["business_name"], "Private Cafe")
            self.assertEqual(stored["profile"]["projected_monthly_revenue_base"], "1000")
            self.assertEqual(stored["result"]["recommendation"], "do-not-proceed")
            self.assertIn("INSUFFICIENT_DEMAND_EVIDENCE", stored["result"]["blocking_flags"])
            self.assertFalse(stored["human_review_approved"])
            baseline = self._get(base + f"/assessments/{BASELINE_ID}/results")
            self.assertEqual(baseline[0], 200)
            self.assertIn("do-not-proceed", baseline[1])
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

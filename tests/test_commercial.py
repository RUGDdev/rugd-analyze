"""Simulated entitlements, account meters, and mock billing events."""

from __future__ import annotations

import json
import os
import tempfile
import threading
import unittest
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from app.accounts import register_account
from app.commercial import (
    accept_webhook,
    account_access,
    allows,
    apply_event,
    meter_open,
    sign_body,
)
from app.future import billing_hooks
from app.server import make_server
from app import server as server_module
from app.store import connect, create_assessment, get_assessment, list_retrieval_batches, seed

_ENV = (
    "RUGD_BILLING_SIMULATION",
    "RUGD_BILLING_WEBHOOK_SECRET",
    "RUGD_AI_REPLY_QUOTA",
    "RUGD_RETRIEVAL_QUOTA",
)
_SECRET = "local-webhook-secret"


def _payload(event_id: str, user_id: str, kind: str, plan_id: str, sequence: int) -> dict:
    return {
        "event_id": event_id,
        "user_id": user_id,
        "kind": kind,
        "plan_id": plan_id,
        "sequence": sequence,
    }


class TestCommercialModel(unittest.TestCase):
    def setUp(self) -> None:
        self._saved = {key: os.environ.get(key) for key in _ENV}
        for key in _ENV:
            os.environ.pop(key, None)
        self.directory = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.connection = connect(Path(self.directory.name) / "analyze.sqlite")
        seed(self.connection)
        self.user = register_account(
            self.connection,
            email="plan@pilot.example",
            password="session-pass-1",
        )

    def tearDown(self) -> None:
        self.connection.close()
        self.directory.cleanup()
        for key, value in self._saved.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value

    def test_included_access_is_not_a_paid_plan(self) -> None:
        access = account_access(self.connection, self.user["id"])
        self.assertEqual(access["plan_id"], "pilot")
        self.assertFalse(access["paid"])
        self.assertFalse(access["simulated"])
        self.assertTrue(allows(self.connection, self.user["id"], "analyze"))
        self.assertTrue(allows(self.connection, self.user["id"], "partner"))
        billing = billing_hooks()
        self.assertFalse(billing["enabled"])
        self.assertIsNone(billing["charge"])

    def test_disabled_simulation_records_without_changing_access(self) -> None:
        os.environ["RUGD_BILLING_WEBHOOK_SECRET"] = _SECRET
        body = json.dumps(_payload("evt-disabled-01", self.user["id"], "upgrade", "partner", 1)).encode()
        result = accept_webhook(self.connection, body, sign_body(body, _SECRET))
        self.assertEqual(result["category"], "billing_disabled")
        self.assertFalse(result["applied"])
        self.assertEqual(account_access(self.connection, self.user["id"])["status"], "included")

    def test_simulation_is_idempotent_and_ordered(self) -> None:
        os.environ["RUGD_BILLING_SIMULATION"] = "1"
        user_id = self.user["id"]
        first = apply_event(self.connection, _payload("evt-upgrade-0001", user_id, "upgrade", "partner", 1))
        again = apply_event(self.connection, _payload("evt-upgrade-0001", user_id, "upgrade", "partner", 1))
        stale = apply_event(self.connection, _payload("evt-stale-00001", user_id, "downgrade", "explore", 1))
        down = apply_event(self.connection, _payload("evt-down-000001", user_id, "downgrade", "explore", 2))
        self.assertEqual(first["category"], "applied")
        self.assertEqual(again["category"], "duplicate")
        self.assertEqual(stale["category"], "out_of_order")
        self.assertFalse(allows(self.connection, user_id, "analyze"))
        self.assertEqual(down["category"], "applied")
        self.assertFalse(account_access(self.connection, user_id)["paid"])
        canceled = apply_event(self.connection, _payload("evt-cancel-0001", user_id, "cancel", "explore", 3))
        self.assertEqual(canceled["category"], "applied")
        self.assertTrue(allows(self.connection, user_id, "analyze"))
        renewed = apply_event(self.connection, _payload("evt-renew-00001", user_id, "renew", "partner", 4))
        self.assertEqual(renewed["category"], "applied")
        self.assertEqual(account_access(self.connection, user_id)["plan_id"], "partner")
        self.assertTrue(account_access(self.connection, user_id)["simulated"])

    def test_bad_signature_and_card_fields_are_rejected(self) -> None:
        os.environ["RUGD_BILLING_WEBHOOK_SECRET"] = _SECRET
        os.environ["RUGD_BILLING_SIMULATION"] = "1"
        body = json.dumps(_payload("evt-signed-0001", self.user["id"], "upgrade", "analyze", 1)).encode()
        with self.assertRaises(Exception) as bad:
            accept_webhook(self.connection, body, "not-the-signature")
        self.assertEqual(bad.exception.category, "signature")
        card = _payload("evt-card-000001", self.user["id"], "upgrade", "analyze", 1)
        card["card_number"] = "not-stored"
        encoded = json.dumps(card).encode()
        with self.assertRaises(Exception) as rejected:
            accept_webhook(self.connection, encoded, sign_body(encoded, _SECRET))
        self.assertEqual(rejected.exception.category, "not_allowed")
        stored = self.connection.execute("SELECT COUNT(*) AS n FROM billing_events").fetchone()["n"]
        self.assertEqual(stored, 0)

    def test_meter_stays_on_the_account(self) -> None:
        os.environ["RUGD_AI_REPLY_QUOTA"] = "1"
        from app.commercial import record_use

        self.assertTrue(meter_open(self.connection, self.user["id"], "ai_reply"))
        record_use(self.connection, self.user["id"], "ai_reply")
        self.assertFalse(meter_open(self.connection, self.user["id"], "ai_reply"))


class TestCommercialHttp(unittest.TestCase):
    def setUp(self) -> None:
        self._saved = {key: os.environ.get(key) for key in _ENV}
        for key in _ENV:
            os.environ.pop(key, None)
        self._transport = server_module.public_transport
        self.directory = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.database = Path(self.directory.name) / "analyze.sqlite"
        self.connection = connect(self.database)
        seed(self.connection)
        self.server = make_server(self.database, port=0)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base = f"http://127.0.0.1:{self.server.server_address[1]}"

    def tearDown(self) -> None:
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=5)
        self.connection.close()
        self.directory.cleanup()
        server_module.public_transport = self._transport
        for key, value in self._saved.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value

    def test_usage_page_and_signed_webhook(self) -> None:
        cookie, user_id = self._customer()
        status, body = self._get("/settings/usage", cookie)
        self.assertEqual(status, 200)
        self.assertIn("Included local pilot", body)
        self.assertIn("not a paid subscription", body)
        os.environ["RUGD_BILLING_WEBHOOK_SECRET"] = _SECRET
        payload = _payload("evt-http-000001", user_id, "upgrade", "partner", 1)
        encoded = json.dumps(payload).encode()
        refused, refused_body = self._post_bytes(
            "/billing/webhook",
            encoded,
            {"X-RUGD-Signature": "bad", "Content-Type": "application/json"},
        )
        self.assertEqual(refused, 403)
        self.assertIn("billing event rejected: signature", refused_body)
        accepted, accepted_body = self._post_bytes(
            "/billing/webhook",
            encoded,
            {"X-RUGD-Signature": sign_body(encoded, _SECRET), "Content-Type": "application/json"},
        )
        self.assertEqual(accepted, 200)
        self.assertIn("billing event recorded: billing_disabled", accepted_body)
        self.assertIn("not a paid subscription", self._get("/settings/usage", cookie)[1])
        self.assertNotIn("4242", self._get("/settings/usage", cookie)[1])

    def test_simulated_downgrade_blocks_analyze(self) -> None:
        cookie, user_id = self._customer()
        os.environ["RUGD_BILLING_SIMULATION"] = "1"
        apply_event(self.connection, _payload("evt-block-00001", user_id, "downgrade", "explore", 1))
        assessment_id = create_assessment(
            self.connection,
            business_name="Quota Cafe",
            purpose="startup_feasibility",
            tier="explore",
            owner_user_id=user_id,
        )
        status, body = self._post(f"/assessments/{assessment_id}/analyze", {}, cookie)
        self.assertEqual(status, 403)
        self.assertIn("does not include Analyze", body)
        self.assertIn("not a paid subscription", body)
        record = get_assessment(self.connection, assessment_id)
        self.assertIsNone(record["result"])

    def test_adviser_quota_survives_a_new_session(self) -> None:
        os.environ["RUGD_AI_REPLY_QUOTA"] = "1"
        email = "adviser-quota@pilot.example"
        user = register_account(self.connection, email=email, password="session-pass-1")
        from app.store import set_email_verified

        set_email_verified(self.connection, user["id"])
        cookie = self._login(email)
        assessment_id = create_assessment(
            self.connection,
            business_name="Adviser Cafe",
            purpose="startup_feasibility",
            tier="explore",
            owner_user_id=user["id"],
        )
        first, _body = self._post(
            f"/assessments/{assessment_id}/advice",
            {"question": "What evidence is missing?"},
            cookie,
        )
        self.assertEqual(first, 303)
        second, second_body = self._post(
            f"/assessments/{assessment_id}/advice",
            {"question": "What evidence is missing?"},
            cookie,
        )
        self.assertEqual(second, 403)
        self.assertIn("used its adviser replies", second_body)
        replacement = self._login(email)
        self.assertNotEqual(replacement, cookie)
        third, third_body = self._post(
            f"/assessments/{assessment_id}/advice",
            {"question": "What evidence is missing?"},
            replacement,
        )
        self.assertEqual(third, 403)
        self.assertIn("used its adviser replies", third_body)

    def test_retrieval_quota_survives_a_new_project(self) -> None:
        os.environ["RUGD_RETRIEVAL_QUOTA"] = "1"
        calls = []

        def transport(url: str) -> str:
            calls.append(url)
            return "not,a,csv\n"

        server_module.public_transport = transport
        cookie, user_id = self._customer()
        assessment_id = create_assessment(
            self.connection,
            business_name="Retrieval Cafe",
            purpose="startup_feasibility",
            tier="explore",
            owner_user_id=user_id,
        )
        first_project = self._project(assessment_id, cookie, "First project")
        second_project = self._project(assessment_id, cookie, "Second project")
        form = {
            "op": "retrieve_public",
            "industry": "Restaurant",
            "geography": "Colbert County, Alabama",
            "year": "2024",
        }
        self.assertEqual(self._post(first_project, form, cookie)[0], 303)
        self.assertEqual(self._post(second_project, form, cookie)[0], 303)
        self.assertEqual(len(calls), 1)
        project_id = second_project.rstrip("/").rsplit("/", 1)[-1]
        batches = list_retrieval_batches(self.connection, project_id)
        self.assertEqual(batches[-1]["error_category"], "rate_limited")
        self.assertIn("used its public retrieval quota", batches[-1]["notice"])

    def _customer(self) -> tuple[str, str]:
        from tests.session_cookie import open_customer

        return open_customer(self.connection, self.base)

    def _login(self, email: str) -> str:
        status, _body, headers = self._open(
            "/login",
            urllib.parse.urlencode({"email": email, "password": "session-pass-1"}).encode(),
            {},
        )
        self.assertEqual(status, 303)
        return (headers.get("Set-Cookie") or "").split(";", 1)[0]

    def _project(self, assessment_id: str, cookie: str, title: str) -> str:
        status, _body, headers = self._open(
            f"/assessments/{assessment_id}/intelligence",
            urllib.parse.urlencode(
                {"op": "create_project", "title": title, "objective": "demand", "geography": "Colbert County"}
            ).encode(),
            {"Cookie": cookie},
        )
        self.assertEqual(status, 303)
        return headers["Location"]

    def _get(self, path: str, cookie: str) -> tuple[int, str]:
        request = urllib.request.Request(self.base + path, headers={"Cookie": cookie})
        try:
            response = urllib.request.urlopen(request)
        except urllib.error.HTTPError as exc:
            response = exc
        try:
            status = response.status if hasattr(response, "status") else response.code
            return status, response.read().decode("utf-8", "replace")
        finally:
            response.close()

    def _post(self, path: str, form: dict[str, str], cookie: str) -> tuple[int, str]:
        status, body, _headers = self._open(
            path,
            urllib.parse.urlencode(form).encode(),
            {"Cookie": cookie},
        )
        return status, body

    def _post_bytes(self, path: str, body: bytes, headers: dict[str, str]) -> tuple[int, str]:
        status, text, _headers = self._open(path, body, headers)
        return status, text

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
            return status, response.read().decode("utf-8", "replace"), dict(response.headers)
        finally:
            response.close()


if __name__ == "__main__":
    unittest.main()

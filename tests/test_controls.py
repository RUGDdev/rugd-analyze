"""Session, audit, and retrieval limits stay on the existing account boundary."""

from __future__ import annotations

import os
import tempfile
import threading
import unittest
from pathlib import Path

import app.server as server_module
from app.access import DENIAL
from app.config import production_secret_error, session_cookie
from app.server import make_server
from app.store import connect, create_assessment, list_audit_events, seed
from tests.session_cookie import open_customer
from tests.test_public_retrieval import CSV, _get, _raw


class TestSessionAndLimits(unittest.TestCase):
    def test_cookie_and_production_secret_stay_explicit(self) -> None:
        cookie = session_cookie("rugd_session", "token", 60)
        self.assertIn("HttpOnly", cookie)
        self.assertIn("SameSite=Lax", cookie)
        self.assertNotIn("Secure", cookie)
        previous_env = os.environ.get("RUGD_ENV")
        previous_secret = os.environ.get("SECRET_KEY")
        os.environ["RUGD_ENV"] = "production"
        os.environ["SECRET_KEY"] = "short"
        try:
            self.assertIn("SECRET_KEY", production_secret_error() or "")
            secure = session_cookie("rugd_session", "token", 60)
            self.assertIn("Secure", secure)
        finally:
            if previous_env is None:
                os.environ.pop("RUGD_ENV", None)
            else:
                os.environ["RUGD_ENV"] = previous_env
            if previous_secret is None:
                os.environ.pop("SECRET_KEY", None)
            else:
                os.environ["SECRET_KEY"] = previous_secret

    def test_import_is_audited_and_isolated_and_the_source_budget_is_configurable(self) -> None:
        directory = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        database = Path(directory.name) / "analyze.sqlite"
        connection = connect(database)
        seed(connection)
        calls = {"n": 0}

        def transport(url: str) -> str:
            calls["n"] += 1
            return CSV

        server_module.public_transport = transport
        server = make_server(database, port=0)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        base = f"http://127.0.0.1:{server.server_address[1]}"
        previous = os.environ.get("RUGD_SOURCE_BATCH_LIMIT")
        os.environ["RUGD_SOURCE_BATCH_LIMIT"] = "1"
        try:
            cookie, user_id = open_customer(connection, base)
            other, _other = open_customer(connection, base)
            assessment_id = create_assessment(
                connection,
                business_name="Control Cafe",
                purpose="startup_feasibility",
                tier="explore",
                owner_user_id=user_id,
            )
            created = _raw(
                base + f"/assessments/{assessment_id}/intelligence",
                {"op": "create_project", "title": "Controls", "objective": "trends", "geography": "County"},
                cookie,
            )
            project_path = created[2].get("Location") or ""
            form = {
                "op": "retrieve_public",
                "source": "bls-qcew",
                "industry": "Restaurant",
                "geography": "Colbert County, Alabama",
                "year": "2024",
            }
            self.assertEqual(_raw(base + project_path, form, cookie)[0], 303)
            self.assertEqual(_raw(base + project_path, form, cookie)[0], 303)
            self.assertEqual(calls["n"], 1)
            page = _get(base + project_path, cookie)
            self.assertIn("rate_limited", page[1])
            batch_id = page[1].split('name="batch_id" value="', 1)[1].split('"', 1)[0]
            self.assertEqual(
                _raw(base + project_path, {"op": "import_public", "batch_id": batch_id, "selected": "0"}, cookie)[0],
                303,
            )
            events = list_audit_events(connection, assessment_id)
            actions = [item["action"] for item in events]
            self.assertIn("public_retrieval", actions)
            self.assertIn("public_import", actions)
            joined = " ".join(item["detail"] for item in events)
            self.assertNotIn("120", joined)
            self.assertNotIn("Control Cafe", joined)
            denied = _get(base + project_path, other)
            self.assertEqual(denied[0], 403)
            self.assertIn(DENIAL, denied[1])
            self.assertNotIn("Control Cafe", denied[1])
        finally:
            if previous is None:
                os.environ.pop("RUGD_SOURCE_BATCH_LIMIT", None)
            else:
                os.environ["RUGD_SOURCE_BATCH_LIMIT"] = previous
            connection.close()
            server.shutdown()
            directory.cleanup()


if __name__ == "__main__":
    unittest.main()

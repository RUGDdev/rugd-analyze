"""Production cookie flags and Render configuration stay off the local default."""

import hashlib
import os
import tempfile
import threading
import unittest
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from app.accounts import bootstrap_reviewer
from app.config import (
    SECURITY_HEADERS,
    bind_host,
    bind_port,
    database_path,
    production_secret_error,
    secure_cookies_enabled,
    session_cookie,
)
from app.server import make_server
from app.store import DEFAULT_DB, SAMPLE, connect, seed

ENV_NAMES = ("RUGD_ENV", "SECURE_COOKIES", "SECRET_KEY", "PORT", "RUGD_DATABASE")


class TestDeploymentConfig(unittest.TestCase):
    def setUp(self) -> None:
        self.saved = {name: os.environ.get(name) for name in ENV_NAMES}
        for name in ENV_NAMES:
            os.environ.pop(name, None)

    def tearDown(self) -> None:
        for name, value in self.saved.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value

    def test_local_defaults_keep_the_cookie_unsecured_and_the_baseline(self) -> None:
        before = hashlib.sha256(SAMPLE.read_bytes()).hexdigest()
        self.assertFalse(secure_cookies_enabled())
        self.assertEqual(bind_host(), "127.0.0.1")
        self.assertEqual(bind_port(), 8765)
        self.assertEqual(database_path(DEFAULT_DB), DEFAULT_DB)
        self.assertIsNone(production_secret_error())
        header = session_cookie("rugd_session", "token", 60)
        self.assertIn("HttpOnly", header)
        self.assertIn("SameSite=Lax", header)
        self.assertNotIn("Secure", header)
        self.assertEqual(hashlib.sha256(SAMPLE.read_bytes()).hexdigest(), before)

    def test_production_flags_mark_the_cookie_secure_and_require_a_secret(self) -> None:
        os.environ["RUGD_ENV"] = "production"
        self.assertTrue(secure_cookies_enabled())
        self.assertEqual(bind_host(), "0.0.0.0")
        os.environ["PORT"] = "10000"
        self.assertEqual(bind_port(), 10000)
        os.environ["RUGD_DATABASE"] = "/var/data/analyze.sqlite"
        self.assertEqual(database_path(DEFAULT_DB), Path("/var/data/analyze.sqlite"))
        self.assertIn("SECRET_KEY", production_secret_error() or "")
        os.environ["SECRET_KEY"] = "x" * 32
        self.assertIsNone(production_secret_error())
        header = session_cookie("rugd_session", "token", 60)
        self.assertIn("HttpOnly", header)
        self.assertIn("SameSite=Lax", header)
        self.assertTrue(header.endswith("Secure"))
        os.environ.pop("RUGD_ENV")
        os.environ["SECURE_COOKIES"] = "true"
        self.assertTrue(secure_cookies_enabled())
        self.assertEqual(bind_host(), "127.0.0.1")

    def test_http_sets_secure_cookie_and_security_headers_without_changing_baseline(self) -> None:
        before = hashlib.sha256(SAMPLE.read_bytes()).hexdigest()
        directory = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        db = Path(directory.name) / "analyze.sqlite"
        connection = connect(db)
        seed(connection)
        bootstrap_reviewer(
            connection,
            email="reviewer@pilot.example",
            password="reviewer-pass-1",
        )
        os.environ["SECURE_COOKIES"] = "true"
        server = make_server(db, port=0)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        host, port = server.server_address
        base = f"http://{host}:{port}"
        try:
            with urllib.request.urlopen(base + "/") as response:
                page = response.read().decode("utf-8")
                for name, value in SECURITY_HEADERS:
                    self.assertEqual(response.headers.get(name), value)
            self.assertIn("This screen does not grant investor-ready status.", page)
            self.assertIn("Official baseline", page)
            request = urllib.request.Request(
                base + "/login",
                data=urllib.parse.urlencode(
                    {"email": "reviewer@pilot.example", "password": "reviewer-pass-1"}
                ).encode(),
                method="POST",
            )

            class NoRedirect(urllib.request.HTTPRedirectHandler):
                def redirect_request(self, req, fp, code, msg, headers, newurl):
                    return None

            opener = urllib.request.build_opener(NoRedirect)
            try:
                opener.open(request)
            except urllib.error.HTTPError as exc:
                self.assertEqual(exc.code, 303)
                cookie = exc.headers.get("Set-Cookie") or ""
                self.assertEqual(exc.headers.get("X-Content-Type-Options"), "nosniff")
            else:
                self.fail("login should redirect")
            self.assertTrue(cookie.startswith("rugd_session="))
            self.assertIn("HttpOnly", cookie)
            self.assertIn("SameSite=Lax", cookie)
            self.assertIn("Secure", cookie)
            self.assertNotIn("reviewer-pass-1", cookie)
            baseline = connection.execute(
                "SELECT read_only FROM assessments WHERE id = ?",
                ("rugd-intelligence-baseline",),
            ).fetchone()
            self.assertEqual(baseline["read_only"], 1)
            self.assertEqual(hashlib.sha256(SAMPLE.read_bytes()).hexdigest(), before)
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=3)
            connection.close()
            directory.cleanup()

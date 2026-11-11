"""Sign-in and registration attempts are limited. The rest of the app stays open."""

import hashlib
import tempfile
import threading
import unittest
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from app.ratelimit import AUTH_LIMIT, AUTH_LIMIT_MESSAGE, AUTH_WINDOW_SECONDS, AttemptLimiter
from app.server import make_server
from app.store import BASELINE_ID, SAMPLE, connect, get_assessment, seed


class TestAttemptLimiter(unittest.TestCase):
    def test_window_blocks_one_address_and_releases_later(self) -> None:
        now = {"t": 1_000.0}
        limiter = AttemptLimiter(clock=lambda: now["t"])
        for _ in range(AUTH_LIMIT):
            self.assertTrue(limiter.allow("203.0.113.8"))
        self.assertFalse(limiter.allow("203.0.113.8"))
        self.assertTrue(limiter.allow("203.0.113.9"))
        now["t"] += AUTH_WINDOW_SECONDS
        self.assertTrue(limiter.allow("203.0.113.8"))


class TestAuthEndpointLimit(unittest.TestCase):
    def test_login_limit_leaves_the_rest_of_the_app_open(self) -> None:
        directory = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        db = Path(directory.name) / "analyze.sqlite"
        connection = connect(db)
        seed(connection)
        before = hashlib.sha256(SAMPLE.read_bytes()).hexdigest()
        server = make_server(db, port=0)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        base = f"http://127.0.0.1:{server.server_address[1]}"
        try:
            for _ in range(AUTH_LIMIT):
                status, body, _headers = self._post(
                    base + "/login",
                    {"email": "nobody@pilot.example", "password": "wrong-password"},
                )
                self.assertEqual(status, 403, body)
                self.assertNotIn(AUTH_LIMIT_MESSAGE, body)
            blocked, message, _headers = self._post(
                base + "/login",
                {"email": "nobody@pilot.example", "password": "wrong-password"},
            )
            self.assertEqual(blocked, 429)
            self.assertIn(AUTH_LIMIT_MESSAGE, message)
            self.assertIn("still available", message)
            other, other_body, _headers = self._post(
                base + "/login",
                {"email": "nobody@pilot.example", "password": "wrong-password"},
                headers={"X-Forwarded-For": "203.0.113.50"},
            )
            self.assertEqual(other, 403, other_body)
            with urllib.request.urlopen(base + "/") as response:
                home = response.read().decode("utf-8")
            self.assertEqual(response.status, 200)
            self.assertIn("Welcome to RUGD Intelligence", home)
            with urllib.request.urlopen(base + f"/assessments/{BASELINE_ID}/results") as response:
                baseline_page = response.read().decode("utf-8")
            self.assertEqual(response.status, 200)
            self.assertIn("do-not-proceed", baseline_page)
            created, created_body, _headers = self._post(
                base + "/assessments",
                {"business_name": "Limit Check", "venture_path": "startup"},
            )
            self.assertEqual(created, 403)
            self.assertIn("Sign in to create a draft", created_body)
            baseline = get_assessment(connection, BASELINE_ID)
            assert baseline is not None
            self.assertFalse(baseline["human_review_approved"])
            self.assertIsNone(baseline["result"])
            self.assertEqual(hashlib.sha256(SAMPLE.read_bytes()).hexdigest(), before)
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=3)
            connection.close()
            directory.cleanup()

    def _post(
        self,
        url: str,
        fields: dict[str, str],
        headers: dict[str, str] | None = None,
    ) -> tuple[int, str, dict[str, str]]:
        class NoRedirect(urllib.request.HTTPRedirectHandler):
            def redirect_request(self, req, fp, code, msg, headers, newurl):
                return None

        opener = urllib.request.build_opener(NoRedirect)
        request = urllib.request.Request(
            url,
            data=urllib.parse.urlencode(fields).encode(),
            method="POST",
            headers=headers or {},
        )
        try:
            response = opener.open(request)
        except urllib.error.HTTPError as exc:
            return exc.code, exc.read().decode("utf-8"), dict(exc.headers)
        return response.status, response.read().decode("utf-8"), dict(response.headers)

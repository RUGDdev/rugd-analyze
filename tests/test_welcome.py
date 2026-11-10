"""The welcome banner is for someone who has not started a draft."""

import hashlib
import tempfile
import threading
import unittest
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from app.pages import dashboard
from app.server import make_server
from app.store import BASELINE_ID, SAMPLE, connect, get_assessment, get_user_by_id, seed

EMAIL = "welcome-owner@pilot.example"
PASSWORD = "welcome-pass-1"


class TestWelcomeBanner(unittest.TestCase):
    def test_banner_is_optional_on_the_dashboard(self) -> None:
        shown = dashboard([], welcome=True)
        self.assertIn('id="welcome-banner"', shown)
        self.assertIn("RUGD Analyze helps you write down a business idea", shown)
        self.assertIn("local pilot prototype", shown)
        self.assertIn('class="button" href="/assessments/new"', shown)
        self.assertIn("Start a new assessment", shown)
        self.assertIn('action="/welcome/dismiss"', shown)
        hidden = dashboard([], welcome=False)
        self.assertNotIn('id="welcome-banner"', hidden)

    def test_banner_hides_after_dismiss_or_the_first_draft(self) -> None:
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
            home = self._get(base + "/")
            self.assertIn('id="welcome-banner"', home[1])
            dismissed = self._post(base + "/welcome/dismiss", {})
            self.assertEqual(dismissed[0], 303)
            cookie = self._cookie(dismissed[2], "rugd_welcome")
            self.assertIn("dismissed", cookie)
            quiet = self._get(base + "/", cookie)
            self.assertNotIn('id="welcome-banner"', quiet[1])

            registered = self._post(
                base + "/register",
                {
                    "email": EMAIL,
                    "password": PASSWORD,
                    "password_confirm": PASSWORD,
                },
            )
            self.assertEqual(registered[0], 303, registered[1])
            session = self._cookie(registered[2], "rugd_session")
            signed_in = self._get(base + "/", session)
            self.assertIn('id="welcome-banner"', signed_in[1])
            self.assertEqual(self._post(base + "/welcome/dismiss", {}, session)[0], 303)
            after_dismiss = self._get(base + "/", session)
            self.assertNotIn('id="welcome-banner"', after_dismiss[1])
            user = connection.execute(
                "SELECT id, role, welcome_dismissed FROM users WHERE email = ?",
                (EMAIL,),
            ).fetchone()
            assert user is not None
            self.assertEqual(user["role"], "customer")
            self.assertEqual(user["welcome_dismissed"], 1)
            self.assertEqual(get_user_by_id(connection, user["id"])["role"], "customer")

            second = self._post(
                base + "/register",
                {
                    "email": "welcome-next@pilot.example",
                    "password": PASSWORD,
                    "password_confirm": PASSWORD,
                },
            )
            second_session = self._cookie(second[2], "rugd_session")
            created = self._post(
                base + "/assessments",
                {"business_name": "Welcome Shop", "venture_path": "existing"},
                second_session,
            )
            self.assertEqual(created[0], 303, created[1])
            started = self._get(base + "/", second_session)
            self.assertNotIn('id="welcome-banner"', started[1])
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

    def _cookie(self, headers: dict[str, str], name: str) -> str:
        raw = headers.get("Set-Cookie") or ""
        for part in raw.split(","):
            piece = part.strip()
            if piece.startswith(name + "="):
                return piece.split(";", 1)[0]
        self.fail(f"{name} cookie missing from {raw}")
        return ""

    def _get(self, url: str, cookie: str = "") -> tuple[int, str]:
        request = urllib.request.Request(url, headers={"Cookie": cookie} if cookie else {})
        with urllib.request.urlopen(request) as response:
            return response.status, response.read().decode("utf-8")

    def _post(
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

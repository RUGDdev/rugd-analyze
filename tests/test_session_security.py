"""Session rotation, expiry, logout, foreign Origin, and password reset capture."""

from __future__ import annotations

import io
import sys
import tempfile
import threading
import unittest
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from app.mail import OUTBOX
from app.review import SESSION_COOKIE
from app.server import make_server
from app.store import connect


def _login(base: str, email: str, password: str) -> tuple[int, str]:
    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, req, fp, code, msg, headers, newurl):
            return None

    request = urllib.request.Request(
        base + "/login",
        data=urllib.parse.urlencode({"email": email, "password": password}).encode(),
        method="POST",
    )
    try:
        response = urllib.request.build_opener(NoRedirect).open(request)
    except urllib.error.HTTPError as exc:
        response = exc
    try:
        cookie = (response.headers.get("Set-Cookie") or "").split(";", 1)[0]
        return response.status if hasattr(response, "status") else response.code, cookie
    finally:
        response.close()


def _get(url: str, cookie: str = "", origin: str = "") -> tuple[int, str]:
    headers = {}
    if cookie:
        headers["Cookie"] = cookie
    if origin:
        headers["Origin"] = origin
    request = urllib.request.Request(url, headers=headers)
    try:
        response = urllib.request.urlopen(request)
    except urllib.error.HTTPError as exc:
        response = exc
    try:
        status = response.status if hasattr(response, "status") else response.code
        return status, response.read().decode("utf-8", "replace")
    finally:
        response.close()


class SessionSecurityTests(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.database = Path(self.directory.name) / "analyze.sqlite"
        connect(self.database).close()
        self.server = make_server(self.database, port=0)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        host, port = self.server.server_address
        self.base = f"http://{host}:{port}"
        OUTBOX.clear()

    def tearDown(self) -> None:
        self.server.shutdown()
        self.server.server_close()
        self.directory.cleanup()

    def _register(self, email: str, password: str = "session-pass-1") -> int:
        request = urllib.request.Request(
            self.base + "/register",
            data=urllib.parse.urlencode(
                {"email": email, "password": password, "password_confirm": password}
            ).encode(),
            method="POST",
        )
        try:
            response = urllib.request.urlopen(request)
        except urllib.error.HTTPError as exc:
            response = exc
        try:
            return response.status if hasattr(response, "status") else response.code
        finally:
            response.close()

    def test_login_replaces_the_previous_session(self) -> None:
        email = "rotate@pilot.example"
        self.assertIn(self._register(email), {200, 303})
        first_status, first_cookie = _login(self.base, email, "session-pass-1")
        self.assertEqual(first_status, 303)
        _second_status, second_cookie = _login(self.base, email, "session-pass-1")
        self.assertNotEqual(first_cookie, second_cookie)
        status, page = _get(self.base + "/", first_cookie)
        self.assertEqual(status, 200)
        self.assertNotIn("Your assessments", page)
        status, page = _get(self.base + "/", second_cookie)
        self.assertIn("Your assessments", page)

    def test_logout_invalidates_the_session(self) -> None:
        email = "leave@pilot.example"
        self._register(email)
        _status, cookie = _login(self.base, email, "session-pass-1")
        request = urllib.request.Request(
            self.base + "/logout",
            data=b"",
            method="POST",
            headers={"Cookie": cookie},
        )
        try:
            urllib.request.urlopen(request).close()
        except urllib.error.HTTPError as exc:
            exc.close()
        status, page = _get(self.base + "/", cookie)
        self.assertEqual(status, 200)
        self.assertNotIn("Your assessments", page)

    def test_expired_session_is_signed_out(self) -> None:
        email = "expire@pilot.example"
        self._register(email)
        _status, cookie = _login(self.base, email, "session-pass-1")
        connection = connect(self.database)
        try:
            connection.execute(
                "UPDATE reviewer_sessions SET expires_at = ?",
                ("2020-01-01T00:00:00+00:00",),
            )
            connection.commit()
        finally:
            connection.close()
        status, page = _get(self.base + "/", cookie)
        self.assertEqual(status, 200)
        self.assertNotIn("Your assessments", page)

    def test_foreign_origin_is_rejected(self) -> None:
        status, page = _get(self.base + "/login", origin="https://evil.example")
        request = urllib.request.Request(
            self.base + "/login",
            data=urllib.parse.urlencode(
                {"email": "anyone@pilot.example", "password": "session-pass-1"}
            ).encode(),
            headers={"Origin": "https://evil.example"},
            method="POST",
        )
        try:
            response = urllib.request.urlopen(request)
        except urllib.error.HTTPError as exc:
            response = exc
        try:
            body = response.read().decode("utf-8", "replace")
            code = response.status if hasattr(response, "status") else response.code
        finally:
            response.close()
        self.assertEqual(code, 403)
        self.assertIn("not sent from this site", body)
        self.assertNotIn("Set-Cookie", response.headers.get("Set-Cookie") or "")
        connection = connect(self.database)
        try:
            row = connection.execute(
                "SELECT detail FROM audit_events WHERE action = ?",
                ("csrf_rejected",),
            ).fetchone()
        finally:
            connection.close()
        self.assertEqual(row["detail"], "origin")
        self.assertEqual(status, 200)
        self.assertNotIn("not sent from this site", page)

    def test_browser_post_without_origin_is_rejected(self) -> None:
        request = urllib.request.Request(
            self.base + "/login",
            data=urllib.parse.urlencode(
                {"email": "anyone@pilot.example", "password": "session-pass-1"}
            ).encode(),
            headers={"Sec-Fetch-Site": "same-origin"},
            method="POST",
        )
        try:
            response = urllib.request.urlopen(request)
        except urllib.error.HTTPError as exc:
            response = exc
        try:
            body = response.read().decode("utf-8", "replace")
            code = response.status if hasattr(response, "status") else response.code
        finally:
            response.close()
        self.assertEqual(code, 403)
        self.assertIn("not sent from this site", body)
        connection = connect(self.database)
        try:
            row = connection.execute(
                "SELECT detail FROM audit_events WHERE action = ? ORDER BY id DESC LIMIT 1",
                ("csrf_rejected",),
            ).fetchone()
        finally:
            connection.close()
        self.assertEqual(row["detail"], "fetch")
        plain = urllib.request.Request(
            self.base + "/login",
            data=urllib.parse.urlencode(
                {"email": "anyone@pilot.example", "password": "session-pass-1"}
            ).encode(),
            method="POST",
        )
        try:
            response = urllib.request.urlopen(plain)
        except urllib.error.HTTPError as exc:
            response = exc
        try:
            plain_body = response.read().decode("utf-8", "replace")
        finally:
            response.close()
        self.assertNotIn("not sent from this site", plain_body)

    def test_reset_link_stays_out_of_the_log_and_ends_the_session(self) -> None:
        from app import mail

        email = "reset@pilot.example"
        self._register(email)
        _status, cookie = _login(self.base, email, "session-pass-1")
        OUTBOX.clear()
        mail.echo = True
        captured = io.StringIO()
        previous = sys.stderr
        sys.stderr = captured
        try:
            request = urllib.request.Request(
                self.base + "/forgot-password",
                data=urllib.parse.urlencode({"email": email}).encode(),
                method="POST",
            )
            try:
                urllib.request.urlopen(request).close()
            except urllib.error.HTTPError as exc:
                exc.close()
        finally:
            sys.stderr = previous
            mail.echo = False
        self.assertTrue(OUTBOX)
        body = OUTBOX[-1]["body"]
        self.assertIn("/account/reset?token=", body)
        token = body.split("token=", 1)[1].split()[0]
        self.assertNotIn(token, captured.getvalue())
        self.assertNotIn(email, captured.getvalue())
        reset = urllib.request.Request(
            self.base + "/account/reset",
            data=urllib.parse.urlencode(
                {
                    "token": token,
                    "password": "session-pass-2",
                    "password_confirm": "session-pass-2",
                }
            ).encode(),
            method="POST",
        )
        try:
            urllib.request.urlopen(reset).close()
        except urllib.error.HTTPError as exc:
            exc.close()
        status, page = _get(self.base + "/", cookie)
        self.assertEqual(status, 200)
        self.assertNotIn("Your assessments", page)
        replaced, _new_cookie = _login(self.base, email, "session-pass-2")
        self.assertEqual(replaced, 303)

    def test_another_customer_cannot_open_the_draft(self) -> None:
        self._register("owner@pilot.example")
        self._register("other@pilot.example")
        _status, owner = _login(self.base, "owner@pilot.example", "session-pass-1")
        _status, other = _login(self.base, "other@pilot.example", "session-pass-1")

        class NoRedirect(urllib.request.HTTPRedirectHandler):
            def redirect_request(self, req, fp, code, msg, headers, newurl):
                return None

        request = urllib.request.Request(
            self.base + "/assessments",
            data=urllib.parse.urlencode(
                {"business_name": "Private Cafe", "purpose": "startup_feasibility", "tier": "explore"}
            ).encode(),
            headers={"Cookie": owner},
            method="POST",
        )
        try:
            response = urllib.request.build_opener(NoRedirect).open(request)
        except urllib.error.HTTPError as exc:
            response = exc
        try:
            location = response.headers.get("Location") or ""
        finally:
            response.close()
        status, page = _get(self.base + location, other)
        self.assertEqual(status, 403)
        self.assertNotIn("Private Cafe", page)


if __name__ == "__main__":
    unittest.main()

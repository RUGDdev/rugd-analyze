"""Email verification and password reset. Neither link changes a role."""

import hashlib
import threading
import unittest
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

from app.accounts import (
    RESET_NOTICE,
    AccountError,
    authenticate_user,
    confirm_email,
    register_account,
    request_password_reset,
    reset_password,
    send_verification,
)
from app.mail import OUTBOX
from app.review import approve_assessment, open_account_session
from app.server import make_server
from app.store import BASELINE_ID, SAMPLE, connect, get_assessment, seed

CUSTOMER_EMAIL = "mail-customer@pilot.example"
CUSTOMER_PASSWORD = "customer-pass-1"
NEW_PASSWORD = "customer-pass-2"


class TestAccountMail(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = __import__("tempfile").TemporaryDirectory(ignore_cleanup_errors=True)
        self.connection = connect(Path(self.directory.name) / "analyze.sqlite")
        seed(self.connection)
        OUTBOX.clear()

    def tearDown(self) -> None:
        self.connection.close()
        self.directory.cleanup()

    def test_expired_and_used_links_do_not_change_role_or_the_baseline(self) -> None:
        before = hashlib.sha256(SAMPLE.read_bytes()).hexdigest()
        past = datetime(2020, 1, 1, tzinfo=timezone.utc)
        user = register_account(
            self.connection,
            email=CUSTOMER_EMAIL,
            password=CUSTOMER_PASSWORD,
        )
        self.assertEqual(user["role"], "customer")
        self.assertFalse(user["email_verified"])
        self.assertNotIn(CUSTOMER_PASSWORD, OUTBOX[-1]["body"])
        send_verification(self.connection, user, now=past)
        expired = _token(OUTBOX[-1]["body"])
        with self.assertRaises(AccountError) as caught:
            confirm_email(self.connection, expired, now=past + timedelta(hours=25))
        self.assertIn("expired", str(caught.exception))
        self.assertEqual(_role(self.connection), "customer")
        self.assertFalse(_verified(self.connection))

        send_verification(self.connection, user)
        first = _token(OUTBOX[-1]["body"])
        send_verification(self.connection, user)
        second = _token(OUTBOX[-1]["body"])
        with self.assertRaises(AccountError):
            confirm_email(self.connection, first)
        verified = confirm_email(self.connection, second)
        self.assertTrue(verified["email_verified"])
        self.assertEqual(verified["role"], "customer")
        with self.assertRaises(AccountError) as used:
            confirm_email(self.connection, second)
        self.assertIn("already been used", str(used.exception))

        request_password_reset(self.connection, "nobody@pilot.example")
        self.assertNotIn("nobody@pilot.example", " ".join(item["to"] for item in OUTBOX))
        request_password_reset(self.connection, CUSTOMER_EMAIL, now=past)
        stale_reset = _token(OUTBOX[-1]["body"])
        with self.assertRaises(AccountError) as reset_expired:
            reset_password(
                self.connection,
                stale_reset,
                NEW_PASSWORD,
                now=past + timedelta(hours=2),
            )
        self.assertIn("expired", str(reset_expired.exception))
        authenticate_user(self.connection, email=CUSTOMER_EMAIL, password=CUSTOMER_PASSWORD)

        request_password_reset(self.connection, CUSTOMER_EMAIL)
        reset_token = _token(OUTBOX[-1]["body"])
        with self.assertRaises(AccountError):
            confirm_email(self.connection, reset_token)
        changed = reset_password(self.connection, reset_token, NEW_PASSWORD)
        self.assertEqual(changed["role"], "customer")
        self.assertTrue(changed["email_verified"])
        with self.assertRaises(AccountError):
            authenticate_user(self.connection, email=CUSTOMER_EMAIL, password=CUSTOMER_PASSWORD)
        authenticate_user(self.connection, email=CUSTOMER_EMAIL, password=NEW_PASSWORD)
        with self.assertRaises(AccountError) as reused:
            reset_password(self.connection, reset_token, "customer-pass-3")
        self.assertIn("already been used", str(reused.exception))

        session = open_account_session(
            self.connection,
            email=CUSTOMER_EMAIL,
            password=NEW_PASSWORD,
        )
        with self.assertRaises(PermissionError):
            approve_assessment(self.connection, BASELINE_ID, session=session)
        baseline = get_assessment(self.connection, BASELINE_ID)
        assert baseline is not None
        self.assertFalse(baseline["human_review_approved"])
        self.assertEqual(hashlib.sha256(SAMPLE.read_bytes()).hexdigest(), before)

    def test_http_banner_and_reset_do_not_escalate_the_role(self) -> None:
        before = hashlib.sha256(SAMPLE.read_bytes()).hexdigest()
        server = make_server(Path(self.directory.name) / "analyze.sqlite", port=0)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        host, port = server.server_address
        base = f"http://{host}:{port}"
        try:
            self._post(
                base + "/register",
                {
                    "email": CUSTOMER_EMAIL,
                    "password": CUSTOMER_PASSWORD,
                    "password_confirm": CUSTOMER_PASSWORD,
                    "role": "reviewer",
                },
                403,
            )
            self.assertIsNone(
                self.connection.execute(
                    "SELECT role FROM users WHERE email = ?",
                    (CUSTOMER_EMAIL,),
                ).fetchone()
            )
            self._post(
                base + "/register",
                {
                    "email": CUSTOMER_EMAIL,
                    "password": CUSTOMER_PASSWORD,
                    "password_confirm": CUSTOMER_PASSWORD,
                },
                303,
            )
            self.assertEqual(_role(self.connection), "customer")
            cookie = self._login(base, CUSTOMER_EMAIL, CUSTOMER_PASSWORD)
            home = self._get(base + "/", cookie)
            self.assertIn('id="email-unverified"', home)
            self.assertIn("Your email is not verified.", home)
            results = self._get(base + f"/assessments/{BASELINE_ID}/results", cookie)
            self.assertIn("Recommendation:</strong> do-not-proceed", results)
            self.assertIn("INSUFFICIENT_DEMAND_EVIDENCE", results)
            self.assertIn("Investor readiness:</strong> internal", results)
            missing = self._post(base + "/forgot-password", {"email": "nobody@pilot.example"}, 200)
            known = self._post(base + "/forgot-password", {"email": CUSTOMER_EMAIL}, 200)
            self.assertIn(RESET_NOTICE, missing)
            self.assertIn(RESET_NOTICE, known)
            token = _token(OUTBOX[-1]["body"])
            updated = self._post(
                base + "/account/reset",
                {
                    "token": token,
                    "password": NEW_PASSWORD,
                    "password_confirm": NEW_PASSWORD,
                    "role": "reviewer",
                },
                200,
            )
            self.assertIn("Your role is unchanged.", updated)
            self.assertEqual(_role(self.connection), "customer")
            self._login(base, CUSTOMER_EMAIL, NEW_PASSWORD)
            self._post(
                base + "/login",
                {"email": CUSTOMER_EMAIL, "password": CUSTOMER_PASSWORD},
                403,
            )
            verify = _token(next(item["body"] for item in OUTBOX if "account/verify?token=" in item["body"]))
            page = self._get(base + "/account/verify?token=" + urllib.parse.quote(verify), cookie)
            self.assertIn("Email verified.", page)
            self.assertEqual(_role(self.connection), "customer")
            self.assertNotIn('id="email-unverified"', self._get(base + "/", cookie))
            self.assertFalse(get_assessment(self.connection, BASELINE_ID)["human_review_approved"])
            self.assertEqual(hashlib.sha256(SAMPLE.read_bytes()).hexdigest(), before)
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=3)

    def _login(self, base: str, email: str, password: str) -> str:
        status, _body, headers = self._raw(
            base + "/login",
            {"email": email, "password": password},
        )
        self.assertEqual(status, 303)
        return (headers.get("Set-Cookie") or "").split(";", 1)[0]

    def _post(self, url: str, fields: dict[str, str], status: int) -> str:
        code, body, _headers = self._raw(url, fields)
        self.assertEqual(code, status)
        return body

    def _get(self, url: str, cookie: str) -> str:
        request = urllib.request.Request(url, headers={"Cookie": cookie})
        with urllib.request.urlopen(request) as response:
            self.assertEqual(response.status, 200)
            return response.read().decode("utf-8")

    def _raw(self, url: str, fields: dict[str, str]) -> tuple[int, str, dict[str, str]]:
        class NoRedirect(urllib.request.HTTPRedirectHandler):
            def redirect_request(self, req, fp, code, msg, headers, newurl):
                return None

        opener = urllib.request.build_opener(NoRedirect)
        request = urllib.request.Request(
            url,
            data=urllib.parse.urlencode(fields).encode(),
            method="POST",
        )
        try:
            response = opener.open(request)
        except urllib.error.HTTPError as exc:
            return exc.code, exc.read().decode("utf-8"), dict(exc.headers)
        return response.status, response.read().decode("utf-8"), dict(response.headers)


def _token(body: str) -> str:
    for line in body.splitlines():
        if "token=" in line:
            return urllib.parse.parse_qs(urllib.parse.urlparse(line.strip()).query)["token"][0]
    raise AssertionError("mail did not include a token")


def _role(connection) -> str:
    return connection.execute(
        "SELECT role FROM users WHERE email = ?",
        (CUSTOMER_EMAIL,),
    ).fetchone()["role"]


def _verified(connection) -> bool:
    return bool(
        connection.execute(
            "SELECT email_verified FROM users WHERE email = ?",
            (CUSTOMER_EMAIL,),
        ).fetchone()["email_verified"]
    )


if __name__ == "__main__":
    unittest.main()

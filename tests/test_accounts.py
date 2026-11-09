"""Local email and password accounts. A customer session cannot approve."""

import hashlib
import tempfile
import threading
import unittest
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from app.accounts import (
    AccountError,
    bootstrap_reviewer,
    create_reviewer_account,
    hash_password,
    register_account,
    verify_password,
)
from app.pages import login_page, logout_page, register_page
from app.review import approve_assessment, open_account_session
from app.server import make_server
from app.store import (
    BASELINE_ID,
    SAMPLE,
    connect,
    create_assessment,
    get_assessment,
    seed,
    session_storage_key,
)

REVIEWER_EMAIL = "reviewer@pilot.example"
REVIEWER_PASSWORD = "reviewer-pass-1"
CUSTOMER_EMAIL = "customer@pilot.example"
CUSTOMER_PASSWORD = "customer-pass-1"


class TestLocalAccounts(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.connection = connect(Path(self.directory.name) / "analyze.sqlite")
        seed(self.connection)

    def tearDown(self) -> None:
        self.connection.close()
        self.directory.cleanup()

    def test_registration_stores_a_hash_and_login_keeps_the_baseline(self) -> None:
        before = hashlib.sha256(SAMPLE.read_bytes()).hexdigest()
        reviewer = bootstrap_reviewer(
            self.connection,
            email="Reviewer@Pilot.Example",
            password=REVIEWER_PASSWORD,
        )
        customer = register_account(
            self.connection,
            email=CUSTOMER_EMAIL,
            password=CUSTOMER_PASSWORD,
        )
        self.assertEqual(reviewer["email"], REVIEWER_EMAIL)
        self.assertEqual(reviewer["role"], "reviewer")
        self.assertNotIn("password", reviewer)
        self.assertEqual(customer["role"], "customer")
        stored = self.connection.execute("SELECT email, password_hash, role FROM users").fetchall()
        joined = " ".join(" ".join(row) for row in stored)
        self.assertNotIn(REVIEWER_PASSWORD, joined)
        self.assertNotIn(CUSTOMER_PASSWORD, joined)
        self.assertIn("scrypt$", joined)
        self.assertTrue(verify_password(REVIEWER_PASSWORD, stored[0]["password_hash"]))
        with self.assertRaises(AccountError):
            register_account(
                self.connection,
                email=REVIEWER_EMAIL,
                password=REVIEWER_PASSWORD,
            )
        with self.assertRaises(AccountError):
            register_account(
                self.connection,
                email="short@pilot.example",
                password="short",
            )
        with self.assertRaises(PermissionError):
            open_account_session(
                self.connection,
                email=REVIEWER_EMAIL,
                password="wrong-pass-1",
            )
        customer_session = open_account_session(
            self.connection,
            email=CUSTOMER_EMAIL,
            password=CUSTOMER_PASSWORD,
        )
        reviewer_session = open_account_session(
            self.connection,
            email=REVIEWER_EMAIL,
            password=REVIEWER_PASSWORD,
        )
        self.assertEqual(customer_session["role"], "customer")
        self.assertEqual(reviewer_session["role"], "reviewer")
        self.assertNotEqual(
            self.connection.execute("SELECT token FROM reviewer_sessions").fetchone()["token"],
            customer_session["token"],
        )
        self.assertEqual(
            session_storage_key(reviewer_session["token"]),
            self.connection.execute(
                "SELECT token FROM reviewer_sessions WHERE reviewer_identity = ?",
                (REVIEWER_EMAIL,),
            ).fetchone()["token"],
        )
        assessment_id = create_assessment(
            self.connection,
            business_name="Account Cafe",
            purpose="startup_feasibility",
            tier="analyze",
        )
        with self.assertRaises(PermissionError):
            approve_assessment(self.connection, assessment_id, session=customer_session)
        self.assertFalse(get_assessment(self.connection, assessment_id)["human_review_approved"])
        result = approve_assessment(self.connection, assessment_id, session=reviewer_session)
        self.assertTrue(result["human_review_approved"])
        self.assertEqual(result["audit"]["approvals"][0]["reviewer_identity"], REVIEWER_EMAIL)
        self.assertEqual(result["recommendation"], "do-not-proceed")
        self.assertIn("INSUFFICIENT_DEMAND_EVIDENCE", result["blocking_flags"])
        self.assertEqual(result["readiness_status"], "internal")
        self.assertFalse(result["is_final"])
        with self.assertRaises(PermissionError):
            approve_assessment(self.connection, BASELINE_ID, session=reviewer_session)
        baseline = get_assessment(self.connection, BASELINE_ID)
        assert baseline is not None
        self.assertFalse(baseline["human_review_approved"])
        self.assertEqual(hashlib.sha256(SAMPLE.read_bytes()).hexdigest(), before)
        self.assertTrue(hash_password("another-password").startswith("scrypt$"))

    def test_account_pages_keep_the_prototype_warning(self) -> None:
        note = "This screen does not grant investor-ready status."
        for page in (login_page("/reviewer"), register_page(), logout_page(None)):
            self.assertIn('class="sidebar"', page)
            self.assertIn(note, page)
            self.assertIn("not production authentication", page.lower())
            self.assertNotIn(REVIEWER_PASSWORD, page)
        register = register_page()
        self.assertIn("Self-registration creates a customer account.", register)
        self.assertNotIn('value="reviewer"', register)
        self.assertIn("cannot create a reviewer", login_page().lower())
        self.assertIn('href="/login" class="active"', login_page())

    def test_self_registration_cannot_create_or_escalate_a_reviewer(self) -> None:
        before = hashlib.sha256(SAMPLE.read_bytes()).hexdigest()
        customer = register_account(
            self.connection,
            email=CUSTOMER_EMAIL,
            password=CUSTOMER_PASSWORD,
        )
        self.assertEqual(customer["role"], "customer")
        self.assertIsNone(
            bootstrap_reviewer(
                self.connection,
                email=CUSTOMER_EMAIL,
                password=CUSTOMER_PASSWORD,
            )
        )
        self.assertEqual(
            self.connection.execute(
                "SELECT role FROM users WHERE email = ?",
                (CUSTOMER_EMAIL,),
            ).fetchone()["role"],
            "customer",
        )
        reviewer = bootstrap_reviewer(
            self.connection,
            email=REVIEWER_EMAIL,
            password=REVIEWER_PASSWORD,
        )
        assert reviewer is not None
        self.assertEqual(reviewer["role"], "reviewer")
        self.assertIsNone(
            bootstrap_reviewer(
                self.connection,
                email="second@pilot.example",
                password=REVIEWER_PASSWORD,
            )
        )
        customer_session = open_account_session(
            self.connection,
            email=CUSTOMER_EMAIL,
            password=CUSTOMER_PASSWORD,
        )
        with self.assertRaises(AccountError):
            create_reviewer_account(
                self.connection,
                email="second@pilot.example",
                password=REVIEWER_PASSWORD,
                session=customer_session,
            )
        reviewer_session = open_account_session(
            self.connection,
            email=REVIEWER_EMAIL,
            password=REVIEWER_PASSWORD,
        )
        created = create_reviewer_account(
            self.connection,
            email="second@pilot.example",
            password=REVIEWER_PASSWORD,
            session=reviewer_session,
        )
        self.assertEqual(created["role"], "reviewer")
        with self.assertRaises(AccountError):
            create_reviewer_account(
                self.connection,
                email=CUSTOMER_EMAIL,
                password=REVIEWER_PASSWORD,
                session=reviewer_session,
            )
        self.assertEqual(
            self.connection.execute(
                "SELECT role FROM users WHERE email = ?",
                (CUSTOMER_EMAIL,),
            ).fetchone()["role"],
            "customer",
        )
        server = make_server(Path(self.directory.name) / "analyze.sqlite", port=0)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        host, port = server.server_address
        base = f"http://{host}:{port}"
        try:
            self._expect_status(base + "/reviewer/accounts", b"email=third%40pilot.example&password=reviewer-pass-1&password_confirm=reviewer-pass-1", 403)
            self._expect_status(
                base + "/register",
                urllib.parse.urlencode(
                    {
                        "email": "sneak@pilot.example",
                        "password": CUSTOMER_PASSWORD,
                        "password_confirm": CUSTOMER_PASSWORD,
                        "role": "reviewer",
                    }
                ).encode(),
                403,
            )
            self.assertIsNone(
                self.connection.execute(
                    "SELECT role FROM users WHERE email = ?",
                    ("sneak@pilot.example",),
                ).fetchone()
            )
            customer_cookie = self._login(base, CUSTOMER_EMAIL, CUSTOMER_PASSWORD)
            self._expect_status_with_cookie(
                base + "/reviewer/accounts",
                urllib.parse.urlencode(
                    {
                        "email": "third@pilot.example",
                        "password": REVIEWER_PASSWORD,
                        "password_confirm": REVIEWER_PASSWORD,
                    }
                ).encode(),
                customer_cookie,
                403,
                "cannot create a reviewer",
            )
            reviewer_cookie = self._login(base, REVIEWER_EMAIL, REVIEWER_PASSWORD)
            self._post_redirect(
                base + "/reviewer/accounts",
                urllib.parse.urlencode(
                    {
                        "email": "third@pilot.example",
                        "password": REVIEWER_PASSWORD,
                        "password_confirm": REVIEWER_PASSWORD,
                    }
                ).encode(),
                reviewer_cookie,
            )
            self.assertEqual(
                self.connection.execute(
                    "SELECT role FROM users WHERE email = ?",
                    ("third@pilot.example",),
                ).fetchone()["role"],
                "reviewer",
            )
            third = open_account_session(
                self.connection,
                email="third@pilot.example",
                password=REVIEWER_PASSWORD,
            )
            assessment_id = create_assessment(
                self.connection,
                business_name="Controlled Cafe",
                purpose="startup_feasibility",
                tier="analyze",
            )
            result = approve_assessment(self.connection, assessment_id, session=third)
            self.assertEqual(result["audit"]["approvals"][0]["reviewer_identity"], "third@pilot.example")
            self.assertEqual(result["recommendation"], "do-not-proceed")
            self.assertIn("INSUFFICIENT_DEMAND_EVIDENCE", result["blocking_flags"])
            self.assertEqual(result["readiness_status"], "internal")
            self.assertFalse(get_assessment(self.connection, BASELINE_ID)["human_review_approved"])
            self.assertEqual(hashlib.sha256(SAMPLE.read_bytes()).hexdigest(), before)
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=3)

    def _login(self, base: str, email: str, password: str) -> str:
        class NoRedirect(urllib.request.HTTPRedirectHandler):
            def redirect_request(self, req, fp, code, msg, headers, newurl):
                return None

        opener = urllib.request.build_opener(NoRedirect)
        request = urllib.request.Request(
            base + "/login",
            data=urllib.parse.urlencode({"email": email, "password": password}).encode(),
            method="POST",
        )
        try:
            opener.open(request)
        except urllib.error.HTTPError as exc:
            self.assertEqual(exc.code, 303)
            cookie = exc.headers.get("Set-Cookie") or ""
        else:
            self.fail("login should redirect")
        return cookie.split(";", 1)[0]

    def _post_redirect(self, url: str, body: bytes, cookie: str) -> None:
        class NoRedirect(urllib.request.HTTPRedirectHandler):
            def redirect_request(self, req, fp, code, msg, headers, newurl):
                return None

        opener = urllib.request.build_opener(NoRedirect)
        request = urllib.request.Request(
            url,
            data=body,
            method="POST",
            headers={"Cookie": cookie},
        )
        try:
            opener.open(request)
        except urllib.error.HTTPError as exc:
            self.assertEqual(exc.code, 303)
            return
        self.fail("reviewer creation should redirect")

    def _expect_status(self, url: str, body: bytes, status: int) -> None:
        request = urllib.request.Request(url, data=body, method="POST")
        try:
            urllib.request.urlopen(request)
        except urllib.error.HTTPError as exc:
            self.assertEqual(exc.code, status)
            return
        self.fail(f"expected HTTP {status}")

    def _expect_status_with_cookie(
        self,
        url: str,
        body: bytes,
        cookie: str,
        status: int,
        text: str,
    ) -> None:
        request = urllib.request.Request(url, data=body, method="POST", headers={"Cookie": cookie})
        try:
            urllib.request.urlopen(request)
        except urllib.error.HTTPError as exc:
            self.assertEqual(exc.code, status)
            self.assertIn(text, exc.read().decode("utf-8"))
            return
        self.fail(f"expected HTTP {status}")

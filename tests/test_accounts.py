"""Local email and password accounts. A customer session cannot approve."""

import hashlib
import tempfile
import unittest
from pathlib import Path

from app.accounts import AccountError, hash_password, register_account, verify_password
from app.pages import login_page, logout_page, register_page
from app.review import approve_assessment, open_account_session
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
        reviewer = register_account(
            self.connection,
            email="Reviewer@Pilot.Example",
            password=REVIEWER_PASSWORD,
            role="reviewer",
        )
        customer = register_account(
            self.connection,
            email=CUSTOMER_EMAIL,
            password=CUSTOMER_PASSWORD,
            role="customer",
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
                role="reviewer",
            )
        with self.assertRaises(AccountError):
            register_account(
                self.connection,
                email="other@pilot.example",
                password=REVIEWER_PASSWORD,
                role="owner",
            )
        with self.assertRaises(AccountError):
            register_account(
                self.connection,
                email="short@pilot.example",
                password="short",
                role="customer",
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
        self.assertIn("Customer", register_page())
        self.assertIn("Reviewer", register_page())
        self.assertIn('href="/login" class="active"', login_page())

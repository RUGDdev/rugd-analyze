"""Read-only share links cannot edit an assessment or approve it."""

import hashlib
import json
import tempfile
import threading
import unittest
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from app.accounts import bootstrap_reviewer, register_account
from app.review import open_account_session
from app.server import make_server
from app.share import ShareError, issue_share_link, open_share, revoke_share
from app.store import (
    BASELINE_ID,
    SAMPLE,
    connect,
    create_assessment,
    get_assessment,
    save_profile,
    save_result,
    seed,
)

CUSTOMER_EMAIL = "share-owner@pilot.example"
OTHER_EMAIL = "share-other@pilot.example"
REVIEWER_EMAIL = "share-reviewer@pilot.example"
PASSWORD = "share-pass-1"


class TestReadOnlyShare(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.connection = connect(Path(self.directory.name) / "analyze.sqlite")
        seed(self.connection)
        self.owner = register_account(self.connection, email=CUSTOMER_EMAIL, password=PASSWORD)
        self.other = register_account(self.connection, email=OTHER_EMAIL, password=PASSWORD)
        self.reviewer = bootstrap_reviewer(self.connection, email=REVIEWER_EMAIL, password=PASSWORD)
        assert self.reviewer is not None
        self.assessment_id = create_assessment(
            self.connection,
            business_name="Share Cafe",
            purpose="startup_feasibility",
            tier="analyze",
            owner_user_id=self.owner["id"],
        )
        save_profile(
            self.connection,
            self.assessment_id,
            {
                "business_name": "Share Cafe",
                "purpose": "startup_feasibility",
                "tier": "analyze",
                "industry": "Restaurant",
                "market": "Example county",
                "stage": "Idea",
            },
        )
        save_result(self.connection, self.assessment_id, None, _engine_result())

    def tearDown(self) -> None:
        self.connection.close()
        self.directory.cleanup()

    def test_expired_revoked_and_foreign_links_do_not_change_the_baseline(self) -> None:
        before = hashlib.sha256(SAMPLE.read_bytes()).hexdigest()
        record = get_assessment(self.connection, self.assessment_id)
        assert record is not None
        owner_session = open_account_session(self.connection, email=CUSTOMER_EMAIL, password=PASSWORD)
        other_session = open_account_session(self.connection, email=OTHER_EMAIL, password=PASSWORD)
        reviewer_session = open_account_session(self.connection, email=REVIEWER_EMAIL, password=PASSWORD)
        with self.assertRaises(ShareError):
            issue_share_link(self.connection, record, other_session, "7d")
        with self.assertRaises(ShareError):
            issue_share_link(self.connection, get_assessment(self.connection, BASELINE_ID), owner_session, "7d")
        stale = issue_share_link(
            self.connection,
            record,
            owner_session,
            "24h",
            now=datetime(2020, 1, 1, tzinfo=timezone.utc),
        )
        with self.assertRaises(ShareError) as expired:
            open_share(self.connection, stale["token"], now=datetime(2020, 1, 3, tzinfo=timezone.utc))
        self.assertIn("expired", str(expired.exception))
        issued = issue_share_link(self.connection, record, owner_session, "until-revoked")
        opened = open_share(self.connection, issued["token"])
        self.assertEqual(opened["id"], self.assessment_id)
        self.assertFalse(opened["human_review_approved"])
        revoke_share(self.connection, record, owner_session, issued["id"])
        with self.assertRaises(ShareError) as revoked:
            open_share(self.connection, issued["token"])
        self.assertIn("revoked", str(revoked.exception))
        with self.assertRaises(ShareError):
            revoke_share(self.connection, record, other_session, issued["id"])
        baseline_link = issue_share_link(
            self.connection,
            get_assessment(self.connection, BASELINE_ID),
            reviewer_session,
            "7d",
        )
        shared_baseline = open_share(self.connection, baseline_link["token"])
        self.assertEqual(shared_baseline["id"], BASELINE_ID)
        self.assertFalse(shared_baseline["human_review_approved"])
        self.assertEqual(get_assessment(self.connection, self.assessment_id)["result"]["recommendation"], "do-not-proceed")
        self.assertEqual(hashlib.sha256(SAMPLE.read_bytes()).hexdigest(), before)

    def test_http_share_cannot_mutate_or_approve(self) -> None:
        before = hashlib.sha256(SAMPLE.read_bytes()).hexdigest()
        stored = json.dumps(get_assessment(self.connection, self.assessment_id)["result"], sort_keys=True)
        server = make_server(Path(self.directory.name) / "analyze.sqlite", port=0)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        host, port = server.server_address
        base = f"http://{host}:{port}"
        try:
            denied = self._post(base + f"/assessments/{self.assessment_id}/share", {"lifetime": "7d"}, 403)
            self.assertIn("not available to this session", denied)
            self.assertNotIn("Share Cafe", denied)
            cookie = self._login(base, CUSTOMER_EMAIL, PASSWORD)
            status, _body, headers = self._raw(
                base + f"/assessments/{self.assessment_id}/share",
                {"lifetime": "7d"},
                cookie,
            )
            self.assertEqual(status, 303)
            location = headers.get("Location") or ""
            token = urllib.parse.parse_qs(urllib.parse.urlparse(location).query)["share"][0]
            page = self._get(base + f"/share/{token}")
            self.assertIn("Local prototype. Not production security. This screen does not grant investor-ready status.", page)
            self.assertIn("Read-only share.", page)
            self.assertIn("Indicative assessment — market validity, financial viability, and stewardship readiness.", page)
            self.assertIn("Market context", page)
            self.assertIn("Restaurant", page)
            self.assertIn("These figures do not clear INSUFFICIENT_DEMAND_EVIDENCE", page)
            self.assertIn("Recommendation:</strong> do-not-proceed", page)
            self.assertIn("human_review_approved:</strong> false", page)
            self.assertIn("Audit summary", page)
            self.assertNotIn("<form", page.lower())
            self.assertNotIn("Save draft", page)
            self.assertNotIn("Run Analyze", page)
            self.assertNotIn("Request review", page)
            self.assertNotIn(">Approve<", page)
            self._post(
                base + f"/share/{token}",
                {"business_name": "Changed", "role": "reviewer"},
                403,
            )
            self._post(
                base + f"/share/{token}/approve",
                {"note": "approve"},
                403,
            )
            self._post(
                base + f"/share/{token}",
                {"human_review_approved": "true"},
                403,
                cookie,
            )
            current = get_assessment(self.connection, self.assessment_id)
            assert current is not None
            self.assertEqual(json.dumps(current["result"], sort_keys=True), stored)
            self.assertEqual(current["business_name"], "Share Cafe")
            self.assertFalse(current["human_review_approved"])
            self.assertEqual(current["result"]["recommendation"], "do-not-proceed")
            self.assertIn("INSUFFICIENT_DEMAND_EVIDENCE", current["result"]["blocking_flags"])
            baseline = get_assessment(self.connection, BASELINE_ID)
            assert baseline is not None
            self.assertFalse(baseline["human_review_approved"])
            self.assertEqual(hashlib.sha256(SAMPLE.read_bytes()).hexdigest(), before)
            self._raw(
                base + f"/assessments/{self.assessment_id}/share/{_share_id(self.connection, self.assessment_id)}/revoke",
                {},
                cookie,
            )
            revoked = self._get_status(base + f"/share/{token}")
            self.assertEqual(revoked[0], 403)
            self.assertIn("revoked", revoked[1])
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=3)

    def _login(self, base: str, email: str, password: str) -> str:
        status, _body, headers = self._raw(base + "/login", {"email": email, "password": password})
        self.assertEqual(status, 303)
        return (headers.get("Set-Cookie") or "").split(";", 1)[0]

    def _post(self, url: str, fields: dict[str, str], status: int, cookie: str = "") -> str:
        code, body, _headers = self._raw(url, fields, cookie)
        self.assertEqual(code, status, body)
        return body

    def _get(self, url: str) -> str:
        code, body = self._get_status(url)
        self.assertEqual(code, 200)
        return body

    def _get_status(self, url: str) -> tuple[int, str]:
        request = urllib.request.Request(url)
        try:
            with urllib.request.urlopen(request) as response:
                return response.status, response.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            return exc.code, exc.read().decode("utf-8")

    def _raw(
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


def _engine_result() -> dict:
    return {
        "engine_ran": True,
        "model_version": "0.1-pilot",
        "recommendation": "do-not-proceed",
        "blocking_flags": ["INSUFFICIENT_DEMAND_EVIDENCE"],
        "gap_flags": [],
        "missing": [],
        "human_review_approved": False,
        "human_review_status": "pending",
        "readiness_status": "internal",
        "is_final": False,
        "score_line": "Not calculated — methodology pending approval.",
        "financial": None,
        "projection": {"calculated": False, "views": None},
        "demand": {"status": "uncleared"},
    }


def _share_id(connection, assessment_id: str) -> str:
    row = connection.execute(
        "SELECT id FROM share_links WHERE assessment_id = ? AND revoked_at IS NULL",
        (assessment_id,),
    ).fetchone()
    assert row is not None
    return row["id"]


if __name__ == "__main__":
    unittest.main()

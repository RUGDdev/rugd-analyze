"""Business profiles are local structure. They do not change the baseline or the engine."""

import hashlib
import json
import tempfile
import threading
import unittest
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from app.analysis import analyze_record
from app.server import make_server
from app.store import (
    BASELINE_ID,
    BASELINE_PROFILE_ID,
    ISOLATION_BASELINE,
    ISOLATION_CUSTOMER,
    ISOLATION_PILOT,
    RESTAURANT_ID,
    RESTAURANT_PROFILE_ID,
    RESTAURANT_VERIFIED_PROFILE_ID,
    SAMPLE,
    connect,
    create_assessment,
    create_linked_assessment,
    get_assessment,
    get_business_profile,
    save_profile,
    save_result,
    seed,
)

ROOT = Path(__file__).resolve().parent.parent
DRAFT_REPORT = ROOT / "reports" / "output" / "rugd-intelligence-draft.md"


class TestBusinessProfiles(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.db = Path(self.directory.name) / "analyze.sqlite"
        self.connection = connect(self.db)
        seed(self.connection)

    def tearDown(self) -> None:
        self.connection.close()
        self.directory.cleanup()

    def _snapshot(self, assessment_id: str) -> tuple[str, str, str]:
        row = self.connection.execute(
            "SELECT profile_json, intake_json, result_json FROM assessments WHERE id = ?",
            (assessment_id,),
        ).fetchone()
        return (row["profile_json"], row["intake_json"] or "", row["result_json"] or "")

    def test_profiles_link_drafts_and_leave_the_baseline_unchanged(self) -> None:
        sample_before = hashlib.sha256(SAMPLE.read_bytes()).hexdigest()
        report_before = hashlib.sha256(DRAFT_REPORT.read_bytes()).hexdigest()
        baseline_before = self._snapshot(BASELINE_ID)
        baseline = get_assessment(self.connection, BASELINE_ID)
        assert baseline is not None
        self.assertEqual(baseline["business_profile_id"], BASELINE_PROFILE_ID)
        self.assertEqual(baseline["business_profile"]["isolation"], ISOLATION_BASELINE)
        restaurant = get_assessment(self.connection, RESTAURANT_ID)
        assert restaurant is not None
        self.assertEqual(restaurant["business_profile_id"], RESTAURANT_PROFILE_ID)
        self.assertEqual(restaurant["business_profile"]["isolation"], ISOLATION_PILOT)
        self.assertNotEqual(RESTAURANT_PROFILE_ID, RESTAURANT_VERIFIED_PROFILE_ID)
        self.assertNotEqual(BASELINE_PROFILE_ID, RESTAURANT_PROFILE_ID)

        bunny_id = create_assessment(
            self.connection,
            business_name="Bunny Hive",
            purpose="startup_feasibility",
            tier="explore",
            pilot_label="Named-pilot draft. Not a completed assessment. Only RUGD Intelligence is the official baseline.",
        )
        bunny = get_assessment(self.connection, bunny_id)
        assert bunny is not None
        self.assertEqual(bunny["business_profile"]["isolation"], ISOLATION_PILOT)
        self.assertNotEqual(bunny["business_profile_id"], BASELINE_PROFILE_ID)

        with self.assertRaises(PermissionError):
            create_linked_assessment(self.connection, BASELINE_ID, tier="analyze")
        with self.assertRaises(PermissionError):
            create_assessment(
                self.connection,
                business_name="Copied baseline",
                purpose="startup_feasibility",
                tier="explore",
                business_profile_id=BASELINE_PROFILE_ID,
            )
        with self.assertRaises(PermissionError):
            create_assessment(
                self.connection,
                business_name="Copied pilot",
                purpose="startup_feasibility",
                tier="explore",
                business_profile_id=bunny["business_profile_id"],
            )

        assessment_id = create_assessment(
            self.connection,
            business_name="North Cafe",
            purpose="startup_feasibility",
            tier="explore",
        )
        current = get_assessment(self.connection, assessment_id)
        assert current is not None
        self.assertEqual(current["business_profile"]["isolation"], ISOLATION_CUSTOMER)
        save_profile(
            self.connection,
            assessment_id,
            {
                **current["profile"],
                "industry": "Restaurant",
                "market": "Example county",
                "stage": "Idea",
                "seats": "12",
            },
        )
        stored = get_assessment(self.connection, assessment_id)
        assert stored is not None
        result = analyze_record(stored)
        save_result(self.connection, assessment_id, result.get("intake"), result)
        result_before = self._snapshot(assessment_id)[2]
        linked_id = create_linked_assessment(
            self.connection, assessment_id, tier="validate"
        )
        linked = get_assessment(self.connection, linked_id)
        assert linked is not None
        self.assertEqual(linked["business_profile_id"], stored["business_profile_id"])
        self.assertEqual(linked["tier"], "validate")
        self.assertEqual(linked["profile"]["business_name"], "North Cafe")
        self.assertEqual(linked["profile"]["industry"], "Restaurant")
        self.assertEqual(linked["profile"]["market"], "Example county")
        self.assertEqual(linked["profile"]["stage"], "Idea")
        self.assertEqual(linked["profile"]["seats"], "")
        self.assertEqual(linked["profile"]["demand_evidence"], "")
        source = get_assessment(self.connection, assessment_id)
        assert source is not None
        self.assertEqual(source["tier"], "explore")
        self.assertEqual(source["profile"]["seats"], "12")
        self.assertEqual(self._snapshot(assessment_id)[2], result_before)
        self.assertEqual(len(source["linked_assessments"]), 2)

        save_profile(
            self.connection,
            assessment_id,
            {**source["profile"], "tier": "analyze", "industry": "Bakery"},
        )
        moved = get_assessment(self.connection, assessment_id)
        shared = get_assessment(self.connection, linked_id)
        assert moved is not None and shared is not None
        self.assertEqual(moved["tier"], "analyze")
        self.assertEqual(moved["profile"]["industry"], "Bakery")
        self.assertEqual(moved["profile"]["seats"], "12")
        self.assertEqual(shared["tier"], "validate")
        self.assertEqual(shared["profile"]["industry"], "Bakery")
        self.assertEqual(shared["profile"]["seats"], "")
        self.assertEqual(moved["business_profile"]["industry"], "Bakery")
        self.assertEqual(moved["business_profile"]["geography"], "Example county")
        self.assertEqual(self._snapshot(assessment_id)[2], result_before)
        rerun = analyze_record(moved)
        self.assertEqual(rerun["recommendation"], "do-not-proceed")
        self.assertIn("INSUFFICIENT_DEMAND_EVIDENCE", rerun["blocking_flags"])
        self.assertEqual(rerun["readiness_status"], "internal")
        self.assertFalse(rerun["human_review_approved"])
        self.assertEqual(self._snapshot(BASELINE_ID), baseline_before)
        baseline_after = analyze_record(get_assessment(self.connection, BASELINE_ID))
        self.assertEqual(baseline_after["recommendation"], "do-not-proceed")
        self.assertIn("INSUFFICIENT_DEMAND_EVIDENCE", baseline_after["blocking_flags"])
        self.assertEqual(baseline_after["readiness_status"], "internal")
        self.assertFalse(baseline_after["human_review_approved"])
        self.assertEqual(get_business_profile(self.connection, BASELINE_PROFILE_ID)["industry"], "")
        self.assertEqual(hashlib.sha256(SAMPLE.read_bytes()).hexdigest(), sample_before)
        self.assertEqual(hashlib.sha256(DRAFT_REPORT.read_bytes()).hexdigest(), report_before)

    def test_http_keeps_baseline_profile_isolated(self) -> None:
        baseline_before = self._snapshot(BASELINE_ID)
        server = make_server(self.db, port=0)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        host, port = server.server_address
        base = f"http://{host}:{port}"
        try:
            blocked = urllib.request.Request(
                base + "/assessments",
                data=urllib.parse.urlencode(
                    {
                        "business_name": "Should fail",
                        "purpose": "startup_feasibility",
                        "tier": "explore",
                        "business_profile_id": BASELINE_PROFILE_ID,
                    }
                ).encode("utf-8"),
                method="POST",
            )
            with self.assertRaises(urllib.error.HTTPError) as caught:
                urllib.request.urlopen(blocked)
            self.assertEqual(caught.exception.code, 403)
            linked = urllib.request.Request(
                base + f"/assessments/{BASELINE_ID}/linked",
                data=urllib.parse.urlencode({"tier": "explore"}).encode("utf-8"),
                method="POST",
            )
            with self.assertRaises(urllib.error.HTTPError) as caught:
                urllib.request.urlopen(linked)
            self.assertEqual(caught.exception.code, 403)
            self.assertEqual(self._snapshot(BASELINE_ID), baseline_before)
            opener = urllib.request.build_opener(urllib.request.HTTPRedirectHandler)
            created = urllib.request.Request(
                base + "/assessments",
                data=urllib.parse.urlencode(
                    {
                        "business_name": "South Cafe",
                        "purpose": "startup_feasibility",
                        "tier": "explore",
                    }
                ).encode("utf-8"),
                method="POST",
            )
            with opener.open(created) as response:
                page = response.read().decode("utf-8")
                assessment_url = response.geturl()
            self.assertIn("South Cafe", page)
            self.assertIn("Local prototype business profile.", page)
            self.assertIn("Start another assessment for this business", page)
            follow = urllib.request.Request(
                assessment_url.rstrip("/") + "/linked",
                data=urllib.parse.urlencode({"tier": "analyze", "purpose": "startup_feasibility"}).encode("utf-8"),
                method="POST",
            )
            with opener.open(follow) as response:
                second = response.read().decode("utf-8")
            self.assertIn("South Cafe", second)
            self.assertIn("Identity:", second)
            self.assertEqual(self._snapshot(BASELINE_ID), baseline_before)
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=3)

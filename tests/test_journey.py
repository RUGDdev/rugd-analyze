"""The business workflow links the existing pages and does not write the assessment."""

from __future__ import annotations

import tempfile
import threading
import unittest
from pathlib import Path

from app.server import make_server
from app.store import connect, create_assessment, get_assessment, seed
from tests.session_cookie import open_customer
from tests.test_public_retrieval import _get

STEPS = (
    "",
    "/intelligence",
    "/results",
    "/plans",
    "/decks",
    "/reports",
    "/actions",
    "/advice",
)


class TestJourneyNavigation(unittest.TestCase):
    def test_each_step_links_the_workflow_without_changing_the_file(self) -> None:
        directory = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        database = Path(directory.name) / "analyze.sqlite"
        connection = connect(database)
        seed(connection)
        server = make_server(database, port=0)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        base = f"http://127.0.0.1:{server.server_address[1]}"
        try:
            cookie, user_id = open_customer(connection, base)
            assessment_id = create_assessment(
                connection,
                business_name="Journey Cafe",
                purpose="startup_feasibility",
                tier="explore",
                owner_user_id=user_id,
            )
            before = get_assessment(connection, assessment_id)
            assert before is not None
            for step in STEPS:
                status, body = _get(base + f"/assessments/{assessment_id}{step}", cookie)
                self.assertEqual(status, 200, step)
                self.assertIn('id="journey-nav"', body)
                self.assertIn(f"/assessments/{assessment_id}/intelligence", body)
                self.assertIn(f"/assessments/{assessment_id}/results", body)
                self.assertIn(f"/assessments/{assessment_id}/plans", body)
                self.assertIn(f"/assessments/{assessment_id}/decks", body)
                self.assertIn(f"/assessments/{assessment_id}/advice", body)
                self.assertIn("does not replace the official result", body)
            after = get_assessment(connection, assessment_id)
            assert after is not None
            self.assertEqual(after["human_review_approved"], before["human_review_approved"])
            self.assertFalse(after["human_review_approved"])
            self.assertEqual(after.get("result"), before.get("result"))
        finally:
            connection.close()
            server.shutdown()
            directory.cleanup()


if __name__ == "__main__":
    unittest.main()

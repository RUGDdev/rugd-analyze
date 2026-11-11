"""Cross-source synthesis quotes saved evidence and waits for approval."""

from __future__ import annotations

import tempfile
import threading
import unittest
from pathlib import Path

from app.adviser_workspace import ask_adviser
from app.analyst import get_analyst
from app.adviser_context import build_adviser_context
from app.research import adviser_research_view, evidence_review
from app.server import make_server
from app.store import connect, create_assessment, get_assessment, get_research_project, seed
from tests.session_cookie import open_customer
from tests.test_public_retrieval import _get, _raw


def _record(**overrides):
    item = {
        "evidence_class": "retrieved_public",
        "source_organization": "U.S. Bureau of Labor Statistics",
        "source_title": "Quarterly Census of Employment and Wages",
        "finding": "Private employment: 120. This is covered employment, not demand.",
        "limitations": "Covered employment is not demand for this business.",
        "geography": "Colbert County, Alabama",
        "industry": "Restaurant",
        "category": "trends",
        "published_on": "2024-01-01",
        "retrieved_on": "2026-11-11",
        "project_id": "project-1",
    }
    item.update(overrides)
    return item


class TestEvidenceReview(unittest.TestCase):
    def test_comparison_uses_only_saved_records(self) -> None:
        project = {"id": "project-1", "document": {"geography": "Colbert County, Alabama"}}
        one = evidence_review(project, [_record()])
        self.assertIn("Fewer than two sources", one["source_comparison"][0])
        review = evidence_review(
            project,
            [
                _record(),
                _record(
                    source_organization="Office of the Federal Register",
                    source_title="A proposed reporting change",
                    finding="A proposed reporting change. Proposed rule. This is not an enacted requirement.",
                    category="regulatory",
                    geography="",
                    industry="",
                    published_on="2020-01-15",
                ),
                _record(
                    source_organization="Office of the Federal Register",
                    finding="A final reporting rule. Final rule. Publication does not verify that it applies to this business.",
                    category="regulatory",
                    geography="Alaska",
                    industry="",
                    published_on="2026-10-01",
                ),
            ],
        )
        text = " ".join(review["source_comparison"] + review["conflicting_evidence"] + review["staleness"] + review["geographic_relevance"])
        self.assertIn("U.S. Bureau of Labor Statistics", text)
        self.assertIn("Office of the Federal Register", text)
        self.assertIn("not an enacted requirement", text)
        self.assertIn("Neither record is treated as the correct one", text)
        self.assertIn("more than 18 months", text)
        self.assertIn("does not match the project area", text)
        self.assertNotIn("%", text)
        self.assertNotIn("market size", text.lower())
        context = build_adviser_context(
            {"business_name": "Harbor", "result": {"recommendation": "do-not-proceed", "readiness_status": "internal", "risk_flags": ["INSUFFICIENT_DEMAND_EVIDENCE"]}},
            research=adviser_research_view([{"id": "project-1", "title": "Rules", "document": project["document"]}], [
                _record(),
                _record(source_organization="Office of the Federal Register", finding="Proposed rule. This is not an enacted requirement.", category="regulatory"),
            ]),
        )
        reply = ask_adviser(context, "Compare the saved research sources.", get_analyst(environ={}))
        self.assertIn("Saved comparison", reply["text"])
        self.assertIn("does not add a source", reply["text"])
        self.assertIn("human_review_approved stays false", reply["text"])


class TestApprovedUpdate(unittest.TestCase):
    def test_update_is_saved_only_after_approval(self) -> None:
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
                business_name="Synthesis Cafe",
                purpose="startup_feasibility",
                tier="explore",
                owner_user_id=user_id,
            )
            created = _raw(
                base + f"/assessments/{assessment_id}/intelligence",
                {"op": "create_project", "title": "Compare", "objective": "regulatory", "geography": "Alabama"},
                cookie,
            )
            project_path = created[2].get("Location") or ""
            project_id = project_path.rstrip("/").rsplit("/", 1)[-1]
            for org, finding in (
                ("Bureau of Labor Statistics", "Employment was retrieved for a county."),
                ("Office of the Federal Register", "Proposed rule. This is not an enacted requirement."),
            ):
                self.assertEqual(
                    _raw(
                        base + project_path,
                        {
                            "op": "save_evidence",
                            "evidence_class": "source_backed_unverified",
                            "source_title": org,
                            "source_organization": org,
                            "category": "regulatory",
                            "finding": finding,
                        },
                        cookie,
                    )[0],
                    303,
                )
            page = _get(base + project_path, cookie)
            self.assertIn("Source comparison", page[1])
            self.assertIn("Bureau of Labor Statistics", page[1])
            self.assertEqual(_raw(base + project_path, {"op": "propose_update"}, cookie)[0], 303)
            waiting = _get(base + project_path, cookie)
            self.assertIn("Research update awaiting approval", waiting[1])
            self.assertEqual(_raw(base + project_path, {"op": "decide_update", "decision": "reject"}, cookie)[0], 303)
            rejected = get_research_project(connection, project_id)
            assert rejected is not None
            self.assertIsNone(rejected["document"].get("update_proposal"))
            self.assertFalse(rejected["document"].get("summaries"))
            self.assertEqual(_raw(base + project_path, {"op": "propose_update"}, cookie)[0], 303)
            self.assertEqual(_raw(base + project_path, {"op": "decide_update", "decision": "approve"}, cookie)[0], 303)
            approved = get_research_project(connection, project_id)
            assert approved is not None
            self.assertTrue(approved["document"].get("summaries"))
            self.assertTrue(approved["document"]["summaries"][-1].get("approved"))
            official = get_assessment(connection, assessment_id)
            assert official is not None
            self.assertFalse(official["human_review_approved"])
        finally:
            connection.close()
            server.shutdown()
            directory.cleanup()


if __name__ == "__main__":
    unittest.main()

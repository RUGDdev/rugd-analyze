"""Pitch decks copy a saved plan and export a presentation without a new calculation."""

from __future__ import annotations

import hashlib
import io
import re
import tempfile
from pathlib import Path
import threading
import unittest
import urllib.error
import urllib.parse
import urllib.request

from pptx import Presentation

from app import display
from app.access import DENIAL
from app.deck import build_deck_document, edited_deck, included_slides
from app.deck_export import chart_points, pdf_bytes, powerpoint_bytes
from app.plan import build_plan_document
from app.server import make_server
from app.store import BASELINE_ID, SAMPLE, connect, create_assessment, get_assessment, seed
from engine.financial import FinancialInputs, result_to_dict, run_financials
from tests.session_cookie import open_customer


def _plan_for(profile: dict, financial: dict | None, *, stage: str = "startup") -> dict:
    record = {
        "id": "deck-source",
        "business_name": profile.get("business_name") or "Assessment",
        "human_review_approved": False,
        "profile": profile,
        "result": None
        if financial is None
        else {
            "engine_ran": True,
            "financial": financial,
            "recommendation": "do-not-proceed",
            "blocking_flags": ["INSUFFICIENT_DEMAND_EVIDENCE"],
            "gap_flags": ["INSUFFICIENT_DEMAND_EVIDENCE"],
            "readiness_status": "internal",
            "human_review_status": "pending",
            "score_line": "Not calculated — methodology pending approval.",
        },
    }
    record["profile"]["venture_path"] = stage
    return {"id": "plan-1", "title": "Saved plan", "document": build_plan_document(record)}


class TestPitchDeck(unittest.TestCase):
    def test_investor_deck_selects_slides_and_keeps_engine_figures(self) -> None:
        expected = result_to_dict(run_financials(FinancialInputs(10000, 400, 0.5, 1000, 0.6)))
        plan = _plan_for(
            {
                "business_name": "Harbor Books",
                "concept": "A neighborhood bookstore.",
                "projected_monthly_revenue_base": 1000,
                "monthly_fixed_costs": 400,
                "initial_capital": 10000,
                "gross_margin_pct": 0.5,
                "downside_multiplier": 0.6,
            },
            expected,
        )
        deck = build_deck_document(plan, audience="investor")
        shown = [slide["id"] for slide in included_slides(deck)]
        self.assertIn("competition", shown)
        self.assertIn("funding", shown)
        self.assertIn("financials", shown)
        self.assertNotIn("marketing", shown)
        self.assertLess(len(shown), 18)
        self.assertEqual(deck["figures"]["base_cash_flow"], expected["base_monthly_cash_flow"])
        self.assertEqual(deck["figures"]["revenue_gap"], 200.0)
        self.assertIn("not established", deck["disclaimer"])
        funding = next(slide for slide in deck["slides"] if slide["id"] == "funding")
        self.assertIn("investment return is not stated", funding["narrative"])
        customers = next(slide for slide in deck["slides"] if slide["id"] == "customers")
        self.assertIn("Market size is not stored", customers["narrative"])
        points = chart_points(deck, "cash")
        self.assertIn(("Cash flow", expected["base_monthly_cash_flow"]), points)
        self.assertIn(("Downside cash flow", expected["downside_monthly_cash_flow"]), points)

    def test_audiences_change_emphasis_and_existing_businesses_skip_startup_capital(self) -> None:
        expected = result_to_dict(run_financials(FinancialInputs(10000, 400, 0.5, 1000, 0.6)))
        profile = {
            "business_name": "Harbor Books",
            "concept": "A neighborhood bookstore.",
            "projected_monthly_revenue_base": 1000,
            "monthly_fixed_costs": 0,
            "initial_capital": 10000,
            "gross_margin_pct": 0.5,
        }
        lender = build_deck_document(_plan_for(profile, expected), audience="lender")
        lender_ids = [slide["id"] for slide in included_slides(lender)]
        self.assertIn("break_even", lender_ids)
        self.assertIn("capital", lender_ids)
        self.assertNotIn("competition", lender_ids)
        lender_funding = next(slide for slide in lender["slides"] if slide["id"] == "funding")
        self.assertIn("Monthly debt service: Not stored", lender_funding["narrative"])
        partner = build_deck_document(_plan_for(profile, expected), audience="partner")
        partner_funding = next(slide for slide in partner["slides"] if slide["id"] == "funding")
        self.assertIn("Mutual benefits are not added", partner_funding["narrative"])
        overview = [slide["id"] for slide in included_slides(build_deck_document(_plan_for(profile, expected), audience="overview"))]
        self.assertIn("products", overview)
        self.assertNotIn("funding", overview)
        existing = build_deck_document(_plan_for(profile, expected, stage="existing"), audience="overview")
        capital = next(slide for slide in existing["slides"] if slide["id"] == "capital")
        self.assertIn("not part of this existing or expanding business", capital["narrative"])
        self.assertEqual(existing["figures"]["uses"], [])
        self.assertEqual(existing["figures"]["fixed_costs"], 0.0)
        blank = build_deck_document(
            _plan_for({"business_name": "Harbor Books", "concept": "A neighborhood bookstore."}, None),
            audience="overview",
        )
        self.assertIsNone(blank["figures"]["assumed_revenue"])
        self.assertIn("Not stored", next(slide for slide in blank["slides"] if slide["id"] == "financials")["facts"][0])

    def test_edits_reorder_slides_without_replacing_figures(self) -> None:
        expected = result_to_dict(run_financials(FinancialInputs(10000, 400, 0.5, 1000, 0.6)))
        plan = _plan_for(
            {
                "business_name": "Harbor Books",
                "concept": "A neighborhood bookstore.",
                "projected_monthly_revenue_base": 1000,
                "monthly_fixed_costs": 400,
                "gross_margin_pct": 0.5,
            },
            expected,
        )
        deck = build_deck_document(plan, audience="investor")
        form = {f"narrative_{slide['id']}": slide["narrative"] for slide in deck["slides"]}
        for slide in deck["slides"]:
            if slide["optional"] and slide["included"]:
                form[f"include_{slide['id']}"] = "1"
        form["narrative_opportunity"] = "Ask weekday neighbors before ordering inventory."
        form["include_marketing"] = "1"
        form["move"] = "financials:earlier"
        form["base_monthly_cash_flow"] = "1"
        slides = edited_deck(deck, form)
        deck["slides"] = slides
        opportunity = next(slide for slide in slides if slide["id"] == "opportunity")
        marketing = next(slide for slide in slides if slide["id"] == "marketing")
        self.assertEqual(opportunity["narrative"], "Ask weekday neighbors before ordering inventory.")
        self.assertTrue(marketing["included"])
        financials = next(index for index, slide in enumerate(slides) if slide["id"] == "financials")
        operations = next(index for index, slide in enumerate(slides) if slide["id"] == "operations")
        self.assertLess(financials, operations)
        self.assertEqual(deck["figures"]["base_cash_flow"], expected["base_monthly_cash_flow"])

    def test_exports_open_with_the_saved_figures(self) -> None:
        expected = result_to_dict(run_financials(FinancialInputs(10000, 400, 0.5, 1000, 0.6)))
        deck = build_deck_document(
            _plan_for(
                {
                    "business_name": "Harbor Books",
                    "concept": "A neighborhood bookstore.",
                    "projected_monthly_revenue_base": 1000,
                    "monthly_fixed_costs": 400,
                    "gross_margin_pct": 0.5,
                },
                expected,
            ),
            audience="investor",
        )
        deck["slides"][1]["narrative"] = "Ask weekday neighbors before ordering inventory. " + ("detail " * 200)
        pptx = powerpoint_bytes(deck, title="Harbor Books Investor presentation")
        opened = Presentation(io.BytesIO(pptx))
        text = "\n".join(
            shape.text_frame.text
            for slide in opened.slides
            for shape in slide.shapes
            if shape.has_text_frame
        )
        self.assertEqual(len(opened.slides), len(included_slides(deck)))
        self.assertIn("Harbor Books", text)
        self.assertIn("weekday neighbors", text)
        self.assertIn("The full narrative is saved in the workspace.", text)
        self.assertIn(display.dollars(expected["base_monthly_cash_flow"]), text)
        self.assertIn("not established", text)
        pdf = pdf_bytes(deck, title="Harbor Books Investor presentation")
        self.assertTrue(pdf.startswith(b"%PDF"))
        self.assertIn(b"%%EOF", pdf)
        self.assertIn(b"Harbor Books", pdf)
        self.assertIn(display.dollars(expected["base_monthly_cash_flow"]).encode(), pdf)
        self.assertIn(b"weekday neighbors", pdf)

    def test_http_deck_persists_exports_and_stays_private(self) -> None:
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
            other, _other_user = open_customer(connection, base)
            sample_before = hashlib.sha256(SAMPLE.read_bytes()).hexdigest()
            baseline_before = get_assessment(connection, BASELINE_ID)
            assessment_id = create_assessment(
                connection,
                business_name="Harbor Books",
                purpose="startup_feasibility",
                tier="explore",
                owner_user_id=user_id,
            )
            expected = result_to_dict(run_financials(FinancialInputs(10000, 400, 0.5, 1000, 0.6)))
            ran = self._raw(
                base + f"/assessments/{assessment_id}/analyze",
                {
                    "business_name": "Harbor Books",
                    "concept": "A neighborhood bookstore.",
                    "initial_capital": "10000",
                    "monthly_fixed_costs": "400",
                    "gross_margin_pct": "0.5",
                    "projected_monthly_revenue_base": "1000",
                    "downside_multiplier": "0.6",
                },
                cookie,
            )
            self.assertEqual(ran[0], 303)
            created_plan = self._raw(base + f"/assessments/{assessment_id}/plans", {}, cookie)
            self.assertEqual(created_plan[0], 303)
            listing = self._get(base + f"/assessments/{assessment_id}/plans", cookie)
            plan_path = re.findall(r'href="(/assessments/[^"]+/plans/[0-9a-f-]+)"', listing[1])[0]
            plan_id = plan_path.rsplit("/", 1)[-1]
            created = self._raw(
                base + f"/assessments/{assessment_id}/decks",
                {"plan_id": plan_id, "audience": "investor"},
                cookie,
            )
            self.assertEqual(created[0], 303)
            decks = self._get(base + f"/assessments/{assessment_id}/decks?saved=1", cookie)
            self.assertIn("Pitch deck saved.", decks[1])
            deck_path = re.findall(r'href="(/assessments/[^"]+/decks/[0-9a-f-]+)"', decks[1])[0]
            page = self._get(base + deck_path, cookie)
            self.assertEqual(page[0], 200)
            self.assertIn("Investor presentation", page[1])
            self.assertIn("Harbor Books", page[1])
            self.assertIn(f"Monthly cash flow: {display.dollars(expected['base_monthly_cash_flow'])}", page[1])
            self.assertIn("Save deck", page[1])
            self.assertIn("Export PowerPoint", page[1])
            self.assertIn("Export PDF", page[1])
            self.assertIn("not established", page[1])
            saved = self._raw(
                base + deck_path,
                {
                    "narrative_opportunity": "Ask weekday neighbors before ordering inventory.",
                    "include_opportunity": "1",
                    "include_problem": "1",
                    "include_solution": "1",
                    "include_customers": "1",
                    "include_competition": "1",
                    "include_revenue": "1",
                    "include_financials": "1",
                    "include_scenarios": "1",
                    "include_capital": "1",
                    "include_growth": "1",
                    "include_funding": "1",
                    "include_marketing": "1",
                    "move": "financials:earlier",
                    "base_monthly_cash_flow": "1",
                },
                cookie,
            )
            self.assertEqual(saved[0], 303)
            reloaded = self._get(base + deck_path, cookie)
            self.assertIn("Ask weekday neighbors before ordering inventory.", reloaded[1])
            self.assertIn(f"Monthly cash flow: {display.dollars(expected['base_monthly_cash_flow'])}", reloaded[1])
            self.assertIn("Include this slide", reloaded[1])
            financials = reloaded[1].find('id="slide-financials"')
            operations = reloaded[1].find('id="slide-operations"')
            self.assertLess(financials, operations)
            pptx = self._bytes(base + deck_path + "/pptx", cookie)
            self.assertEqual(pptx[0], 200)
            opened = Presentation(io.BytesIO(pptx[1]))
            self.assertGreaterEqual(len(opened.slides), 1)
            pdf = self._bytes(base + deck_path + "/pdf", cookie)
            self.assertEqual(pdf[0], 200)
            self.assertTrue(pdf[1].startswith(b"%PDF"))
            self.assertIn(b"weekday neighbors", pdf[1])
            proposed = self._raw(base + deck_path + "/propose", {}, cookie)
            self.assertEqual(proposed[0], 200)
            self.assertIn("No live adviser is configured.", proposed[1])
            denied = self._get(base + deck_path, other)
            self.assertEqual(denied[0], 403)
            self.assertIn(DENIAL, denied[1])
            self.assertNotIn("Harbor Books", denied[1])
            self.assertNotIn("weekday neighbors", denied[1])
            self.assertEqual(self._bytes(base + deck_path + "/pptx", other)[0], 403)
            self.assertEqual(self._bytes(base + deck_path + "/pdf", "")[0], 403)
            self.assertNotIn("Harbor Books", self._get(base + "/decks", other)[1])
            stored = get_assessment(connection, assessment_id)
            assert stored is not None and stored["result"] is not None
            self.assertEqual(stored["result"]["financial"]["base_monthly_cash_flow"], expected["base_monthly_cash_flow"])
            self.assertEqual(stored["result"]["recommendation"], "do-not-proceed")
            self.assertFalse(stored["human_review_approved"])
            baseline_plan = self._raw(base + f"/assessments/{BASELINE_ID}/plans", {}, cookie)
            self.assertEqual(baseline_plan[0], 303)
            baseline_listing = self._get(base + f"/assessments/{BASELINE_ID}/plans", cookie)
            baseline_plan_id = re.findall(r'href="(/assessments/[^"]+/plans/[0-9a-f-]+)"', baseline_listing[1])[0].rsplit("/", 1)[-1]
            baseline_deck = self._raw(
                base + f"/assessments/{BASELINE_ID}/decks",
                {"plan_id": baseline_plan_id, "audience": "overview"},
                cookie,
            )
            self.assertEqual(baseline_deck[0], 303)
            baseline_after = get_assessment(connection, BASELINE_ID)
            assert baseline_after is not None and baseline_before is not None
            self.assertEqual(baseline_after["result"], baseline_before["result"])
            self.assertFalse(baseline_after["human_review_approved"])
            self.assertEqual(hashlib.sha256(SAMPLE.read_bytes()).hexdigest(), sample_before)
        finally:
            connection.close()
            server.shutdown()
            server.server_close()
            thread.join(timeout=3)
            directory.cleanup()

    def _get(self, url: str, cookie: str = "") -> tuple[int, str]:
        headers = {"Cookie": cookie} if cookie else {}
        request = urllib.request.Request(url, headers=headers)
        try:
            with urllib.request.urlopen(request) as response:
                return response.status, response.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            return exc.code, exc.read().decode("utf-8")

    def _bytes(self, url: str, cookie: str = "") -> tuple[int, bytes]:
        headers = {"Cookie": cookie} if cookie else {}
        request = urllib.request.Request(url, headers=headers)
        try:
            with urllib.request.urlopen(request) as response:
                return response.status, response.read()
        except urllib.error.HTTPError as exc:
            return exc.code, exc.read()

    def _raw(self, url: str, fields: dict[str, str], cookie: str = "") -> tuple[int, str, dict[str, str]]:
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

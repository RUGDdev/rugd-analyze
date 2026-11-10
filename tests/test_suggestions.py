"""Explore intake suggestions stay examples and do not change the engine."""

import unittest

from app.analysis import analyze_record
from app.pages import assessment_form
from app.suggestions import SUGGESTION_NOTE, suggestions_for


def _draft(industry: str = "", stage: str = "") -> dict:
    return {
        "id": "suggest-1",
        "business_name": "Suggestion Cafe",
        "tier": "explore",
        "owner_user_id": "suggest-reader",
        "read_only": False,
        "hypothetical": False,
        "pilot_label": "Customer draft. Not a completed assessment.",
        "purpose": "startup_feasibility",
        "created_at": "2026-11-10",
        "profile": {
            "business_name": "Suggestion Cafe",
            "purpose": "startup_feasibility",
            "tier": "explore",
            "venture_path": "startup",
            "industry": industry,
            "stage": stage,
        },
        "result": None,
        "human_review_approved": False,
    }


class TestSuggestions(unittest.TestCase):
    def test_blank_industry_uses_general_examples(self) -> None:
        chosen = suggestions_for("")
        self.assertIn("Concept", chosen["stage"])
        self.assertNotIn("Beta", chosen["stage"])
        self.assertIn("The closest alternative a customer would choose instead", chosen["competition"])
        page = assessment_form(_draft())
        self.assertIn('id="suggestion-note"', page)
        self.assertIn(SUGGESTION_NOTE, page)
        self.assertIn("The closest alternative a customer would choose instead", page)
        self.assertIn('class="chip"', page)
        self.assertIn('data-field="competition"', page)
        self.assertNotIn("A hosted software subscription for a named workflow", page)
        self.assertIn(
            "Is there demand evidence? A yes here is still only a user-supplied assumption.",
            page,
        )

    def test_industry_and_stage_narrow_the_examples(self) -> None:
        restaurant = suggestions_for("Neighborhood restaurant")
        self.assertIn("Lunch and dinner service for guests on site", restaurant["products"])
        self.assertNotIn("A hosted software subscription for a named workflow", restaurant["products"])
        self.assertNotIn("Beta", restaurant["stage"])
        idea = suggestions_for("Neighborhood restaurant", "Idea")
        expanding = suggestions_for("Neighborhood restaurant", "Expanding")
        self.assertIn("A short sample menu of lunch plates", idea["products"])
        self.assertNotIn("The same menu offered at a second location", idea["products"])
        self.assertIn("The same menu offered at a second location", expanding["products"])
        self.assertNotIn("A short sample menu of lunch plates", expanding["products"])
        software = suggestions_for("Software")
        self.assertIn("Beta", software["stage"])
        self.assertIn("A hosted software subscription for a named workflow", software["products"])

        idea_page = assessment_form(_draft("Neighborhood restaurant", "Idea"))
        self.assertIn("A short sample menu of lunch plates", idea_page)
        self.assertNotIn("The same menu offered at a second location", idea_page)
        self.assertNotIn("A hosted software subscription for a named workflow", idea_page)
        self.assertNotIn("The closest alternative a customer would choose instead", idea_page)
        software_page = assessment_form(_draft("Software", "Beta"))
        self.assertIn("Beta", software_page)
        self.assertIn("A hosted software subscription for a named workflow", software_page)
        self.assertNotIn("A short sample menu of lunch plates", software_page)

    def test_examples_contain_no_numbers_and_do_not_change_the_engine(self) -> None:
        for industry, stage in (("", ""), ("Restaurant", "Idea"), ("Software", "Beta"), ("Retail shop", "Operating")):
            chosen = suggestions_for(industry, stage)
            self.assertEqual(set(chosen), {"stage", "products", "customers", "competition"})
            for examples in chosen.values():
                self.assertTrue(examples)
                for example in examples:
                    self.assertFalse(any(character.isdigit() for character in example))
        blank = analyze_record(_draft())
        filled = _draft("Neighborhood restaurant", "Idea")
        chosen = suggestions_for("Neighborhood restaurant", "Idea")
        filled["profile"]["products"] = chosen["products"][0]
        filled["profile"]["customers"] = chosen["customers"][0]
        filled["profile"]["competition"] = chosen["competition"][0]
        filled["profile"]["stage"] = chosen["stage"][0]
        after = analyze_record(filled)
        self.assertEqual(after["recommendation"], blank["recommendation"])
        self.assertEqual(after["blocking_flags"], blank["blocking_flags"])
        self.assertEqual(after["readiness_status"], blank["readiness_status"])
        self.assertEqual(after["financial"], blank["financial"])
        self.assertIn("INSUFFICIENT_DEMAND_EVIDENCE", after["blocking_flags"])
        self.assertEqual(after["recommendation"], "do-not-proceed")
        self.assertEqual(after["readiness_status"], "internal")
        self.assertFalse(after["human_review_approved"])
        self.assertEqual(after["demand"]["status"], "uncleared")

    def test_read_only_intake_shows_examples_without_fill_buttons(self) -> None:
        record = _draft()
        record["read_only"] = True
        page = assessment_form(record)
        self.assertIn(SUGGESTION_NOTE, page)
        self.assertIn('class="chip"', page)
        self.assertNotIn('type="button" class="chip"', page)
        self.assertIn(
            "Is there demand evidence? A yes here is still only a user-supplied assumption.",
            page,
        )

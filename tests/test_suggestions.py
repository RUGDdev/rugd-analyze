"""Explore intake suggestions stay examples and do not change the engine."""

import unittest

from app.analysis import analyze_record
from app.pages import assessment_form
from app.suggestions import SUGGESTION_NOTE, load_catalog, suggestions_for


def _chip(field: str, example: str) -> str:
    return f'data-field="{field}" data-example="{example}"'


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
        self.assertIn("mature", chosen["stage"])
        self.assertIn("planning", chosen["stage"])
        self.assertIn("Other local businesses", chosen["competition"])
        page = assessment_form(_draft())
        self.assertIn('id="suggestion-note"', page)
        self.assertIn('id="suggestion-catalog"', page)
        self.assertIn(SUGGESTION_NOTE, page)
        self.assertIn("Examples only. Guidance.", page)
        self.assertIn(_chip("competition", "Other local businesses"), page)
        self.assertIn(_chip("stage", "mature"), page)
        self.assertIn('class="chip"', page)
        self.assertNotIn(_chip("products", "Full-service dining"), page)
        self.assertIn(
            "Is there demand evidence? A yes here is still only a user-supplied assumption.",
            page,
        )

    def test_industry_and_stage_narrow_the_examples(self) -> None:
        restaurant = suggestions_for("Neighborhood restaurant")
        self.assertIn("Full-service dining", restaurant["products"])
        self.assertIn("planning", restaurant["stage"])
        self.assertNotIn("mature", restaurant["stage"])
        self.assertNotIn("Specialty retail", restaurant["products"])
        idea = suggestions_for("Neighborhood restaurant", "idea")
        expanding = suggestions_for("Neighborhood restaurant", "expanding")
        self.assertEqual(idea["products"], expanding["products"])
        self.assertIn("Catering", idea["products"])
        software = suggestions_for("Software")
        self.assertEqual(software["products"], suggestions_for("")["products"])
        self.assertIn("mature", software["stage"])
        self.assertNotIn("Full-service dining", software["products"])

        idea_page = assessment_form(_draft("Neighborhood restaurant", "idea"))
        self.assertIn(_chip("products", "Full-service dining"), idea_page)
        self.assertIn(_chip("stage", "planning"), idea_page)
        self.assertNotIn(_chip("stage", "mature"), idea_page)
        self.assertNotIn(_chip("products", "Specialty retail"), idea_page)
        self.assertNotIn(_chip("competition", "Other local businesses"), idea_page)
        software_page = assessment_form(_draft("Software", "idea"))
        self.assertIn(_chip("stage", "mature"), software_page)
        self.assertIn(_chip("products", "Custom products or services"), software_page)
        self.assertNotIn(_chip("products", "Full-service dining"), software_page)

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

    def test_aliases_keywords_and_unknown_industry_use_the_json_catalog(self) -> None:
        catalog = load_catalog()
        self.assertIn("industries", catalog)
        self.assertIn("general", catalog)
        restaurant = next(item for item in catalog["industries"] if item["name"] == "Restaurant")
        self.assertIn("cafe", restaurant["aliases"])
        self.assertIn("food service", restaurant["keywords"])
        self.assertIn("food truck", restaurant["search_terms"])
        self.assertEqual(catalog["version"], "0.3")
        by_alias = suggestions_for("Cafe")
        by_keyword = suggestions_for("FOOD SERVICE")
        self.assertIn("Full-service dining", by_alias["products"])
        self.assertIn("Full-service dining", by_keyword["products"])
        self.assertEqual(suggestions_for("barber")["products"], suggestions_for("")["products"])
        self.assertIn("Hotel / motel", suggestions_for("hospitality")["products"])
        self.assertEqual(suggestions_for("bed and breakfast")["products"], suggestions_for("")["products"])
        unknown = suggestions_for("underwater basket weaving")
        self.assertEqual(unknown["competition"], suggestions_for("")["competition"])
        self.assertNotIn("Full-service dining", unknown["products"])
        page = assessment_form(_draft("Cafe", "idea"))
        self.assertIn(_chip("products", "Full-service dining"), page)
        self.assertIn('id="suggestion-catalog"', page)

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

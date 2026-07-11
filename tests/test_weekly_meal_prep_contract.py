import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "plugins/meal-prep-agent/skills/weekly-meal-prep/SKILL.md"
PROFILE = ROOT / "plugins/meal-prep-agent/data/profile.template.json"
HISTORY = ROOT / "plugins/meal-prep-agent/data/history.template.json"


class WeeklyMealPrepContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.skill = SKILL.read_text()

    def test_templates_are_valid_json(self):
        json.loads(PROFILE.read_text())
        json.loads(HISTORY.read_text())

    def test_seed_selection_has_override_preferences_rotation_and_fallback(self):
        required = (
            "explicitly requested by the user",
            "profile.preferred_cuisines",
            "profile.avoid_cuisines",
            "last four accepted plans",
            "least-recently-used allowed seed",
        )
        for phrase in required:
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, self.skill)

    def test_seed_is_propagated_and_verified(self):
        required = (
            '"flavour_seed": ""',
            '"seed_selection_note": ""',
            '"seed_alignment_note": ""',
            "Every recipe must clearly express the seed",
            "reject or revise a result",
        )
        for phrase in required:
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, self.skill)
        self.assertGreaterEqual(self.skill.count('"seed_alignment_note": ""'), 2)

    def test_accepted_plan_memory_records_seed(self):
        memory_section = self.skill.split("## Memory Update", 1)[1]
        self.assertIn("- `flavour_seed`", memory_section)
        self.assertIn("- `seed_selection_note`", memory_section)

    def test_clean_checkout_initialization_remains_documented(self):
        self.assertIn("On first run, create missing private runtime files", self.skill)
        self.assertFalse((ROOT / "plugins/meal-prep-agent/data/local").exists())


if __name__ == "__main__":
    unittest.main()

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "plugins/meal-prep-agent/skills/woolworths-cart-builder/SKILL.md"


class WoolworthsCartBuilderContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.skill = SKILL.read_text()

    def test_uses_woolworths_mcp_instead_of_item_adder(self):
        required = (
            "woolworths_open_browser",
            "woolworths_get_cookies",
            "woolworths_search_products",
            "woolworths_add_to_cart",
            "woolworths_get_cart",
            "Use the tools from the `woolworths` MCP server directly",
        )
        for phrase in required:
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, self.skill)
        self.assertNotIn("Item-Adder Sub-Agent Brief", self.skill)

    def test_preserves_existing_cart_and_verifies_mutations(self):
        required = (
            "Call `woolworths_get_cart` before adding anything",
            "preserve all existing items",
            "never retry an add blindly",
            "Never remove or reduce pre-existing cart items",
            "final cart read is consistent with the mutation",
        )
        for phrase in required:
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, self.skill)

    def test_stops_before_purchase_and_leaves_browser_open(self):
        required = (
            "never place the order",
            "Never call checkout",
            "Leave the browser open",
            "final purchase",
        )
        for phrase in required:
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, self.skill)


if __name__ == "__main__":
    unittest.main()

import json
import unittest
from pathlib import Path

from groundpitch.nutrient import extract_page_texts


class NutrientResponseTests(unittest.TestCase):
    def test_page_text_normalization(self):
        payload = json.loads(
            (Path(__file__).parents[1] / "fixtures" / "nutrient_sample.json").read_text()
        )
        pages = extract_page_texts(payload)
        self.assertEqual(len(pages), 2)
        self.assertIn("10,000 invoices", pages[0]["text"])
        self.assertIn("37%", pages[1]["text"])


if __name__ == "__main__":
    unittest.main()

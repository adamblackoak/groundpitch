import json
import unittest
from pathlib import Path

from groundpitch.gate import gate_claims
from groundpitch.nutrient import extract_page_texts


class GateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        payload = json.loads(
            (Path(__file__).parents[1] / "fixtures" / "nutrient_sample.json").read_text()
        )
        cls.pages = extract_page_texts(payload)

    def disposition(self, claim):
        return gate_claims([claim], self.pages)[0].disposition

    def test_supported_throughput_is_admitted(self):
        self.assertEqual(self.disposition("Process up to 10,000 invoices per hour."), "ADMIT")

    def test_supported_pilot_result_is_admitted(self):
        self.assertEqual(
            self.disposition("Manual review time fell by 37% in a controlled pilot."),
            "ADMIT",
        )

    def test_unsupported_superlative_is_rejected(self):
        self.assertEqual(self.disposition("The fastest invoice platform in Europe."), "REJECT")

    def test_unsupported_numeric_claim_is_rejected(self):
        self.assertEqual(self.disposition("Cut manual review time by 90%."), "REJECT")

    def test_supported_deployment_claim_is_admitted(self):
        self.assertEqual(self.disposition("Supports EU and UK deployments."), "ADMIT")


if __name__ == "__main__":
    unittest.main()

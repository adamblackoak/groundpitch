import unittest

from groundpitch.serpapi import (
    build_search_query,
    claim_requires_live_context,
    normalize_search_payload,
)


class SerpApiTests(unittest.TestCase):
    def test_flags_live_or_market_state_claims(self):
        self.assertTrue(claim_requires_live_context("The fastest platform in Europe."))
        self.assertTrue(claim_requires_live_context("Supports EU and UK deployments."))
        self.assertFalse(
            claim_requires_live_context(
                "Manual review time fell by 37% in a controlled pilot."
            )
        )

    def test_builds_subject_aware_query(self):
        self.assertEqual(
            build_search_query("Supports EU deployments.", "AsterFlow"),
            "AsterFlow Supports EU deployments.",
        )

    def test_normalizes_structured_results(self):
        payload = {
            "search_metadata": {"id": "abc", "status": "Success"},
            "organic_results": [
                {
                    "position": 1,
                    "title": "AsterFlow availability",
                    "link": "https://example.com/asterflow",
                    "snippet": "AsterFlow is available in the EU and UK.",
                    "date": "Aug 2026",
                }
            ],
        }
        scan = normalize_search_payload(
            claim="Supports EU and UK deployments.",
            query="AsterFlow Supports EU and UK deployments.",
            payload=payload,
        )
        self.assertEqual(scan.search_status, "Success")
        self.assertEqual(scan.results[0].domain, "example.com")
        self.assertEqual(scan.results[0].position, 1)
        self.assertTrue(scan.response_sha256)


if __name__ == "__main__":
    unittest.main()

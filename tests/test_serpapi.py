import unittest
from unittest.mock import Mock, patch

from groundpitch.serpapi import (
    build_search_query,
    claim_requires_live_context,
    normalize_search_payload,
    search_claim_context,
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
            '"AsterFlow" Supports EU deployments.',
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
            query='"AsterFlow" Supports EU and UK deployments.',
            subject="AsterFlow",
            payload=payload,
        )
        self.assertEqual(scan.search_status, "Success")
        self.assertEqual(scan.raw_result_count, 1)
        self.assertEqual(scan.relevant_result_count, 1)
        self.assertEqual(scan.results[0].domain, "example.com")
        self.assertEqual(scan.results[0].position, 1)
        self.assertTrue(scan.response_sha256)

    def test_filters_results_that_do_not_match_subject(self):
        payload = {
            "search_metadata": {"id": "abc", "status": "Success"},
            "organic_results": [
                {
                    "position": 1,
                    "title": "Thousands of British troops support NATO in Europe",
                    "link": "https://example.com/troops",
                    "snippet": "British forces will complete planned deployments.",
                }
            ],
        }
        scan = normalize_search_payload(
            claim="Supports EU and UK deployments.",
            query='"AsterFlow" Supports EU and UK deployments.',
            subject="AsterFlow",
            payload=payload,
        )
        self.assertEqual(scan.raw_result_count, 1)
        self.assertEqual(scan.relevant_result_count, 0)
        self.assertEqual(scan.results, [])

    def test_does_not_match_product_name_by_substring(self):
        payload = {
            "search_metadata": {"id": "abc", "status": "Success"},
            "organic_results": [
                {
                    "position": 1,
                    "title": "MasterFlow 9500 launches in UK",
                    "link": "https://example.com/masterflow",
                    "snippet": "MasterFlow is used in offshore wind grout applications.",
                }
            ],
        }
        scan = normalize_search_payload(
            claim="Supports EU and UK deployments.",
            query='"AsterFlow" Supports EU and UK deployments.',
            subject="AsterFlow",
            payload=payload,
        )
        self.assertEqual(scan.raw_result_count, 1)
        self.assertEqual(scan.relevant_result_count, 0)
        self.assertEqual(scan.results, [])

    def test_redirect_url_does_not_create_subject_match(self):
        payload = {
            "search_metadata": {"id": "redirect-1", "status": "Success"},
            "organic_results": [
                {
                    "position": 1,
                    "title": "MasterFlow 9500 launches in UK",
                    "link": "https://www.google.com/goto?url=https%3A%2F%2Fexample.com%2Fmasterflow%3Fq%3DAsterFlow",
                    "snippet": "MasterFlow is used in offshore wind grout applications.",
                }
            ],
        }
        scan = normalize_search_payload(
            claim="Supports EU and UK deployments.",
            query='"AsterFlow" Supports EU and UK deployments.',
            subject="AsterFlow",
            payload=payload,
        )
        self.assertEqual(scan.raw_result_count, 1)
        self.assertEqual(scan.relevant_result_count, 0)
        self.assertEqual(scan.results, [])

    @patch("groundpitch.serpapi.requests.get")
    def test_no_results_error_becomes_reviewable_empty_scan(self, mock_get):
        response = Mock()
        response.ok = True
        response.json.return_value = {
            "search_metadata": {"id": "no-results-1"},
            "error": "Google hasn't returned any results for this query.",
        }
        response.content = b'{"error":"Google hasn\'t returned any results for this query."}'
        mock_get.return_value = response

        scan = search_claim_context(
            claim="Supports EU and UK deployments.",
            subject="AsterFlow",
            api_key="test-key",
        )

        self.assertEqual(scan.search_status, "No organic results")
        self.assertEqual(scan.raw_result_count, 0)
        self.assertEqual(scan.relevant_result_count, 0)
        self.assertEqual(scan.results, [])
        self.assertEqual(scan.search_id, "no-results-1")
        self.assertTrue(scan.response_sha256)


if __name__ == "__main__":
    unittest.main()

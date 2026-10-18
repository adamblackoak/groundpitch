"""Regression boundaries for lexical evidence and per-run reviewer state."""
import unittest

from groundpitch.audit import build_audit_ledger
from groundpitch.gate import gate_claims
from groundpitch.review_keys import review_widget_key
from groundpitch.validation import numeric_assertions

class MinimumClosureTests(unittest.TestCase):
    def decision(self, claim, source):
        return gate_claims([claim], [{"page_index": 0, "text": source}])[0]

    def ledger(self, decisions, reviews=None, scans=None, live_reviews=None):
        return build_audit_ledger(
            filename="test.txt", file_bytes=b"source", nutrient_response_sha256="a"*64,
            nutrient_instructions={}, decisions=[x.to_dict() for x in decisions],
            human_reviews=reviews or {}, live_context_scans=scans or {},
            live_context_reviews=live_reviews or {},
        )["claims"]

    def test_numeric_prefix_and_units(self):
        self.assertNotEqual(numeric_assertions("10"), numeric_assertions("100"))
        self.assertNotEqual(numeric_assertions("10%"), numeric_assertions("10"))
        self.assertEqual(numeric_assertions("1,000"), numeric_assertions("1000.0"))

    def test_prefix_number_cannot_clear_false_claim(self):
        d = self.decision("Platform handles exactly 10 requests per minute.", "Platform handles exactly 100 requests per minute.")
        self.assertEqual(d.disposition, "REJECT")

    def test_negated_source_requires_review(self):
        d = self.decision("Platform permits EU withdrawals.", "Platform does not permit EU withdrawals.")
        self.assertNotEqual(d.disposition, "ADMIT")

    def test_candidate_never_releases_without_human(self):
        d = self.decision("Platform permits EU withdrawals.", "Platform permits EU withdrawals.")
        self.assertEqual(self.ledger([d])[0]["final_disposition"], "HOLD_SOURCE_REVIEW")

    def test_explicit_human_can_clear_non_temporal_demo_candidate(self):
        d = self.decision("Platform processes paper invoices.", "Platform processes paper invoices.")
        self.assertEqual(self.ledger([d], {f"0:{d.claim}": "APPROVE"})[0]["final_disposition"], "ADMIT_BY_HUMAN_REVIEW")

    def test_reversed_relation_cannot_be_automatically_released(self):
        d = self.decision("Product A is faster than Product B.", "Product B is faster than Product A.")
        self.assertNotIn(self.ledger([d])[0]["final_disposition"], {"ADMIT", "ADMIT_BY_HUMAN_REVIEW"})

    def test_time_sensitive_claim_holds_without_live_scan(self):
        d = self.decision("Platform supports EU deployments.", "Platform supports EU deployments.")
        out = self.ledger([d], {f"0:{d.claim}": "APPROVE"})[0]
        self.assertEqual(out["final_disposition"], "HOLD_FRESHNESS_NOT_VERIFIED")

    def test_time_sensitive_claim_holds_without_relevant_results(self):
        d = self.decision("Platform supports EU deployments.", "Platform supports EU deployments.")
        scans = {d.claim: {"results": [], "relevant_result_count": 0}}
        out = self.ledger([d], {f"0:{d.claim}": "APPROVE"}, scans)[0]
        self.assertEqual(out["final_disposition"], "HOLD_FRESHNESS_NOT_VERIFIED")

    def test_approval_bound_to_evidence_and_run(self):
        p=dict(run_id="a",source_sha256="sha-a",extraction_sha256="dws-a",claim="claim A",index=0,lane="source")
        a=review_widget_key(**p)
        for mutation in (
            dict(run_id="b"),dict(source_sha256="sha-b"),dict(extraction_sha256="dws-b"),
            dict(claim="claim B"),dict(index=1),dict(lane="live"),
        ):
            self.assertNotEqual(a,review_widget_key(**(p|mutation)))

    def test_two_identical_claim_rows_need_separate_approval(self):
        d = self.decision("Platform processes invoices.", "Platform processes invoices.")
        out = self.ledger([d,d],{f"0:{d.claim}":"APPROVE"})
        self.assertEqual(out[0]["final_disposition"],"ADMIT_BY_HUMAN_REVIEW")
        self.assertEqual(out[1]["final_disposition"],"HOLD_SOURCE_REVIEW")

if __name__ == "__main__":
    unittest.main()

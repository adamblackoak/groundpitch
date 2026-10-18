from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import Any
from .serpapi import claim_requires_live_context


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def build_audit_ledger(
    *,
    filename: str,
    file_bytes: bytes,
    nutrient_response_sha256: str,
    nutrient_instructions: dict[str, Any],
    decisions: list[dict[str, Any]],
    human_reviews: dict[str, str] | None = None,
    live_context_scans: dict[str, dict[str, Any]] | None = None,
    live_context_reviews: dict[str, str] | None = None,
    live_context_skips: dict[str, str] | None = None,
) -> dict[str, Any]:
    human_reviews = human_reviews or {}
    live_context_scans = live_context_scans or {}
    live_context_reviews = live_context_reviews or {}
    live_context_skips = live_context_skips or {}
    finalized = []

    for index, decision in enumerate(decisions):
        item = dict(decision)
        claim = item["claim"]
        human = human_reviews.get(f"{index}:{claim}", "PENDING")
        live_scan = live_context_scans.get(claim)
        live_skip = live_context_skips.get(claim)
        live_review = (
            live_context_reviews.get(claim, "PENDING")
            if live_scan
            else "NOT_REQUIRED"
        )

        item["human_review"] = human
        item["live_context"] = live_scan
        item["live_context_review"] = live_review
        item["live_context_skip_reason"] = live_skip

        item["freshness_review_required"] = claim_requires_live_context(claim)
        if item["disposition"] == "REJECT":
            final = "REJECT"
        elif human == "REJECT":
            final = "REJECT_BY_HUMAN_REVIEW"
        elif human != "APPROVE":
            final = "HOLD_SOURCE_REVIEW"
        elif item["freshness_review_required"] and (
            not live_scan or not live_scan.get("results") or not live_scan.get("relevant_result_count", 0)
        ):
            final = "HOLD_FRESHNESS_NOT_VERIFIED"
        elif live_scan and live_review == "REJECT":
            final = "REJECT_BY_LIVE_CONTEXT_REVIEW"
        elif live_scan and live_review != "APPROVE":
            final = "HOLD_LIVE_CONTEXT"
        else:
            final = "ADMIT_BY_HUMAN_REVIEW"

        item["final_disposition"] = final
        finalized.append(item)

    serp_scans = list(live_context_scans.values())

    return {
        "groundpitch_version": "0.3.0",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "source": {
            "filename": filename,
            "sha256": sha256_bytes(file_bytes),
        },
        "nutrient_dws": {
            "endpoint": "https://api.nutrient.io/build",
            "operation": "json-content extraction",
            "instructions": nutrient_instructions,
            "response_sha256": nutrient_response_sha256,
            "role": (
                "Primary extraction input for provisional lexical screening; "
                "not semantic or publication authority."
            ),
        },
        "serpapi": {
            "endpoint": "https://serpapi.com/search.json",
            "engine": "google",
            "scan_count": len(serp_scans),
            "skip_count": len(live_context_skips),
            "role": (
                "Live-context boundary for source-supported claims whose truth depends "
                "on current or public market state. SerpApi results can hold or "
                "downgrade release for human review; they never upgrade an unsupported "
                "source claim."
            ),
            "scans": serp_scans,
            "skips": live_context_skips,
        },
        "claims": finalized,
        "release_rule": (
            "Every non-rejected claim requires demonstration reviewer selection. "
            "Time-dependent claims additionally require relevant live results and review. "
            "Neither UI approval nor lexical scoring establishes truth or publication authority."
        ),
    }

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import Any


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

    for decision in decisions:
        item = dict(decision)
        claim = item["claim"]
        human = human_reviews.get(claim, "NOT_REQUIRED")
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

        if item["disposition"] == "REJECT":
            final = "REJECT"
        elif item["disposition"] == "REVIEW" and human != "APPROVE":
            final = "REJECT_BY_HUMAN_REVIEW" if human == "REJECT" else "HOLD"
        else:
            final = (
                "ADMIT_BY_HUMAN_REVIEW"
                if item["disposition"] == "REVIEW"
                else "ADMIT"
            )

            # Live public context is a second release boundary. Search results
            # never create authority; when a live scan was required and run,
            # a human must explicitly clear it before release.
            if live_scan:
                if live_review == "REJECT":
                    final = "REJECT_BY_LIVE_CONTEXT_REVIEW"
                elif live_review != "APPROVE":
                    final = "HOLD_LIVE_CONTEXT"

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
                "Primary evidence boundary. GroundPitch gates claim release against "
                "the source-grounded evidence extracted by Nutrient DWS."
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
            "A claim must first satisfy the Nutrient-derived source-evidence gate. "
            "Claims rejected there stop before SerpApi. If live public context is "
            "required and scanned, it must also be explicitly cleared by a human. "
            "SerpApi evidence cannot turn a source-unsupported claim into an admitted claim."
        ),
    }

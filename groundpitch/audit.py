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
) -> dict[str, Any]:
    human_reviews = human_reviews or {}
    finalized = []

    for decision in decisions:
        item = dict(decision)
        claim = item["claim"]
        human = human_reviews.get(claim, "NOT_REQUIRED")
        item["human_review"] = human

        if item["disposition"] == "REVIEW":
            if human == "APPROVE":
                item["final_disposition"] = "ADMIT_BY_HUMAN_REVIEW"
            elif human == "REJECT":
                item["final_disposition"] = "REJECT_BY_HUMAN_REVIEW"
            else:
                item["final_disposition"] = "HOLD"
        else:
            item["final_disposition"] = item["disposition"]

        finalized.append(item)

    return {
        "groundpitch_version": "0.1.0",
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
                "Core document operation. GroundPitch gates claim release against "
                "the deterministic evidence extracted by Nutrient DWS."
            ),
        },
        "claims": finalized,
        "release_rule": (
            "Only ADMIT or ADMIT_BY_HUMAN_REVIEW claims may enter released copy. "
            "HOLD and REJECT claims are excluded."
        ),
    }

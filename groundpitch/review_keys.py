"""Run- and evidence-scoped demonstration review keys; not reviewer authentication."""
from __future__ import annotations
import hashlib
import json
from typing import Literal

ReviewLane = Literal["source", "live"]

def review_widget_key(*, run_id: str, source_sha256: str, extraction_sha256: str,
                      claim: str, index: int, lane: ReviewLane) -> str:
    if not all((run_id.strip(), source_sha256.strip(), extraction_sha256.strip(), claim.strip())):
        raise ValueError("Review key requires run, source, extraction and claim identity")
    if index < 0:
        raise ValueError("Review index must be nonnegative")
    if lane not in ("source", "live"):
        raise ValueError("Unrecognised review lane")
    data = json.dumps(["groundpitch-review-v1", run_id, source_sha256, extraction_sha256,
                       claim, index, lane], ensure_ascii=False, separators=(",", ":"))
    return f"gp-review-{lane}-{hashlib.sha256(data.encode('utf-8')).hexdigest()}"

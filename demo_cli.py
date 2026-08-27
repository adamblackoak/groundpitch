from __future__ import annotations

import json
from pathlib import Path

from groundpitch.audit import build_audit_ledger
from groundpitch.gate import gate_claims
from groundpitch.nutrient import extract_page_texts

ROOT = Path(__file__).parent
payload = json.loads((ROOT / "fixtures" / "nutrient_sample.json").read_text())
source = (ROOT / "sample" / "product_brief.pdf").read_bytes()

claims = [
    "Process up to 10,000 invoices per hour.",
    "Cut manual review time by 37% in a controlled pilot.",
    "The fastest invoice platform in Europe.",
    "Guaranteed zero compliance errors.",
    "Supports EU and UK deployments.",
]

pages = extract_page_texts(payload)
decisions = gate_claims(claims, pages)

for decision in decisions:
    print(f"{decision.disposition:6} | {decision.confidence:.2f} | {decision.claim}")
    if decision.evidence:
        top = decision.evidence[0]
        print(f"         receipt p{top.page_index + 1}: {top.text}")

ledger = build_audit_ledger(
    filename="product_brief.pdf",
    file_bytes=source,
    nutrient_response_sha256="OFFLINE_FIXTURE_NOT_SUBMISSION_PROOF",
    nutrient_instructions={
        "parts": [{"file": "document"}],
        "output": {
            "type": "json-content",
            "plainText": True,
            "structuredText": True,
            "keyValuePairs": True,
            "tables": True,
            "language": "english",
        },
    },
    decisions=[d.to_dict() for d in decisions],
)

out = ROOT / "sample" / "groundpitch_audit_ledger.example.json"
out.write_text(json.dumps(ledger, indent=2), encoding="utf-8")
print(f"\nWrote {out}")

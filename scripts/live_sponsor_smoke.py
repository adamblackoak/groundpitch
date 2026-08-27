from __future__ import annotations

import os
from pathlib import Path

from groundpitch.nutrient import extract_document, extract_page_texts
from groundpitch.serpapi import search_claim_context

ROOT = Path(__file__).parents[1]
SOURCE = ROOT / "sample" / "product_brief.pdf"

nutrient_key = os.getenv("NUTRIENT_API_KEY", "").strip()
serpapi_key = os.getenv("SERPAPI_API_KEY", "").strip()

missing = [
    name
    for name, value in {
        "NUTRIENT_API_KEY": nutrient_key,
        "SERPAPI_API_KEY": serpapi_key,
    }.items()
    if not value
]
if missing:
    raise SystemExit("Missing environment variable(s): " + ", ".join(missing))

print("[1/2] Nutrient DWS live extraction")
result = extract_document(
    file_bytes=SOURCE.read_bytes(),
    filename=SOURCE.name,
    api_key=nutrient_key,
)
pages = extract_page_texts(result.raw)
if not pages or not any(page["text"].strip() for page in pages):
    raise SystemExit("FAIL: Nutrient DWS returned no usable page text.")

print(f"PASS: {len(pages)} page record(s)")
print(f"DWS response SHA-256: {result.response_sha256}")

print("\n[2/2] SerpApi live-context search")
scan = search_claim_context(
    claim="AsterFlow is currently the fastest invoice platform in Europe.",
    subject="invoice automation platform",
    api_key=serpapi_key,
    num=5,
)
if scan.search_status.lower() not in {"success", "cached"}:
    raise SystemExit(f"FAIL: SerpApi search status was {scan.search_status!r}")
if not scan.results:
    raise SystemExit("FAIL: SerpApi returned no organic results.")

print(f"PASS: {len(scan.results)} structured organic result(s)")
print(f"SerpApi search id: {scan.search_id or 'not supplied'}")
print(f"SerpApi response SHA-256: {scan.response_sha256}")
for item in scan.results[:3]:
    print(f"  {item.position or '-'} | {item.domain} | {item.title}")

print("\nLIVE SPONSOR SMOKE: PASS")

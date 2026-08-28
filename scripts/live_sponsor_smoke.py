from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from groundpitch.nutrient import NutrientError, extract_document, extract_page_texts
from groundpitch.serpapi import SerpApiError, search_claim_context

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

failures: list[str] = []

print("[1/2] Nutrient DWS live extraction")
try:
    result = extract_document(
        file_bytes=SOURCE.read_bytes(),
        filename=SOURCE.name,
        api_key=nutrient_key,
    )
    pages = extract_page_texts(result.raw)
    if not pages or not any(page["text"].strip() for page in pages):
        raise NutrientError("Nutrient DWS returned no usable page text.")

    print(f"PASS: {len(pages)} page record(s)")
    print(f"DWS response SHA-256: {result.response_sha256}")
except NutrientError as exc:
    failures.append(f"Nutrient: {exc}")
    print(f"FAIL: {exc}")

print("\n[2/2] SerpApi live-context search")
try:
    scan = search_claim_context(
        claim="AsterFlow is currently the fastest invoice platform in Europe.",
        subject="invoice automation platform",
        api_key=serpapi_key,
        num=5,
    )
    if scan.search_status.lower() not in {"success", "cached"}:
        raise SerpApiError(f"SerpApi search status was {scan.search_status!r}")
    if not scan.results:
        raise SerpApiError("SerpApi returned no organic results.")

    print(f"PASS: {len(scan.results)} structured organic result(s)")
    print(f"SerpApi search id: {scan.search_id or 'not supplied'}")
    print(f"SerpApi response SHA-256: {scan.response_sha256}")
    for item in scan.results[:3]:
        print(f"  {item.position or '-'} | {item.domain} | {item.title}")
except SerpApiError as exc:
    failures.append(f"SerpApi: {exc}")
    print(f"FAIL: {exc}")

if failures:
    print("\nLIVE SPONSOR SMOKE: FAIL")
    for failure in failures:
        print(f"- {failure}")
    raise SystemExit(1)

print("\nLIVE SPONSOR SMOKE: PASS")

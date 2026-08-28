from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from groundpitch.nutrient import extract_document, extract_page_texts

key = os.getenv("NUTRIENT_API_KEY", "").strip()
if not key:
    raise SystemExit("Set NUTRIENT_API_KEY before running this live smoke test.")

source = ROOT / "sample" / "product_brief.pdf"
result = extract_document(
    file_bytes=source.read_bytes(),
    filename=source.name,
    api_key=key,
)
pages = extract_page_texts(result.raw)

if not pages or not any(page["text"].strip() for page in pages):
    raise SystemExit("DWS returned no usable page text.")

print(f"LIVE DWS OK: {len(pages)} page record(s)")
print(f"DWS response SHA-256: {result.response_sha256}")
for page in pages:
    preview = page["text"].replace("\n", " ")[:160]
    print(f"p{int(page['page_index']) + 1}: {preview}")

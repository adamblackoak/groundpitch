from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any

import requests

DWS_BUILD_URL = "https://api.nutrient.io/build"


class NutrientError(RuntimeError):
    pass


@dataclass(frozen=True)
class NutrientExtraction:
    raw: dict[str, Any]
    response_sha256: str
    request_instructions: dict[str, Any]


def extract_document(
    *,
    file_bytes: bytes,
    filename: str,
    api_key: str,
    timeout_seconds: int = 90,
) -> NutrientExtraction:
    if not api_key or not api_key.strip():
        raise NutrientError("NUTRIENT_API_KEY is missing.")

    instructions = {
        "parts": [{"file": "document"}],
        "output": {
            "type": "json-content",
            "plainText": True,
            "structuredText": True,
            "keyValuePairs": True,
            "tables": True,
            "language": "english",
        },
    }

    response = requests.post(
        DWS_BUILD_URL,
        headers={"Authorization": f"Bearer {api_key.strip()}"},
        files={"document": (filename, file_bytes, "application/octet-stream")},
        data={"instructions": json.dumps(instructions)},
        timeout=timeout_seconds,
    )

    if not response.ok:
        detail = response.text[:1200]
        raise NutrientError(f"Nutrient DWS returned HTTP {response.status_code}: {detail}")

    try:
        payload = response.json()
    except ValueError as exc:
        raise NutrientError("Nutrient DWS did not return JSON content.") from exc

    return NutrientExtraction(
        raw=payload,
        response_sha256=hashlib.sha256(response.content).hexdigest(),
        request_instructions=instructions,
    )


def extract_page_texts(payload: dict[str, Any]) -> list[dict[str, Any]]:
    pages = payload.get("pages")
    normalized: list[dict[str, Any]] = []

    if isinstance(pages, list):
        for fallback_index, page in enumerate(pages):
            if not isinstance(page, dict):
                continue
            text = page.get("plainText")
            if not isinstance(text, str):
                text = _collect_strings(page)
            normalized.append({
                "page_index": page.get("pageIndex", fallback_index),
                "text": _clean_text(text),
            })

    if not normalized:
        normalized.append({"page_index": 0, "text": _clean_text(_collect_strings(payload))})

    return normalized


def _collect_strings(value: Any) -> str:
    chunks: list[str] = []

    def walk(node: Any) -> None:
        if isinstance(node, str):
            if len(node.strip()) >= 2:
                chunks.append(node.strip())
        elif isinstance(node, list):
            for item in node:
                walk(item)
        elif isinstance(node, dict):
            for key, item in node.items():
                if key not in {"type", "kind", "id", "pageIndex"}:
                    walk(item)

    walk(value)
    return "\n".join(chunks)


def _clean_text(text: str) -> str:
    return "\n".join(line.strip() for line in text.splitlines() if line.strip())

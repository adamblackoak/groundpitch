from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlparse

import requests

SERPAPI_URL = "https://serpapi.com/search.json"

_LIVE_CONTEXT_PATTERNS = (
    r"\bcurrent(?:ly)?\b",
    r"\btoday\b",
    r"\bnow\b",
    r"\blatest\b",
    r"\brecent(?:ly)?\b",
    r"\bas of\b",
    r"\bfastest\b",
    r"\bbest\b",
    r"\bleading\b",
    r"\blargest\b",
    r"\bsmallest\b",
    r"\bcheapest\b",
    r"\bmost\b",
    r"\bonly\b",
    r"\bnumber one\b",
    r"#1\b",
    r"\btop[- ]ranked\b",
    r"\bprice\b",
    r"\bpricing\b",
    r"\bavailable\b",
    r"\bavailability\b",
    r"\bsupports?\b",
    r"\bcoverage\b",
    r"\boperates?\b",
)


class SerpApiError(RuntimeError):
    pass


@dataclass(frozen=True)
class SearchResult:
    position: int | None
    title: str
    link: str
    domain: str
    snippet: str
    date: str | None


@dataclass(frozen=True)
class LiveContextScan:
    claim: str
    query: str
    checked_at_utc: str
    search_id: str | None
    search_status: str
    response_sha256: str
    results: list[SearchResult]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def claim_requires_live_context(claim: str) -> bool:
    text = claim.lower()
    return any(re.search(pattern, text) for pattern in _LIVE_CONTEXT_PATTERNS)


def build_search_query(claim: str, subject: str | None = None) -> str:
    claim = re.sub(r"\s+", " ", claim).strip()
    subject = re.sub(r"\s+", " ", subject or "").strip()
    if subject and subject.lower() not in claim.lower():
        return f"{subject} {claim}"
    return claim


def search_claim_context(
    *,
    claim: str,
    api_key: str,
    subject: str | None = None,
    num: int = 5,
    timeout_seconds: int = 30,
) -> LiveContextScan:
    if not api_key or not api_key.strip():
        raise SerpApiError("SERPAPI_API_KEY is missing.")

    query = build_search_query(claim, subject)
    response = requests.get(
        SERPAPI_URL,
        params={
            "engine": "google",
            "q": query,
            "num": max(1, min(int(num), 10)),
            "output": "json",
            "api_key": api_key.strip(),
        },
        timeout=timeout_seconds,
    )

    if not response.ok:
        raise SerpApiError(
            f"SerpApi returned HTTP {response.status_code}: {response.text[:1200]}"
        )

    try:
        payload = response.json()
    except ValueError as exc:
        raise SerpApiError("SerpApi did not return JSON.") from exc

    if payload.get("error"):
        raise SerpApiError(f"SerpApi error: {payload['error']}")

    return normalize_search_payload(
        claim=claim,
        query=query,
        payload=payload,
        raw_response=response.content,
    )


def normalize_search_payload(
    *,
    claim: str,
    query: str,
    payload: dict[str, Any],
    raw_response: bytes | None = None,
) -> LiveContextScan:
    organic = payload.get("organic_results") or []
    results: list[SearchResult] = []

    for item in organic[:10]:
        if not isinstance(item, dict):
            continue
        link = str(item.get("link") or "")
        results.append(
            SearchResult(
                position=_safe_int(item.get("position")),
                title=str(item.get("title") or ""),
                link=link,
                domain=_domain(link),
                snippet=str(item.get("snippet") or ""),
                date=(str(item["date"]) if item.get("date") else None),
            )
        )

    metadata = payload.get("search_metadata") or {}
    if raw_response is None:
        raw_response = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode(
            "utf-8"
        )

    return LiveContextScan(
        claim=claim,
        query=query,
        checked_at_utc=datetime.now(timezone.utc).isoformat(),
        search_id=(str(metadata["id"]) if metadata.get("id") else None),
        search_status=str(metadata.get("status") or "Unknown"),
        response_sha256=hashlib.sha256(raw_response).hexdigest(),
        results=results,
    )


def _domain(link: str) -> str:
    try:
        return urlparse(link).netloc.lower()
    except ValueError:
        return ""


def _safe_int(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None

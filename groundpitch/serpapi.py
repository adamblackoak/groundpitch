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

_SUBJECT_GENERIC_TERMS = {
    "app",
    "application",
    "company",
    "platform",
    "product",
    "service",
    "software",
    "solution",
    "system",
}


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
    subject: str | None
    checked_at_utc: str
    search_id: str | None
    search_status: str
    response_sha256: str
    raw_result_count: int
    relevant_result_count: int
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
        return f'"{subject}" {claim}'
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

    error_text = str(payload.get("error") or "").strip()
    if error_text:
        normalized_error = error_text.lower()
        no_results = (
            "hasn't returned any results" in normalized_error
            or "has not returned any results" in normalized_error
            or normalized_error == "google hasn't returned any results for this query."
        )
        if not no_results:
            raise SerpApiError(f"SerpApi error: {error_text}")

        metadata = payload.get("search_metadata") or {}
        return normalize_search_payload(
            claim=claim,
            query=query,
            subject=subject,
            payload={"search_metadata": metadata, "organic_results": []},
            raw_response=response.content,
            search_status_override="No organic results",
        )

    return normalize_search_payload(
        claim=claim,
        query=query,
        subject=subject,
        payload=payload,
        raw_response=response.content,
    )


def normalize_search_payload(
    *,
    claim: str,
    query: str,
    payload: dict[str, Any],
    subject: str | None = None,
    raw_response: bytes | None = None,
    search_status_override: str | None = None,
) -> LiveContextScan:
    organic = payload.get("organic_results") or []
    candidates: list[SearchResult] = []

    for item in organic[:10]:
        if not isinstance(item, dict):
            continue
        link = str(item.get("link") or "")
        candidates.append(
            SearchResult(
                position=_safe_int(item.get("position")),
                title=str(item.get("title") or ""),
                link=link,
                domain=_domain(link),
                snippet=str(item.get("snippet") or ""),
                date=(str(item["date"]) if item.get("date") else None),
            )
        )

    clean_subject = re.sub(r"\s+", " ", subject or "").strip() or None
    if clean_subject:
        results = [
            result
            for result in candidates
            if _result_matches_subject(result, clean_subject)
        ]
    else:
        results = candidates

    metadata = payload.get("search_metadata") or {}
    if raw_response is None:
        raw_response = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode(
            "utf-8"
        )

    return LiveContextScan(
        claim=claim,
        query=query,
        subject=clean_subject,
        checked_at_utc=datetime.now(timezone.utc).isoformat(),
        search_id=(str(metadata["id"]) if metadata.get("id") else None),
        search_status=search_status_override or str(metadata.get("status") or "Unknown"),
        response_sha256=hashlib.sha256(raw_response).hexdigest(),
        raw_result_count=len(candidates),
        relevant_result_count=len(results),
        results=results,
    )


def _result_matches_subject(result: SearchResult, subject: str) -> bool:
    normalized_subject = _normalize_subject_text(subject)
    # Only judge subject relevance from actual result content/host. Google
    # redirect/result URLs can contain the original query and therefore must
    # never be treated as evidence that the destination matches the subject.
    haystack = _normalize_subject_text(
        " ".join([result.title, result.snippet, result.domain])
    )

    if normalized_subject and normalized_subject in haystack:
        return True

    terms = _subject_terms(subject)
    if not terms or len(terms) == 1:
        return False

    haystack_terms = set(haystack.split())
    return all(term in haystack_terms for term in terms)


def _normalize_subject_text(text: str) -> str:
    return " ".join(re.findall(r"[a-z0-9]+", text.lower()))


def _subject_terms(subject: str) -> list[str]:
    tokens = [
        token
        for token in re.findall(r"[a-z0-9]+", subject.lower())
        if len(token) > 2
    ]
    specific = [token for token in tokens if token not in _SUBJECT_GENERIC_TERMS]
    return specific or tokens


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

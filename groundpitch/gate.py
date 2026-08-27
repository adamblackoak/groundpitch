from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from typing import Iterable

STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "for", "from", "has",
    "have", "in", "is", "it", "of", "on", "or", "our", "that", "the", "their",
    "this", "to", "up", "we", "with", "your",
}

RISKY_TERMS = {
    "always", "best", "fastest", "guarantee", "guaranteed", "leading",
    "never", "only", "perfect", "safest", "zero",
}


@dataclass(frozen=True)
class EvidenceSpan:
    page_index: int
    text: str
    score: float


@dataclass(frozen=True)
class ClaimDecision:
    claim: str
    disposition: str
    confidence: float
    reason: str
    evidence: list[EvidenceSpan]
    unsupported_numbers: list[str]
    unsupported_risky_terms: list[str]

    def to_dict(self) -> dict:
        return asdict(self)


def gate_claims(
    claims: Iterable[str],
    pages: list[dict],
    *,
    admit_threshold: float = 0.52,
    review_threshold: float = 0.28,
) -> list[ClaimDecision]:
    spans = _make_spans(pages)
    return [
        gate_claim(
            claim,
            spans,
            admit_threshold=admit_threshold,
            review_threshold=review_threshold,
        )
        for claim in claims
        if claim.strip()
    ]


def gate_claim(
    claim: str,
    evidence_spans: list[EvidenceSpan],
    *,
    admit_threshold: float = 0.52,
    review_threshold: float = 0.28,
) -> ClaimDecision:
    claim = claim.strip()

    ranked = sorted(
        (
            EvidenceSpan(
                page_index=span.page_index,
                text=span.text,
                score=_support_score(claim, span.text),
            )
            for span in evidence_spans
        ),
        key=lambda item: item.score,
        reverse=True,
    )
    top = ranked[:3]
    best_score = top[0].score if top else 0.0

    # Numbers and high-risk qualifiers must occur in evidence that is actually
    # relevant to the claim. Merely appearing somewhere else in the document
    # must not launder an assertion through the gate.
    relevant_evidence = [
        span.text
        for span in top
        if span.score >= review_threshold
    ]
    if not relevant_evidence and top:
        relevant_evidence = [top[0].text]

    numbers = _numbers(claim)
    unsupported_numbers = [
        number
        for number in numbers
        if not any(number.lower() in text.lower() for text in relevant_evidence)
    ]

    risky = sorted({token for token in _tokens(claim) if token in RISKY_TERMS})
    unsupported_risky = [
        term
        for term in risky
        if not any(term in _tokens(text) for text in relevant_evidence)
    ]

    if unsupported_numbers:
        disposition = "REJECT"
        reason = (
            "Claim contains numeric assertions absent from the relevant extracted "
            "source evidence."
        )
    elif unsupported_risky:
        disposition = "REJECT"
        reason = (
            "Claim adds an absolute or superlative qualifier the relevant source "
            "evidence does not support."
        )
    elif best_score >= admit_threshold:
        disposition = "ADMIT"
        reason = "Claim is materially supported by extracted source evidence."
    elif best_score >= review_threshold:
        disposition = "REVIEW"
        reason = "Some support exists, but the claim needs a human decision before release."
    else:
        disposition = "REJECT"
        reason = "No sufficiently close source evidence was found."

    confidence = min(1.0, max(0.0, best_score))
    if disposition == "REJECT" and (unsupported_numbers or unsupported_risky):
        confidence = max(confidence, 0.95)

    return ClaimDecision(
        claim=claim,
        disposition=disposition,
        confidence=round(confidence, 4),
        reason=reason,
        evidence=top,
        unsupported_numbers=unsupported_numbers,
        unsupported_risky_terms=unsupported_risky,
    )


def _make_spans(pages: list[dict]) -> list[EvidenceSpan]:
    spans: list[EvidenceSpan] = []
    for page in pages:
        page_index = int(page.get("page_index", 0))
        text = str(page.get("text", ""))
        for sentence in _sentences(text):
            if len(sentence) >= 12:
                spans.append(EvidenceSpan(page_index, sentence, 0.0))
    if not spans:
        spans.append(EvidenceSpan(0, "", 0.0))
    return spans


def _support_score(claim: str, evidence: str) -> float:
    c = _content_tokens(claim)
    e = _content_tokens(evidence)
    if not c or not e:
        return 0.0

    intersection = len(c & e)
    precision = intersection / len(c)
    recall = intersection / len(e)
    lexical = (2 * precision * recall / (precision + recall)) if precision + recall else 0.0

    claim_numbers = _numbers(claim)
    number_bonus = 0.0
    if claim_numbers:
        matched = sum(1 for n in claim_numbers if n.lower() in evidence.lower())
        number_bonus = 0.18 * (matched / len(claim_numbers))

    phrase_bonus = 0.0
    claim_norm = " ".join(_tokens(claim))
    evidence_norm = " ".join(_tokens(evidence))
    for n in (5, 4, 3):
        grams = _ngrams(claim_norm.split(), n)
        if any(" ".join(g) in evidence_norm for g in grams):
            phrase_bonus = max(phrase_bonus, 0.08 * (n / 3))
            break

    return min(1.0, lexical + number_bonus + phrase_bonus)


def _tokens(text: str) -> list[str]:
    return re.findall(r"[a-z0-9%£$€.-]+", text.lower())


def _content_tokens(text: str) -> set[str]:
    return {
        token
        for token in _tokens(text)
        if token not in STOPWORDS and len(token) > 1
    }


def _numbers(text: str) -> list[str]:
    return re.findall(
        r"(?<!\w)(?:[$£€]\s*)?\d[\d,]*(?:\.\d+)?\s*%?(?!\w)",
        text,
    )


def _sentences(text: str) -> list[str]:
    flat = re.sub(r"\s+", " ", text).strip()
    if not flat:
        return []
    return [
        s.strip()
        for s in re.split(r"(?<=[.!?])\s+|\s*[•●]\s*", flat)
        if s.strip()
    ]


def _ngrams(tokens: list[str], n: int):
    if len(tokens) < n:
        return []
    return [tuple(tokens[i : i + n]) for i in range(len(tokens) - n + 1)]

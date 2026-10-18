"""Conservative negative screens. Lexical plausibility is not semantic entailment."""
from __future__ import annotations
from decimal import Decimal, InvalidOperation
import re

_NUMBER = re.compile(
    r"(?<![\w.])(?P<currency>[£$€])?\s*(?P<sign>-)?"
    r"(?P<value>(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?)"
    r"\s*(?P<unit>%|percent|per\s+cent)?(?!\w)",
    re.IGNORECASE,
)
_WORD = re.compile(r"[a-z0-9]+", re.IGNORECASE)
_NEGATIVE = frozenset({
    "not", "no", "never", "without", "cannot", "prohibit", "prohibits",
    "prohibited", "forbid", "forbidden", "deny", "denies", "denied",
    "exclude", "excludes", "excluded", "blocked",
})

def numeric_assertions(text: str) -> frozenset[str]:
    result = set()
    for match in _NUMBER.finditer(text):
        try:
            value = Decimal(match.group("value").replace(",", ""))
        except InvalidOperation:
            continue
        if match.group("sign"):
            value = -value
        unit = "%" if match.group("unit") else ""
        result.add(f"{match.group('currency') or ''}{value.normalize()}{unit}")
    return frozenset(result)

def potential_negation_conflict(claim: str, evidence: str) -> bool:
    c, e = set(_WORD.findall(claim.lower())), set(_WORD.findall(evidence.lower()))
    shared = c.intersection(e) - _NEGATIVE
    return len(shared) >= 2 and bool(c.intersection(_NEGATIVE)) != bool(e.intersection(_NEGATIVE))

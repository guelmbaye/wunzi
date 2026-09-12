"""
Critical Fact Accuracy (CFA) — the metric that actually decides a mediation.

Exact canonical match only. There is no partial credit: 150,000 heard as 50,000
is wrong, and a system that scores it 0.66 for sharing digits would be lying
about the risk it creates.

Also computes Negation Preservation Rate: a dropped "not" reverses an issue from
AGREED to DISPUTED, which is a mediation-level failure, not a typo.
"""

from __future__ import annotations

import re

from app.intelligence.canonicalizer import extract_amounts, extract_dates
from app.intelligence.negation import detect_polarity


def _canonical_facts(text: str) -> set[str]:
    facts = {f"amount:{a.value}:{a.currency or 'NONE'}" for a in extract_amounts(text)}
    facts |= {f"date:{d.iso or (str(d.day) + chr(45) + str(d.month))}" for d in extract_dates(text)}
    return facts


def critical_fact_accuracy(reference: str, hypothesis: str) -> float:
    """Fraction of reference critical facts reproduced exactly after canonicalisation."""
    expected = _canonical_facts(reference)
    if not expected:
        return 1.0

    produced = _canonical_facts(hypothesis)
    return len(expected & produced) / len(expected)


def critical_fact_detail(reference: str, hypothesis: str) -> dict:
    expected = _canonical_facts(reference)
    produced = _canonical_facts(hypothesis)

    return {
        "expected": sorted(expected),
        "produced": sorted(produced),
        "matched": sorted(expected & produced),
        "missed": sorted(expected - produced),
        "invented": sorted(produced - expected),
    }


def _sentences(text: str) -> list[str]:
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+|\n+", text) if s.strip()]


def _best_match(sentence: str, candidates: list[str]) -> str | None:
    """Aligns by lexical overlap so a per-sentence comparison survives ASR drift."""
    target = set(sentence.lower().split())
    if not target:
        return None

    best, best_score = None, 0.0
    for candidate in candidates:
        overlap = target & set(candidate.lower().split())
        score = len(overlap) / len(target)
        if score > best_score:
            best, best_score = candidate, score

    return best if best_score >= 0.4 else None


def negation_preservation(reference: str, hypothesis: str) -> float | None:
    """
    Measured clause by clause. A paragraph containing both a negation and an
    assertion has no single polarity, so comparing whole documents would score
    every provider identically and hide the failure this metric exists to catch.
    """
    hypothesis_sentences = _sentences(hypothesis)
    scores: list[float] = []

    for sentence in _sentences(reference):
        ref_polarity, _ = detect_polarity(sentence)
        if ref_polarity.value != "NEGATIVE":
            continue  # only negated statements can lose a negation

        match = _best_match(sentence, hypothesis_sentences)
        if match is None:
            scores.append(0.0)  # the clause vanished: the negation went with it
            continue

        hyp_polarity, _ = detect_polarity(match)
        scores.append(1.0 if hyp_polarity.value == "NEGATIVE" else 0.0)

    return sum(scores) / len(scores) if scores else None

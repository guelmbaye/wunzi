"""
Negation preservation.

A single lost negation reverses a claim: "did not promise" → "promised" turns a
DISPUTED issue into an AGREED one. Ambiguous polarity on a high-impact predicate
always escalates to NEEDS_CONFIRMATION rather than being silently resolved.
"""

from __future__ import annotations

import re

from app.intelligence.lexicon import NEGATION_EXCEPTIONS, NEGATION_MARKERS
from app.schemas.common import Polarity

HIGH_IMPACT_PREDICATES: frozenset[str] = frozenset(
    {
        "promised_refund",
        "paid_deposit",
        "caused_damage",
        "received_payment",
        "accepted_deduction",
        "returned_property",
        "agreed_amount",
    }
)

_AMBIGUITY_MARKERS = (
    "i think", "maybe", "not sure", "i don't remember", "peut-être",
    "je ne suis pas sûr", "sinzi neza", "ntabwo nzi neza",
)


def detect_polarity(text: str, languages: tuple[str, ...] = ("en", "fr", "rw")) -> tuple[Polarity, list[str]]:
    """Returns the polarity plus the markers that produced it (for auditability)."""
    lowered = f" {text.lower().strip()} "

    for exception in NEGATION_EXCEPTIONS:
        lowered = lowered.replace(exception, " ")

    hits: list[str] = []
    for language in languages:
        for marker in NEGATION_MARKERS.get(language, ()):  # ordered, longest first is not required
            if marker in lowered:
                hits.append(f"{language}:{marker.strip()}")

    ambiguous = any(marker in lowered for marker in _AMBIGUITY_MARKERS)

    if ambiguous and hits:
        return Polarity.UNCLEAR, hits + ["ambiguity_marker"]
    if not hits:
        return Polarity.POSITIVE, []

    # Two independent negation markers in one clause is a classic ASR/semantic trap.
    distinct = {hit.split(":", 1)[1] for hit in hits}
    if len(distinct) >= 3:
        return Polarity.UNCLEAR, hits + ["multiple_negation_markers"]

    return Polarity.NEGATIVE, hits


def polarity_is_ambiguous(polarity: Polarity, predicate: str) -> bool:
    return polarity is Polarity.UNCLEAR and predicate in HIGH_IMPACT_PREDICATES


def polarity_conflicts(a: Polarity | str, b: Polarity | str) -> bool | None:
    """None when at least one side is UNCLEAR: uncertainty is not disagreement."""
    a = Polarity(a) if isinstance(a, str) else a
    b = Polarity(b) if isinstance(b, str) else b

    if a is Polarity.UNCLEAR or b is Polarity.UNCLEAR:
        return None
    return a is not b


def strip_negation(text: str) -> str:
    """Utility for surface comparison; never used to decide state."""
    pattern = "|".join(
        re.escape(marker.strip())
        for markers in NEGATION_MARKERS.values()
        for marker in markers
    )
    return re.sub(rf"\b({pattern})\b", " ", text, flags=re.IGNORECASE)

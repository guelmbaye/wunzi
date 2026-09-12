"""
Shared, deterministic text normalisation.

Applied identically to every provider before scoring. Provider-specific
formatting may be normalised; semantic post-processing may not.
"""

from __future__ import annotations

import re
import unicodedata

_WHITESPACE = re.compile(r"\s+")
_PUNCTUATION = re.compile(r"[^\w\s'-]", flags=re.UNICODE)
_DIGIT_GROUP = re.compile(r"(?<=\d)[ ,.\u00a0](?=\d{3}\b)")


def normalise_unicode(text: str) -> str:
    return unicodedata.normalize("NFKC", text)


def normalise_for_wer(text: str) -> str:
    """Lexical view: what the ASR literally produced."""
    text = normalise_unicode(text).lower()
    text = _DIGIT_GROUP.sub("", text)
    text = _PUNCTUATION.sub(" ", text)
    return _WHITESPACE.sub(" ", text).strip()


def normalise_for_cer(text: str) -> str:
    text = normalise_unicode(text).lower()
    return _WHITESPACE.sub(" ", text).strip()


def canonical_number_view(text: str) -> str:
    """
    Canonical view: "one hundred fifty thousand" and "150000" may be
    semantically equivalent even though their lexical forms differ.
    """
    from app.intelligence.canonicalizer import extract_amounts

    result = normalise_for_wer(text)
    for amount in extract_amounts(text):
        result = result.replace(normalise_for_wer(amount.surface), str(amount.value))
    return _WHITESPACE.sub(" ", result).strip()


def merge_segment_text(segments: list[dict]) -> str:
    return _WHITESPACE.sub(" ", " ".join(s.get("text", "") for s in segments)).strip()

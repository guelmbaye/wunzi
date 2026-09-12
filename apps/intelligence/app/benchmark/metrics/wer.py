"""
Word / Character Error Rate.

Reported for completeness and comparability with the wider ASR field — never as
the headline result. WER is a lexical measure; a mediation outcome is not.
"""

from __future__ import annotations

from app.asr.normalizer import normalise_for_cer, normalise_for_wer


def _levenshtein(reference: list[str], hypothesis: list[str]) -> int:
    if not reference:
        return len(hypothesis)
    if not hypothesis:
        return len(reference)

    previous = list(range(len(hypothesis) + 1))

    for i, ref_token in enumerate(reference, start=1):
        current = [i]
        for j, hyp_token in enumerate(hypothesis, start=1):
            current.append(
                min(
                    previous[j] + 1,                                  # deletion
                    current[j - 1] + 1,                               # insertion
                    previous[j - 1] + (ref_token != hyp_token),       # substitution
                )
            )
        previous = current

    return previous[-1]


def word_error_rate(reference: str, hypothesis: str) -> float:
    ref_tokens = normalise_for_wer(reference).split()
    hyp_tokens = normalise_for_wer(hypothesis).split()

    if not ref_tokens:
        return 0.0 if not hyp_tokens else 1.0

    return _levenshtein(ref_tokens, hyp_tokens) / len(ref_tokens)


def character_error_rate(reference: str, hypothesis: str) -> float:
    ref = list(normalise_for_cer(reference))
    hyp = list(normalise_for_cer(hypothesis))

    if not ref:
        return 0.0 if not hyp else 1.0

    return _levenshtein(ref, hyp) / len(ref)

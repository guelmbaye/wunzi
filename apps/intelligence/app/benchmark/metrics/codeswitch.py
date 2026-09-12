"""
Code-switching metrics.

WER answers "how many words were wrong". It does not answer the question a
code-switched benchmark actually needs: *did the model keep the speaker's
languages, or did it quietly rewrite them into one?*

Three measures here, none of which WER captures:

  Matrix Language Collapse   the model translated instead of transcribing
  Switch Point Preservation  the alternation points survived
  Span Language Fidelity     each span stayed in the language it was spoken in

The first is the important one and the reason this module exists. A model that
hears Kinyarwanda and emits fluent English scores badly on WER, but so does a
model that simply mishears — and those two failures need completely different
responses. In mediation the difference is decisive: a translated account is no
longer the speaker's own words, and a case built on it cannot be traced back to
what anyone said.

Ground truth comes from AfriSwitch's `transcription_tagged` field, where English
spans are wrapped in `[[EN]]`…`[[/EN]]`. Nothing here is inferred.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.asr.normalizer import normalise_for_wer

# Function words that appear in almost any English utterance. Presence of a few
# proves nothing; a transcript built almost entirely from them is English.
ENGLISH_MARKERS = frozenset(
    """
    the a an and or but if then than that this these those there here
    is are was were be been being am do does did doing done
    have has had having will would shall should can could may might must
    i you he she it we they me him her us them my your his its our their
    of to in on at by for with from about into over under after before
    not no yes so very just only also too more most some any all
    what when where who why how which
    """.split()
)


@dataclass(frozen=True)
class CodeSwitchScores:
    matrix_language_collapse: float
    switch_point_preservation: float
    span_language_fidelity: float
    english_ratio_reference: float
    english_ratio_hypothesis: float

    def as_dict(self) -> dict[str, float]:
        return {
            "matrix_language_collapse_rate": round(self.matrix_language_collapse, 4),
            "switch_point_preservation": round(self.switch_point_preservation, 4),
            "span_language_fidelity": round(self.span_language_fidelity, 4),
            "english_ratio_reference": round(self.english_ratio_reference, 4),
            "english_ratio_hypothesis": round(self.english_ratio_hypothesis, 4),
        }


def _tokens(text: str) -> list[str]:
    return normalise_for_wer(text).split()


def english_ratio(text: str) -> float:
    """
    Share of tokens that are common English function words.

    A crude signal on purpose: it needs no language identifier, no model, and no
    per-language configuration, so it behaves identically across all 14 AfriSwitch
    languages and cannot itself become a source of bias between them.
    """
    tokens = _tokens(text)
    if not tokens:
        return 0.0
    return sum(1 for token in tokens if token in ENGLISH_MARKERS) / len(tokens)


def matrix_language_collapse(reference: str, hypothesis: str, threshold: float = 1.6) -> float:
    """
    1.0 when the hypothesis looks substantially more English than the reference.

    This catches the failure where a model *translates* a Kinyarwanda utterance
    into English rather than transcribing it. The output can be fluent, useful
    prose and still be the wrong artefact: it is no longer what the speaker said.

    The threshold is a ratio, not an absolute, so an utterance that was already
    half English does not register as collapsed just for being English-heavy.
    """
    ref = english_ratio(reference)
    hyp = english_ratio(hypothesis)

    if not _tokens(hypothesis):
        return 0.0  # an empty transcript is a failure, but not this one

    if ref < 0.02:
        # Reference is essentially free of English function words: any
        # English-shaped output is a rewrite.
        return 1.0 if hyp > 0.25 else 0.0

    return 1.0 if hyp / ref >= threshold else 0.0


def switch_point_preservation(
    english_spans: list[str],
    hypothesis: str,
) -> float | None:
    """
    Fraction of the reference's English spans that survive in the hypothesis.

    An English span is counted as preserved when most of its content words
    appear in the hypothesis. Exact position is not required — an ASR may shift
    boundaries by a word without losing the switch, and penalising that would
    measure alignment rather than code-switch handling.

    Returns None for a monolingual utterance, which is excluded rather than
    scored 1.0: there was nothing to preserve, and counting it as a success
    would inflate every model's average with free marks.
    """
    if not english_spans:
        return None

    hypothesis_tokens = set(_tokens(hypothesis))
    preserved = 0

    for span in english_spans:
        tokens = [t for t in _tokens(span) if t not in ENGLISH_MARKERS] or _tokens(span)
        if not tokens:
            continue
        overlap = sum(1 for token in tokens if token in hypothesis_tokens) / len(tokens)
        if overlap >= 0.5:
            preserved += 1

    return preserved / len(english_spans)


def span_language_fidelity(
    matrix_spans: list[str],
    hypothesis: str,
) -> float | None:
    """
    Fraction of matrix-language spans still recognisable in the hypothesis.

    Paired with switch_point_preservation this separates two opposite failures:
    a model that drops the English spans, and a model that drops the matrix
    language. Both look like "high WER" and neither is fixed the same way.
    """
    if not matrix_spans:
        return None

    hypothesis_tokens = set(_tokens(hypothesis))
    preserved = 0

    for span in matrix_spans:
        tokens = _tokens(span)
        if not tokens:
            continue
        overlap = sum(1 for token in tokens if token in hypothesis_tokens) / len(tokens)
        if overlap >= 0.4:
            preserved += 1

    return preserved / len(matrix_spans)


def score_utterance(
    reference: str,
    hypothesis: str,
    english_spans: list[str],
    matrix_spans: list[str],
) -> CodeSwitchScores:
    switch = switch_point_preservation(english_spans, hypothesis)
    fidelity = span_language_fidelity(matrix_spans, hypothesis)

    return CodeSwitchScores(
        matrix_language_collapse=matrix_language_collapse(reference, hypothesis),
        switch_point_preservation=switch if switch is not None else 1.0,
        span_language_fidelity=fidelity if fidelity is not None else 1.0,
        english_ratio_reference=english_ratio(reference),
        english_ratio_hypothesis=english_ratio(hypothesis),
    )

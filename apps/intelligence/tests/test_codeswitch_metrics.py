"""
Code-switch metrics.

The examples are shaped like real AfriSwitch Kinyarwanda utterances: a matrix
language carrying English insertions, tagged with [[EN]]...[[/EN]].
"""

from app.benchmark.afriswitch import parse_spans
from app.benchmark.metrics.codeswitch import (
    english_ratio,
    matrix_language_collapse,
    score_utterance,
    span_language_fidelity,
    switch_point_preservation,
)

TAGGED = (
    "Nishyuye [[EN]]deposit[[/EN]] ya 150,000 RWF, kandi narangije "
    "[[EN]]contract[[/EN]] yanjye. [[EN]]The landlord told me he would refund "
    "everything[[/EN]] ariko ntabwo nabonye amafaranga."
)
REFERENCE = (
    "Nishyuye deposit ya 150,000 RWF, kandi narangije contract yanjye. "
    "The landlord told me he would refund everything ariko ntabwo nabonye amafaranga."
)


def _spans():
    spans = parse_spans(TAGGED, "rw")
    english = [s.text for s in spans if s.language == "en"]
    matrix = [s.text for s in spans if s.language != "en"]
    return english, matrix


# ── span parsing ───────────────────────────────────────────────────────────
def test_tagged_transcription_yields_alternating_spans():
    spans = parse_spans(TAGGED, "rw")
    languages = [s.language for s in spans]

    assert "en" in languages and "rw" in languages
    # Alternation is the point: consecutive spans must not share a language.
    assert all(a != b for a, b in zip(languages, languages[1:]))


def test_english_spans_are_extracted_verbatim():
    english, _ = _spans()
    assert "deposit" in english
    assert "contract" in english
    assert any("landlord" in span for span in english)


def test_token_offsets_are_contiguous():
    spans = parse_spans(TAGGED, "rw")
    for previous, current in zip(spans, spans[1:]):
        assert current.start_token == previous.end_token


def test_monolingual_text_is_one_span():
    spans = parse_spans("Ntabwo nangije icyumba.", "rw")
    assert len(spans) == 1 and spans[0].language == "rw"


# ── matrix language collapse ───────────────────────────────────────────────
def test_faithful_transcription_is_not_collapse():
    assert matrix_language_collapse(REFERENCE, REFERENCE) == 0.0


def test_translating_instead_of_transcribing_is_collapse():
    # Fluent, useful English — and the wrong artefact. The speaker's own words
    # are gone, so nothing in the case can be traced back to them.
    translated = (
        "I paid a deposit of 150,000 RWF and I finished my contract. "
        "The landlord told me he would refund everything but I did not get the money."
    )
    assert matrix_language_collapse(REFERENCE, translated) == 1.0


def test_mishearing_is_not_reported_as_collapse():
    # High WER, but the languages are intact — a different failure needing a
    # different fix, and the metric must not conflate them.
    misheard = (
        "Nishyuye deposit ya 50,000 RWF, kandi narangije contract yanjye. "
        "The landlord told me he would refund everything ariko ntabwo nabonye amafaranga."
    )
    assert matrix_language_collapse(REFERENCE, misheard) == 0.0


def test_english_heavy_reference_is_not_penalised_for_being_english():
    reference = "The landlord said he would refund the deposit but he did not pay me."
    assert matrix_language_collapse(reference, reference) == 0.0


def test_empty_hypothesis_is_not_collapse():
    assert matrix_language_collapse(REFERENCE, "") == 0.0


# ── switch points ──────────────────────────────────────────────────────────
def test_preserved_switches_score_one():
    english, _ = _spans()
    assert switch_point_preservation(english, REFERENCE) == 1.0


def test_dropped_english_spans_lower_the_score():
    english, _ = _spans()
    stripped = "Nishyuye ya 150,000 RWF, kandi narangije yanjye. Ariko ntabwo nabonye amafaranga."
    assert switch_point_preservation(english, stripped) < 1.0


def test_monolingual_utterance_is_excluded_not_scored():
    # Scoring it 1.0 would hand every model free marks on utterances that
    # contained no switch to preserve.
    assert switch_point_preservation([], "Ntabwo nangije icyumba.") is None


# ── span fidelity ──────────────────────────────────────────────────────────
def test_matrix_spans_survive_a_faithful_transcript():
    _, matrix = _spans()
    assert span_language_fidelity(matrix, REFERENCE) == 1.0


def test_matrix_spans_vanish_under_translation():
    _, matrix = _spans()
    translated = "I paid a deposit of 150,000 RWF and I finished my contract."
    assert span_language_fidelity(matrix, translated) < 0.5


# ── combined ───────────────────────────────────────────────────────────────
def test_translation_separates_from_mishearing_on_the_full_score():
    english, matrix = _spans()

    translated = score_utterance(
        REFERENCE,
        "I paid a deposit of 150,000 RWF and I finished my contract.",
        english,
        matrix,
    )
    misheard = score_utterance(
        REFERENCE,
        REFERENCE.replace("150,000", "50,000"),
        english,
        matrix,
    )

    assert translated.matrix_language_collapse == 1.0
    assert misheard.matrix_language_collapse == 0.0
    assert misheard.span_language_fidelity > translated.span_language_fidelity


def test_english_ratio_rises_with_english_content():
    assert english_ratio("Ntabwo nangije icyumba") < english_ratio(
        "I did not damage the room and it was not me"
    )

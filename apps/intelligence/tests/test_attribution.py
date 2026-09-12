"""Reported speech must never be flattened into a direct fact."""

from app.intelligence.attribution import detect_reported_speech, resolve


def test_reported_speech_detected():
    reported, _ = detect_reported_speech("The landlord told me he would refund everything")
    assert reported is True


def test_direct_statement_is_not_reported():
    reported, _ = detect_reported_speech("I paid the deposit in March")
    assert reported is False


def test_speaker_role_is_authoritative():
    attribution = resolve("I paid the deposit", "PARTY_A")
    assert attribution.source_party == "PARTY_A"


def test_unresolved_pronoun_stays_unresolved():
    # Guessing a subject here would invent an accusation.
    attribution = resolve("He said he would pay", "PARTY_A")
    assert attribution.subject is None or attribution.is_ambiguous

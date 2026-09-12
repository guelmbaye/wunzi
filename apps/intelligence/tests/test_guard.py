"""The Critical Speech Guard decides what a mediator is allowed to see unflagged."""

from app.intelligence.criticality import CriticalSpeechGuard, build_verification_prompt
from app.schemas.claims import AsrMetadata, ExtractedClaim
from app.schemas.common import CriticalFieldType, GuardDecision, Polarity


def _claim(**overrides) -> ExtractedClaim:
    payload = {
        "claim_id": "c1",
        "source_party": "PARTY_A",
        "party_role": "PARTY_A",
        "subject": "party_a",
        "type": "deposit_amount",
        "predicate": "paid_deposit_of",
        "canonical_value": {"amount_minor": 150000, "currency": "RWF"},
        "extraction_confidence": 0.95,
        "attribution_confidence": 0.95,
    }
    payload.update(overrides)
    return ExtractedClaim(**payload)


def test_low_confidence_amount_needs_confirmation():
    guard = CriticalSpeechGuard()
    outcome = guard.evaluate_claim(_claim(extraction_confidence=0.55), AsrMetadata())
    assert outcome.decision is not GuardDecision.ACCEPT_FOR_CASE


def test_unclear_negation_is_never_silently_accepted():
    guard = CriticalSpeechGuard()
    outcome = guard.evaluate_claim(
        _claim(type="refund_commitment", polarity=Polarity.UNCLEAR), AsrMetadata()
    )
    assert outcome.decision is not GuardDecision.ACCEPT_FOR_CASE


def test_ablation_mode_lets_everything_through():
    # This is the point of the ablation: it measures the cost of removing the guard.
    guard = CriticalSpeechGuard()
    outcome = guard.evaluate_claim(_claim(extraction_confidence=0.20), AsrMetadata(), enabled=False)
    assert outcome.decision is GuardDecision.ACCEPT_FOR_CASE


def test_verification_prompt_is_not_suggestive():
    prompt = build_verification_prompt(_claim(), CriticalFieldType.AMOUNT)
    lowered = prompt.lower()
    for leading in ("are you sure", "you probably", "don't you", "isn't it"):
        assert leading not in lowered
    assert "?" in prompt

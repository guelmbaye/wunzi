"""A lost negation reverses a mediation state. It is never a cosmetic error."""

from app.intelligence.negation import detect_polarity, polarity_conflicts
from app.schemas.common import Polarity


def test_english_negation():
    polarity, markers = detect_polarity("I did not damage the room")
    assert polarity is Polarity.NEGATIVE and markers


def test_french_negation():
    polarity, _ = detect_polarity("je n'ai rien recu")
    assert polarity is Polarity.NEGATIVE


def test_kinyarwanda_negation():
    polarity, _ = detect_polarity("Ntabwo namusezeranyije ko nzamusubiza amafaranga yose")
    assert polarity is Polarity.NEGATIVE


def test_positive_by_default():
    polarity, _ = detect_polarity("I paid the deposit in March")
    assert polarity is Polarity.POSITIVE


def test_opposite_polarity_is_a_conflict():
    assert polarity_conflicts(Polarity.POSITIVE, Polarity.NEGATIVE) is True


def test_unclear_polarity_is_not_a_disagreement():
    # Uncertainty must not be promoted into a dispute the parties never had.
    assert polarity_conflicts(Polarity.UNCLEAR, Polarity.NEGATIVE) is None

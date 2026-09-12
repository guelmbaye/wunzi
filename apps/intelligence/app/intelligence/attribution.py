"""
Claim Attribution Engine.

Reconstructs (source_party, subject, predicate, object) and preserves the
speaker-vs-quoted-speaker distinction. A correct transcript with wrong
attribution counts as a failure.

Failure modes explicitly guarded here:
  E05 wrong speaker · E06 reported-speech flattening · E07 pronoun resolution
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from app.intelligence.lexicon import FIRST_PERSON_RW, REPORTED_SPEECH_MARKERS

FIRST_PERSON = (
    "i ", "i'", "my ", "me ", "we ", "our ",
    "je ", "j'", "mon ", "ma ", "mes ", "nous ",
    "n", "njye", "nanjye", "nge",
)
THIRD_PERSON = (
    "he ", "she ", "they ", "him ", "her ", "them ", "his ", "their ",
    "il ", "elle ", "ils ", "elles ", "lui ", "leur ",
    "we ", "nyiri inzu", "umukode", "nyirinzu",
)
LANDLORD_MARKERS = ("landlord", "owner", "propriétaire", "nyir'inzu", "nyirinzu", "nyiri inzu")
TENANT_MARKERS = ("tenant", "locataire", "umukode", "umukodesha")


@dataclass(frozen=True)
class Attribution:
    source_party: str
    subject: str | None
    reported_speech: bool
    confidence: float
    reasons: list[str]

    @property
    def is_ambiguous(self) -> bool:
        return self.subject is None or self.confidence < 0.7


def detect_reported_speech(text: str) -> tuple[bool, str | None]:
    lowered = text.lower()
    for language, markers in REPORTED_SPEECH_MARKERS.items():
        for marker in markers:
            if marker in lowered:
                return True, f"{language}:{marker}"
    return False, None


def resolve(text: str, speaker_role: str) -> Attribution:
    """
    speaker_role is authoritative: it comes from the recording, not from the model.
    The subject is inferred and stays None when it cannot be resolved safely.
    """
    lowered = f" {text.lower().strip()} "
    reasons: list[str] = []

    reported, marker = detect_reported_speech(lowered)
    if marker:
        reasons.append(f"reported_speech_marker:{marker}")

    other_role = "party_b" if speaker_role == "PARTY_A" else "party_a"
    subject: str | None = None
    confidence = 0.5

    # MVP convention for the rental-deposit scenario: Party A = tenant,
    # Party B = landlord. An explicit role word resolves the subject
    # independently of who is speaking.
    if any(m in lowered for m in LANDLORD_MARKERS):
        subject = "party_b"
        reasons.append("explicit_role_reference:landlord")
        confidence = 0.9
    elif any(m in lowered for m in TENANT_MARKERS):
        subject = "party_a"
        reasons.append("explicit_role_reference:tenant")
        confidence = 0.85

    if subject is None and reported:
        # "The landlord told me he would return the money" → the other party.
        # With only a bare pronoun and no role word, this is a two-party
        # convention rather than a resolution, so it stays below the ambiguity
        # threshold and the guard asks the speaker instead of guessing.
        subject = other_role
        if _has_bare_pronoun(lowered):
            reasons.append("reported_speech_default_subject_unresolved_pronoun")
            confidence = 0.6
        else:
            reasons.append("reported_speech_default_subject")
            confidence = 0.72

    if subject is None and _has_first_person(lowered):
        subject = speaker_role.lower()
        reasons.append("first_person_self_reference")
        confidence = 0.9

    if subject is None and _has_bare_pronoun(lowered):
        # Two parties, one pronoun: in this MVP scenario a third-person referent
        # is the other party. That is a convention, not a resolution, so the
        # confidence stays below the threshold used for anything consequential.
        subject = other_role
        reasons.append("two_party_pronoun_convention")
        confidence = 0.72

    if subject is None and not _references_a_person(lowered):
        # Existential statement about the property, not about a person.
        # There is no attribution here to get wrong.
        reasons.append("subject_not_applicable")
        confidence = 0.85
    elif subject is None:
        reasons.append("unresolved_subject")
        confidence = 0.4

    return Attribution(
        # The recording says who spoke. The model never overrides it.
        source_party=speaker_role.upper(),
        subject=subject,
        reported_speech=reported,
        confidence=confidence,
        reasons=reasons,
    )


def _has_first_person(lowered: str) -> bool:
    if any(lowered.lstrip().startswith(m.strip() + " ") for m in FIRST_PERSON if m.strip()):
        return True
    if re.search(r"\b(i|my|me|we|our|je|j'|mon|ma|mes|nous)\b", lowered):
        return True
    return any(re.search(rf"\b{form}", lowered) for form in FIRST_PERSON_RW)


def _references_a_person(lowered: str) -> bool:
    """True when the clause points at somebody. False for 'there was damage'."""
    if _has_bare_pronoun(lowered) or _has_first_person(lowered):
        return True
    if any(m in lowered for m in LANDLORD_MARKERS + TENANT_MARKERS):
        return True
    return bool(re.search(r"\b(you|your|vous|votre|we|us)\b", lowered))


def _has_bare_pronoun(lowered: str) -> bool:
    return bool(re.search(r"\b(he|she|they|il|elle|ils|we)\b", lowered))

"""
Critical Speech Guard.

Asks one question: could an error here materially change the mediation state?

Inputs : semantic criticality + ASR uncertainty + attribution uncertainty
         + cross-model disagreement + domain validation.
Output : ACCEPT_FOR_CASE | NEEDS_CONFIRMATION | REJECT_AS_UNRESOLVED

Rules are preferable to a learned risk model for the MVP: the reason a field was
escalated must be inspectable by a judge.
"""

from __future__ import annotations

from app.config import get_settings
from app.intelligence.negation import HIGH_IMPACT_PREDICATES
from app.schemas.claims import (
    AsrMetadata,
    CriticalFieldOutput,
    ExtractedClaim,
    GuardOutcome,
)
from app.schemas.common import Criticality, CriticalFieldType, GuardDecision, Polarity

# Criticality taxonomy (blueprint §21).
CRITICAL_CLAIM_TYPES: frozenset[str] = frozenset(
    {
        "deposit_amount",
        "repair_cost",
        "tenancy_end_date",
        "deposit_payment_date",
        "refund_commitment",
        "refund_denial",
        "responsibility_claim",
        "requested_outcome",
    }
)

FIELD_TYPE_BY_CLAIM: dict[str, CriticalFieldType] = {
    "deposit_amount": CriticalFieldType.AMOUNT,
    "repair_cost": CriticalFieldType.AMOUNT,
    "tenancy_end_date": CriticalFieldType.DATE,
    "deposit_payment_date": CriticalFieldType.DATE,
    "refund_commitment": CriticalFieldType.COMMITMENT,
    "refund_denial": CriticalFieldType.NEGATION,
    "responsibility_claim": CriticalFieldType.RESPONSIBILITY,
    "requested_outcome": CriticalFieldType.REQUESTED_OUTCOME,
    "damage_claim": CriticalFieldType.RESPONSIBILITY,
}

# Domain validation for the rental-deposit MVP.
MIN_PLAUSIBLE_AMOUNT = 1_000
MAX_PLAUSIBLE_AMOUNT = 100_000_000


class CriticalSpeechGuard:
    version = "critical-speech-guard-v1"

    def __init__(self, settings=None) -> None:
        self.settings = settings or get_settings()

    def evaluate(self, claims: list[ExtractedClaim], asr: AsrMetadata, enabled: bool = True) -> list[GuardOutcome]:
        return [self.evaluate_claim(claim, asr, enabled) for claim in claims]

    def evaluate_claim(self, claim: ExtractedClaim, asr: AsrMetadata, enabled: bool = True) -> GuardOutcome:
        reasons: list[str] = []
        field_type = FIELD_TYPE_BY_CLAIM.get(claim.type)
        is_critical = claim.type in CRITICAL_CLAIM_TYPES or claim.criticality is Criticality.HIGH

        if not enabled:
            # Ablation mode: measures what a system without the guard would let through.
            return GuardOutcome(
                claim_id=claim.claim_id,
                risk="HIGH" if is_critical else "LOW",
                decision=GuardDecision.ACCEPT_FOR_CASE,
                reasons=["guard_disabled_ablation"],
            )

        if is_critical:
            reasons.append(f"critical_{(field_type or CriticalFieldType.PERSON).value.lower()}")

        # 1. ASR confidence, thresholded per field type.
        threshold = self._threshold(field_type)
        if claim.extraction_confidence is not None and claim.extraction_confidence < threshold:
            reasons.append("low_asr_confidence")

        # 2. Attribution uncertainty — never guess a referent in a consequential claim.
        if is_critical and (claim.attribution_confidence or 1.0) < 0.7:
            reasons.append("attribution_uncertainty")
        if is_critical and claim.subject is None and claim.reported_speech:
            reasons.append("quoted_speaker_unresolved")

        # 3. Negation ambiguity on a high-impact predicate.
        # An unresolved negation on a consequential claim is exactly what flips
        # an issue from AGREED to DISPUTED. Predicate lists are a hint, not a gate.
        if claim.polarity is Polarity.UNCLEAR and (
            is_critical or claim.predicate in HIGH_IMPACT_PREDICATES
        ):
            reasons.append("negation_ambiguous")

        # 4. Domain validation.
        reasons.extend(self._validate_domain(claim))

        # 5. Cross-model disagreement (benchmark signal fed back into the guard).
        if self._models_disagree(claim, asr):
            reasons.append("cross_model_disagreement")

        decision = self._decide(is_critical, reasons)

        fields: list[CriticalFieldOutput] = []
        if decision is not GuardDecision.ACCEPT_FOR_CASE and field_type is not None:
            fields.append(
                CriticalFieldOutput(
                    field_type=field_type,
                    detected_value=self._surface_value(claim),
                    normalized_value=self._normalised_value(claim),
                    prompt_text=build_verification_prompt(claim, field_type),
                )
            )

        return GuardOutcome(
            claim_id=claim.claim_id,
            risk="HIGH" if is_critical else "MEDIUM",
            decision=decision,
            reasons=reasons,
            fields=fields,
        )

    # ── internals ──────────────────────────────────────────────────────────
    def _threshold(self, field_type: CriticalFieldType | None) -> float:
        if field_type is CriticalFieldType.AMOUNT:
            return self.settings.guard_amount_confidence_threshold
        if field_type is CriticalFieldType.DATE:
            return self.settings.guard_date_confidence_threshold
        return self.settings.guard_default_confidence_threshold

    def _validate_domain(self, claim: ExtractedClaim) -> list[str]:
        reasons: list[str] = []
        value = claim.canonical_value or {}

        if "amount_minor" in value:
            amount = int(value["amount_minor"])
            if amount < MIN_PLAUSIBLE_AMOUNT or amount > MAX_PLAUSIBLE_AMOUNT:
                reasons.append("implausible_amount")

        if claim.type in {"tenancy_end_date", "deposit_payment_date"}:
            if not value.get("iso_date") and not (value.get("day") and value.get("month")):
                reasons.append("incomplete_date")

        return reasons

    def _models_disagree(self, claim: ExtractedClaim, asr: AsrMetadata) -> bool:
        """
        Disagreement never resolves the value by majority vote. It only routes
        the field to the speaker for confirmation.
        """
        candidates = asr.cross_model_values.get(claim.type)
        if not candidates:
            return False
        return len({c for c in candidates if c}) > 1

    def _decide(self, is_critical: bool, reasons: list[str]) -> GuardDecision:
        hard_blockers = {"quoted_speaker_unresolved", "implausible_amount"}
        soft_blockers = {
            "low_asr_confidence",
            "attribution_uncertainty",
            "negation_ambiguous",
            "cross_model_disagreement",
            "incomplete_date",
        }

        if set(reasons) & hard_blockers:
            return GuardDecision.REJECT_AS_UNRESOLVED
        if is_critical and (set(reasons) & soft_blockers):
            return GuardDecision.NEEDS_CONFIRMATION
        return GuardDecision.ACCEPT_FOR_CASE

    def _surface_value(self, claim: ExtractedClaim) -> str | None:
        value = claim.canonical_value or {}
        return value.get("surface") or self._normalised_value(claim)

    def _normalised_value(self, claim: ExtractedClaim) -> str | None:
        value = claim.canonical_value or {}
        if "amount_minor" in value:
            return f"{value['amount_minor']} {value.get('currency', 'RWF')}"
        if value.get("iso_date"):
            return str(value["iso_date"])
        if value.get("day") and value.get("month"):
            return f"{value['day']:02d}-{value['month']:02d}"
        if value.get("scope"):
            return str(value["scope"])
        return None


def build_verification_prompt(claim: ExtractedClaim, field_type: CriticalFieldType) -> str:
    """
    Neutral and non-leading.
      good: "I heard the deposit amount as 150,000 RWF. Is that correct?"
      bad : "The deposit was 150,000 RWF, right?"
    """
    value = claim.canonical_value or {}

    if field_type is CriticalFieldType.AMOUNT and "amount_minor" in value:
        formatted = f"{int(value['amount_minor']):,}".replace(",", ",")
        return f"I heard the amount as {formatted} {value.get('currency', 'RWF')}. Is that correct?"

    if field_type is CriticalFieldType.DATE:
        if value.get("iso_date"):
            return f"I heard the date as {value['iso_date']}. Is that correct?"
        if value.get("day") and value.get("month"):
            return f"I heard the date as day {value['day']} of month {value['month']}. Is that correct?"
        return "I could not hear the date clearly. Which date did you mean?"

    if field_type is CriticalFieldType.COMMITMENT:
        return "I heard that you said a refund was promised. Is that what you meant?"

    if field_type is CriticalFieldType.NEGATION:
        return "I heard that you said a refund was NOT promised. Is that what you meant?"

    if field_type is CriticalFieldType.RESPONSIBILITY:
        return "I heard a statement about who is responsible for the damage. Could you repeat that part?"

    if field_type is CriticalFieldType.REQUESTED_OUTCOME:
        return "I heard what you are asking for. Could you state it once more so I record it correctly?"

    return "I am not sure I captured this detail correctly. Could you repeat it?"

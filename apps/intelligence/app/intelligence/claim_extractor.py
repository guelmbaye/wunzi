"""
Switch-Aware Claim Reconstruction.

Continuous multilingual speech → atomic, attributed, source-linked claims.
Language switching is part of the semantic structure of the account: a claim may
span several spans in different languages, and the claim context is never reset
at a language boundary.

The engine is deterministic by design. An LLM may be plugged in for semantic
parsing (see app/llm), but the state of the case is always governed by rules.
"""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass, field

from app.intelligence import lexicon
from app.intelligence.attribution import resolve as resolve_attribution
from app.intelligence.canonicalizer import extract_amounts, extract_dates
from app.intelligence.negation import detect_polarity
from app.schemas.claims import ExtractedClaim, SegmentInput, Supersession
from app.schemas.common import Criticality, Polarity

_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+|\n+")

# "…he would refund everything, mais je n'ai rien recu."
# Two clauses, two polarities. Splitting here keeps the reported promise
# POSITIVE instead of letting the second clause negate it.
_CONTRAST_SPLIT = re.compile(
    r"\s*(?:,\s*)?\b(?:but|however|mais|pourtant|cependant|ariko|nyamara)\b\s*",
    re.IGNORECASE,
)


@dataclass
class Span:
    """A semantic unit that may cross language boundaries."""

    text: str
    segment_ids: list[str]
    languages: list[str] = field(default_factory=list)
    confidences: list[float] = field(default_factory=list)
    start_ms: int = 0
    end_ms: int = 0

    @property
    def min_confidence(self) -> float | None:
        values = [c for c in self.confidences if c is not None]
        return min(values) if values else None

    @property
    def switch_count(self) -> int:
        langs = [lang for lang in self.languages if lang]
        return sum(1 for a, b in zip(langs, langs[1:]) if a != b)


def build_spans(segments: list[SegmentInput]) -> list[Span]:
    """
    Groups ASR segments into sentence-level spans WITHOUT breaking at language
    switches. A switch inside one thought stays inside one span.
    """
    if not segments:
        return []

    spans: list[Span] = []
    current = Span(text="", segment_ids=[], start_ms=segments[0].start_ms, end_ms=segments[0].end_ms)

    for segment in sorted(segments, key=lambda s: s.sequence):
        text = segment.text.strip()
        if not text:
            continue

        current.text = f"{current.text} {text}".strip()
        current.segment_ids.append(segment.segment_id)
        current.languages.append(segment.language or "")
        current.confidences.append(segment.confidence if segment.confidence is not None else None)
        current.end_ms = segment.end_ms

        # Sentence boundary — not language boundary — closes a span.
        if re.search(r"[.!?]\s*$", text):
            spans.append(current)
            current = Span(text="", segment_ids=[], start_ms=segment.end_ms, end_ms=segment.end_ms)

    if current.text:
        spans.append(current)

    # Providers differ in how much text they put in one segment. Splitting every
    # span down to clause level makes claim scope independent of that choice.
    clauses: list[Span] = []
    for span in spans:
        clauses.extend(_split_long_span(span))

    return clauses


def _split_long_span(span: Span) -> list[Span]:
    pieces: list[str] = []
    for sentence in _SENTENCE_SPLIT.split(span.text):
        for clause in _CONTRAST_SPLIT.split(sentence):
            cleaned = clause.strip(" ,;")
            if cleaned:
                pieces.append(cleaned)

    if len(pieces) <= 1:
        return [span]
    return [
        Span(
            text=piece,
            segment_ids=span.segment_ids,
            languages=span.languages,
            confidences=span.confidences,
            start_ms=span.start_ms,
            end_ms=span.end_ms,
        )
        for piece in pieces
    ]


def _contains(text: str, markers) -> bool:
    lowered = text.lower()
    return any(marker in lowered for marker in markers)


class ClaimExtractor:
    """One sentence may contain several claims. Atomicity makes comparison possible."""

    version = "claim-extraction-v1"

    def extract(
        self,
        segments: list[SegmentInput],
        party_id: str,
        party_role: str,
        transcript: str = "",
    ) -> tuple[list[ExtractedClaim], list[Supersession]]:
        spans = build_spans(segments)

        if not spans and transcript:
            spans = [Span(text=transcript, segment_ids=[], start_ms=0, end_ms=0)]

        claims: list[ExtractedClaim] = []
        for span in spans:
            claims.extend(self._claims_for_span(span, party_id, party_role))

        supersessions = self._detect_supersessions(spans, claims)
        return claims, supersessions

    # ── per-span extraction ────────────────────────────────────────────────
    def _claims_for_span(self, span: Span, party_id: str, party_role: str) -> list[ExtractedClaim]:
        text = span.text
        lowered = text.lower()
        polarity, polarity_markers = detect_polarity(text)
        attribution = resolve_attribution(text, party_role)
        claims: list[ExtractedClaim] = []

        def emit(
            claim_type: str,
            predicate: str,
            canonical_value: dict | None = None,
            criticality: Criticality = Criticality.MEDIUM,
            claim_polarity: Polarity | None = None,
            subject: str | None = None,
        ) -> None:
            claims.append(
                ExtractedClaim(
                    claim_id=f"claim_{uuid.uuid4().hex[:12]}",
                    source_party=party_id,
                    party_role=party_role,
                    subject=subject if subject is not None else attribution.subject,
                    type=claim_type,
                    predicate=predicate,
                    canonical_value=canonical_value,
                    polarity=claim_polarity or polarity,
                    criticality=criticality,
                    reported_speech=attribution.reported_speech,
                    extraction_confidence=span.min_confidence,
                    attribution_confidence=attribution.confidence,
                    source_segments=list(span.segment_ids),
                    source_text=text,
                )
            )

        amounts = extract_amounts(text)
        dates = extract_dates(text)

        deposit_context = _contains(lowered, lexicon.DEPOSIT_MARKERS)
        refund_context = _contains(lowered, lexicon.REFUND_MARKERS)
        commitment_context = _contains(lowered, lexicon.COMMITMENT_MARKERS)
        damage_context = _contains(lowered, lexicon.DAMAGE_MARKERS)
        repair_context = _contains(lowered, lexicon.REPAIR_MARKERS)
        move_out_context = _contains(lowered, lexicon.MOVE_OUT_MARKERS)
        deduction_context = _contains(lowered, lexicon.DEDUCTION_MARKERS)

        # 1. Deposit existence
        if deposit_context:
            emit("deposit_paid", "paid_deposit", {"asserted": True}, Criticality.HIGH)

        # 2. Amounts — always critical. Repair cost is distinguished from deposit.
        for amount in amounts:
            if repair_context and (deduction_context or not deposit_context):
                emit("repair_cost", "claims_repair_cost", amount.as_dict(), Criticality.HIGH)
            elif refund_context and not deposit_context:
                emit("requested_outcome", "requests_refund_amount", amount.as_dict(), Criticality.HIGH)
            else:
                emit("deposit_amount", "states_deposit_amount", amount.as_dict(), Criticality.HIGH)

        # 3. Dates
        for date in dates:
            claim_type = "tenancy_end_date" if move_out_context else "deposit_payment_date"
            predicate = "states_move_out_date" if move_out_context else "states_payment_date"
            emit(claim_type, predicate, date.as_dict(), Criticality.HIGH)

        # 4. Commitment / denial — the strongest sponsor-proof surface.
        if refund_context and commitment_context:
            claim_type = "refund_denial" if polarity is Polarity.NEGATIVE else "refund_commitment"
            emit(
                claim_type,
                "promised_refund",
                {"scope": "full_deposit" if "full" in lowered or "tout" in lowered else "deposit"},
                Criticality.HIGH,
            )

        # 5. Damage + responsibility
        if damage_context:
            emit("damage_claim", "caused_damage", {"asserted": True}, Criticality.HIGH)
            emit(
                "responsibility_claim",
                "bears_responsibility",
                {"scope": "damage"},
                Criticality.HIGH,
            )

        # 6. Requested outcome
        if _contains(lowered, lexicon.REQUESTED_OUTCOME_MARKERS):
            if deduction_context:
                scope = "deduct_repair_cost"
            elif refund_context:
                scope = "full_refund"
            else:
                scope = "unspecified"
            emit("requested_outcome", "requests_outcome", {"scope": scope}, Criticality.HIGH)

        # 7. Evidence mentions — referenced, never analysed.
        for evidence_type, markers in lexicon.EVIDENCE_MARKERS.items():
            if _contains(lowered, markers):
                emit(
                    "evidence_mention",
                    "mentions_evidence",
                    {"evidence_type": evidence_type},
                    Criticality.MEDIUM,
                )

        for claim in claims:
            if polarity_markers:
                claim.canonical_value = {**(claim.canonical_value or {}), "polarity_markers": polarity_markers}

        return claims

    # ── self-correction ────────────────────────────────────────────────────
    def _detect_supersessions(self, spans: list[Span], claims: list[ExtractedClaim]) -> list[Supersession]:
        """
        "It was the tenth… no, the twelfth of August."
        Both readings keep their provenance, but only the correction is current.
        """
        supersessions: list[Supersession] = []

        for span in spans:
            if not any(marker in span.text.lower() for marker in lexicon.CORRECTION_MARKERS):
                continue

            span_claims = [c for c in claims if set(c.source_segments) & set(span.segment_ids)]

            by_type: dict[str, list[ExtractedClaim]] = {}
            for claim in span_claims:
                by_type.setdefault(claim.type, []).append(claim)

            for grouped in by_type.values():
                if len(grouped) < 2:
                    continue
                for superseded in grouped[:-1]:
                    supersessions.append(
                        Supersession(
                            superseded_claim_id=superseded.claim_id,
                            current_claim_id=grouped[-1].claim_id,
                        )
                    )

        return supersessions

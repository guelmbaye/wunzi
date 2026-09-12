from __future__ import annotations

from pydantic import BaseModel, Field

from app.schemas.common import (
    Criticality,
    CriticalFieldType,
    GuardDecision,
    Polarity,
    VerificationStatus,
)


class SegmentInput(BaseModel):
    segment_id: str
    sequence: int
    start_ms: int
    end_ms: int
    text: str
    language: str | None = None
    confidence: float | None = None


class ClaimObject(BaseModel):
    type: str | None = None
    scope: str | None = None
    value: str | int | float | None = None
    currency: str | None = None
    iso_date: str | None = None


class ExtractedClaim(BaseModel):
    """
    Atomic, attributed proposition.
    (source_party, subject, predicate, object) — reported speech is never flattened.
    """

    claim_id: str
    source_party: str
    party_role: str | None = None
    subject: str | None = None
    type: str
    predicate: str
    canonical_value: dict | None = None
    polarity: Polarity = Polarity.POSITIVE
    certainty: str = "asserted"
    criticality: Criticality = Criticality.MEDIUM
    reported_speech: bool = False
    verification_status: VerificationStatus = VerificationStatus.UNVERIFIED
    extraction_confidence: float | None = None
    attribution_confidence: float | None = None
    source_segments: list[str] = Field(default_factory=list)
    source_text: str | None = None


class Supersession(BaseModel):
    superseded_claim_id: str
    current_claim_id: str
    reason: str = "speaker_self_correction"


class ExtractClaimsRequest(BaseModel):
    case_id: str
    party_id: str
    party_role: str
    transcript_run_id: str | None = None
    provider: str | None = None
    transcript: str = ""
    segments: list[SegmentInput] = Field(default_factory=list)
    issue_types: list[str] | None = None
    pipeline_version: str | None = None


class ExtractClaimsResponse(BaseModel):
    claims: list[ExtractedClaim] = Field(default_factory=list)
    supersessions: list[Supersession] = Field(default_factory=list)
    extraction_version: str = "claim-extraction-v1"
    engine: str = "deterministic"


class CriticalFieldOutput(BaseModel):
    field_type: CriticalFieldType
    detected_value: str | None = None
    normalized_value: str | None = None
    prompt_text: str | None = None


class GuardOutcome(BaseModel):
    claim_id: str
    risk: str
    decision: GuardDecision
    reasons: list[str] = Field(default_factory=list)
    fields: list[CriticalFieldOutput] = Field(default_factory=list)


class AsrMetadata(BaseModel):
    provider: str | None = None
    segment_confidences: list[float | None] = Field(default_factory=list)
    cross_model_values: dict[str, list[str]] = Field(default_factory=dict)


class EvaluateCriticalityRequest(BaseModel):
    case_id: str | None = None
    claims: list[ExtractedClaim] = Field(default_factory=list)
    asr_metadata: AsrMetadata = Field(default_factory=AsrMetadata)
    guard_enabled: bool = True


class EvaluateCriticalityResponse(BaseModel):
    decisions: list[GuardOutcome] = Field(default_factory=list)
    guard_version: str = "critical-speech-guard-v1"


class AnalyzeTurnRequest(ExtractClaimsRequest):
    """
    Extraction and the Critical Speech Guard in one call.

    The two steps were originally two endpoints, which meant Laravel shipped the
    full claim set out and straight back in for the guard to read. Nothing
    between them needs a database round trip, so the second hop bought latency
    and a second chance to fail without buying any auditability.

    The granular endpoints stay: the benchmark runs the guard in ablation mode
    against a fixed claim set, which needs them separate.
    """

    asr_metadata: AsrMetadata = Field(default_factory=AsrMetadata)
    guard_enabled: bool = True


class AnalyzeTurnResponse(BaseModel):
    claims: list[ExtractedClaim] = Field(default_factory=list)
    supersessions: list[Supersession] = Field(default_factory=list)
    decisions: list[GuardOutcome] = Field(default_factory=list)
    extraction_version: str = "claim-extraction-v1"
    guard_version: str = "critical-speech-guard-v1"
    engine: str = "deterministic"

from __future__ import annotations

from pydantic import BaseModel, Field


class PacketParty(BaseModel):
    party_id: str
    role: str
    display_name: str


class PacketClaim(BaseModel):
    claim_id: str
    party_role: str
    type: str
    subject: str | None = None
    predicate: str
    canonical_value: dict | None = None
    polarity: str = "POSITIVE"
    reported_speech: bool = False
    verification_status: str = "UNVERIFIED"


class PacketIssue(BaseModel):
    issue_id: str
    canonical_type: str
    status: str
    reason: str | None = None
    party_a_value: dict | None = None
    party_b_value: dict | None = None


class PacketEvidence(BaseModel):
    evidence_id: str
    type: str
    availability: str
    description: str | None = None


class GenerateCaseRequest(BaseModel):
    case_id: str
    public_reference: str
    category: str
    parties: list[PacketParty] = Field(default_factory=list)
    claims: list[PacketClaim] = Field(default_factory=list)
    issues: list[PacketIssue] = Field(default_factory=list)
    evidence: list[PacketEvidence] = Field(default_factory=list)


class ProvenanceStatement(BaseModel):
    """
    Every factual sentence must map to exactly one backing kind:
    SOURCE_CLAIM | DERIVED_RELATION | MISSING_INFORMATION | SYSTEM_METADATA
    """

    text: str
    kind: str
    claim_id: str | None = None
    issue_id: str | None = None


class GenerateCaseResponse(BaseModel):
    packet: dict
    statements: list[ProvenanceStatement] = Field(default_factory=list)
    model: str | None = None
    prompt_version: str = "case-generation-v1"

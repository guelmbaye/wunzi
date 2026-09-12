from __future__ import annotations

from pydantic import BaseModel, Field

from app.schemas.common import Criticality, EvidenceAvailability, IssueStatus


class ComparableClaim(BaseModel):
    claim_id: str
    type: str
    subject: str | None = None
    predicate: str
    canonical_value: dict | None = None
    polarity: str = "POSITIVE"
    criticality: str = "MEDIUM"
    verification_status: str = "UNVERIFIED"
    reported_speech: bool = False
    has_pending_critical_field: bool = False


class IssueOutput(BaseModel):
    canonical_type: str
    status: IssueStatus
    criticality: Criticality = Criticality.HIGH
    summary: str | None = None
    reason: str | None = None
    party_a_value: dict | None = None
    party_b_value: dict | None = None
    confidence: float | None = None
    supporting_claim_ids: list[str] = Field(default_factory=list)
    conflicting_claim_ids: list[str] = Field(default_factory=list)


class EvidenceOutput(BaseModel):
    type: str
    issue_type: str | None = None
    # A role, never an id. The intelligence service has no party ids and must
    # not appear to supply one: Laravel resolves the role to its own FK.
    mentioned_by_role: str | None = None
    description: str | None = None
    availability: EvidenceAvailability = EvidenceAvailability.MISSING


class BuildIssueGraphRequest(BaseModel):
    case_id: str
    party_a: list[ComparableClaim] = Field(default_factory=list)
    party_b: list[ComparableClaim] = Field(default_factory=list)
    issue_types: list[str] | None = None
    critical_issue_types: list[str] | None = None
    pipeline_version: str | None = None


class BuildIssueGraphResponse(BaseModel):
    issues: list[IssueOutput] = Field(default_factory=list)
    evidence: list[EvidenceOutput] = Field(default_factory=list)
    graph_version: str = "issue-graph-v1"

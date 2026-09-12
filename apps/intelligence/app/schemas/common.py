from __future__ import annotations

from enum import Enum


class Polarity(str, Enum):
    POSITIVE = "POSITIVE"
    NEGATIVE = "NEGATIVE"
    UNCLEAR = "UNCLEAR"


class Criticality(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class VerificationStatus(str, Enum):
    UNVERIFIED = "UNVERIFIED"
    CONFIRMED_BY_SPEAKER = "CONFIRMED_BY_SPEAKER"
    CORRECTED_BY_SPEAKER = "CORRECTED_BY_SPEAKER"
    UNRESOLVED = "UNRESOLVED"


class GuardDecision(str, Enum):
    ACCEPT_FOR_CASE = "ACCEPT_FOR_CASE"
    NEEDS_CONFIRMATION = "NEEDS_CONFIRMATION"
    REJECT_AS_UNRESOLVED = "REJECT_AS_UNRESOLVED"


class CriticalFieldType(str, Enum):
    AMOUNT = "AMOUNT"
    DATE = "DATE"
    PERSON = "PERSON"
    NEGATION = "NEGATION"
    COMMITMENT = "COMMITMENT"
    OWNERSHIP = "OWNERSHIP"
    RESPONSIBILITY = "RESPONSIBILITY"
    REQUESTED_OUTCOME = "REQUESTED_OUTCOME"
    CASE_REFERENCE = "CASE_REFERENCE"
    QUOTED_STATEMENT = "QUOTED_STATEMENT"


class IssueStatus(str, Enum):
    AGREED = "AGREED"
    DISPUTED = "DISPUTED"
    MISSING = "MISSING"
    UNVERIFIED = "UNVERIFIED"


class SemanticRelation(str, Enum):
    COMPATIBLE = "COMPATIBLE"
    CONFLICTING = "CONFLICTING"
    UNRELATED = "UNRELATED"
    UNCERTAIN = "UNCERTAIN"


class EvidenceAvailability(str, Enum):
    AVAILABLE = "AVAILABLE"
    MENTIONED_NOT_PROVIDED = "MENTIONED_NOT_PROVIDED"
    MISSING = "MISSING"
    DISPUTED = "DISPUTED"


class PartyRole(str, Enum):
    PARTY_A = "PARTY_A"
    PARTY_B = "PARTY_B"


# Canonical, language-independent concepts. UI language ≠ speech language ≠ graph.
CANONICAL_ISSUE_TYPES: tuple[str, ...] = (
    "deposit_exists",
    "deposit_amount",
    "deposit_payment_date",
    "tenancy_end_date",
    "property_return_date",
    "damage_exists",
    "damage_responsibility",
    "repair_cost",
    "repair_evidence",
    "refund_commitment",
    "refund_amount",
    "refund_deadline",
    "requested_outcome",
)

CRITICAL_ISSUE_TYPES: tuple[str, ...] = (
    "deposit_amount",
    "refund_commitment",
    "damage_responsibility",
    "tenancy_end_date",
    "repair_cost",
    "requested_outcome",
)

# Claim types for the Rental Deposit MVP. Deliberately tiny.
CLAIM_TYPES: tuple[str, ...] = (
    "deposit_paid",
    "deposit_amount",
    "deposit_payment_date",
    "tenancy_end_date",
    "damage_claim",
    "repair_cost",
    "refund_commitment",
    "refund_denial",
    "responsibility_claim",
    "requested_outcome",
    "evidence_mention",
)

CLAIM_TYPE_TO_ISSUE: dict[str, str] = {
    "deposit_paid": "deposit_exists",
    "deposit_amount": "deposit_amount",
    "deposit_payment_date": "deposit_payment_date",
    "tenancy_end_date": "tenancy_end_date",
    "damage_claim": "damage_exists",
    "responsibility_claim": "damage_responsibility",
    "repair_cost": "repair_cost",
    "refund_commitment": "refund_commitment",
    "refund_denial": "refund_commitment",
    "requested_outcome": "requested_outcome",
    # evidence_mention is deliberately absent: evidence is an Evidence node on
    # its own axis, not a proposition two parties assert against each other.
    # "Mentioned, not provided" must never become "both parties agree".
}

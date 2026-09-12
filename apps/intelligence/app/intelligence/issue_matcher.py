"""
Issue matching — three stages.

  1. canonical type match      deposit_amount ↔ deposit_amount
  2. deterministic comparison  numbers · dates · polarity
  3. semantic comparison       free-text propositions (LLM-assisted, optional)

The system never averages, never chooses a side, and never resolves a
disagreement. Uncertainty stays UNCERTAIN and flows to UNVERIFIED.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.intelligence.canonicalizer import canonical_amount_equal, canonical_date_equal
from app.intelligence.negation import polarity_conflicts
from app.schemas.common import CLAIM_TYPE_TO_ISSUE, SemanticRelation
from app.schemas.issues import ComparableClaim


@dataclass(frozen=True)
class MatchResult:
    relation: SemanticRelation
    reason: str
    confidence: float | None = None


def issue_type_for(claim: ComparableClaim) -> str | None:
    return CLAIM_TYPE_TO_ISSUE.get(claim.type)


def group_by_issue(claims: list[ComparableClaim]) -> dict[str, list[ComparableClaim]]:
    grouped: dict[str, list[ComparableClaim]] = {}
    for claim in claims:
        issue = issue_type_for(claim)
        if issue:
            grouped.setdefault(issue, []).append(claim)
    return grouped


def compare(a: ComparableClaim, b: ComparableClaim) -> MatchResult:
    """Deterministic first. The LLM is only consulted when rules cannot decide."""
    value_a = a.canonical_value or {}
    value_b = b.canonical_value or {}

    # 1. Amounts — exact canonical match, no partial credit. 150,000 != 50,000.
    amount_equal = canonical_amount_equal(value_a, value_b)
    if amount_equal is not None:
        return MatchResult(
            SemanticRelation.COMPATIBLE if amount_equal else SemanticRelation.CONFLICTING,
            "normalized amounts match" if amount_equal else "normalized values differ",
            1.0,
        )

    # 2. Dates.
    date_equal = canonical_date_equal(value_a, value_b)
    if date_equal is not None:
        return MatchResult(
            SemanticRelation.COMPATIBLE if date_equal else SemanticRelation.CONFLICTING,
            "normalized dates match" if date_equal else "normalized dates differ",
            1.0,
        )

    # 3. Polarity — one lost negation reverses the whole issue.
    conflict = polarity_conflicts(a.polarity, b.polarity)
    if conflict is True:
        return MatchResult(SemanticRelation.CONFLICTING, "opposite polarity on the same proposition", 1.0)
    if conflict is None:
        return MatchResult(
            SemanticRelation.UNCERTAIN,
            "polarity could not be resolved on at least one account",
            None,
        )

    # 4. Same-scope assertions.
    scope_a, scope_b = value_a.get("scope"), value_b.get("scope")
    if scope_a and scope_b and scope_a != scope_b:
        return MatchResult(SemanticRelation.CONFLICTING, "different scope asserted", 0.8)

    if a.predicate == b.predicate:
        return MatchResult(SemanticRelation.COMPATIBLE, "materially equivalent propositions", 0.9)

    return MatchResult(SemanticRelation.UNCERTAIN, "insufficient structure for deterministic comparison", None)


def best_claim(claims: list[ComparableClaim]) -> ComparableClaim | None:
    """
    Picks the claim representing a party's position on an issue: a
    speaker-verified claim outranks an unverified one. This selects a
    representative of one account, never a winner between accounts.
    """
    if not claims:
        return None

    def rank(claim: ComparableClaim) -> tuple[int, int, int]:
        verified = claim.verification_status in {"CONFIRMED_BY_SPEAKER", "CORRECTED_BY_SPEAKER"}
        # A party's own position is what they assert directly. What they report
        # the other side as saying belongs to the other side's issue, not theirs.
        direct = not claim.reported_speech
        critical = claim.criticality == "HIGH"
        return (int(verified), int(direct), int(critical))

    return sorted(claims, key=rank, reverse=True)[0]

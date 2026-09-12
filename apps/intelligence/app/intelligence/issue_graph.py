"""
Mediation Issue Graph builder.

  Party → Claim → Event → Entity → Evidence → Counterclaim
  ⇒ AGREED | DISPUTED | MISSING | UNVERIFIED     (without deciding truth)

Deterministic given claims + verification states + comparison relations.
The LLM is never asked to "build the final truth map".
"""

from __future__ import annotations

from app.intelligence.issue_matcher import best_claim, compare, group_by_issue
from app.schemas.common import (
    CRITICAL_ISSUE_TYPES,
    Criticality,
    EvidenceAvailability,
    IssueStatus,
    SemanticRelation,
)
from app.schemas.issues import (
    BuildIssueGraphRequest,
    BuildIssueGraphResponse,
    ComparableClaim,
    EvidenceOutput,
    IssueOutput,
)

# Issues whose resolution requires evidence neither party may have supplied.
REQUIRED_EVIDENCE: dict[str, str] = {
    "repair_cost": "repair_invoice",
    "damage_responsibility": "property_photos",
}

HUMAN_LABELS: dict[str, str] = {
    "deposit_exists": "Deposit existence",
    "deposit_amount": "Deposit amount",
    "deposit_payment_date": "Deposit payment date",
    "tenancy_end_date": "Tenancy end date",
    "property_return_date": "Property return date",
    "damage_exists": "Damage",
    "damage_responsibility": "Damage responsibility",
    "repair_cost": "Repair cost",
    "repair_evidence": "Repair evidence",
    "refund_commitment": "Full refund commitment",
    "refund_amount": "Refund amount",
    "refund_deadline": "Refund deadline",
    "requested_outcome": "Requested outcome",
}


class IssueGraphBuilder:
    version = "issue-graph-v1"

    def build(self, request: BuildIssueGraphRequest) -> BuildIssueGraphResponse:
        grouped_a = group_by_issue(request.party_a)
        grouped_b = group_by_issue(request.party_b)

        critical_types = tuple(request.critical_issue_types or CRITICAL_ISSUE_TYPES)
        issue_types = sorted(set(grouped_a) | set(grouped_b))

        issues: list[IssueOutput] = [
            self._build_issue(
                issue_type,
                grouped_a.get(issue_type, []),
                grouped_b.get(issue_type, []),
                critical_types,
            )
            for issue_type in issue_types
        ]

        evidence = self._collect_evidence(request, {i.canonical_type for i in issues})
        issues.extend(self._missing_evidence_issues(issues, evidence, critical_types))

        return BuildIssueGraphResponse(issues=issues, evidence=evidence, graph_version=self.version)

    # ── one issue ──────────────────────────────────────────────────────────
    def _build_issue(
        self,
        issue_type: str,
        claims_a: list[ComparableClaim],
        claims_b: list[ComparableClaim],
        critical_types: tuple[str, ...],
    ) -> IssueOutput:
        criticality = Criticality.HIGH if issue_type in critical_types else Criticality.MEDIUM
        label = HUMAN_LABELS.get(issue_type, issue_type.replace("_", " "))

        representative_a = best_claim(claims_a)
        representative_b = best_claim(claims_b)

        # 1. Consequential uncertainty must survive into the mediator case and
        #    must never be forced into agreed/disputed.
        #
        #    Only the representatives count here. A party quoting the other side
        #    ("he says there is damage") is not that party's own position, so an
        #    unresolved referent inside the quote must not blank out an issue the
        #    two accounts genuinely disagree on.
        representatives = [c for c in (representative_a, representative_b) if c is not None]
        pending = [c for c in representatives if c.has_pending_critical_field]
        if pending and issue_type in critical_types:
            return IssueOutput(
                canonical_type=issue_type,
                status=IssueStatus.UNVERIFIED,
                criticality=criticality,
                summary=f"{label} — not yet verified.",
                reason="a critical claim on this issue is still awaiting speaker confirmation",
                party_a_value=representative_a.canonical_value if representative_a else None,
                party_b_value=representative_b.canonical_value if representative_b else None,
                supporting_claim_ids=[c.claim_id for c in claims_a + claims_b],
            )

        # 2. Only one account addresses this issue.
        if not claims_a or not claims_b:
            present = claims_a or claims_b
            side = "Party A" if claims_a else "Party B"
            return IssueOutput(
                canonical_type=issue_type,
                status=IssueStatus.MISSING,
                criticality=criticality,
                summary=f"{label} — only one account addresses this.",
                reason=f"{side} states a position; the other account provides no information",
                party_a_value=representative_a.canonical_value if representative_a else None,
                party_b_value=representative_b.canonical_value if representative_b else None,
                supporting_claim_ids=[c.claim_id for c in present],
            )

        # 3. Deterministic then semantic comparison.
        match = compare(representative_a, representative_b)  # type: ignore[arg-type]

        status = {
            SemanticRelation.COMPATIBLE: IssueStatus.AGREED,
            SemanticRelation.CONFLICTING: IssueStatus.DISPUTED,
            SemanticRelation.UNCERTAIN: IssueStatus.UNVERIFIED,
            SemanticRelation.UNRELATED: IssueStatus.UNVERIFIED,
        }[match.relation]

        summary = {
            IssueStatus.AGREED: f"{label} — both accounts align.",
            IssueStatus.DISPUTED: f"{label} — the accounts differ.",
            IssueStatus.UNVERIFIED: f"{label} — not yet established.",
        }.get(status, label)

        return IssueOutput(
            canonical_type=issue_type,
            status=status,
            criticality=criticality,
            summary=summary,
            reason=match.reason,
            confidence=match.confidence,
            party_a_value=representative_a.canonical_value if representative_a else None,
            party_b_value=representative_b.canonical_value if representative_b else None,
            supporting_claim_ids=[c.claim_id for c in (claims_a + claims_b)]
            if status is IssueStatus.AGREED
            else [],
            conflicting_claim_ids=[c.claim_id for c in (claims_a + claims_b)]
            if status is IssueStatus.DISPUTED
            else [],
        )

    # ── evidence ───────────────────────────────────────────────────────────
    def _collect_evidence(
        self, request: BuildIssueGraphRequest, issue_types: set[str]
    ) -> list[EvidenceOutput]:
        evidence: list[EvidenceOutput] = []
        seen: set[tuple[str, str | None]] = set()

        for party_label, claims in (("PARTY_A", request.party_a), ("PARTY_B", request.party_b)):
            for claim in claims:
                value = claim.canonical_value or {}
                evidence_type = value.get("evidence_type")
                if not evidence_type:
                    continue
                key = (evidence_type, party_label)
                if key in seen:
                    continue
                seen.add(key)
                evidence.append(
                    EvidenceOutput(
                        type=evidence_type,
                        issue_type="repair_evidence" if evidence_type == "repair_invoice" else None,
                        mentioned_by_role=party_label,
                        description=f"Mentioned by {party_label.replace('_', ' ').title()}.",
                        # "mentioned, not provided" is not "does not exist".
                        availability=EvidenceAvailability.MENTIONED_NOT_PROVIDED,
                    )
                )

        for issue_type, evidence_type in REQUIRED_EVIDENCE.items():
            if issue_type in issue_types and not any(e.type == evidence_type for e in evidence):
                evidence.append(
                    EvidenceOutput(
                        type=evidence_type,
                        issue_type=issue_type,
                        description="Required to understand this issue; not supplied by either account.",
                        availability=EvidenceAvailability.MISSING,
                    )
                )

        return evidence

    def _missing_evidence_issues(
        self,
        issues: list[IssueOutput],
        evidence: list[EvidenceOutput],
        critical_types: tuple[str, ...],
    ) -> list[IssueOutput]:
        existing = {issue.canonical_type for issue in issues}
        extra: list[IssueOutput] = []

        for item in evidence:
            if item.availability not in {
                EvidenceAvailability.MISSING,
                EvidenceAvailability.MENTIONED_NOT_PROVIDED,
            }:
                continue
            if item.type != "repair_invoice" or "repair_evidence" in existing:
                continue

            extra.append(
                IssueOutput(
                    canonical_type="repair_evidence",
                    status=IssueStatus.MISSING,
                    criticality=Criticality.HIGH
                    if "repair_evidence" in critical_types
                    else Criticality.MEDIUM,
                    summary="Repair evidence — mentioned, not provided.",
                    reason="no repair invoice has been supplied",
                )
            )
            existing.add("repair_evidence")

        return extra

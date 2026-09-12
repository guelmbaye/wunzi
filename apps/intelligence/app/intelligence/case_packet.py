"""
Case Packet generator.

The generator receives structured objects only — claims, issues, verification
states, evidence references — never uncontrolled speculation. Every factual
sentence it emits carries a provenance kind and, where applicable, the id of the
claim or issue that backs it.
"""

from __future__ import annotations

from app.intelligence.hallucination import HallucinationValidator
from app.intelligence.issue_graph import HUMAN_LABELS
from app.intelligence.neutrality import assert_payload
from app.schemas.packet import (
    GenerateCaseRequest,
    GenerateCaseResponse,
    PacketClaim,
    PacketIssue,
    ProvenanceStatement,
)

VERIFICATION_LABELS = {
    "UNVERIFIED": "Not yet verified",
    "CONFIRMED_BY_SPEAKER": "Speaker confirmed",
    "CORRECTED_BY_SPEAKER": "Corrected by speaker",
    "UNRESOLVED": "Unresolved",
}


class CasePacketGenerator:
    prompt_version = "case-generation-v1"

    def __init__(self) -> None:
        self.validator = HallucinationValidator()

    def generate(self, request: GenerateCaseRequest) -> GenerateCaseResponse:
        statements: list[ProvenanceStatement] = []

        by_status: dict[str, list[PacketIssue]] = {"AGREED": [], "DISPUTED": [], "MISSING": [], "UNVERIFIED": []}
        for issue in request.issues:
            by_status.setdefault(issue.status, []).append(issue)

        packet = {
            "case_reference": request.public_reference,
            "category": request.category,
            "status_label": "Ready for Human Mediator",
            "ai_assisted": True,
            "parties": [{"role": p.role, "display_name": p.display_name} for p in request.parties],
            "agreed": [self._render_issue(i, statements) for i in by_status["AGREED"]],
            "disputed": [self._render_issue(i, statements) for i in by_status["DISPUTED"]],
            "missing_information": [self._render_issue(i, statements) for i in by_status["MISSING"]],
            "unverified_information": [self._render_issue(i, statements) for i in by_status["UNVERIFIED"]],
            "party_a_claims": self._render_claims(request.claims, "PARTY_A", statements),
            "party_b_claims": self._render_claims(request.claims, "PARTY_B", statements),
            "requested_outcomes": self._render_requested_outcomes(request.claims, statements),
            "evidence_gaps": self._render_evidence(request, statements),
            "human_boundary": (
                "WUNZI prepared this case. The mediator remains responsible for "
                "interpretation, dialogue and resolution."
            ),
        }

        statements.append(
            ProvenanceStatement(
                text=f"Case {request.public_reference} was prepared with AI assistance and is ready for mediator review.",
                kind="SYSTEM_METADATA",
            )
        )

        # Two independent guards before the packet leaves the service.
        assert_payload(packet)
        self.validator.assert_backed(
            statements,
            {c.claim_id for c in request.claims},
            {i.issue_id for i in request.issues},
        )

        return GenerateCaseResponse(
            packet=packet,
            statements=statements,
            model="deterministic-template",
            prompt_version=self.prompt_version,
        )

    # ── renderers ──────────────────────────────────────────────────────────
    def _render_issue(self, issue: PacketIssue, statements: list[ProvenanceStatement]) -> dict:
        label = HUMAN_LABELS.get(issue.canonical_type, issue.canonical_type.replace("_", " "))

        text = {
            "AGREED": f"Both accounts align on {label.lower()}.",
            "DISPUTED": f"The accounts differ on {label.lower()}.",
            "MISSING": f"No information was provided about {label.lower()} by both accounts.",
            "UNVERIFIED": f"{label} remains unverified.",
        }.get(issue.status, f"{label}: {issue.status}.")

        statements.append(
            ProvenanceStatement(text=text, kind="DERIVED_RELATION", issue_id=issue.issue_id)
            if issue.status != "MISSING"
            else ProvenanceStatement(text=text, kind="MISSING_INFORMATION", issue_id=issue.issue_id)
        )

        return {
            "issue_id": issue.issue_id,
            "type": issue.canonical_type,
            "label": label,
            "status": issue.status,
            "statement": text,
            "reason": issue.reason,
            "party_a_value": issue.party_a_value,
            "party_b_value": issue.party_b_value,
        }

    def _render_claims(
        self, claims: list[PacketClaim], role: str, statements: list[ProvenanceStatement]
    ) -> list[dict]:
        rendered: list[dict] = []

        for claim in claims:
            if claim.party_role != role:
                continue

            text = self._neutral_sentence(claim)
            statements.append(
                ProvenanceStatement(text=text, kind="SOURCE_CLAIM", claim_id=claim.claim_id)
            )

            rendered.append(
                {
                    "claim_id": claim.claim_id,
                    "type": claim.type,
                    "statement": text,
                    "value": claim.canonical_value,
                    "polarity": claim.polarity,
                    "reported_speech": claim.reported_speech,
                    "verification": VERIFICATION_LABELS.get(
                        claim.verification_status, claim.verification_status
                    ),
                    "audio_source_available": True,
                }
            )

        return rendered

    def _render_requested_outcomes(
        self, claims: list[PacketClaim], statements: list[ProvenanceStatement]
    ) -> dict:
        outcomes: dict[str, str | None] = {"PARTY_A": None, "PARTY_B": None}

        for claim in claims:
            if claim.type != "requested_outcome":
                continue
            scope = (claim.canonical_value or {}).get("scope", "unspecified")
            text = f"{self._role_label(claim.party_role)} states a requested outcome: {scope.replace('_', ' ')}."
            outcomes[claim.party_role] = text
            statements.append(
                ProvenanceStatement(text=text, kind="SOURCE_CLAIM", claim_id=claim.claim_id)
            )

        return outcomes

    def _render_evidence(
        self, request: GenerateCaseRequest, statements: list[ProvenanceStatement]
    ) -> list[dict]:
        rendered: list[dict] = []

        for evidence in request.evidence:
            label = evidence.type.replace("_", " ")
            text = (
                f"{label.capitalize()} was mentioned but not provided."
                if evidence.availability == "MENTIONED_NOT_PROVIDED"
                else f"No {label} was provided."
            )
            statements.append(ProvenanceStatement(text=text, kind="MISSING_INFORMATION"))
            rendered.append(
                {
                    "evidence_id": evidence.evidence_id,
                    "type": evidence.type,
                    "availability": evidence.availability,
                    "statement": text,
                }
            )

        return rendered

    # ── helpers ────────────────────────────────────────────────────────────
    def _neutral_sentence(self, claim: PacketClaim) -> str:
        speaker = self._role_label(claim.party_role)
        subject = {"party_a": "Party A", "party_b": "Party B"}.get(claim.subject or "", None)
        negation = " did not " if claim.polarity == "NEGATIVE" else " "
        predicate = claim.predicate.replace("_", " ")
        value = self._format_value(claim.canonical_value)

        if claim.reported_speech and subject and subject != speaker:
            base = f"{speaker} states that {subject}{negation}{predicate}"
        else:
            base = f"{speaker} states{negation}{predicate}"

        return f"{base} ({value})." if value else f"{base}."

    def _format_value(self, value: dict | None) -> str | None:
        if not value:
            return None
        if "amount_minor" in value:
            return f"{int(value['amount_minor']):,} {value.get('currency', 'RWF')}".replace(",", " ")
        if value.get("iso_date"):
            return str(value["iso_date"])
        if value.get("day") and value.get("month"):
            return f"day {value['day']}, month {value['month']}"
        if value.get("scope"):
            return str(value["scope"]).replace("_", " ")
        return None

    def _role_label(self, role: str) -> str:
        return "Party A" if role == "PARTY_A" else "Party B"

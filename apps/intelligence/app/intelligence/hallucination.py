"""
Hallucination guard.

Every factual statement in a case packet must belong to exactly one of:
  SOURCE_CLAIM | DERIVED_RELATION | MISSING_INFORMATION | SYSTEM_METADATA

A generated fact with no provenance is forbidden. Example rejection:
"The property was damaged before the tenant arrived." — if no source says this,
it does not enter the packet.
"""

from __future__ import annotations

from app.schemas.packet import ProvenanceStatement

ALLOWED_KINDS: frozenset[str] = frozenset(
    {"SOURCE_CLAIM", "DERIVED_RELATION", "MISSING_INFORMATION", "SYSTEM_METADATA"}
)

# These kinds describe the absence of information or the system itself, so they
# do not need to point at a claim or an issue.
SELF_BACKED_KINDS: frozenset[str] = frozenset({"MISSING_INFORMATION", "SYSTEM_METADATA"})


class HallucinationViolation(ValueError):
    def __init__(self, statements: list[str]) -> None:
        self.statements = statements
        super().__init__(f"{len(statements)} generated statement(s) have no provenance backing.")


class HallucinationValidator:
    def unbacked(
        self,
        statements: list[ProvenanceStatement],
        claim_ids: set[str],
        issue_ids: set[str],
    ) -> list[str]:
        offenders: list[str] = []

        for statement in statements:
            if statement.kind not in ALLOWED_KINDS:
                offenders.append(statement.text)
                continue

            if statement.kind in SELF_BACKED_KINDS:
                continue

            claim_ok = statement.claim_id is not None and statement.claim_id in claim_ids
            issue_ok = statement.issue_id is not None and statement.issue_id in issue_ids

            if not claim_ok and not issue_ok:
                offenders.append(statement.text)

        return offenders

    def assert_backed(
        self,
        statements: list[ProvenanceStatement],
        claim_ids: set[str],
        issue_ids: set[str],
    ) -> None:
        offenders = self.unbacked(statements, claim_ids, issue_ids)
        if offenders:
            raise HallucinationViolation(offenders)

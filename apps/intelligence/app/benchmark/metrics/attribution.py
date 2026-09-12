"""
Claim Attribution Accuracy (CAA) and Wrong-Party Attribution Rate (WPAR).

WPAR is a safety metric. Attaching Party A's admission to Party B is worse than
a transcription error: it manufactures a false accusation. It is reported
separately and never averaged away inside a general accuracy number.
"""

from __future__ import annotations


def _identity(claim: dict) -> tuple:
    """
    Pairs a produced claim with its ground-truth counterpart. Type alone is too
    coarse — several claims share a type within one account — so the canonical
    value and polarity are part of the identity. Claims that cannot be paired are
    excluded rather than scored against an arbitrary partner.
    """
    value = claim.get("canonical_value") or {}
    return (
        claim.get("type"),
        claim.get("polarity", "POSITIVE"),
        value.get("amount_minor"),
        value.get("iso_date") or (value.get("day"), value.get("month")),
        value.get("scope"),
        value.get("evidence_type"),
    )


def attribution_scores(expected: list[dict], produced: list[dict]) -> dict[str, float]:
    index: dict[tuple, dict] = {_identity(c): c for c in expected}

    comparable = 0
    correct = 0
    wrong_party = 0

    for claim in produced:
        reference = index.get(_identity(claim))
        if reference is None:
            continue

        comparable += 1

        same_source = claim.get("party_role") == reference.get("party_role")
        same_subject = (claim.get("subject") or None) == (reference.get("subject") or None)
        same_reporting = bool(claim.get("reported_speech")) == bool(reference.get("reported_speech"))

        if same_source and same_subject and same_reporting:
            correct += 1
        elif not same_source or not same_subject:
            wrong_party += 1

    return {
        "claim_attribution_accuracy": correct / comparable if comparable else 0.0,
        "wrong_party_attribution_rate": wrong_party / comparable if comparable else 0.0,
        "comparable_claims": float(comparable),
    }

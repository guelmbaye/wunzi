"""Claim-level precision / recall / F1 against annotated ground truth."""

from __future__ import annotations


def _key(claim: dict) -> tuple:
    value = claim.get("canonical_value") or {}
    return (
        claim.get("type"),
        claim.get("polarity", "POSITIVE"),
        value.get("amount_minor") or value.get("value"),
        value.get("iso_date"),
        value.get("scope"),
    )


def claim_scores(expected: list[dict], produced: list[dict]) -> dict[str, float]:
    expected_keys = [_key(c) for c in expected]
    produced_keys = [_key(c) for c in produced]

    remaining = list(expected_keys)
    true_positives = 0
    for key in produced_keys:
        if key in remaining:
            remaining.remove(key)
            true_positives += 1

    precision = true_positives / len(produced_keys) if produced_keys else 0.0
    recall = true_positives / len(expected_keys) if expected_keys else 0.0
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) else 0.0

    return {"precision": precision, "recall": recall, "f1": f1}

"""
Safety and escalation metrics.

  CEAR  Critical Error Absorption Rate — critical ASR errors caught before the
        Issue Graph, i.e. errors that never reached the mediator
  UVVR  Unverified Value Visibility Rate — uncertainty that stayed visible
        instead of being silently resolved
  SRR   Silent Resolution Rate — the anti-metric: a wrong value that entered the
        case with no flag at all. Target: zero.
"""

from __future__ import annotations


def critical_error_absorption_rate(critical_errors: int, absorbed: int) -> float:
    return absorbed / critical_errors if critical_errors else 1.0


def unverified_value_visibility_rate(uncertain_values: int, surfaced: int) -> float:
    return surfaced / uncertain_values if uncertain_values else 1.0


def silent_resolution_rate(wrong_values_entering_case: int, unflagged: int) -> float:
    return unflagged / wrong_values_entering_case if wrong_values_entering_case else 0.0


def clarification_scores(
    true_positives: int, false_positives: int, false_negatives: int
) -> dict[str, float]:
    """
    Precision guards mediator patience; recall guards mediation integrity.
    A system that asks about everything is not safe, it is unusable.
    """
    precision = true_positives / (true_positives + false_positives) if (true_positives + false_positives) else 0.0
    recall = true_positives / (true_positives + false_negatives) if (true_positives + false_negatives) else 0.0

    return {
        "clarification_precision": precision,
        "clarification_recall": recall,
        "clarification_burden": float(true_positives + false_positives),
    }

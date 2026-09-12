"""
Issue Graph fidelity and the headline product metric.

  Issue Macro-F1  — per-status quality across AGREED/DISPUTED/MISSING/UNVERIFIED
  CMSR            — Correct Mediation State Rate: the fraction of cases whose
                    final mediation state is entirely correct

CMSR is deliberately unforgiving. A case is either right or it is not: a mediator
handed one wrong DISPUTED among six correct issues still walks into the room with
a false conflict.
"""

from __future__ import annotations

STATUSES = ("AGREED", "DISPUTED", "MISSING", "UNVERIFIED")


def issue_macro_f1(expected: dict[str, str], produced: dict[str, str]) -> float:
    scores: list[float] = []

    for status in STATUSES:
        tp = sum(1 for k, v in produced.items() if v == status and expected.get(k) == status)
        fp = sum(1 for k, v in produced.items() if v == status and expected.get(k) != status)
        fn = sum(1 for k, v in expected.items() if v == status and produced.get(k) != status)

        if tp == 0 and fp == 0 and fn == 0:
            continue  # status absent from both: it would only dilute the average

        precision = tp / (tp + fp) if (tp + fp) else 0.0
        recall = tp / (tp + fn) if (tp + fn) else 0.0
        scores.append((2 * precision * recall / (precision + recall)) if (precision + recall) else 0.0)

    return sum(scores) / len(scores) if scores else 0.0


def issue_state_accuracy(expected: dict[str, str], produced: dict[str, str]) -> float:
    if not expected:
        return 1.0
    correct = sum(1 for key, status in expected.items() if produced.get(key) == status)
    return correct / len(expected)


def case_state_correct(expected: dict[str, str], produced: dict[str, str]) -> bool:
    """All-or-nothing. This is what CMSR counts."""
    return bool(expected) and all(produced.get(k) == v for k, v in expected.items())


def correct_mediation_state_rate(case_results: list[bool]) -> float:
    return sum(1 for correct in case_results if correct) / len(case_results) if case_results else 0.0

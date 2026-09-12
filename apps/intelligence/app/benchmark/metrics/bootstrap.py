"""
Bootstrap confidence intervals.

A small evaluation set without intervals invites a fair objection: "is that
difference real, or noise?" Reporting a CI is how the claim survives scrutiny.
"""

from __future__ import annotations

import random
from statistics import mean


def bootstrap_ci(
    values: list[float],
    samples: int = 1000,
    confidence: float = 0.95,
    seed: int = 20260915,
) -> tuple[float, float, float]:
    """Returns (point_estimate, ci_low, ci_high). Deterministic for a given seed."""
    clean = [v for v in values if v is not None]
    if not clean:
        return (0.0, 0.0, 0.0)
    if len(clean) == 1:
        return (clean[0], clean[0], clean[0])

    rng = random.Random(seed)
    size = len(clean)
    estimates = [mean(rng.choice(clean) for _ in range(size)) for _ in range(samples)]
    estimates.sort()

    tail = (1.0 - confidence) / 2.0
    low = estimates[int(tail * samples)]
    high = estimates[min(int((1.0 - tail) * samples), samples - 1)]

    return (mean(clean), low, high)


def paired_difference_ci(
    baseline: list[float],
    candidate: list[float],
    samples: int = 1000,
    confidence: float = 0.95,
    seed: int = 20260915,
) -> tuple[float, float, float]:
    """
    Paired bootstrap over the same clips. Pairing matters: both providers saw
    identical audio, so per-clip differences carry the signal.
    """
    pairs = [(b, c) for b, c in zip(baseline, candidate) if b is not None and c is not None]
    if not pairs:
        return (0.0, 0.0, 0.0)

    differences = [c - b for b, c in pairs]
    return bootstrap_ci(differences, samples, confidence, seed)

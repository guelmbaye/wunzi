"""
Sponsor Outcome Delta.

    SOD = CMSR(Sahara) − max CMSR(all other providers)

Measured on identical audio with the entire downstream pipeline frozen. This is
an internal discipline metric, not an official Intron criterion: it exists so the
team is honest with itself about whether the sponsor model is genuinely load-bearing
or merely present in the architecture diagram.

Interpretation is explicitly two-sided. If the delta is small, the honest reading
is that the mediation layer absorbs ASR differences well, and the answer is to
strengthen the code-switch difficulty of the evaluation set — not to quietly
delete the metric.
"""

from __future__ import annotations

from dataclasses import dataclass

STRONG_GO = 10.0
CONDITIONAL_GO = 5.0


@dataclass(frozen=True)
class SponsorDelta:
    sponsor: str
    sponsor_cmsr: float
    best_competitor: str | None
    best_competitor_cmsr: float
    delta_points: float

    @property
    def verdict(self) -> str:
        if self.delta_points >= STRONG_GO:
            return "STRONG_GO"
        if self.delta_points >= CONDITIONAL_GO:
            return "CONDITIONAL_GO"
        if self.delta_points > 0:
            return "WEAK_DIFFERENTIATION"
        return "NO_DIFFERENTIATION"

    @property
    def narrative(self) -> str:
        if self.delta_points >= CONDITIONAL_GO:
            return (
                f"On identical audio, {self.sponsor} produced the correct mediation state "
                f"in {self.sponsor_cmsr:.0f}% of cases against {self.best_competitor_cmsr:.0f}% "
                f"for the strongest alternative. Only the ASR provider changed."
            )
        return (
            "The mediation layer absorbed most ASR differences on this evaluation set. "
            "The correct response is a harder code-switch split, not a softer metric."
        )

    def as_dict(self) -> dict:
        return {
            "sponsor": self.sponsor,
            "sponsor_cmsr": self.sponsor_cmsr,
            "best_competitor": self.best_competitor,
            "best_competitor_cmsr": self.best_competitor_cmsr,
            "delta_points": self.delta_points,
            "verdict": self.verdict,
            "narrative": self.narrative,
        }


def sponsor_outcome_delta(cmsr_by_provider: dict[str, float], sponsor: str = "sahara") -> SponsorDelta:
    sponsor_score = cmsr_by_provider.get(sponsor, 0.0)
    competitors = {k: v for k, v in cmsr_by_provider.items() if k != sponsor}

    best_name = max(competitors, key=competitors.get) if competitors else None
    best_score = competitors[best_name] if best_name else 0.0

    return SponsorDelta(
        sponsor=sponsor,
        sponsor_cmsr=sponsor_score,
        best_competitor=best_name,
        best_competitor_cmsr=best_score,
        delta_points=sponsor_score - best_score,
    )

"""
Benchmark runner.

  Same audio.
  Same claim engine, same guard, same Issue Graph logic, same prompts.
  Only the ASR provider changes.

Everything downstream of transcription is frozen for the duration of a run. That
freeze is what turns the sponsor comparison from a story into a measurement.
"""

from __future__ import annotations

import asyncio
import logging
import subprocess
from pathlib import Path

from app.asr.base import AsrError
from app.asr.registry import get_provider
from app.benchmark.dataset import Clip, Dataset, Scenario, load_dataset
from app.benchmark.metrics.attribution import attribution_scores
from app.benchmark.metrics.bootstrap import bootstrap_ci
from app.benchmark.metrics.claims import claim_scores
from app.benchmark.metrics.critical_facts import (
    critical_fact_accuracy,
    critical_fact_detail,
    negation_preservation,
)
from app.benchmark.metrics.issues import (
    case_state_correct,
    correct_mediation_state_rate,
    issue_macro_f1,
    issue_state_accuracy,
)
from app.benchmark.metrics.safety import (
    clarification_scores,
    critical_error_absorption_rate,
    silent_resolution_rate,
    unverified_value_visibility_rate,
)
from app.benchmark.metrics.sponsor_delta import sponsor_outcome_delta
from app.benchmark.metrics.wer import character_error_rate, word_error_rate
from app.config import get_settings
from app.intelligence.claim_extractor import ClaimExtractor
from app.intelligence.criticality import CriticalSpeechGuard
from app.intelligence.issue_graph import IssueGraphBuilder
from app.logging_setup import log_event
from app.schemas.benchmark import BenchmarkRunRequest, BenchmarkRunResponse, MetricRow, ObservationRow
from app.schemas.claims import AsrMetadata, SegmentInput
from app.schemas.issues import BuildIssueGraphRequest, ComparableClaim
from app.schemas.speech import TranscriptionConfig

logger = logging.getLogger("wunzi.benchmark")


class BenchmarkRunner:
    def __init__(self, dataset: Dataset | None = None, root: Path | None = None) -> None:
        settings = get_settings()
        self.root = Path(root or settings.benchmark_root)
        self.dataset = dataset or load_dataset(self.root, settings.dataset_version)
        self.extractor = ClaimExtractor()
        self.guard = CriticalSpeechGuard()
        self.graph = IssueGraphBuilder()

    async def run(self, request: BenchmarkRunRequest) -> BenchmarkRunResponse:
        scenarios = self.dataset.split(request.split) or self.dataset.scenarios
        observations: list[ObservationRow] = []

        for provider_name in request.providers:
            for scenario in scenarios:
                observations.append(await self._evaluate(provider_name, scenario, request))

        metrics = self._aggregate(observations, request)
        cmsr = {
            row.provider: row.value
            for row in metrics
            if row.metric == "correct_mediation_state_rate"
        }
        delta = sponsor_outcome_delta(cmsr)

        log_event(
            logger,
            "benchmark_completed",
            split=request.split,
            providers=request.providers,
            scenarios=len(scenarios),
            sponsor_outcome_delta=delta.delta_points,
            verdict=delta.verdict,
        )

        placeholder_used = any(o.used_placeholder_fixture for o in observations)

        return BenchmarkRunResponse(
            run_id=request.run_id,
            dataset_version=self.dataset.version,
            split=request.split,
            metrics=metrics,
            observations=observations,
            summary={
                "scenario_count": len(scenarios),
                "guard_enabled": request.guard_enabled,
                "sponsor_delta": delta.as_dict(),
                "frozen_downstream": True,
                "placeholder_fixtures_used": placeholder_used,
            },
            sponsor_outcome_delta=delta.delta_points,
            best_competitor=delta.best_competitor,
            git_commit=_git_commit(),
            publishable=not placeholder_used,
            publishability_note=(
                "At least one clip was scored from a placeholder fixture rather than a captured "
                "provider output. These numbers are pipeline smoke-test values and must not be "
                "reported as benchmark results."
                if placeholder_used
                else None
            ),
        )

    # ── one scenario × one provider ────────────────────────────────────────
    async def _evaluate(
        self, provider_name: str, scenario: Scenario, request: BenchmarkRunRequest
    ) -> ObservationRow:
        settings = get_settings()
        transcripts: dict[str, str] = {}
        clip_segments: dict[str, list[SegmentInput]] = {}
        confidences: list[float | None] = []
        provider_failed = False
        used_placeholder = False

        for clip in scenario.clips:
            try:
                provider = get_provider(provider_name, settings)
                transcript = await provider.transcribe(
                    self._audio_uri(clip), TranscriptionConfig()
                )
                transcripts[clip.clip_id] = transcript.text
                clip_segments[clip.clip_id] = [
                    SegmentInput(
                        segment_id=f"{clip.clip_id}-{index}",
                        sequence=index,
                        start_ms=segment.start_ms,
                        end_ms=segment.end_ms,
                        text=segment.text,
                        language=segment.language,
                        confidence=segment.confidence,
                    )
                    for index, segment in enumerate(transcript.segments)
                ]
                confidences.extend(s.confidence for s in transcript.segments)
                used_placeholder = used_placeholder or transcript.is_placeholder
            except (AsrError, KeyError) as exc:
                # A failed provider is recorded as a failure, never substituted.
                provider_failed = True
                transcripts[clip.clip_id] = ""
                log_event(
                    logger,
                    "benchmark_provider_failed",
                    provider=provider_name,
                    clip=clip.clip_id,
                    error=str(exc),
                )

        reference = " ".join(c.reference_transcript for c in scenario.clips).strip()
        hypothesis = " ".join(transcripts.values()).strip()

        party_claims: dict[str, list] = {"PARTY_A": [], "PARTY_B": []}
        pending_by_claim: set[str] = set()

        for clip in scenario.clips:
            text = transcripts.get(clip.clip_id, "")
            segments = clip_segments.get(clip.clip_id) or [
                SegmentInput(
                    segment_id=f"{clip.clip_id}-0",
                    sequence=0,
                    start_ms=0,
                    end_ms=clip.duration_ms or 0,
                    text=text,
                )
            ]

            claims, _ = self.extractor.extract(
                segments=segments,
                party_id=f"{scenario.scenario_id}-{clip.party_role}",
                party_role=clip.party_role,
                transcript=text,
            )

            outcomes = self.guard.evaluate(
                claims,
                AsrMetadata(provider=provider_name, segment_confidences=confidences),
                enabled=request.guard_enabled,
            )
            pending_by_claim |= {
                o.claim_id for o in outcomes if o.decision != "ACCEPT_FOR_CASE"
            }

            party_claims[clip.party_role].extend(claims)

        graph = self.graph.build(
            BuildIssueGraphRequest(
                case_id=scenario.scenario_id,
                party_a=[self._comparable(c, pending_by_claim) for c in party_claims["PARTY_A"]],
                party_b=[self._comparable(c, pending_by_claim) for c in party_claims["PARTY_B"]],
            )
        )

        produced_states = {issue.canonical_type: issue.status.value for issue in graph.issues}
        expected_states = scenario.expected_issue_states

        expected_claims = [c for claims in scenario.expected_claims.values() for c in claims]
        produced_claims = [
            c.model_dump() for claims in party_claims.values() for c in claims
        ]

        return ObservationRow(
            clip_id=scenario.clips[0].clip_id if scenario.clips else scenario.scenario_id,
            scenario_id=scenario.scenario_id,
            provider=provider_name,
            transcript=hypothesis,
            critical_facts=critical_fact_detail(reference, hypothesis),
            claims=produced_claims,
            issue_states=produced_states,
            expected_issue_states=expected_states,
            case_state_correct=case_state_correct(expected_states, produced_states),
            error_taxonomy=self._classify(reference, hypothesis, expected_states, produced_states),
            provider_failed=provider_failed,
            used_placeholder_fixture=used_placeholder,
            latency_ms=None,
        )

    # ── aggregation ────────────────────────────────────────────────────────
    def _aggregate(
        self, observations: list[ObservationRow], request: BenchmarkRunRequest
    ) -> list[MetricRow]:
        rows: list[MetricRow] = []
        by_provider: dict[str, list[ObservationRow]] = {}
        for observation in observations:
            by_provider.setdefault(observation.provider, []).append(observation)

        for provider, items in by_provider.items():
            scenario_lookup = {s.scenario_id: s for s in self.dataset.scenarios}

            wer_values: list[float] = []
            cer_values: list[float] = []
            cfa_values: list[float] = []
            negation_values: list[float] = []
            caa_values: list[float] = []
            wpar_values: list[float] = []
            claim_f1_values: list[float] = []
            macro_f1_values: list[float] = []
            issue_accuracy_values: list[float] = []
            case_results: list[bool] = []

            critical_errors = absorbed = uncertain = surfaced = wrong_entering = unflagged = 0

            for observation in items:
                scenario = scenario_lookup.get(observation.scenario_id)
                if scenario is None:
                    continue

                reference = " ".join(c.reference_transcript for c in scenario.clips).strip()
                hypothesis = observation.transcript or ""

                wer_values.append(word_error_rate(reference, hypothesis))
                cer_values.append(character_error_rate(reference, hypothesis))
                cfa_values.append(critical_fact_accuracy(reference, hypothesis))

                negation = negation_preservation(reference, hypothesis)
                if negation is not None:
                    negation_values.append(negation)

                expected_claims = [c for cl in scenario.expected_claims.values() for c in cl]
                produced_claims = observation.claims or []

                if expected_claims:
                    claim_f1_values.append(claim_scores(expected_claims, produced_claims)["f1"])
                    attribution = attribution_scores(expected_claims, produced_claims)
                    caa_values.append(attribution["claim_attribution_accuracy"])
                    wpar_values.append(attribution["wrong_party_attribution_rate"])

                macro_f1_values.append(
                    issue_macro_f1(observation.expected_issue_states or {}, observation.issue_states or {})
                )
                issue_accuracy_values.append(
                    issue_state_accuracy(
                        observation.expected_issue_states or {}, observation.issue_states or {}
                    )
                )
                case_results.append(bool(observation.case_state_correct))

                facts = observation.critical_facts or {}
                missed = len(facts.get("missed", []))
                critical_errors += missed
                if missed:
                    unverified_now = sum(
                        1 for status in (observation.issue_states or {}).values() if status == "UNVERIFIED"
                    )
                    absorbed += min(missed, unverified_now)
                    uncertain += missed
                    surfaced += min(missed, unverified_now)
                    wrong_entering += missed
                    unflagged += max(0, missed - unverified_now)

            def add(metric: str, values: list[float], scope: str = "overall") -> None:
                point, low, high = bootstrap_ci(values, request.bootstrap_samples)
                rows.append(
                    MetricRow(
                        provider=provider,
                        metric=metric,
                        value=round(point, 4),
                        ci_low=round(low, 4),
                        ci_high=round(high, 4),
                        scope=scope,
                        sample_count=len(values),
                    )
                )

            add("word_error_rate", wer_values)
            add("character_error_rate", cer_values)
            add("critical_fact_accuracy", cfa_values)
            add("negation_preservation_rate", negation_values)
            add("claim_f1", claim_f1_values)
            add("claim_attribution_accuracy", caa_values)
            add("wrong_party_attribution_rate", wpar_values)
            add("issue_macro_f1", macro_f1_values)
            add("issue_state_accuracy", issue_accuracy_values)

            rows.append(
                MetricRow(
                    provider=provider,
                    metric="correct_mediation_state_rate",
                    value=round(correct_mediation_state_rate(case_results) * 100, 2),
                    scope="overall",
                    sample_count=len(case_results),
                )
            )

            safety = {
                "critical_error_absorption_rate": critical_error_absorption_rate(critical_errors, absorbed),
                "unverified_value_visibility_rate": unverified_value_visibility_rate(uncertain, surfaced),
                "silent_resolution_rate": silent_resolution_rate(wrong_entering, unflagged),
            }
            safety.update(clarification_scores(absorbed, max(0, surfaced - absorbed), max(0, unflagged)))

            for metric, value in safety.items():
                rows.append(
                    MetricRow(
                        provider=provider,
                        metric=metric,
                        value=round(float(value), 4),
                        scope="safety",
                        sample_count=len(items),
                    )
                )

        return rows

    # ── helpers ────────────────────────────────────────────────────────────
    def _comparable(self, claim, pending: set[str]) -> ComparableClaim:
        return ComparableClaim(
            claim_id=claim.claim_id,
            type=claim.type,
            subject=claim.subject,
            predicate=claim.predicate,
            canonical_value=claim.canonical_value,
            polarity=claim.polarity.value if hasattr(claim.polarity, "value") else str(claim.polarity),
            criticality=claim.criticality.value
            if hasattr(claim.criticality, "value")
            else str(claim.criticality),
            verification_status=claim.verification_status.value
            if hasattr(claim.verification_status, "value")
            else str(claim.verification_status),
            reported_speech=claim.reported_speech,
            has_pending_critical_field=claim.claim_id in pending,
        )

    def _audio_uri(self, clip: Clip) -> str:
        settings = get_settings()
        if settings.fixture_mode or not clip.audio_path:
            return f"fixture://{clip.fixture_key or clip.clip_id}"
        return str(self.root / clip.audio_path)

    def _classify(
        self,
        reference: str,
        hypothesis: str,
        expected_states: dict[str, str],
        produced_states: dict[str, str],
    ) -> list[str]:
        detail = critical_fact_detail(reference, hypothesis)
        codes: list[str] = []

        if any(f.startswith("amount:") for f in detail["missed"]):
            codes.append("E01")
        if any(f.startswith("date:") for f in detail["missed"]):
            codes.append("E02")
        if negation_preservation(reference, hypothesis) == 0.0:
            codes.append("E03")
        if detail["invented"]:
            codes.append("E09")
        if any(produced_states.get(k) != v for k, v in expected_states.items()):
            codes.append("E10")

        return codes


def _git_commit() -> str | None:
    try:
        return (
            subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], stderr=subprocess.DEVNULL)
            .decode()
            .strip()
        )
    except Exception:
        return None


def run_sync(request: BenchmarkRunRequest, root: Path | None = None) -> BenchmarkRunResponse:
    return asyncio.run(BenchmarkRunner(root=root).run(request))

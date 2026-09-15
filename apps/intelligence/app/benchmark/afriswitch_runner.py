"""
Tier 1 — AfriSwitch.

The external, standard, citable half of the benchmark. Same audio, four speech
models, WER and CER computed exactly the way Intron computes them, plus the
code-switch measures WER cannot express.

Results are stratified by Code-Mixing Index band. A single average over a corpus
that spans barely-mixed to heavily-mixed speech hides the finding: models
usually hold up on light mixing and come apart on heavy mixing, and the average
describes neither case.

Tier 2 (`runner.py`) then asks the question this tier cannot: did the difference
change the mediation outcome?
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from pathlib import Path

from app.asr.base import AsrError
from app.asr.registry import get_provider
from app.benchmark.afriswitch import (
    INTRON_REFERENCE_KINYARWANDA,
    AfriSwitchUtterance,
    band_summary,
    verify_against_published,
)
from app.benchmark.metrics.bootstrap import bootstrap_ci, paired_difference_ci
from app.benchmark.metrics.codeswitch import score_utterance
from app.benchmark.metrics.wer import character_error_rate, word_error_rate
from app.config import get_settings
from app.logging_setup import log_event
from app.schemas.speech import TranscriptionConfig

logger = logging.getLogger("wunzi.afriswitch")


def _fallback_notes(label: str) -> list[str]:
    from app.benchmark.hf_audio import applicability_notes

    return applicability_notes(label)

CODE_SWITCH_METRICS = (
    "matrix_language_collapse_rate",
    "switch_point_preservation",
    "span_language_fidelity",
)


@dataclass
class UtteranceResult:
    utterance_id: str
    provider: str
    cmi: float
    cmi_band: str
    num_switch_points: int
    duration: float
    reference: str
    hypothesis: str
    wer: float
    cer: float
    code_switch: dict[str, float]
    latency_ms: int | None = None
    failed: bool = False
    # Why it failed. "100% of calls failed" without the reason is the same
    # unhelpful report one layer down: it names the symptom and hides the cause.
    failure_reason: str | None = None
    used_placeholder_fixture: bool = False


@dataclass
class AfriSwitchReport:
    config: str
    providers: list[str]
    utterance_count: int
    dataset_notes: list[str]
    band_profile: dict[str, dict[str, float]]
    # "afriswitch" or "fallback". Which metrics are meaningful depends on it, so
    # it travels with the numbers rather than living in someone's memory.
    source: str = "afriswitch"
    # The dataset that actually loaded. Named so a reader never has to guess
    # which corpus produced a figure.
    source_label: str | None = None
    results: list[UtteranceResult] = field(default_factory=list)
    overall: dict[str, dict[str, dict[str, float]]] = field(default_factory=dict)
    by_band: dict[str, dict[str, dict[str, float]]] = field(default_factory=dict)
    paired: dict[str, dict[str, tuple[float, float, float]]] = field(default_factory=dict)
    sanity: list[str] = field(default_factory=list)
    publishable: bool = True
    publishability_note: str | None = None


class AfriSwitchRunner:
    def __init__(self, audio_root: Path | None = None) -> None:
        self.settings = get_settings()
        self.audio_root = audio_root

    async def run(
        self,
        utterances: list[AfriSwitchUtterance],
        providers: list[str],
        config: str = "kinyarwanda",
        bootstrap_samples: int = 1000,
        source: str = "afriswitch",
        source_label: str | None = None,
    ) -> AfriSwitchReport:
        code_switched = source == "afriswitch"

        report = AfriSwitchReport(
            config=config,
            providers=providers,
            utterance_count=len(utterances),
            # Published statistics only exist for AfriSwitch; comparing a
            # Common Voice load against them would report false mismatches.
            dataset_notes=verify_against_published(config, utterances)
            if code_switched
            else _fallback_notes(source_label or "a monolingual Kinyarwanda corpus"),
            source=source,
            source_label=source_label,
            # Every Common Voice utterance has CMI 0, so band tables would be one
            # row pretending to be three.
            band_profile=band_summary(utterances) if code_switched else {},
        )

        for provider_name in providers:
            for utterance in utterances:
                report.results.append(await self._score(provider_name, utterance))

        self._aggregate(report, bootstrap_samples, code_switched)
        self._pair(report, bootstrap_samples, code_switched)
        report.sanity = self._sanity_check(report, config)

        placeholder = any(r.used_placeholder_fixture for r in report.results)

        # A failed call is recorded as an empty transcript, which scores WER 1.0
        # — indistinguishable, in a table, from a model that transcribed badly.
        # Without this the worst possible outcome (nothing was measured at all)
        # renders as the most confident one (every model scored exactly 1.000).
        failures = sum(1 for r in report.results if r.failed)
        failure_rate = failures / len(report.results) if report.results else 0.0

        # Failures no longer contaminate the error rates — they are excluded
        # from scoring. What a high failure rate costs is coverage, so the bar
        # is about how much of the sample was actually measured.
        report.publishable = not placeholder and failure_rate < 0.20

        if failure_rate >= 0.20:
            report.publishability_note = (
                f"{failures} of {len(report.results)} provider calls failed "
                f"({failure_rate:.0%}). Error rates below are computed over the "
                "successful calls only, but at this rate the surviving sample is "
                "no longer representative of the corpus."
            )
        elif failures:
            report.publishability_note = (
                f"{failures} of {len(report.results)} provider calls failed "
                f"({failure_rate:.0%}) and are excluded from the error rates, which "
                "are computed over successful calls. Reported for completeness."
            )
        elif placeholder:
            report.publishability_note = (
                "At least one utterance was scored from a placeholder fixture rather "
                "than a captured provider output. These numbers exercise the harness; "
                "they do not measure any speech model."
            )

        log_event(
            logger,
            "afriswitch_run_completed",
            config=config,
            providers=providers,
            utterances=len(utterances),
            publishable=report.publishable,
        )

        return report

    # ── one utterance × one provider ───────────────────────────────────────
    async def _score(self, provider_name: str, utterance: AfriSwitchUtterance) -> UtteranceResult:
        hypothesis = ""
        latency = None
        failed = False
        reason: str | None = None
        placeholder = False

        try:
            provider = get_provider(provider_name, self.settings)
            transcript = await provider.transcribe(
                self._audio_uri(utterance),
                TranscriptionConfig(languages=[utterance.language, "en"]),
            )
            hypothesis = transcript.text
            latency = transcript.latency_ms
            placeholder = transcript.is_placeholder
        except (AsrError, KeyError) as exc:
            # A provider failure is recorded, never replaced by another model.
            failed = True
            reason = f"{type(exc).__name__}: {str(exc).strip(chr(39))[:180]}"
            log_event(
                logger,
                "afriswitch_provider_failed",
                provider=provider_name,
                utterance=utterance.utterance_id,
                error=str(exc),
            )

        scores = score_utterance(
            utterance.transcription,
            hypothesis,
            [span.text for span in utterance.english_spans],
            [span.text for span in utterance.matrix_spans],
        )

        return UtteranceResult(
            utterance_id=utterance.utterance_id,
            provider=provider_name,
            cmi=utterance.cmi,
            cmi_band=utterance.cmi_band,
            num_switch_points=utterance.num_switch_points,
            duration=utterance.duration,
            reference=utterance.transcription,
            hypothesis=hypothesis,
            wer=word_error_rate(utterance.transcription, hypothesis),
            cer=character_error_rate(utterance.transcription, hypothesis),
            code_switch=scores.as_dict(),
            latency_ms=latency,
            failed=failed,
            failure_reason=reason,
            used_placeholder_fixture=placeholder,
        )

    def _audio_uri(self, utterance: AfriSwitchUtterance) -> str:
        """
        Where the audio for one utterance lives.

        In fixture mode this addresses a cached provider output by utterance id,
        so the harness can be exercised without the 6.8 GB download or a live
        API key.
        """
        if self.settings.fixture_mode or not utterance.audio_path:
            return f"fixture://{utterance.utterance_id}"

        if self.audio_root:
            return str(Path(self.audio_root) / utterance.audio_path)

        return utterance.audio_path

    # ── aggregation ────────────────────────────────────────────────────────
    def _aggregate(self, report: AfriSwitchReport, samples: int, code_switched: bool = True) -> None:
        for provider in report.providers:
            rows = [r for r in report.results if r.provider == provider]
            report.overall[provider] = self._summarise(rows, samples, code_switched)

            if not code_switched:
                continue

            for band in ("light", "moderate", "heavy"):
                banded = [r for r in rows if r.cmi_band == band]
                if banded:
                    report.by_band.setdefault(band, {})[provider] = self._summarise(
                        banded, samples, code_switched
                    )

    def _summarise(
        self, rows: list[UtteranceResult], samples: int, code_switched: bool = True
    ) -> dict[str, dict[str, float]]:
        # A failed call is a failure to measure, not a measurement of zero.
        # Scoring it as an empty transcript gives a word error rate of 1.0 and
        # averaging that in inflates every figure — on the first 200-utterance
        # run, twelve queued clips pushed Sahara's WER from roughly 0.36 to
        # 0.399, and the number that would have been reported was partly a
        # measure of the provider's queue.
        #
        # Error rates are computed over successful calls; the failure rate is
        # reported separately and prominently, so nothing is hidden by the
        # exclusion.
        scored = [row for row in rows if not row.failed]
        def ci(values: list[float]) -> dict[str, float]:
            point, low, high = bootstrap_ci(values, samples)
            return {"value": round(point, 4), "ci_low": round(low, 4), "ci_high": round(high, 4)}

        summary = {
            "word_error_rate": ci([r.wer for r in scored]),
            "character_error_rate": ci([r.cer for r in scored]),
        }

        for metric in CODE_SWITCH_METRICS:
            # Switch preservation has no meaning without switches. Excluding it
            # is the point: scoring monolingual audio 1.0 would hand every model
            # free marks on the one axis this challenge is about.
            if metric == "switch_point_preservation" and not code_switched:
                continue
            summary[metric] = ci([r.code_switch[metric] for r in scored])

        latencies = [float(r.latency_ms) for r in scored if r.latency_ms is not None]
        if latencies:
            summary["latency_ms"] = ci(latencies)

        # The count of what was actually scored, not of what was attempted.
        summary["sample_count"] = {"value": float(len(scored)), "ci_low": 0.0, "ci_high": 0.0}
        summary["attempted_count"] = {"value": float(len(rows)), "ci_low": 0.0, "ci_high": 0.0}
        summary["failure_rate"] = ci([1.0 if r.failed else 0.0 for r in rows])

        return summary

    def _pair(self, report: AfriSwitchReport, samples: int, code_switched: bool = True) -> None:
        """
        Paired bootstrap of Sahara against each other provider.

        Every model saw the same utterances, so the per-utterance difference
        carries the signal. An unpaired comparison of two averages would throw
        that away and widen the interval for no reason.
        """
        if "sahara" not in report.providers:
            return

        index = {(r.provider, r.utterance_id): r for r in report.results}
        ids = sorted({r.utterance_id for r in report.results})

        for provider in report.providers:
            if provider == "sahara":
                continue

            comparisons: dict[str, tuple[float, float, float]] = {}

            for metric, getter in (
                ("word_error_rate", lambda r: r.wer),
                ("character_error_rate", lambda r: r.cer),
                # Same exclusion as the summary table: a metric with no meaning
                # on this corpus must not reappear in the comparison.
                *[
                    (m, (lambda m: lambda r: r.code_switch[m])(m))
                    for m in CODE_SWITCH_METRICS
                    if code_switched or m != "switch_point_preservation"
                ],
            ):
                sahara_values, other_values = [], []
                for utterance_id in ids:
                    a = index.get(("sahara", utterance_id))
                    b = index.get((provider, utterance_id))
                    if a and b:
                        sahara_values.append(getter(a))
                        other_values.append(getter(b))

                comparisons[metric] = paired_difference_ci(
                    sahara_values, other_values, samples
                )

            report.paired[provider] = comparisons

    # ── sanity ─────────────────────────────────────────────────────────────
    def _sanity_check(self, report: AfriSwitchReport, config: str) -> list[str]:
        """
        Cross-checks the harness against Intron's published numbers.

        Different corpus — theirs is clinical, AfriSwitch is conversational — so
        the absolute values will differ and that is expected. What would not be
        expected is Sahara landing an order of magnitude away, or the ordering
        inverting completely. Either means the harness is wrong before it means
        anything about a model.
        """
        # Common Voice names the language `rw`; AfriSwitch names it
        # `kinyarwanda`. Both are Kinyarwanda, and the cross-check against
        # Intron's published figure is the main reason to run this at all —
        # refusing it on a naming difference would throw away the validation.
        if config.lower() not in {"kinyarwanda", "rw", "kin"}:
            return [f"No published reference on file for '{config}'; harness unverified."]

        notes: list[str] = []
        sahara = report.overall.get("sahara", {}).get("word_error_rate", {}).get("value")

        if sahara is None:
            return ["Sahara was not in this run, so the harness could not be cross-checked."]

        published = INTRON_REFERENCE_KINYARWANDA["sahara"]["wer"]
        corpus = (
            "conversational code-switched speech"
            if report.source == "afriswitch"
            else "read monolingual speech"
        )
        notes.append(
            f"Sahara WER here {sahara:.3f} · Intron AfriHealth Kinyarwanda {published:.3f}. "
            f"Different corpora — theirs is clinical, this is {corpus} — so a gap is "
            f"expected; an order of magnitude is not."
        )

        if sahara > published * 3:
            notes.append(
                "Sahara WER is more than 3x the published figure. Check audio "
                "resampling, the normalisation step and the language hints before "
                "reading anything into these results."
            )

        return notes


def run_sync(
    utterances: list[AfriSwitchUtterance],
    providers: list[str],
    config: str = "kinyarwanda",
    bootstrap_samples: int = 1000,
    source: str = "afriswitch",
    source_label: str | None = None,
) -> AfriSwitchReport:
    return asyncio.run(
        AfriSwitchRunner().run(
            utterances, providers, config, bootstrap_samples, source, source_label
        )
    )

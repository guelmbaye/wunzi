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
    used_placeholder_fixture: bool = False


@dataclass
class AfriSwitchReport:
    config: str
    providers: list[str]
    utterance_count: int
    dataset_notes: list[str]
    band_profile: dict[str, dict[str, float]]
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
    ) -> AfriSwitchReport:
        report = AfriSwitchReport(
            config=config,
            providers=providers,
            utterance_count=len(utterances),
            dataset_notes=verify_against_published(config, utterances),
            band_profile=band_summary(utterances),
        )

        for provider_name in providers:
            for utterance in utterances:
                report.results.append(await self._score(provider_name, utterance))

        self._aggregate(report, bootstrap_samples)
        self._pair(report, bootstrap_samples)
        report.sanity = self._sanity_check(report, config)

        placeholder = any(r.used_placeholder_fixture for r in report.results)
        report.publishable = not placeholder
        if placeholder:
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
    def _aggregate(self, report: AfriSwitchReport, samples: int) -> None:
        for provider in report.providers:
            rows = [r for r in report.results if r.provider == provider]
            report.overall[provider] = self._summarise(rows, samples)

            for band in ("light", "moderate", "heavy"):
                banded = [r for r in rows if r.cmi_band == band]
                if banded:
                    report.by_band.setdefault(band, {})[provider] = self._summarise(
                        banded, samples
                    )

    def _summarise(self, rows: list[UtteranceResult], samples: int) -> dict[str, dict[str, float]]:
        def ci(values: list[float]) -> dict[str, float]:
            point, low, high = bootstrap_ci(values, samples)
            return {"value": round(point, 4), "ci_low": round(low, 4), "ci_high": round(high, 4)}

        summary = {
            "word_error_rate": ci([r.wer for r in rows]),
            "character_error_rate": ci([r.cer for r in rows]),
        }

        for metric in CODE_SWITCH_METRICS:
            summary[metric] = ci([r.code_switch[metric] for r in rows])

        latencies = [float(r.latency_ms) for r in rows if r.latency_ms is not None]
        if latencies:
            summary["latency_ms"] = ci(latencies)

        summary["sample_count"] = {"value": float(len(rows)), "ci_low": 0.0, "ci_high": 0.0}
        summary["failure_rate"] = ci([1.0 if r.failed else 0.0 for r in rows])

        return summary

    def _pair(self, report: AfriSwitchReport, samples: int) -> None:
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
                *[
                    (m, (lambda m: lambda r: r.code_switch[m])(m))
                    for m in CODE_SWITCH_METRICS
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
        if config != "kinyarwanda":
            return [f"No published reference on file for '{config}'; harness unverified."]

        notes: list[str] = []
        sahara = report.overall.get("sahara", {}).get("word_error_rate", {}).get("value")

        if sahara is None:
            return ["Sahara was not in this run, so the harness could not be cross-checked."]

        published = INTRON_REFERENCE_KINYARWANDA["sahara"]["wer"]
        notes.append(
            f"Sahara WER here {sahara:.3f} · Intron AfriHealth Kinyarwanda {published:.3f} "
            f"(clinical corpus, so a gap is expected; an order of magnitude is not)."
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
) -> AfriSwitchReport:
    return asyncio.run(
        AfriSwitchRunner().run(utterances, providers, config, bootstrap_samples)
    )

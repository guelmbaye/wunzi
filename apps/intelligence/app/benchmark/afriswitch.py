"""
AfriSwitch — the external, standard benchmark tier.

`intronhealth/AfriSwitch` is a 54.41-hour human-transcribed benchmark of
in-the-wild conversational code-switched speech across 14 African languages,
each switching with English. It ships as a single `test` split, evaluation only.

WUNZI uses the Kinyarwanda config: 5.00 hours, 1,577 utterances, CMI 16.95, 4.51
average switch points per utterance.

Why this matters more than the mediation set on its own: the WUNZI evaluation
scenarios are ours, which means a reader has to take our word for their
difficulty. AfriSwitch is external, human-transcribed, published, and Intron has
already reported provider numbers on the same language — so a harness that
produces wildly different WER is a broken harness, not a discovery. Tier 1 is
where the benchmark earns the right to be believed; tier 2 is where it says
something new.

Access
------
The dataset is gated and licensed CC BY-NC-SA 4.0. Before first use:

    huggingface-cli login
    # then accept the conditions at
    # https://huggingface.co/datasets/intronhealth/AfriSwitch

Nothing here downloads audio implicitly: a benchmark that quietly pulls 6.8 GB
on import is a benchmark nobody can reason about.
"""

from __future__ import annotations

import json
import logging
import re
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterator

DATASET_ID = "intronhealth/AfriSwitch"
DEFAULT_CONFIG = "kinyarwanda"
SPLIT = "test"

logger = logging.getLogger("wunzi.afriswitch")

# English spans are wrapped in the tagged transcription. This is the ground
# truth for where a speaker actually switched — not something we infer.
EN_SPAN = re.compile(r"\[\[EN\]\](.*?)\[\[/EN\]\]", re.DOTALL)
TAG_STRIP = re.compile(r"\[\[/?EN\]\]")

# Published statistics, for sanity-checking a local load rather than trusting it.
# Source: the AfriSwitch dataset card.
PUBLISHED_STATS: dict[str, dict[str, float]] = {
    "kinyarwanda": {"hours": 5.00, "utterances": 1577, "avg_switch_points": 4.51, "cmi": 16.95},
    "swahili": {"hours": 3.89, "utterances": 650, "avg_switch_points": 10.29, "cmi": 25.72},
    "french": {"hours": 3.22, "utterances": 903, "avg_switch_points": 3.00, "cmi": 10.92},
    "yoruba": {"hours": 5.00, "utterances": 1877, "avg_switch_points": 5.33, "cmi": 22.93},
    "hausa": {"hours": 5.00, "utterances": 1515, "avg_switch_points": 4.00, "cmi": 13.09},
    "igbo": {"hours": 5.00, "utterances": 1848, "avg_switch_points": 4.10, "cmi": 27.64},
    "zulu": {"hours": 5.00, "utterances": 1465, "avg_switch_points": 4.40, "cmi": 24.76},
    "amharic": {"hours": 5.00, "utterances": 1229, "avg_switch_points": 4.60, "cmi": 13.11},
}

# Intron's own AfriHealth MultiBench WER/CER on Kinyarwanda, for cross-checking
# the harness. Different corpus (clinical, not conversational), so the absolute
# numbers will differ — but an ordering that inverts, or a Sahara WER far from
# this range, means the harness is wrong before it means anything else.
INTRON_REFERENCE_KINYARWANDA = {
    "sahara": {"wer": 0.258, "cer": 0.084},
    "omnillm": {"wer": 0.312, "cer": 0.124},
    "omnictc": {"wer": 0.375, "cer": 0.136},
    "gemini_flash": {"wer": 0.426, "cer": 0.181},
    "gemma4": {"wer": 0.716, "cer": 0.269},
    "gpt4o": {"wer": 0.839, "cer": 0.427},
    "qwen3": {"wer": 1.000, "cer": 0.607},
}


@dataclass
class SwitchSpan:
    """One contiguous run of tokens in a single language."""

    language: str  # "en" or the matrix language code
    text: str
    start_token: int
    end_token: int


@dataclass
class AfriSwitchUtterance:
    utterance_id: str
    language: str
    filename: str
    transcription: str
    transcription_tagged: str
    cmi: float
    num_switch_points: int
    duration: float
    audio_path: str | None = None
    spans: list[SwitchSpan] = field(default_factory=list)

    @property
    def english_spans(self) -> list[SwitchSpan]:
        return [span for span in self.spans if span.language == "en"]

    @property
    def matrix_spans(self) -> list[SwitchSpan]:
        return [span for span in self.spans if span.language != "en"]

    @property
    def cmi_band(self) -> str:
        """
        Stratification band.

        Reporting one average over an evaluation set that ranges from barely
        mixed to heavily mixed hides the finding: models usually hold up on
        light mixing and fall apart on heavy mixing, and an average splits the
        difference into a number that describes neither.
        """
        if self.cmi < 10:
            return "light"
        if self.cmi < 20:
            return "moderate"
        return "heavy"


def parse_spans(tagged: str, matrix_language: str) -> list[SwitchSpan]:
    """
    Splits a tagged transcription into language spans.

    `[[EN]]…[[/EN]]` marks English; everything outside is the matrix language.
    Token offsets are computed on the untagged text so they align with the
    plain `transcription` field a model is scored against.
    """
    spans: list[SwitchSpan] = []
    cursor = 0
    token_cursor = 0

    for match in EN_SPAN.finditer(tagged):
        before = tagged[cursor : match.start()]
        before_clean = TAG_STRIP.sub("", before).strip()

        if before_clean:
            tokens = before_clean.split()
            spans.append(
                SwitchSpan(matrix_language, before_clean, token_cursor, token_cursor + len(tokens))
            )
            token_cursor += len(tokens)

        english = match.group(1).strip()
        if english:
            tokens = english.split()
            spans.append(SwitchSpan("en", english, token_cursor, token_cursor + len(tokens)))
            token_cursor += len(tokens)

        cursor = match.end()

    trailing = TAG_STRIP.sub("", tagged[cursor:]).strip()
    if trailing:
        tokens = trailing.split()
        spans.append(
            SwitchSpan(matrix_language, trailing, token_cursor, token_cursor + len(tokens))
        )

    return spans


def load_afriswitch(
    config: str = DEFAULT_CONFIG,
    limit: int | None = None,
    cmi_band: str | None = None,
    audio_dir: Path | None = None,
) -> list[AfriSwitchUtterance]:
    """
    Loads one language config. Requires `datasets`, a Hugging Face login and
    acceptance of the dataset conditions.

    Metadata is read first and sampled before any audio is touched. `limit`
    samples deterministically across the CMI range rather than taking the first
    N, because the first N of a sorted corpus is not a sample — and materialising
    all 1,577 clips to keep ten of them would waste minutes on every run.
    """
    try:
        from datasets import Audio, load_dataset
    except ImportError as exc:  # pragma: no cover - depends on the environment
        raise RuntimeError(
            "AfriSwitch needs the `datasets` package: pip install datasets"
        ) from exc

    raw = load_dataset(DATASET_ID, config, split=SPLIT)

    # decode=False keeps torchcodec out of the picture. `datasets` 4.x decodes
    # audio through it — torch and FFmpeg, gigabytes of dependency — to produce
    # an array this loader would immediately re-encode to a file. The ASR
    # adapters want a file, so the original bytes are written straight through.
    try:
        raw = raw.cast_column("audio", Audio(decode=False))
    except Exception as exc:  # noqa: BLE001 — the cast is an optimisation
        logger.info("afriswitch_cast_skipped: %s: %s", type(exc).__name__, exc)

    # Pass one: metadata only, so sampling costs nothing.
    metadata = [
        AfriSwitchUtterance(
            utterance_id=str(row.get("filename") or f"{config}-{index}"),
            language=str(row.get("language", config)),
            filename=str(row.get("filename", "")),
            transcription=str(row.get("transcription", "")),
            transcription_tagged=str(row.get("transcription_tagged", "")),
            cmi=float(row.get("cmi") or 0.0),
            num_switch_points=int(row.get("num_switch_points") or 0),
            duration=float(row.get("duration") or 0.0),
            audio_path=None,
            spans=parse_spans(str(row.get("transcription_tagged", "")), config[:2]),
        )
        for index, row in enumerate(
            raw.remove_columns([c for c in raw.column_names if c == "audio"])
        )
    ]

    if cmi_band:
        keep = {u.utterance_id for u in metadata if u.cmi_band == cmi_band}
        metadata = [u for u in metadata if u.utterance_id in keep]

    if limit is not None and limit < len(metadata):
        metadata = stratified_sample(metadata, limit)

    # Pass two: write audio for the sampled clips only.
    from app.benchmark.hf_audio import _audio_payload, _store_clip

    root = Path(audio_dir or Path(tempfile.gettempdir()) / "wunzi-afriswitch-audio")
    root.mkdir(parents=True, exist_ok=True)

    wanted = {u.utterance_id: u for u in metadata}
    resolved: list[AfriSwitchUtterance] = []

    for index, row in enumerate(raw):
        utterance_id = str(row.get("filename") or f"{config}-{index}")
        target = wanted.get(utterance_id)
        if target is None:
            continue

        payload = _audio_payload(row)
        if payload is None:
            logger.warning("afriswitch_no_audio: %s", utterance_id)
            continue

        path = _store_clip(payload, root, _safe_id(utterance_id))
        if path is None:
            logger.warning("afriswitch_empty_audio: %s", utterance_id)
            continue

        target.audio_path = str(path)
        resolved.append(target)

        if len(resolved) == len(wanted):
            break

    logger.info("afriswitch_loaded: %d clips from %s/%s", len(resolved), DATASET_ID, config)
    return resolved


def _safe_id(utterance_id: str) -> str:
    stem = Path(utterance_id).stem
    return "".join(ch for ch in stem if ch.isalnum() or ch in "-_")[:64] or "clip"


def stratified_sample(
    utterances: list[AfriSwitchUtterance], size: int
) -> list[AfriSwitchUtterance]:
    """
    Samples proportionally across CMI bands, preserving the corpus's mixing
    profile. Taking the head of the list would silently pick whichever band
    happens to sort first.
    """
    bands: dict[str, list[AfriSwitchUtterance]] = {}
    for utterance in utterances:
        bands.setdefault(utterance.cmi_band, []).append(utterance)

    for band in bands.values():
        band.sort(key=lambda u: u.utterance_id)  # deterministic, no RNG seed to forget

    sampled: list[AfriSwitchUtterance] = []
    total = len(utterances)

    for band, members in sorted(bands.items()):
        share = max(1, round(size * len(members) / total))
        step = max(1, len(members) // share)
        sampled.extend(members[::step][:share])

    return sorted(sampled, key=lambda u: u.utterance_id)[:size]


def band_summary(utterances: list[AfriSwitchUtterance]) -> dict[str, dict[str, float]]:
    """Per-band counts and mixing statistics, for the report header."""
    summary: dict[str, dict[str, float]] = {}

    for band in ("light", "moderate", "heavy"):
        members = [u for u in utterances if u.cmi_band == band]
        if not members:
            continue

        summary[band] = {
            "utterances": len(members),
            "hours": round(sum(u.duration for u in members) / 3600, 3),
            "mean_cmi": round(sum(u.cmi for u in members) / len(members), 2),
            "mean_switch_points": round(
                sum(u.num_switch_points for u in members) / len(members), 2
            ),
        }

    return summary


def verify_against_published(config: str, utterances: list[AfriSwitchUtterance]) -> list[str]:
    """
    Compares a local load against the published statistics.

    A benchmark whose own inputs are unverified cannot support a claim about
    anything downstream. This is cheap and catches a truncated download, a wrong
    config, or a schema change long before it becomes a wrong conclusion.
    """
    expected = PUBLISHED_STATS.get(config)
    if not expected:
        return [f"No published statistics on file for config '{config}'."]

    notes: list[str] = []

    if len(utterances) != expected["utterances"]:
        notes.append(
            f"Loaded {len(utterances)} utterances, dataset card says "
            f"{int(expected['utterances'])}. A sampled run is fine; a full run is not."
        )

    hours = sum(u.duration for u in utterances) / 3600
    if abs(hours - expected["hours"]) > 0.25 and len(utterances) == expected["utterances"]:
        notes.append(f"Loaded {hours:.2f} hours, dataset card says {expected['hours']:.2f}.")

    if utterances:
        mean_switches = sum(u.num_switch_points for u in utterances) / len(utterances)
        if abs(mean_switches - expected["avg_switch_points"]) > 1.0:
            notes.append(
                f"Mean switch points {mean_switches:.2f} vs published "
                f"{expected['avg_switch_points']:.2f}."
            )

    return notes


def iter_clips(utterances: list[AfriSwitchUtterance]) -> Iterator[tuple[str, str, str]]:
    """(utterance_id, audio_path, reference_transcription) for the runner."""
    for utterance in utterances:
        if utterance.audio_path:
            yield utterance.utterance_id, utterance.audio_path, utterance.transcription

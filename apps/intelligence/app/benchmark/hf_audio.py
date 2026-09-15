"""
Generic Hugging Face audio loader — the fallback evaluation source.

AfriSwitch is the right corpus and remains the default. It is gated behind
**manual author review**, which can take days. This module exists so a measured
result is possible today against whatever Kinyarwanda corpus is actually
reachable.

Why generic rather than one hard-coded dataset
----------------------------------------------
Three attempts failed in sequence, each for a different reason:

    mozilla-foundation/common_voice_17_0   script-based; `datasets` 3.x dropped
                                           script support entirely
    fsicoli/common_voice_17_0              same, explicitly: "Dataset scripts are
                                           no longer supported"
    google/fleurs                          same; the Parquet conversion PR is
                                           still open

Guessing a fourth would repeat the mistake. Instead this loader takes any dataset
id and **discovers the schema**: it finds the transcript column and the audio
column by name, and says plainly which columns it found when it cannot. Point it
at whatever you can access.

WHAT A MONOLINGUAL CORPUS MEASURES
----------------------------------
Every candidate below is read, monolingual Kinyarwanda. That changes what the
Tier-1 metrics can honestly report:

    word_error_rate               MEASURED
    character_error_rate          MEASURED
    matrix_language_collapse      MEASURED — a model returning English for a
                                  Kinyarwanda utterance has translated rather
                                  than transcribed, detectable without switches
    span_language_fidelity        MEASURED
    switch_point_preservation     NOT APPLICABLE — excluded, never scored 1.0

Scoring monolingual audio as perfect switch preservation would hand every model a
free mark on the one axis this challenge is about.
"""

from __future__ import annotations

import logging
import tempfile
import wave
from pathlib import Path

from app.benchmark.afriswitch import AfriSwitchUtterance, SwitchSpan

logger = logging.getLogger("wunzi.hf_audio")

SAMPLE_RATE = 16_000

# Tried in order. All are Kinyarwanda; none is code-switched. Each is gated by
# click-through acceptance rather than author review, so access is immediate —
# but that could not be verified from the build environment, so the loader
# reports exactly which one worked.
CANDIDATES: tuple[tuple[str, str | None, str], ...] = (
    ("mbazaNLP/fleurs-kinyarwanda", None, "train"),
    ("benax-rw/KinyaWhisperDataset", None, "train"),
    ("fsicoli/common_voice_19_0", "rw", "test"),
    ("fsicoli/common_voice_17_0", "rw", "test"),
    ("mozilla-foundation/common_voice_17_0", "rw", "test"),
)

# Column names used by the corpora above, most specific first.
TRANSCRIPT_COLUMNS = ("transcription", "raw_transcription", "sentence", "text", "transcript")
AUDIO_COLUMNS = ("audio", "speech", "file")

# Containers the ASR adapters can forward as-is.
AUDIO_SUFFIXES = (".wav", ".mp3", ".flac", ".ogg", ".opus", ".m4a", ".webm")


class NoReachableDataset(RuntimeError):
    pass


def load_hf_audio(
    limit: int = 200,
    dataset_id: str | None = None,
    config: str | None = None,
    split: str | None = None,
    audio_dir: Path | None = None,
) -> tuple[list[AfriSwitchUtterance], str]:
    """
    Returns (utterances, source_label).

    With no explicit `dataset_id`, each candidate is tried in order and the first
    that loads is used. The label names it, so the report can never be ambiguous
    about which corpus produced the numbers.
    """
    try:
        from datasets import Audio, load_dataset
    except ImportError as exc:  # pragma: no cover - environment dependent
        raise RuntimeError("This needs the `datasets` package: pip install datasets") from exc

    attempts = (
        [(dataset_id, config, split)] if dataset_id else list(CANDIDATES)
    )

    failures: list[str] = []

    for candidate_id, candidate_config, candidate_split in attempts:
        # Corpora disagree about which split holds the evaluation data, and an
        # explicit --dataset-id rarely comes with a --dataset-split. Trying the
        # usual names is cheaper than making the caller guess.
        splits = [candidate_split] if candidate_split else ["test", "train", "validation"]
        stream = None
        used_split = None

        for name in splits:
            try:
                stream = (
                    load_dataset(candidate_id, candidate_config, split=name, streaming=True)
                    if candidate_config
                    else load_dataset(candidate_id, split=name, streaming=True)
                )
                used_split = name
                break
            except Exception as exc:  # noqa: BLE001 — every failure mode is reportable
                failures.append(
                    f"  {candidate_id} [{name}]: {type(exc).__name__}: {str(exc)[:140]}"
                )

        if stream is None:
            continue

        stream = _undecoded(stream, Audio)

        utterances = _materialise(stream, candidate_id, limit, audio_dir)
        if utterances:
            label = candidate_id + (f"/{candidate_config}" if candidate_config else "")
            logger.info(
                "hf_audio_loaded: %d utterances from %s [%s]", len(utterances), label, used_split
            )
            return utterances, label

        failures.append(f"  {candidate_id} [{used_split}]: loaded but produced no usable rows")

    raise NoReachableDataset(
        "No fallback corpus could be loaded. Attempts:\n"
        + "\n".join(failures)
        + "\n\nCheck the log lines above for the reason. A gated dataset raises "
        "an access error; 'no usable rows' means the corpus loaded but carried no "
        "transcript column or no embedded audio, which no flag here can fix.\n"
        "Known to work: --dataset-id benax-rw/KinyaWhisperDataset"
    )


def _undecoded(stream, Audio):
    """
    Asks for raw bytes instead of decoded audio — without insisting.

    `datasets` 4.x decodes through torchcodec, which drags in torch and FFmpeg to
    produce a numpy array this loader would immediately re-encode to a file. The
    ASR adapters want a file, so the original bytes go straight through.

    `cast_column` needs inferred features to do this, and a streaming dataset may
    have none — then it raises `TypeError: 'NoneType' object does not support
    item assignment`. When that happens the rows already arrive undecoded, so the
    cast is skipped rather than treated as a failure.
    """
    try:
        return stream.cast_column(_audio_column(stream), Audio(decode=False))
    except Exception as exc:  # noqa: BLE001 — the cast is an optimisation, not a requirement
        logger.info("hf_audio_cast_skipped: %s: %s", type(exc).__name__, exc)
        return stream


def _audio_column(stream) -> str:
    names = list(getattr(stream, "column_names", None) or [])
    for candidate in AUDIO_COLUMNS:
        if candidate in names:
            return candidate
    return "audio"


def _transcript_column(row: dict) -> str | None:
    for candidate in TRANSCRIPT_COLUMNS:
        if isinstance(row.get(candidate), str) and row[candidate].strip():
            return candidate
    return None


def _materialise(stream, dataset_id: str, limit: int, audio_dir: Path | None) -> list[AfriSwitchUtterance]:
    root = Path(audio_dir or Path(tempfile.gettempdir()) / "wunzi-fallback-audio")
    root.mkdir(parents=True, exist_ok=True)

    utterances: list[AfriSwitchUtterance] = []
    column: str | None = None

    for index, row in enumerate(stream):
        if len(utterances) >= limit:
            break

        if column is None:
            column = _transcript_column(row)
            if column is None:
                if _looks_headerless(row):
                    # The keys are data, not names: a headerless table whose
                    # first row became the header. No column mapping can fix
                    # that from here — the dataset needs repackaging.
                    logger.warning(
                        "hf_audio_headerless: %s has no header row; keys are values: %s",
                        dataset_id,
                        sorted(row.keys())[:4],
                    )
                else:
                    logger.warning(
                        "hf_audio_no_transcript_column: %s has %s",
                        dataset_id,
                        sorted(row.keys()),
                    )
                return []
            logger.info("hf_audio_transcript_column: %s -> %s", dataset_id, column)

        sentence = (row.get(column) or "").strip()
        audio = _audio_payload(row)

        if not sentence or audio is None:
            continue

        path = _store_clip(audio, root, _clip_id(row, index))
        if path is None:
            continue

        utterances.append(
            AfriSwitchUtterance(
                utterance_id=path.stem,
                language="rw",
                filename=path.name,
                transcription=sentence,
                # No English spans: these corpora are monolingual, so switch
                # preservation has nothing to preserve and is excluded downstream.
                #
                # The whole utterance IS the matrix span, and saying so makes span
                # fidelity a real measurement rather than a default. Leaving
                # `spans` empty scored it 1.0 for every model — a fabricated
                # measurement of exactly the kind this benchmark exists to refuse.
                transcription_tagged=sentence,
                cmi=0.0,
                num_switch_points=0,
                duration=_wav_duration(path),
                audio_path=str(path),
                spans=[SwitchSpan("rw", sentence, 0, len(sentence.split()))],
            )
        )

    return utterances


def _clip_id(row: dict, index: int) -> str:
    raw = row.get("path") or row.get("id") or row.get("client_id") or ""
    stem = Path(str(raw)).stem
    safe = "".join(ch for ch in stem if ch.isalnum() or ch in "-_")[:48]
    return f"rw_{safe}" if safe else f"rw_{index:05d}"


def _looks_headerless(row: dict) -> bool:
    """
    True when the column names are obviously data.

    A table published without a header row loads with its first record as the
    header, so `row.keys()` comes back as sentences, filenames and numbers.
    Reporting that as "no transcript column" sends the reader looking for a
    mapping problem when the dataset itself needs repackaging.
    """
    keys = [str(k) for k in row.keys()]
    if not keys:
        return False

    data_shaped = sum(
        1
        for key in keys
        if key.isdigit() or " " in key.strip() or "." in key and len(key) > 12
    )
    return data_shaped >= max(2, len(keys) // 3)


def _audio_payload(row: dict) -> dict | None:
    """
    Normalises the audio cell to `{"path": …, "bytes": …}`.

    Without inferred features the cell can arrive as a dict, as a bare path
    string, or as raw bytes. Each shape is real; none of them is an error.
    """
    for key in AUDIO_COLUMNS:
        value = row.get(key)
        if value is None:
            continue
        if isinstance(value, dict):
            return value
        if isinstance(value, (bytes, bytearray)):
            return {"path": row.get("path") or "", "bytes": bytes(value)}
        if isinstance(value, str):
            return {"path": value, "bytes": None}
    return None


def _store_clip(audio: dict, root: Path, clip_id: str) -> Path | None:
    """
    Writes the provider-bound clip to disk, byte for byte.

    With `decode=False` the row carries `{"path": ..., "bytes": ...}`. The
    extension is kept from the original path so the ASR adapter labels the
    upload correctly — sending an MP3 announced as `audio/wav` is the kind of
    mismatch that produces a plausible-looking but wrong transcript.
    """
    source = str(audio.get("path") or "")
    suffix = Path(source).suffix.lower() or ".wav"
    if suffix not in AUDIO_SUFFIXES:
        suffix = ".wav"

    path = root / f"{clip_id}{suffix}"
    if path.exists() and path.stat().st_size > 0:
        return path

    payload = audio.get("bytes")

    if payload is None and source and Path(source).exists():
        # Some builders hand back a local path instead of bytes.
        payload = Path(source).read_bytes()

    if not payload:
        return None

    path.write_bytes(payload)
    return path


def _wav_duration(path: Path) -> float:
    """
    Duration from the container header when it is readable.

    Only used for the hours figure in the report header, never for scoring, so
    an unreadable container returns 0.0 rather than pulling in a decoder.
    """
    if path.suffix.lower() != ".wav":
        return 0.0

    try:
        with wave.open(str(path)) as handle:
            return handle.getnframes() / float(handle.getframerate())
    except Exception:  # noqa: BLE001 — a missing duration is not a failure
        return 0.0


def applicability_notes(source_label: str = "a monolingual Kinyarwanda corpus") -> list[str]:
    """Printed in the report header so the limits travel with the numbers."""
    return [
        f"Source: {source_label} — read, monolingual Kinyarwanda. Used because "
        "AfriSwitch access was pending author review.",
        "Word and character error rate are measured on real Kinyarwanda audio.",
        "Matrix Language Collapse is measured: a model returning English for a "
        "Kinyarwanda utterance has translated rather than transcribed.",
        "Switch Point Preservation is NOT APPLICABLE and is excluded — this "
        "corpus contains no code-switching, and scoring it 1.0 would hand every "
        "model free marks on the axis the challenge is about.",
        "Code-mixing stratification is suppressed: every utterance has CMI 0.",
    ]

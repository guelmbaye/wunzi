"""
The Common Voice fallback.

It exists because AfriSwitch is gated behind author review. The risk it carries
is subtle: running a code-switching benchmark on monolingual audio and letting
the numbers look like code-switching results. These tests pin the exclusions.
"""

import asyncio
import wave
from pathlib import Path

import numpy as np
import pytest

from app.benchmark.afriswitch import AfriSwitchUtterance
from app.benchmark.afriswitch_cli import render
from app.benchmark.afriswitch_runner import AfriSwitchRunner
from app.asr.http_client import content_type_for
from app.benchmark.hf_audio import (
    _clip_id,
    _store_clip,
    _transcript_column,
    _wav_duration,
    applicability_notes,
)


def _utterances(count: int = 6) -> list[AfriSwitchUtterance]:
    return [
        AfriSwitchUtterance(
            utterance_id=f"cv_{index:04d}",
            language="rw",
            filename=f"cv_{index}.wav",
            transcription="Nishyuye amafaranga ku munsi wa gatatu",
            transcription_tagged="",
            cmi=0.0,
            num_switch_points=0,
            duration=4.0,
            audio_path=None,
            spans=[],
        )
        for index in range(count)
    ]


@pytest.fixture(scope="module")
def report():
    return asyncio.run(
        AfriSwitchRunner().run(
            _utterances(), ["sahara", "whisper"], "rw", 200, "fallback", "example/corpus"
        )
    )


# ── the exclusions that stop a false claim ─────────────────────────────────
def test_switch_preservation_is_excluded_not_scored(report):
    # Scoring monolingual audio 1.0 would hand every model a free mark on the
    # one axis this challenge is about.
    assert "switch_point_preservation" not in report.overall["sahara"]


def test_switch_preservation_is_absent_from_the_paired_comparison(report):
    for metrics in report.paired.values():
        assert "switch_point_preservation" not in metrics


def test_code_mixing_bands_are_suppressed(report):
    # Every utterance has CMI 0, so band tables would be one row pretending
    # to be three.
    assert report.band_profile == {}
    assert report.by_band == {}


def test_the_rendered_report_omits_the_empty_band_table(report):
    assert "Code-mixing profile" not in render(report)


# ── what the fallback still does measure ───────────────────────────────────
def test_error_rates_are_still_measured(report):
    assert "word_error_rate" in report.overall["sahara"]
    assert "character_error_rate" in report.overall["sahara"]


def test_matrix_collapse_is_still_measured(report):
    # A model returning English for a Kinyarwanda utterance has translated
    # rather than transcribed, and that is detectable without any switches.
    assert "matrix_language_collapse_rate" in report.overall["sahara"]


def test_the_harness_cross_check_recognises_the_iso_code(report):
    # Common Voice says `rw`, AfriSwitch says `kinyarwanda`. Refusing the
    # cross-check on a naming difference would throw away the one thing that
    # validates the harness.
    joined = " ".join(report.sanity)
    assert "Intron AfriHealth Kinyarwanda" in joined
    assert "harness unverified" not in joined


# ── the report must carry its own limits ───────────────────────────────────
def test_the_report_states_it_is_the_fallback(report):
    markdown = render(report)
    assert "fallback source" in markdown
    assert "does **not** measure code-switch handling" in markdown


def test_source_travels_with_the_numbers(report):
    assert report.source == "fallback"
    assert report.source_label == "example/corpus"


def test_applicability_notes_name_the_excluded_metric():
    assert any("NOT APPLICABLE" in note for note in applicability_notes())


# ── audio pass-through ─────────────────────────────────────────────────────
# The clip is written byte for byte rather than decoded and re-encoded.
# `datasets` 4.x decodes through torchcodec, which drags in torch and FFmpeg to
# produce an array this loader would immediately turn back into a file.


def _wav_bytes(seconds: float = 1.0, rate: int = 16000) -> bytes:
    import io

    samples = 0.5 * np.sin(2 * np.pi * 440 * np.linspace(0, seconds, int(rate * seconds), dtype=np.float32))
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(rate)
        handle.writeframes((samples * 32767).astype(np.int16).tobytes())
    return buffer.getvalue()


def test_clip_bytes_are_written_unchanged(tmp_path: Path):
    payload = _wav_bytes()
    path = _store_clip({"path": "sample.wav", "bytes": payload}, tmp_path, "rw_0001")

    assert path is not None
    assert path.read_bytes() == payload, "no re-encoding, no generation loss"


def test_original_container_is_preserved(tmp_path: Path):
    # Sending an MP3 announced as audio/wav produces a plausible-looking but
    # wrong transcript, so the extension must survive.
    path = _store_clip({"path": "clip.mp3", "bytes": b"ID3fake"}, tmp_path, "rw_0002")
    assert path is not None and path.suffix == ".mp3"


def test_unknown_container_falls_back_to_wav(tmp_path: Path):
    path = _store_clip({"path": "clip.xyz", "bytes": b"data"}, tmp_path, "rw_0003")
    assert path is not None and path.suffix == ".wav"


def test_a_row_without_audio_is_skipped_not_faked(tmp_path: Path):
    assert _store_clip({"path": "clip.wav", "bytes": None}, tmp_path, "rw_0004") is None


def test_duration_is_read_from_the_header_when_possible(tmp_path: Path):
    path = _store_clip({"path": "d.wav", "bytes": _wav_bytes(2.0)}, tmp_path, "rw_0005")
    assert path is not None
    assert 1.9 < _wav_duration(path) < 2.1


def test_an_unreadable_container_reports_zero_rather_than_crashing(tmp_path: Path):
    # Duration only feeds the hours figure in the report header, never scoring.
    path = tmp_path / "broken.mp3"
    path.write_bytes(b"not audio")
    assert _wav_duration(path) == 0.0


# ── upload labelling ───────────────────────────────────────────────────────
def test_content_type_follows_the_extension():
    assert content_type_for("/tmp/a.mp3") == ("a.mp3", "audio/mpeg")
    assert content_type_for("/tmp/a.wav") == ("a.wav", "audio/wav")
    assert content_type_for("/tmp/a.flac") == ("a.flac", "audio/flac")


def test_content_type_ignores_a_query_string():
    assert content_type_for("https://x/y/a.mp3?sig=abc")[1] == "audio/mpeg"


def test_clip_ids_are_filesystem_safe():
    assert _clip_id({"path": "common_voice_rw_12345.mp3"}, 0) == "rw_common_voice_rw_12345"
    assert _clip_id({}, 7) == "rw_00007"
    assert "/" not in _clip_id({"path": "../../etc/passwd"}, 1)


# ── schema discovery ───────────────────────────────────────────────────────
# Three candidate corpora failed in sequence for three different reasons, each
# with a different column layout. Guessing a fourth schema would repeat the
# mistake; the loader discovers it instead.
def test_transcript_column_is_discovered_across_corpora():
    assert _transcript_column({"transcription": "Nishyuye"}) == "transcription"
    assert _transcript_column({"sentence": "Nishyuye"}) == "sentence"
    assert _transcript_column({"text": "Nishyuye"}) == "text"
    assert _transcript_column({"raw_transcription": "Nishyuye"}) == "raw_transcription"


def test_the_most_specific_column_wins():
    row = {"transcription": "normalised", "raw_transcription": "raw", "text": "other"}
    assert _transcript_column(row) == "transcription"


def test_an_unknown_schema_is_reported_not_guessed():
    # Returning None makes the loader log the columns it saw and move to the
    # next candidate, rather than silently producing empty transcripts and a
    # uniform WER of 1.0 that looks like a model result.
    assert _transcript_column({"speaker_id": 3, "duration": 1.0}) is None
    assert _transcript_column({"sentence": "   "}) is None


# ── a run where nothing was measured must not look like a result ───────────
# The first real run returned WER 1.000 for both providers, identically. That
# was not two models performing alike: every call had failed and an empty
# transcript scores 1.0. The report showed it as a clean table.


def _failed_report():
    from app.benchmark.afriswitch import SwitchSpan

    reference = "Nishyuye amafaranga ku munsi wa gatatu"
    utterances = [
        AfriSwitchUtterance(
            utterance_id=f"rw_{index:04d}",
            language="rw",
            filename=f"rw_{index}.wav",
            transcription=reference,
            transcription_tagged=reference,
            cmi=0.0,
            num_switch_points=0,
            duration=4.0,
            audio_path=None,
            spans=[SwitchSpan("rw", reference, 0, 6)],
        )
        for index in range(4)
    ]

    # No audio path and no configured provider: every call fails, exactly as it
    # does when WUNZI_MODE is fixture and no cached output exists.
    return asyncio.run(
        AfriSwitchRunner().run(utterances, ["sahara", "whisper"], "rw", 100, "fallback", "x/y")
    )


def test_a_fully_failed_run_is_not_publishable():
    assert _failed_report().publishable is False


def test_the_note_names_the_failure_rate():
    note = _failed_report().publishability_note or ""
    assert "100%" in note
    # At a total failure the surviving sample is not representative, and the
    # note has to say that rather than quote error rates computed over nothing.
    assert "no longer representative" in note


def test_failures_are_stated_before_the_metric_tables():
    markdown = render(_failed_report())
    assert markdown.index("Provider failures") < markdown.index("## Overall")


def test_span_fidelity_is_not_fabricated_on_empty_transcripts():
    # It read 1.000 while every transcript was empty, because a monolingual
    # corpus had no matrix spans and the metric defaulted to perfect. The whole
    # utterance is the matrix span, so an empty transcript must score zero.
    report = _failed_report()
    assert report.overall["sahara"]["span_language_fidelity"]["value"] == 0.0


# ── loading a corpus whose schema is not declared ──────────────────────────
# A streaming dataset may carry no inferred features. `cast_column` then raises
# "'NoneType' object does not support item assignment" — which surfaced as
# "no fallback corpus could be loaded", blaming dataset access for a code bug.


class _StreamWithoutFeatures:
    column_names = None

    def cast_column(self, *args, **kwargs):
        raise TypeError("'NoneType' object does not support item assignment")


def test_a_stream_without_features_is_used_rather_than_rejected():
    from app.benchmark.hf_audio import _undecoded

    stream = _StreamWithoutFeatures()
    # The cast is an optimisation, not a requirement: rows already arrive
    # undecoded when there are no features to cast.
    assert _undecoded(stream, object) is stream


def test_audio_cells_are_normalised_whatever_shape_they_arrive_in():
    from app.benchmark.hf_audio import _audio_payload

    # Without inferred features the cell can be a dict, a bare path, or raw
    # bytes. Each shape is real; none of them is an error.
    assert _audio_payload({"audio": {"path": "a.wav", "bytes": b"x"}})["bytes"] == b"x"
    assert _audio_payload({"audio": b"raw", "path": "b.mp3"})["path"] == "b.mp3"
    assert _audio_payload({"audio": "/tmp/c.flac"})["path"] == "/tmp/c.flac"


def test_a_row_with_no_audio_column_is_skipped():
    from app.benchmark.hf_audio import _audio_payload

    assert _audio_payload({"speaker_id": 1, "text": "x"}) is None


# ── a table published without a header row ─────────────────────────────────
# mbazaNLP/fleurs-kinyarwanda loads with its first record as the header, so the
# column names come back as sentences and filenames. Reporting that as "no
# transcript column" sends the reader looking for a mapping problem when the
# dataset itself needs repackaging.


def test_a_headerless_table_is_recognised_as_such():
    from app.benchmark.hf_audio import _looks_headerless

    assert _looks_headerless(
        {
            "1903": 1,
            "376298": 1,
            "669040034415576949.wav": 1,
            "Igihe ubutunzi bwose buriho bukoreshwa neza.": 1,
            "Male": 1,
        }
    )


def test_a_normal_schema_is_not_mistaken_for_headerless():
    from app.benchmark.hf_audio import _looks_headerless

    assert not _looks_headerless(
        {"id": 1, "audio": 1, "transcription": 1, "gender": 1, "num_samples": 1}
    )
    assert not _looks_headerless({"sentence": 1, "audio": 1, "client_id": 1})


# ── the run must refuse to start misconfigured ─────────────────────────────
# Two runs in a row produced 100% failures and a table of 1.000s. The report
# named the rate but not the cause, so the same diagnosis had to be made twice
# from the outside.


def test_preflight_refuses_fixture_mode_for_a_hub_corpus(monkeypatch):
    from app.benchmark import afriswitch_cli

    # A corpus pulled from the Hub has no cached provider output, so fixture
    # mode guarantees every call fails.
    monkeypatch.setattr(
        afriswitch_cli.get_settings().__class__, "fixture_mode", property(lambda self: True)
    )
    assert afriswitch_cli._preflight(["sahara"]) is False


def test_failure_reasons_are_counted_and_reported():
    from app.benchmark.afriswitch_cli import _failure_reasons

    report = _failed_report()
    reasons = _failure_reasons(report)

    assert reasons, "a failed run must report why, not only how often"
    reason, count = reasons[0]
    assert count > 0
    # The cause is actionable, not a bare exception class.
    assert "KeyError" in reason or "AsrError" in reason


def test_the_rendered_report_states_the_cause(monkeypatch):
    markdown = render(_failed_report())
    assert "Reported causes" in markdown


# ── a failure is not a measurement of zero ─────────────────────────────────
# A failed call was scored as an empty transcript — word error rate 1.0 — and
# averaged in with the rest. On the first 200-utterance run, twelve queued clips
# pushed Sahara's reported WER from roughly 0.36 to 0.399, so the published
# figure would have been partly a measure of the provider's queue.


def _mixed_report(successes: int = 188, failures: int = 12, success_wer: float = 0.361):
    import asyncio as _asyncio

    from app.benchmark.afriswitch_runner import AfriSwitchReport, AfriSwitchRunner, UtteranceResult

    rows = [
        UtteranceResult(
            utterance_id=f"k{index}",
            provider="sahara",
            cmi=15.0,
            cmi_band="moderate",
            num_switch_points=5,
            duration=4.0,
            reference="reference text",
            hypothesis="" if index >= successes else "hypothesis text",
            wer=1.0 if index >= successes else success_wer,
            cer=1.0 if index >= successes else 0.24,
            code_switch={
                "matrix_language_collapse_rate": 0.0,
                "switch_point_preservation": 0.40,
                "span_language_fidelity": 0.84,
            },
            failed=index >= successes,
            failure_reason="AsrError: FILE_QUEUED" if index >= successes else None,
        )
        for index in range(successes + failures)
    ]

    report = AfriSwitchReport(
        config="kinyarwanda",
        providers=["sahara"],
        utterance_count=len(rows),
        dataset_notes=[],
        band_profile={},
        results=rows,
    )
    AfriSwitchRunner()._aggregate(report, 200, True)
    del _asyncio
    return report


def test_failed_calls_do_not_inflate_the_error_rate():
    report = _mixed_report()
    wer = report.overall["sahara"]["word_error_rate"]["value"]

    # 0.399 is what including the failures produced.
    assert abs(wer - 0.361) < 0.01, f"failures leaked into the mean: {wer}"


def test_the_sample_count_reports_what_was_scored():
    report = _mixed_report()
    assert report.overall["sahara"]["sample_count"]["value"] == 188
    assert report.overall["sahara"]["attempted_count"]["value"] == 200


def test_the_failure_rate_is_still_reported_in_full():
    # Excluding failures from the mean must not hide that they happened.
    report = _mixed_report()
    assert abs(report.overall["sahara"]["failure_rate"]["value"] - 0.06) < 0.005


def test_failure_causes_are_grouped_not_listed_per_occurrence():
    from app.benchmark.afriswitch_cli import _failure_reasons

    class _Row:
        def __init__(self, reason):
            self.failed = True
            self.failure_reason = reason

    class _Report:
        results = [
            _Row(
                f"AsrError: [sahara] transcription did not complete synchronously "
                f"(file_id {uuid}, status FILE_QUEUED). Poll the endpoint"
            )
            for uuid in (
                "ab0a08ab-92a8-4731-a479-694c11e2b364",
                "c8542c1f-f102-4ee6-a9c6-3a2b9cfe351a",
                "47585cf6-8ad4-409c-9322-a9435fbfc5cd",
            )
        ]

    reasons = _failure_reasons(_Report())

    # Twelve identical problems printed as twelve lines differing only by a UUID
    # buried the one thing worth knowing.
    assert len(reasons) == 1
    assert reasons[0][1] == 3


# ── rescoring a run that cannot be repeated ────────────────────────────────
# Provider calls cost money and a benchmark is not repeatable on a spent budget.
# A methodology fix therefore has to be applicable to a run that has already
# happened, from the per-utterance results saved alongside it.


def test_a_saved_run_can_be_rescored_without_any_api_call(tmp_path, monkeypatch):
    import json
    from argparse import Namespace

    from app.benchmark.afriswitch_cli import _rescore

    saved = {
        "config": "kinyarwanda",
        "providers": ["sahara"],
        "utterance_count": 10,
        "dataset_notes": [],
        "band_profile": {},
        "source": "afriswitch",
        "results": [
            {
                "utterance_id": f"kin_{index}",
                "provider": "sahara",
                "cmi": 15.0,
                "cmi_band": "moderate",
                "num_switch_points": 5,
                "duration": 4.0,
                "reference": "reference",
                "hypothesis": "" if index >= 8 else "hypothesis",
                "wer": 1.0 if index >= 8 else 0.30,
                "cer": 1.0 if index >= 8 else 0.20,
                "code_switch": {
                    "matrix_language_collapse_rate": 0.0,
                    "switch_point_preservation": 0.4,
                    "span_language_fidelity": 0.8,
                },
                "failed": index >= 8,
                "failure_reason": "AsrError: FILE_QUEUED" if index >= 8 else None,
            }
            for index in range(10)
        ],
    }

    source = tmp_path / "results.json"
    source.write_text(json.dumps(saved), encoding="utf-8")

    # Any call through the ASR registry would spend credit.
    def _forbidden(*args, **kwargs):
        raise AssertionError("rescoring must not reach a provider")

    monkeypatch.setattr("app.asr.registry.get_provider", _forbidden)

    code = _rescore(Namespace(input=str(source), bootstrap=100, out=str(tmp_path)))
    assert code == 0

    rescored = json.loads(
        next(tmp_path.glob("*rescored*.json")).read_text(encoding="utf-8")
    )

    # 0.30 over the eight successes, not 0.44 with the two failures averaged in.
    wer = rescored["overall"]["sahara"]["word_error_rate"]["value"]
    assert abs(wer - 0.30) < 0.01
    assert rescored["overall"]["sahara"]["sample_count"]["value"] == 8
    assert rescored["overall"]["sahara"]["attempted_count"]["value"] == 10


def test_rescore_reports_a_missing_input_rather_than_crashing(tmp_path):
    from argparse import Namespace

    from app.benchmark.afriswitch_cli import _rescore

    assert _rescore(Namespace(input=str(tmp_path / "nope.json"), bootstrap=10, out=None)) == 2

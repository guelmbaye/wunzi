"""
Sahara adapter, against the published contract.

https://docs.voice.intron.io/docs/stt/file-upload-sync

An earlier version of this adapter was written from guesswork: an invented
hostname, an invented path and an invented JSON body. It failed as a DNS error
twenty calls into a benchmark run. These tests pin the real shape.
"""

import pytest

from app.asr.base import AsrError
from app.asr.sahara import DEFAULT_BASE_URL, UPLOAD_SYNC_PATH, SaharaProvider, _language_code
from app.schemas.speech import TranscriptionConfig


# ── the request ────────────────────────────────────────────────────────────
def test_endpoint_matches_the_published_contract():
    assert DEFAULT_BASE_URL == "https://infer.voice.intron.io"
    assert UPLOAD_SYNC_PATH == "/file/v1/upload/sync"


def test_rw_covers_all_three_languages():
    # Intron documents `rw` as Kinyarwanda-English-French, flagged code-switched.
    # WUNZI's trilingual request must resolve to it, not to whichever code
    # happened to be listed first.
    assert _language_code(TranscriptionConfig(languages=["en", "fr", "rw"])) == "rw"
    assert _language_code(TranscriptionConfig()) == "rw"


def test_a_code_switched_code_wins_over_a_plain_one():
    assert _language_code(TranscriptionConfig(languages=["en", "sw"])) == "sw"


def test_language_names_are_mapped_to_codes():
    # AfriSwitch names its configs in full. Passing "kinyarwanda" straight
    # through produced `use_language_asr_input kinyarwanda is not supported`
    # on every call in a run.
    assert _language_code(TranscriptionConfig(languages=["kinyarwanda", "en"])) == "rw"
    assert _language_code(TranscriptionConfig(languages=["Kinyarwanda"])) == "rw"
    assert _language_code(TranscriptionConfig(languages=["swahili", "en"])) == "sw"


def test_an_unknown_name_is_passed_through_rather_than_guessed():
    # Better a clear rejection from the API than a silent substitution that
    # transcribes the wrong language.
    assert _language_code(TranscriptionConfig(languages=["klingon"])) == "klingon"


@pytest.mark.asyncio
async def test_the_form_disables_llm_corrections_by_default(monkeypatch):
    """
    Intron applies LLM post-processing by default, under a telehealth category.
    Benchmarking that against a raw Whisper transcript would compare a pipeline
    to a model, so corrections are off unless explicitly asked for.
    """
    captured = {}

    async def fake_post(provider, url, *, headers=None, files=None, data=None):
        captured.update({"url": url, "headers": headers, "files": files, "data": data})
        return {"data": {"audio_transcript": "ok"}}

    monkeypatch.setattr("app.asr.sahara.post_multipart", fake_post)
    monkeypatch.setattr("app.asr.sahara.read_audio_bytes", _bytes)

    provider = SaharaProvider(api_key="k", base_url=DEFAULT_BASE_URL)
    await provider.transcribe("/tmp/clip.wav", TranscriptionConfig())

    assert captured["url"] == DEFAULT_BASE_URL + UPLOAD_SYNC_PATH
    assert captured["headers"]["Authorization"] == "Bearer k"
    assert captured["data"]["use_disable_llm_corrections"] == "TRUE"
    assert captured["data"]["use_language_asr_input"] == "rw"
    # The telehealth default would apply medical corrections to a rental dispute.
    assert captured["data"]["use_category"] == "file_category_general"
    assert "audio_file_blob" in captured["files"]
    assert captured["data"]["audio_file_name"] == "clip.wav"


async def _bytes(uri):
    return b"RIFFfake"


# ── the response ───────────────────────────────────────────────────────────
def test_transcript_is_read_from_the_documented_field():
    provider = SaharaProvider(api_key="k")
    transcript = provider._normalize(
        {
            "data": {
                "file_id": "abc",
                "processing_status": "FILE_TRANSCRIBED",
                "audio_transcript": "Nishyuye deposit ya 150,000 RWF",
                "processed_audio_duration_in_seconds": 20,
                "use_language_asr_input": "rw",
            },
            "status": "Ok",
        }
    )

    assert transcript.text == "Nishyuye deposit ya 150,000 RWF"
    assert transcript.segments[0].end_ms == 20000


def test_no_confidence_is_invented():
    # The API returns none. Synthesising one would corrupt the Critical Speech
    # Guard, which reads it to decide whether to question the speaker.
    provider = SaharaProvider(api_key="k")
    transcript = provider._normalize(
        {"data": {"audio_transcript": "hello", "processed_audio_duration_in_seconds": 1}}
    )
    assert transcript.segments[0].confidence is None


def test_no_segment_boundaries_are_invented():
    # A flat transcript stays one segment. Splitting it into plausible spans
    # would falsify the audit trail every claim in a case is traced through.
    provider = SaharaProvider(api_key="k")
    transcript = provider._normalize(
        {"data": {"audio_transcript": "one two three four five", "processed_audio_duration_in_seconds": 5}}
    )
    assert len(transcript.segments) == 1


def test_an_incomplete_transcription_raises_rather_than_returning_empty():
    # A 503 hands back a file_id to poll. Returning "" instead would score as a
    # total miss and look like a model failure.
    provider = SaharaProvider(api_key="k")

    with pytest.raises(AsrError) as raised:
        provider._normalize(
            {"data": {"file_id": "abc-123", "processing_status": "FILE_PROCESSING"}}
        )

    assert "abc-123" in str(raised.value)


# ── a queued clip is not a model failure ───────────────────────────────────
@pytest.mark.asyncio
async def test_a_queued_clip_is_retried_before_being_called_a_failure(monkeypatch):
    """
    The sync endpoint occasionally accepts a file and returns FILE_QUEUED. Scored
    as an empty transcript that is a word error rate of 1.0 — blaming the model
    for a queue.
    """
    calls = []

    async def fake_post(provider, url, *, headers=None, files=None, data=None):
        calls.append(url)
        if len(calls) == 1:
            return {"data": {"file_id": "q-1", "processing_status": "FILE_QUEUED"}}
        return {"data": {"audio_transcript": "Nishyuye deposit", "processed_audio_duration_in_seconds": 3}}

    monkeypatch.setattr("app.asr.sahara.post_multipart", fake_post)
    monkeypatch.setattr("app.asr.sahara.read_audio_bytes", _bytes)
    monkeypatch.setattr("app.asr.sahara.asyncio.sleep", _no_sleep)

    provider = SaharaProvider(api_key="k", base_url=DEFAULT_BASE_URL)
    transcript = await provider.transcribe("/tmp/clip.wav", TranscriptionConfig())

    assert len(calls) == 2
    assert transcript.text == "Nishyuye deposit"


@pytest.mark.asyncio
async def test_a_clip_queued_every_time_still_raises(monkeypatch):
    # Retrying forever would hide a real problem behind a long run.
    async def always_queued(provider, url, *, headers=None, files=None, data=None):
        return {"data": {"file_id": "q-2", "processing_status": "FILE_QUEUED"}}

    monkeypatch.setattr("app.asr.sahara.post_multipart", always_queued)
    monkeypatch.setattr("app.asr.sahara.read_audio_bytes", _bytes)
    monkeypatch.setattr("app.asr.sahara.asyncio.sleep", _no_sleep)

    provider = SaharaProvider(api_key="k", base_url=DEFAULT_BASE_URL)

    with pytest.raises(AsrError) as raised:
        await provider.transcribe("/tmp/clip.wav", TranscriptionConfig())

    assert "q-2" in str(raised.value)


async def _no_sleep(seconds):
    return None


# ── a wrong model name must not cost a run ─────────────────────────────────
# `whisper-large-v3` is the Hugging Face name; OpenAI's hosted name is
# `whisper-1`. The wrong one 404s on every call, and a run of two hundred
# discovered it two hundred times before the preflight checked the model.


@pytest.mark.asyncio
async def test_a_missing_model_is_reported_before_the_run(monkeypatch):
    from app.asr.whisper import WhisperProvider

    class _Response:
        status_code = 404

    class _Client:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return False

        async def get(self, url, headers=None):
            return _Response()

    monkeypatch.setattr("httpx.AsyncClient", lambda **kwargs: _Client())

    error = await WhisperProvider(
        api_key="k", base_url="https://api.openai.com/v1", model="whisper-large-v3"
    ).verify_model()

    assert error is not None
    assert "whisper-1" in error, "the message must name the correct model"


@pytest.mark.asyncio
async def test_a_probe_that_cannot_answer_does_not_block_the_run(monkeypatch):
    # An unverifiable model is not the same as a missing one. A provider with no
    # models endpoint must not be refused on the strength of a failed probe.
    from app.asr.whisper import WhisperProvider

    def _explode(**kwargs):
        raise RuntimeError("no such endpoint")

    monkeypatch.setattr("httpx.AsyncClient", _explode)

    assert await WhisperProvider(api_key="k", base_url="https://x").verify_model() is None


@pytest.mark.asyncio
async def test_a_provider_without_a_probe_returns_none():
    from app.asr.sahara import SaharaProvider

    # Intron publishes no model listing. Guessing one would reintroduce exactly
    # the class of fabrication this check exists to catch.
    assert await SaharaProvider(api_key="k").verify_model() is None

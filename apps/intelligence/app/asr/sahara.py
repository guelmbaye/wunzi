"""
Sahara (Intron) adapter — the sponsor speech layer.

Written against the published contract at
https://docs.voice.intron.io/docs/stt/file-upload-sync

    POST https://infer.voice.intron.io/file/v1/upload/sync
    Authorization: Bearer <key>
    multipart/form-data:
        audio_file_name              required
        audio_file_blob              required, the audio file
        use_language_asr_input       required, e.g. "rw"
        use_disable_llm_corrections  optional, TRUE | FALSE
        use_category                 optional, defaults to telehealth

Language code `rw` is documented as **Kinyarwanda-English-French**, flagged as a
code-switched language. That is WUNZI's exact trilingual combination, handled as
one language rather than as three the caller must switch between.

WHAT THIS API DOES NOT RETURN
-----------------------------
A flat `audio_transcript` string. No segments, no timestamps, no per-segment
language, no confidence.

That matters downstream and is not papered over here. WUNZI's rule is that
provider metadata is never synthesised, so the normalised transcript carries one
segment spanning the clip with `language=None` and `confidence=None`. The
consequences, stated rather than discovered later:

  · the transcript view marks no code-switch boundaries for Sahara, because the
    API reports none — the switching happens inside the model, not in its output
  · the Critical Speech Guard loses its confidence signal and falls back to
    structural cues: negation ambiguity, attribution uncertainty, implausible
    amounts

The adapter contains no mediation logic whatsoever.
"""

from __future__ import annotations

import asyncio
from typing import Any

from app.asr.base import AsrError, AsrProvider
from app.asr.http_client import content_type_for, post_multipart, read_audio_bytes
from app.schemas.speech import NormalizedSegment, NormalizedTranscript, TranscriptionConfig

DEFAULT_BASE_URL = "https://infer.voice.intron.io"
UPLOAD_SYNC_PATH = "/file/v1/upload/sync"

# The sync endpoint refuses clips longer than this.
MAX_CLIP_SECONDS = 120


class SaharaProvider(AsrProvider):
    name = "sahara"

    # A clip occasionally comes back FILE_QUEUED instead of transcribed: the
    # sync endpoint accepted it but the worker had not finished. Scoring that as
    # an empty transcript would blame the model for a queue, so the upload is
    # repeated after a pause. Re-uploading is cheaper than polling an endpoint
    # whose contract this adapter has not verified.
    QUEUED_RETRIES = 2
    QUEUED_BACKOFF_SECONDS = 4.0

    async def _call(self, audio_uri: str, config: TranscriptionConfig) -> dict[str, Any]:
        audio = await read_audio_bytes(audio_uri)
        filename, mime = content_type_for(audio_uri)

        base = (self.base_url or DEFAULT_BASE_URL).rstrip("/")

        # One language code, not a list: `rw` already means
        # Kinyarwanda-English-French to this API.
        language = _language_code(config)

        form = {
            "audio_file_name": filename,
            "use_language_asr_input": language,
            # Post-processing runs an LLM over the transcript by default, and
            # the default category is telehealth — medical corrections applied
            # to a rental dispute. Benchmarking that against a raw Whisper
            # transcript would compare a pipeline to a model. The engine under
            # test is the ASR, so corrections are off unless asked for.
            "use_disable_llm_corrections": "FALSE" if config.llm_corrections else "TRUE",
            "use_category": config.category or "file_category_general",
        }

        response: dict[str, Any] = {}

        for attempt in range(self.QUEUED_RETRIES + 1):
            response = await post_multipart(
                self.name,
                base + UPLOAD_SYNC_PATH,
                headers={"Authorization": f"Bearer {self.api_key}"},
                files={"audio_file_blob": (filename, audio, mime)},
                data=form,
            )

            if not _is_incomplete(response):
                return response

            if attempt < self.QUEUED_RETRIES:
                await asyncio.sleep(self.QUEUED_BACKOFF_SECONDS * (attempt + 1))

        return response

    def _describe_rejection(self, message: str) -> str:
        """Turns an API rejection into something actionable."""
        if "use_language_asr_input" in message and "not supported" in message:
            return (
                f"{message}\n"
                f"Intron expects a code, not a language name. Supported "
                f"code-switched codes: {', '.join(CODE_SWITCHED)}. Kinyarwanda "
                f"is 'rw', documented as Kinyarwanda-English-French."
            )
        return message

    def _normalize(self, raw: dict[str, Any]) -> NormalizedTranscript:
        data = raw.get("data") or {}
        text = (data.get("audio_transcript") or "").strip()

        if not text and data.get("file_id"):
            # A 503 hands back a file_id to poll on the Get File Status
            # endpoint. That path is not implemented here, so the caller is told
            # plainly rather than handed an empty transcript that would score as
            # a total miss.
            raise AsrError(
                self.name,
                f"transcription did not complete synchronously (file_id "
                f"{data['file_id']}, status {data.get('processing_status')}). "
                "Poll the Get File Status endpoint, or use shorter clips: the "
                f"sync endpoint caps at {MAX_CLIP_SECONDS} seconds.",
            )

        duration = data.get("processed_audio_duration_in_seconds")
        end_ms = int(float(duration) * 1000) if duration else 0

        return NormalizedTranscript(
            provider=self.name,
            model=self.model,
            provider_version=None,
            text=text,
            # One segment for the whole clip. The API returns no boundaries, and
            # inventing them would falsify the audit trail every claim in a case
            # is traced through.
            segments=[
                NormalizedSegment(
                    start_ms=0,
                    end_ms=end_ms,
                    text=text,
                    language=data.get("use_language_asr_input"),
                    confidence=None,
                )
            ]
            if text
            else [],
            source_mode="live",
            raw=raw,
        )


# Intron takes ISO-ish codes, not language names. AfriSwitch names its configs
# in full ("kinyarwanda"), and passing that through produced
# `use_language_asr_input kinyarwanda is not supported` on every call.
LANGUAGE_ALIASES: dict[str, str] = {
    "kinyarwanda": "rw", "kinyarwanda-english-french": "rw", "kin": "rw", "rw": "rw",
    "swahili": "sw", "kiswahili": "sw", "sw": "sw",
    "yoruba": "yo", "yo": "yo",
    "igbo": "ig", "ig": "ig",
    "hausa": "ha", "ha": "ha",
    "zulu": "zu", "isizulu": "zu", "zu": "zu",
    "amharic": "am", "am": "am",
    "afrikaans": "af", "af": "af",
    "akan": "ak", "ak": "ak",
    "luganda": "lg", "ganda": "lg", "lg": "lg",
    "wolof": "wo", "wo": "wo",
    "pidgin": "pcm", "nigerian pidgin": "pcm", "pcm": "pcm",
    "english": "en", "en": "en",
    "french": "fr", "fr": "fr",
}

# Codes Intron documents as code-switched. Preferred over a plain code, because
# `rw` already means Kinyarwanda-English-French: choosing `en` for a trilingual
# clip would ask the model to hear one language out of three.
CODE_SWITCHED = ("rw", "sw", "yo", "ig", "ha", "zu", "am", "af", "ak", "lg", "wo", "pcm")


def _is_incomplete(response: dict[str, Any]) -> bool:
    """True when the endpoint accepted the file but returned no transcript."""
    data = response.get("data") or {}
    return not (data.get("audio_transcript") or "").strip() and bool(data.get("file_id"))


def _language_code(config: TranscriptionConfig) -> str:
    """One Intron language code from the requested languages or names."""
    resolved = [
        LANGUAGE_ALIASES.get(str(name).strip().lower(), str(name).strip().lower())
        for name in (config.languages or [])
    ]

    if not resolved:
        return "rw"

    for code in CODE_SWITCHED:
        if code in resolved:
            return code

    return resolved[0]

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, Header, HTTPException

from app.asr.base import AsrError
from app.asr.registry import get_provider
from app.config import get_settings
from app.idempotency import transcription_cache
from app.logging_setup import log_event
from app.schemas.speech import NormalizedTranscript, TranscribeRequest
from app.security import require_internal_token

router = APIRouter(prefix="/speech", tags=["speech"], dependencies=[Depends(require_internal_token)])
logger = logging.getLogger("wunzi.speech")


@router.post("/transcribe", response_model=NormalizedTranscript)
async def transcribe(
    request: TranscribeRequest,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> NormalizedTranscript:
    settings = get_settings()

    try:
        provider = get_provider(request.provider, settings, force_mode=request.mode)
    except KeyError as exc:
        # 400, not 502: a bad request will not become good on retry, and the
        # caller must not spend its retry budget on it.
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    audio_uri = (
        f"fixture://{request.fixture_key}"
        if request.fixture_key and (request.mode or settings.wunzi_mode) == "fixture"
        else request.audio_uri
    )

    async def call() -> NormalizedTranscript:
        return await provider.transcribe(audio_uri, request.config)

    try:
        # A retried POST returns the first result instead of paying for the ASR
        # call twice and producing a second transcript of the same audio.
        transcript = await transcription_cache.run(idempotency_key, call)
    except AsrError as exc:
        log_event(
            logger,
            "asr_failed",
            provider=request.provider,
            audio_id=request.audio_id,
            error=str(exc),
        )
        # A provider failure is an observable outcome, never a silent fallback to
        # another model: substituting providers would corrupt the benchmark and
        # falsify the case provenance.
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    log_event(
        logger,
        "transcript_generated",
        provider=transcript.provider,
        audio_id=request.audio_id,
        segments=len(transcript.segments),
        language_switches=transcript.language_switch_count,
        latency_ms=transcript.latency_ms,
        source_mode=transcript.source_mode,
        idempotent_replay=bool(idempotency_key),
    )

    return transcript

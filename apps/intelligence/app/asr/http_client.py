"""Shared HTTP plumbing for live provider calls."""

from __future__ import annotations

import asyncio
from typing import Any

import httpx

from app.asr.base import AsrError
from app.config import get_settings


async def post_json(
    provider: str,
    url: str,
    *,
    headers: dict[str, str] | None = None,
    json_body: dict[str, Any] | None = None,
    files: dict[str, Any] | None = None,
    data: dict[str, Any] | None = None,
) -> dict[str, Any]:
    settings = get_settings()
    last_error: Exception | None = None

    for attempt in range(settings.asr_max_retries + 1):
        try:
            async with httpx.AsyncClient(timeout=settings.asr_timeout_seconds) as client:
                response = await client.post(
                    url, headers=headers, json=json_body, files=files, data=data
                )

            if response.status_code == 429:
                # Intron documents 30 requests per minute and returns
                # Retry-After. Honouring it is cheaper than burning the retry
                # budget on calls the server has already told us to delay.
                delay = float(response.headers.get("Retry-After", "2") or 2)
                await asyncio.sleep(min(delay, 60.0))
                raise AsrError(provider, "rate limited", 429)

            if response.status_code >= 500:
                raise AsrError(provider, f"upstream error {response.status_code}", response.status_code)
            if response.status_code >= 400:
                # 4xx is not retried: a bad request will not become good.
                raise AsrError(provider, f"request rejected ({response.status_code}): {response.text[:200]}", response.status_code)

            return response.json()
        except (httpx.TimeoutException, httpx.TransportError, AsrError) as exc:
            last_error = exc
            # 429 is retried: the server asked for a delay, not for a different
            # request. Other 4xx will not become 2xx on a second attempt.
            if isinstance(exc, AsrError) and (exc.status_code or 500) < 500 and exc.status_code != 429:
                raise
            if attempt < settings.asr_max_retries:
                await asyncio.sleep(0.5 * (2**attempt))

    raise AsrError(provider, f"failed after retries: {last_error}")


# Announcing an MP3 as audio/wav is the kind of mismatch that produces a
# plausible-looking but wrong transcript, so the container is read from the
# filename rather than assumed.
CONTENT_TYPES = {
    ".wav": "audio/wav",
    ".mp3": "audio/mpeg",
    ".flac": "audio/flac",
    ".ogg": "audio/ogg",
    ".opus": "audio/opus",
    ".m4a": "audio/mp4",
    ".webm": "audio/webm",
}


def content_type_for(audio_uri: str) -> tuple[str, str]:
    """(filename, mime type) for a multipart upload."""
    from pathlib import PurePosixPath

    name = PurePosixPath(audio_uri.split("?")[0]).name or "audio.wav"
    suffix = PurePosixPath(name).suffix.lower()

    return name, CONTENT_TYPES.get(suffix, "audio/wav")


async def post_multipart(
    provider: str,
    url: str,
    *,
    headers: dict[str, str] | None = None,
    files: dict[str, Any] | None = None,
    data: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Multipart upload with the same retry budget as post_json."""
    return await post_json(provider, url, headers=headers, files=files, data=data)


async def read_audio_bytes(audio_uri: str) -> bytes:
    """
    Resolves an audio URI to bytes. s3:// goes through boto3; file paths and
    http(s) URLs are read directly.
    """
    if audio_uri.startswith("s3://"):
        return _read_s3(audio_uri)

    if audio_uri.startswith(("http://", "https://")):
        async with httpx.AsyncClient(timeout=get_settings().asr_timeout_seconds) as client:
            response = await client.get(audio_uri)
            response.raise_for_status()
            return response.content

    with open(audio_uri.replace("file://", ""), "rb") as handle:
        return handle.read()


def _read_s3(audio_uri: str) -> bytes:
    import boto3  # imported lazily so the service starts without AWS deps

    settings = get_settings()
    _, _, remainder = audio_uri.partition("s3://")
    bucket, _, key = remainder.partition("/")

    client = boto3.client(
        "s3",
        endpoint_url=settings.s3_endpoint,
        aws_access_key_id=settings.s3_access_key,
        aws_secret_access_key=settings.s3_secret_key,
    )
    return client.get_object(Bucket=bucket, Key=key)["Body"].read()

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

            if response.status_code >= 500:
                raise AsrError(provider, f"upstream error {response.status_code}", response.status_code)
            if response.status_code >= 400:
                # 4xx is not retried: a bad request will not become good.
                raise AsrError(provider, f"request rejected ({response.status_code}): {response.text[:200]}", response.status_code)

            return response.json()
        except (httpx.TimeoutException, httpx.TransportError, AsrError) as exc:
            last_error = exc
            if isinstance(exc, AsrError) and (exc.status_code or 500) < 500:
                raise
            if attempt < settings.asr_max_retries:
                await asyncio.sleep(0.5 * (2**attempt))

    raise AsrError(provider, f"failed after retries: {last_error}")


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

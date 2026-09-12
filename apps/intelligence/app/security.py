"""Laravel is the only production client of this surface."""

from __future__ import annotations

from fastapi import Header, HTTPException, status

from app.config import get_settings


async def require_internal_token(
    x_internal_service_token: str | None = Header(default=None),
) -> None:
    expected = get_settings().internal_ai_service_secret

    if not x_internal_service_token or x_internal_service_token != expected:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid internal service token.",
        )

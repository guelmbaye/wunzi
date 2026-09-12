from __future__ import annotations

from fastapi import APIRouter

from app.asr.registry import provider_names
from app.config import get_settings

router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> dict:
    settings = get_settings()

    return {
        "status": "ok",
        "service": "wunzi-intelligence",
        "mode": settings.wunzi_mode,
        "pipeline_version": settings.pipeline_version,
        "dataset_version": settings.dataset_version,
        "llm_provider": settings.llm_provider,
        "asr_providers": provider_names(),
        "boundaries": {
            "decides_truth": False,
            "scores_credibility": False,
            "recommends_liability": False,
            "gives_legal_advice": False,
            "resolves_autonomously": False,
        },
    }

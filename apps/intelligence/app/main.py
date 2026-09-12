"""
WUNZI intelligence service.

Owns speech, claims, criticality, comparison and case generation.
Owns no truth: Laravel is the System of Record, and a human mediator is the
decision-maker. This service can refuse to answer; it can never decide a case.
"""

from __future__ import annotations

import logging
import uuid

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.asr.base import AsrError
from app.config import get_settings
from app.intelligence.hallucination import HallucinationViolation
from app.intelligence.neutrality import NeutralityViolation
from app.logging_setup import configure_logging, log_event
from app.routers import benchmark, health, intelligence, speech

settings = get_settings()
configure_logging(settings.intelligence_log_level)
logger = logging.getLogger("wunzi")

app = FastAPI(
    title="WUNZI Intelligence Service",
    version="1.0.0",
    description=(
        "Switch-aware mediation intelligence. Structures what was said; "
        "never decides who is right."
    ),
)

# Laravel is the only production client and it calls /v1/*. /health stays
# unversioned so an orchestrator probe never depends on the API version.
API_PREFIX = "/v1"

app.include_router(health.router)
app.include_router(speech.router, prefix=API_PREFIX)
app.include_router(intelligence.router, prefix=API_PREFIX)
app.include_router(benchmark.router, prefix=API_PREFIX)


@app.middleware("http")
async def request_context(request: Request, call_next):
    request_id = request.headers.get("X-Request-Id") or str(uuid.uuid4())

    response = await call_next(request)
    response.headers["X-Request-Id"] = request_id
    response.headers["X-Pipeline-Version"] = settings.pipeline_version
    response.headers["X-Wunzi-Mode"] = settings.wunzi_mode

    log_event(
        logger,
        "http_request",
        request_id=request_id,
        method=request.method,
        path=request.url.path,
        status=response.status_code,
    )

    return response


@app.exception_handler(NeutralityViolation)
async def neutrality_handler(_: Request, exc: NeutralityViolation) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content={"error": "neutrality_violation", "matches": exc.matches},
    )


@app.exception_handler(HallucinationViolation)
async def hallucination_handler(_: Request, exc: HallucinationViolation) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content={"error": "unbacked_statement", "statements": exc.statements},
    )


@app.exception_handler(AsrError)
async def asr_handler(_: Request, exc: AsrError) -> JSONResponse:
    return JSONResponse(
        status_code=502,
        content={"error": "asr_failure", "provider": exc.provider, "detail": str(exc)},
    )

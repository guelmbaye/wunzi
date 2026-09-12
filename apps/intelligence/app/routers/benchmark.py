"""
Benchmark endpoints.

A full benchmark run is minutes of work across four ASR providers. Holding an
HTTP connection open for that long is how a run dies to a proxy idle timeout with
nothing written down. So the run is accepted, executed in the background, and
polled — Laravel's queue worker owns the waiting, not a socket.
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException

from app.benchmark.runner import BenchmarkRunner
from app.logging_setup import log_event
from app.schemas.benchmark import BenchmarkRunRequest, BenchmarkRunResponse, BenchmarkRunStatus
from app.security import require_internal_token

router = APIRouter(prefix="/benchmark", tags=["benchmark"], dependencies=[Depends(require_internal_token)])
logger = logging.getLogger("wunzi.benchmark")

# In-process run registry. The durable record is the `benchmark_runs` row in
# Postgres; this only tracks work in flight so Laravel can poll it.
_RUNS: dict[str, BenchmarkRunStatus] = {}
_MAX_RUNS = 50


@router.post("/run", response_model=BenchmarkRunStatus, status_code=202)
async def start_run(request: BenchmarkRunRequest, background: BackgroundTasks) -> BenchmarkRunStatus:
    try:
        runner = BenchmarkRunner()
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    run_id = request.run_id or str(uuid.uuid4())

    if run_id in _RUNS and _RUNS[run_id].state in {"QUEUED", "RUNNING"}:
        # Idempotent: a retried dispatch joins the existing run rather than
        # starting a second one over the same audio.
        return _RUNS[run_id]

    status = BenchmarkRunStatus(
        run_id=run_id,
        state="QUEUED",
        started_at=datetime.now(timezone.utc).isoformat(),
        providers=request.providers,
        split=request.split,
    )
    _remember(run_id, status)

    background.add_task(_execute, runner, request, run_id)
    return status


@router.get("/runs/{run_id}", response_model=BenchmarkRunStatus)
async def get_run(run_id: str) -> BenchmarkRunStatus:
    status = _RUNS.get(run_id)
    if status is None:
        raise HTTPException(status_code=404, detail=f"Unknown benchmark run '{run_id}'.")
    return status


@router.post("/run-sync", response_model=BenchmarkRunResponse)
async def run_sync(request: BenchmarkRunRequest) -> BenchmarkRunResponse:
    """Blocking variant for the CLI and tests. Not used by Laravel."""
    try:
        runner = BenchmarkRunner()
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    return await runner.run(request)


async def _execute(runner: BenchmarkRunner, request: BenchmarkRunRequest, run_id: str) -> None:
    _RUNS[run_id].state = "RUNNING"

    try:
        result = await runner.run(request)
        _RUNS[run_id].state = "COMPLETED"
        _RUNS[run_id].result = result
    except asyncio.CancelledError:
        _RUNS[run_id].state = "FAILED"
        _RUNS[run_id].error = "run cancelled during shutdown"
        raise
    except Exception as exc:  # noqa: BLE001 — the failure must be reportable, not fatal
        _RUNS[run_id].state = "FAILED"
        _RUNS[run_id].error = str(exc)
        log_event(logger, "benchmark_run_failed", run_id=run_id, error=str(exc))
    finally:
        _RUNS[run_id].finished_at = datetime.now(timezone.utc).isoformat()


def _remember(run_id: str, status: BenchmarkRunStatus) -> None:
    if len(_RUNS) >= _MAX_RUNS:
        finished = [k for k, v in _RUNS.items() if v.state in {"COMPLETED", "FAILED"}]
        for key in finished[: len(finished) // 2 or 1]:
            _RUNS.pop(key, None)
    _RUNS[run_id] = status

from __future__ import annotations

from pydantic import BaseModel, Field


class BenchmarkRunRequest(BaseModel):
    run_id: str | None = None
    dataset_version: str = "dataset-v1"
    split: str = "holdout"
    providers: list[str] = Field(default_factory=lambda: ["sahara", "whisper", "model_b", "model_c"])
    guard_enabled: bool = True
    pipeline_version: str | None = None
    prompt_version: str | None = None
    bootstrap_samples: int = 1000


class MetricRow(BaseModel):
    provider: str
    metric: str
    value: float
    ci_low: float | None = None
    ci_high: float | None = None
    scope: str = "overall"
    sample_count: int | None = None


class ObservationRow(BaseModel):
    clip_id: str
    scenario_id: str
    provider: str
    transcript: str | None = None
    critical_facts: dict | None = None
    claims: list[dict] | None = None
    issue_states: dict | None = None
    expected_issue_states: dict | None = None
    case_state_correct: bool | None = None
    error_taxonomy: list[str] | None = None
    latency_ms: int | None = None
    provider_failed: bool = False
    used_placeholder_fixture: bool = False


class BenchmarkRunResponse(BaseModel):
    run_id: str | None = None
    dataset_version: str
    split: str
    metrics: list[MetricRow] = Field(default_factory=list)
    observations: list[ObservationRow] = Field(default_factory=list)
    summary: dict = Field(default_factory=dict)
    sponsor_outcome_delta: float | None = None
    best_competitor: str | None = None
    git_commit: str | None = None
    publishable: bool = True
    publishability_note: str | None = None
    integrity: str = "Same audio · same claim engine · same Issue Graph logic — only the ASR provider changed."


class BenchmarkRunStatus(BaseModel):
    """Poll target. Laravel's queue worker waits; the HTTP connection does not."""

    run_id: str
    state: str = "QUEUED"  # QUEUED | RUNNING | COMPLETED | FAILED
    providers: list[str] = Field(default_factory=list)
    split: str = "holdout"
    started_at: str | None = None
    finished_at: str | None = None
    result: BenchmarkRunResponse | None = None
    error: str | None = None

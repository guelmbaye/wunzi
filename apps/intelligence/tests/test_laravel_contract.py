"""
Laravel ↔ FastAPI contract test.

These payloads are copied from the Laravel services that build them, field for
field. They exist because the two services are written in different languages
and nothing else checks that `IntelligenceClient` and the Pydantic schemas agree:
a renamed field or a moved route fails silently in staging and loudly in a demo.

If a Laravel service changes what it sends, this test must change with it.
Sources:
  TranscriptionService::transcribe   -> /v1/speech/transcribe
  ClaimIngestionService::ingest      -> /v1/intelligence/analyze-turn
  IssueGraphService::build           -> /v1/intelligence/build-issue-graph
  CasePacketService::generate        -> /v1/intelligence/generate-case
  BenchmarkService::start            -> /v1/benchmark/run  (+ /runs/{id})
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.config import get_settings
from app.main import app

CASE_ID = "9f1c2b3a-0000-4000-8000-000000000001"
PARTY_A_ID = "9f1c2b3a-0000-4000-8000-00000000000a"
PARTY_B_ID = "9f1c2b3a-0000-4000-8000-00000000000b"


@pytest.fixture(scope="module")
def client() -> TestClient:
    settings = get_settings()
    return TestClient(app, headers={"X-Internal-Service-Token": settings.internal_ai_service_secret})


# ── routing ────────────────────────────────────────────────────────────────
def test_health_is_unversioned(client: TestClient) -> None:
    # Laravel probes /health, not /v1/health: an orchestrator check must not
    # break when the API version moves.
    assert client.get("/health").status_code == 200


@pytest.mark.parametrize(
    "path",
    [
        "/v1/speech/transcribe",
        "/v1/intelligence/analyze-turn",
        "/v1/intelligence/extract-claims",
        "/v1/intelligence/evaluate-criticality",
        "/v1/intelligence/build-issue-graph",
        "/v1/intelligence/generate-case",
        "/v1/benchmark/run",
    ],
    ids=lambda p: p,
)
def test_every_route_laravel_calls_exists(client: TestClient, path: str) -> None:
    # An empty body must be rejected as invalid (422), never as missing (404).
    assert client.post(path, json={}).status_code != 404


def test_internal_token_is_required(client: TestClient) -> None:
    response = TestClient(app).post("/v1/intelligence/analyze-turn", json={})
    assert response.status_code in (401, 403)


# ── transcription ──────────────────────────────────────────────────────────
def test_transcribe_accepts_the_laravel_payload(client: TestClient) -> None:
    response = client.post(
        "/v1/speech/transcribe",
        json={
            "audio_id": "aud-1",
            "audio_uri": "fixture://WZ_DEMO_001_A",
            "audio_sha256": "0" * 64,
            "provider": "sahara",
            "mode": "fixture",
            "fixture_key": "WZ_DEMO_001_A",
            "pipeline_version": "pipeline-v1",
        },
        headers={"Idempotency-Key": "contract-test-key"},
    )
    assert response.status_code == 200

    body = response.json()
    # Every field TranscriptionService reads off the response.
    for field in ("text", "segments", "model", "provider_version", "source_mode", "fixture_origin", "latency_ms"):
        assert field in body, f"TranscriptionService reads '{field}'"

    for segment in body["segments"]:
        assert {"start_ms", "end_ms", "text", "language", "confidence"} <= set(segment)


def test_unknown_provider_is_a_client_error(client: TestClient) -> None:
    # 400 not 502: the caller must not spend its retry budget on a bad request.
    response = client.post(
        "/v1/speech/transcribe",
        json={"audio_id": "a", "audio_uri": "fixture://x", "provider": "not_a_provider"},
    )
    assert response.status_code == 400


def test_idempotency_key_replays_instead_of_recalling(client: TestClient) -> None:
    payload = {
        "audio_id": "aud-2",
        "audio_uri": "fixture://WZ_DEMO_001_B",
        "provider": "sahara",
        "mode": "fixture",
        "fixture_key": "WZ_DEMO_001_B",
    }
    headers = {"Idempotency-Key": "replay-me"}

    first = client.post("/v1/speech/transcribe", json=payload, headers=headers).json()
    second = client.post("/v1/speech/transcribe", json=payload, headers=headers).json()

    assert first["text"] == second["text"]
    # Identical latency proves the second call replayed rather than re-ran.
    assert first["latency_ms"] == second["latency_ms"]


# ── analyze-turn ───────────────────────────────────────────────────────────
def _turn_payload(role: str, text: str) -> dict:
    return {
        "case_id": CASE_ID,
        "party_id": PARTY_A_ID if role == "PARTY_A" else PARTY_B_ID,
        "party_role": role,
        "transcript_run_id": "run-1",
        "provider": "sahara",
        "transcript": text,
        "segments": [
            {
                "segment_id": f"seg-{role}-0",
                "sequence": 0,
                "start_ms": 0,
                "end_ms": 4000,
                "text": text,
                "language": "rw",
                "confidence": 0.94,
            }
        ],
        "issue_types": ["deposit_amount", "refund_commitment"],
        "pipeline_version": "pipeline-v1",
        "asr_metadata": {"provider": "sahara", "segment_confidences": [0.94]},
        "guard_enabled": True,
    }


def test_analyze_turn_returns_claims_and_guard_verdicts_together(client: TestClient) -> None:
    response = client.post(
        "/v1/intelligence/analyze-turn",
        json=_turn_payload("PARTY_A", "Nishyuye deposit ya 150,000 RWF."),
    )
    assert response.status_code == 200

    body = response.json()
    assert {"claims", "supersessions", "decisions", "extraction_version", "guard_version"} <= set(body)
    assert body["claims"], "the demo sentence must yield at least one claim"

    for claim in body["claims"]:
        # Exactly the keys ClaimIngestionService writes into the claims table.
        assert {
            "claim_id", "type", "subject", "predicate", "canonical_value",
            "polarity", "certainty", "criticality", "reported_speech",
            "extraction_confidence", "attribution_confidence", "source_segments",
        } <= set(claim)

    for decision in body["decisions"]:
        assert {"claim_id", "risk", "decision", "reasons", "fields"} <= set(decision)
        for field in decision["fields"]:
            assert {"field_type", "detected_value", "normalized_value", "prompt_text"} <= set(field)


def test_guard_verdicts_reference_returned_claims(client: TestClient) -> None:
    # ClaimIngestionService keys decisions by claim_id. A mismatch would silently
    # drop every critical field instead of failing.
    body = client.post(
        "/v1/intelligence/analyze-turn",
        json=_turn_payload("PARTY_A", "Nishyuye deposit ya 150,000 RWF."),
    ).json()

    claim_ids = {c["claim_id"] for c in body["claims"]}
    assert {d["claim_id"] for d in body["decisions"]} <= claim_ids


def test_source_segments_reference_the_ids_laravel_sent(client: TestClient) -> None:
    # These become claim_sources.transcript_segment_id — a foreign key.
    body = client.post(
        "/v1/intelligence/analyze-turn",
        json=_turn_payload("PARTY_A", "Nishyuye deposit ya 150,000 RWF."),
    ).json()

    for claim in body["claims"]:
        assert set(claim["source_segments"]) <= {"seg-PARTY_A-0"}


# ── issue graph ────────────────────────────────────────────────────────────
def _comparable(claim_id: str, type_: str, value: dict, polarity: str = "POSITIVE") -> dict:
    return {
        "claim_id": claim_id,
        "type": type_,
        "subject": "party_a",
        "predicate": type_,
        "canonical_value": value,
        "polarity": polarity,
        "criticality": "HIGH",
        "verification_status": "UNVERIFIED",
        "reported_speech": False,
        "has_pending_critical_field": False,
    }


def test_build_issue_graph_accepts_the_laravel_payload(client: TestClient) -> None:
    response = client.post(
        "/v1/intelligence/build-issue-graph",
        json={
            "case_id": CASE_ID,
            "issue_types": ["deposit_amount"],
            "critical_issue_types": ["deposit_amount"],
            "party_a": [_comparable("cl-a", "deposit_amount", {"amount_minor": 150000, "currency": "RWF"})],
            "party_b": [_comparable("cl-b", "deposit_amount", {"amount_minor": 100000, "currency": "RWF"})],
            "pipeline_version": "pipeline-v1",
        },
    )
    assert response.status_code == 200

    body = response.json()
    issue = body["issues"][0]
    assert {
        "canonical_type", "status", "criticality", "summary", "reason",
        "party_a_value", "party_b_value", "confidence",
        "supporting_claim_ids", "conflicting_claim_ids",
    } <= set(issue)
    assert issue["status"] == "DISPUTED"


def test_evidence_names_a_role_never_a_party_id(client: TestClient) -> None:
    # IssueGraphService resolves this to a party_id FK. If FastAPI returned
    # "party_a" into that column the insert would violate the constraint.
    body = client.post(
        "/v1/intelligence/build-issue-graph",
        json={
            "case_id": CASE_ID,
            "party_a": [],
            "party_b": [
                {
                    **_comparable("cl-b", "evidence_mention", {"evidence_type": "repair_invoice"}),
                    "type": "evidence_mention",
                }
            ],
        },
    ).json()

    for evidence in body["evidence"]:
        assert "mentioned_by" not in evidence, "a party id must never be implied here"
        assert evidence.get("mentioned_by_role") in (None, "PARTY_A", "PARTY_B")


def test_claim_ids_survive_the_round_trip(client: TestClient) -> None:
    # These come back as issue_claims.claim_id, so they must be echoed verbatim.
    body = client.post(
        "/v1/intelligence/build-issue-graph",
        json={
            "case_id": CASE_ID,
            "party_a": [_comparable("cl-a", "deposit_amount", {"amount_minor": 150000})],
            "party_b": [_comparable("cl-b", "deposit_amount", {"amount_minor": 100000})],
        },
    ).json()

    echoed = {
        cid
        for issue in body["issues"]
        for cid in issue["supporting_claim_ids"] + issue["conflicting_claim_ids"]
    }
    assert echoed <= {"cl-a", "cl-b"}


# ── case packet ────────────────────────────────────────────────────────────
def test_generate_case_accepts_the_laravel_payload(client: TestClient) -> None:
    response = client.post(
        "/v1/intelligence/generate-case",
        json={
            "case_id": CASE_ID,
            "public_reference": "WZ-2026-0001",
            "category": "rental_deposit",
            "parties": [
                {"party_id": PARTY_A_ID, "role": "PARTY_A", "display_name": "Party A"},
                {"party_id": PARTY_B_ID, "role": "PARTY_B", "display_name": "Party B"},
            ],
            "claims": [
                {
                    "claim_id": "cl-a",
                    "party_role": "PARTY_A",
                    "type": "deposit_amount",
                    "subject": "party_a",
                    "predicate": "states_deposit_amount",
                    "canonical_value": {"amount_minor": 150000, "currency": "RWF"},
                    "polarity": "POSITIVE",
                    "reported_speech": False,
                    "verification_status": "UNVERIFIED",
                }
            ],
            "issues": [
                {
                    "issue_id": "is-1",
                    "canonical_type": "deposit_amount",
                    "status": "DISPUTED",
                    "reason": "normalized values differ",
                    "party_a_value": {"amount_minor": 150000},
                    "party_b_value": {"amount_minor": 100000},
                }
            ],
            "evidence": [
                {
                    "evidence_id": "ev-1",
                    "type": "repair_invoice",
                    "availability": "MENTIONED_NOT_PROVIDED",
                    "description": "Mentioned by Party B.",
                }
            ],
        },
    )
    assert response.status_code == 200

    body = response.json()
    assert {"packet", "statements", "model", "prompt_version"} <= set(body)

    for statement in body["statements"]:
        assert {"text", "kind", "claim_id", "issue_id"} <= set(statement)
        assert statement["kind"] in {
            "SOURCE_CLAIM", "DERIVED_RELATION", "MISSING_INFORMATION", "SYSTEM_METADATA",
        }
        # HallucinationValidator on the Laravel side checks the same rule against
        # its own ids; the two implementations must not diverge.
        if statement["kind"] == "SOURCE_CLAIM":
            assert statement["claim_id"] in {"cl-a"}
        if statement["kind"] == "DERIVED_RELATION":
            assert statement["issue_id"] in {"is-1"}


# ── benchmark ──────────────────────────────────────────────────────────────
def test_benchmark_is_accepted_not_awaited(client: TestClient) -> None:
    # A synchronous 30-minute HTTP call is how a run dies to a proxy idle
    # timeout with nothing written down.
    response = client.post(
        "/v1/benchmark/run",
        json={
            "run_id": "bench-contract-1",
            "dataset_version": "dataset-v1",
            "split": "dev",
            "providers": ["sahara", "whisper"],
            "guard_enabled": True,
            "pipeline_version": "pipeline-v1",
            "prompt_version": "claim-extraction-v1",
        },
    )
    assert response.status_code == 202
    assert response.json()["run_id"] == "bench-contract-1"


def test_benchmark_status_is_pollable(client: TestClient) -> None:
    client.post(
        "/v1/benchmark/run",
        json={"run_id": "bench-contract-2", "split": "dev", "providers": ["sahara"]},
    )

    status = client.get("/v1/benchmark/runs/bench-contract-2")
    assert status.status_code == 200

    body = status.json()
    assert {"run_id", "state", "result", "error"} <= set(body)
    assert body["state"] in {"QUEUED", "RUNNING", "COMPLETED", "FAILED"}


def test_unknown_benchmark_run_is_404(client: TestClient) -> None:
    assert client.get("/v1/benchmark/runs/does-not-exist").status_code == 404

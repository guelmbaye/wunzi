"""
The demo golden path, end to end.

Runs the WZ_DEMO_001 rental deposit dispute through every stage the product
actually uses — transcribe both accounts, analyse each turn, build the issue
graph, generate the case packet — and asserts the mediation state a mediator
would be handed.

This is the test that would catch a regression nobody notices otherwise: each
component can pass its own unit tests while the composition produces a case that
says the wrong thing. The assertions below are about meaning, not shape.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.config import get_settings
from app.main import app

CASE_ID = "wz-demo-001"

# Ground truth from benchmark/annotations/WZ_DEMO_001.json. If the pipeline and
# the annotation ever disagree, one of them is wrong and a human must decide
# which — never quietly relax the expectation to make the test pass.
EXPECTED_STATES = {
    "deposit_exists": "AGREED",
    "deposit_amount": "DISPUTED",
    "tenancy_end_date": "MISSING",
    "damage_exists": "DISPUTED",
    "damage_responsibility": "DISPUTED",
    "repair_cost": "MISSING",
    "refund_commitment": "DISPUTED",
    "repair_evidence": "MISSING",
    "requested_outcome": "DISPUTED",
}


@pytest.fixture(scope="module")
def client() -> TestClient:
    settings = get_settings()
    return TestClient(app, headers={"X-Internal-Service-Token": settings.internal_ai_service_secret})


def _transcribe(client: TestClient, clip: str, provider: str = "sahara") -> dict:
    response = client.post(
        "/v1/speech/transcribe",
        json={
            "audio_id": clip,
            "audio_uri": f"fixture://{clip}",
            "provider": provider,
            "mode": "fixture",
            "fixture_key": clip,
        },
    )
    assert response.status_code == 200, response.text
    return response.json()


def _analyze(client: TestClient, clip: str, role: str, transcript: dict) -> dict:
    segments = [
        {
            "segment_id": f"{clip}-{index}",
            "sequence": index,
            "start_ms": segment["start_ms"],
            "end_ms": segment["end_ms"],
            "text": segment["text"],
            "language": segment["language"],
            "confidence": segment["confidence"],
        }
        for index, segment in enumerate(transcript["segments"])
    ]

    response = client.post(
        "/v1/intelligence/analyze-turn",
        json={
            "case_id": CASE_ID,
            "party_id": f"party-{role}",
            "party_role": role,
            "provider": "sahara",
            "transcript": transcript["text"],
            "segments": segments,
            "asr_metadata": {
                "provider": "sahara",
                "segment_confidences": [s["confidence"] for s in transcript["segments"]],
            },
            "guard_enabled": True,
        },
    )
    assert response.status_code == 200, response.text
    return response.json()


def _comparable(claim: dict, pending: set[str]) -> dict:
    return {
        "claim_id": claim["claim_id"],
        "type": claim["type"],
        "subject": claim["subject"],
        "predicate": claim["predicate"],
        "canonical_value": claim["canonical_value"],
        "polarity": claim["polarity"],
        "criticality": claim["criticality"],
        "verification_status": claim["verification_status"],
        "reported_speech": claim["reported_speech"],
        "has_pending_critical_field": claim["claim_id"] in pending,
    }


@pytest.fixture(scope="module")
def golden(client: TestClient) -> dict:
    """Both accounts, analysed and compared, exactly as Laravel would drive it."""
    turns = {}
    pending: set[str] = set()

    for clip, role in (("WZ_DEMO_001_A", "PARTY_A"), ("WZ_DEMO_001_B", "PARTY_B")):
        transcript = _transcribe(client, clip)
        turn = _analyze(client, clip, role, transcript)
        turns[role] = turn
        pending |= {
            decision["claim_id"]
            for decision in turn["decisions"]
            if decision["decision"] != "ACCEPT_FOR_CASE"
        }

    graph = client.post(
        "/v1/intelligence/build-issue-graph",
        json={
            "case_id": CASE_ID,
            "party_a": [_comparable(c, pending) for c in turns["PARTY_A"]["claims"]],
            "party_b": [_comparable(c, pending) for c in turns["PARTY_B"]["claims"]],
        },
    )
    assert graph.status_code == 200, graph.text

    return {"turns": turns, "pending": pending, "graph": graph.json()}


# ── the mediation state ────────────────────────────────────────────────────
def test_issue_states_match_the_annotation(golden: dict) -> None:
    produced = {issue["canonical_type"]: issue["status"] for issue in golden["graph"]["issues"]}
    assert produced == EXPECTED_STATES


def test_the_two_deposit_amounts_are_not_reconciled(golden: dict) -> None:
    issue = next(
        i for i in golden["graph"]["issues"] if i["canonical_type"] == "deposit_amount"
    )

    assert issue["status"] == "DISPUTED"
    assert issue["party_a_value"]["amount_minor"] == 150000
    assert issue["party_b_value"]["amount_minor"] == 100000

    # No averaging, no picking a side, no third number anywhere in the issue.
    rendered = f"{issue['summary']} {issue['reason']}"
    assert "125000" not in rendered and "125,000" not in rendered


def test_the_denied_refund_promise_survives_the_language_switch(golden: dict) -> None:
    """
    Party A reports a promise; Party B denies making it, in Kinyarwanda, in a
    sentence that follows an English one. If the negation is lost, this issue
    collapses to AGREED and a mediator walks in believing a promise was made.
    """
    issue = next(
        i for i in golden["graph"]["issues"] if i["canonical_type"] == "refund_commitment"
    )
    assert issue["status"] == "DISPUTED"

    b_claims = golden["turns"]["PARTY_B"]["claims"]
    denial = [c for c in b_claims if c["type"] == "refund_denial"]
    assert denial, "Party B's denial must be extracted as its own claim"
    assert denial[0]["polarity"] == "NEGATIVE"


def test_party_a_quoting_party_b_is_not_recorded_as_party_b_speaking(golden: dict) -> None:
    a_claims = golden["turns"]["PARTY_A"]["claims"]
    commitment = [c for c in a_claims if c["type"] == "refund_commitment"]

    assert commitment, "the reported promise must be extracted"
    assert commitment[0]["reported_speech"] is True
    assert commitment[0]["party_role"] == "PARTY_A"
    assert commitment[0]["subject"] == "party_b"


def test_mentioned_evidence_is_not_treated_as_provided(golden: dict) -> None:
    repair = next(
        i for i in golden["graph"]["issues"] if i["canonical_type"] == "repair_evidence"
    )
    assert repair["status"] == "MISSING"

    invoice = [e for e in golden["graph"]["evidence"] if e["type"] == "repair_invoice"]
    assert invoice and invoice[0]["availability"] == "MENTIONED_NOT_PROVIDED"


def test_evidence_names_a_role_not_a_party_id(golden: dict) -> None:
    for evidence in golden["graph"]["evidence"]:
        assert evidence.get("mentioned_by_role") in (None, "PARTY_A", "PARTY_B")


# ── the packet ─────────────────────────────────────────────────────────────
@pytest.fixture(scope="module")
def packet(client: TestClient, golden: dict) -> dict:
    claims = [
        {
            "claim_id": claim["claim_id"],
            "party_role": role,
            "type": claim["type"],
            "subject": claim["subject"],
            "predicate": claim["predicate"],
            "canonical_value": claim["canonical_value"],
            "polarity": claim["polarity"],
            "reported_speech": claim["reported_speech"],
            "verification_status": claim["verification_status"],
        }
        for role, turn in golden["turns"].items()
        for claim in turn["claims"]
    ]

    issues = [
        {
            "issue_id": f"issue-{index}",
            "canonical_type": issue["canonical_type"],
            "status": issue["status"],
            "reason": issue["reason"],
            "party_a_value": issue["party_a_value"],
            "party_b_value": issue["party_b_value"],
        }
        for index, issue in enumerate(golden["graph"]["issues"])
    ]

    response = client.post(
        "/v1/intelligence/generate-case",
        json={
            "case_id": CASE_ID,
            "public_reference": "WZ-2026-0001",
            "category": "rental_deposit",
            "parties": [
                {"party_id": "party-a", "role": "PARTY_A", "display_name": "Tenant"},
                {"party_id": "party-b", "role": "PARTY_B", "display_name": "Landlord"},
            ],
            "claims": claims,
            "issues": issues,
            "evidence": [
                {
                    "evidence_id": f"ev-{index}",
                    "type": item["type"],
                    "availability": item["availability"],
                    "description": item["description"],
                }
                for index, item in enumerate(golden["graph"]["evidence"])
            ],
        },
    )
    assert response.status_code == 200, response.text
    return response.json()


def test_packet_separates_the_four_states(packet: dict) -> None:
    payload = packet["packet"]
    assert payload["disputed"], "the demo case has disputed issues"
    assert payload["missing_information"], "the demo case has missing information"
    assert payload["status_label"] == "Ready for Human Mediator"


def test_every_packet_sentence_carries_provenance(packet: dict) -> None:
    claim_ids = {
        statement["claim_id"] for statement in packet["statements"] if statement["claim_id"]
    }
    for statement in packet["statements"]:
        assert statement["kind"] in {
            "SOURCE_CLAIM",
            "DERIVED_RELATION",
            "MISSING_INFORMATION",
            "SYSTEM_METADATA",
        }
        if statement["kind"] == "SOURCE_CLAIM":
            assert statement["claim_id"] in claim_ids


def test_packet_never_adjudicates(packet: dict) -> None:
    """
    The guard runs server-side, but assert the outcome here too: a packet that
    told a mediator who was right would be the product's worst failure, and it
    should be caught by the test that exercises the real demo case.
    """
    text = " ".join(statement["text"] for statement in packet["statements"]).lower()

    for forbidden in (
        "is lying",
        "is correct",
        "is wrong",
        "should pay",
        "liable",
        "at fault",
        "credible",
        "the truth is",
    ):
        assert forbidden not in text, f"packet contains adjudicative language: {forbidden}"


def test_packet_attributes_every_claim_to_a_party(packet: dict) -> None:
    for statement in packet["statements"]:
        if statement["kind"] != "SOURCE_CLAIM":
            continue
        assert statement["text"].startswith(("Party A", "Party B")), statement["text"]


# ── the sponsor proof ──────────────────────────────────────────────────────
def test_a_misheard_amount_changes_the_mediation_state(client: TestClient) -> None:
    """
    The claim the benchmark exists to support, exercised through the product
    rather than the scoring code: swap only the speech model and the case a
    mediator receives changes.
    """
    states_by_provider: dict[str, dict[str, str]] = {}

    for provider in ("sahara", "whisper"):
        pending: set[str] = set()
        turns = {}

        for clip, role in (("WZ_DEMO_001_A", "PARTY_A"), ("WZ_DEMO_001_B", "PARTY_B")):
            transcript = _transcribe(client, clip, provider)
            turn = _analyze(client, clip, role, transcript)
            turns[role] = turn
            pending |= {
                d["claim_id"] for d in turn["decisions"] if d["decision"] != "ACCEPT_FOR_CASE"
            }

        graph = client.post(
            "/v1/intelligence/build-issue-graph",
            json={
                "case_id": CASE_ID,
                "party_a": [_comparable(c, pending) for c in turns["PARTY_A"]["claims"]],
                "party_b": [_comparable(c, pending) for c in turns["PARTY_B"]["claims"]],
            },
        ).json()

        states_by_provider[provider] = {
            issue["canonical_type"]: issue["status"] for issue in graph["issues"]
        }

    assert states_by_provider["sahara"] == EXPECTED_STATES

    # These fixtures are hand-written placeholders, so this asserts the
    # mechanism — a degraded transcript propagates to a different mediation
    # state — and says nothing about any provider's real accuracy.
    assert states_by_provider["whisper"] != states_by_provider["sahara"]

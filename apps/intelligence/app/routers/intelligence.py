from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException

from app.intelligence.case_packet import CasePacketGenerator
from app.intelligence.claim_extractor import ClaimExtractor
from app.intelligence.criticality import CriticalSpeechGuard
from app.intelligence.hallucination import HallucinationViolation
from app.intelligence.issue_graph import IssueGraphBuilder
from app.intelligence.neutrality import NeutralityViolation
from app.logging_setup import log_event
from app.schemas.claims import (
    AnalyzeTurnRequest,
    AnalyzeTurnResponse,
    EvaluateCriticalityRequest,
    EvaluateCriticalityResponse,
    ExtractClaimsRequest,
    ExtractClaimsResponse,
)
from app.schemas.issues import BuildIssueGraphRequest, BuildIssueGraphResponse
from app.schemas.packet import GenerateCaseRequest, GenerateCaseResponse
from app.security import require_internal_token

router = APIRouter(
    prefix="/intelligence", tags=["intelligence"], dependencies=[Depends(require_internal_token)]
)
logger = logging.getLogger("wunzi.intelligence")

extractor = ClaimExtractor()
guard = CriticalSpeechGuard()
graph_builder = IssueGraphBuilder()
packet_generator = CasePacketGenerator()


@router.post("/analyze-turn", response_model=AnalyzeTurnResponse)
async def analyze_turn(request: AnalyzeTurnRequest) -> AnalyzeTurnResponse:
    """
    One party's turn, start to finish: extraction plus the Critical Speech Guard.
    Laravel calls this once per recording instead of shipping the claim set out
    and back for a second verdict.
    """
    claims, supersessions = extractor.extract(
        segments=request.segments,
        party_id=request.party_id,
        party_role=request.party_role,
        transcript=request.transcript,
    )

    decisions = guard.evaluate(claims, request.asr_metadata, request.guard_enabled)

    log_event(
        logger,
        "turn_analyzed",
        case_id=request.case_id,
        party_role=request.party_role,
        provider=request.provider,
        claims=len(claims),
        supersessions=len(supersessions),
        needs_confirmation=sum(1 for d in decisions if d.decision == "NEEDS_CONFIRMATION"),
        rejected=sum(1 for d in decisions if d.decision == "REJECT_AS_UNRESOLVED"),
    )

    return AnalyzeTurnResponse(
        claims=claims,
        supersessions=supersessions,
        decisions=decisions,
        extraction_version=extractor.version,
        guard_version=guard.version,
    )


@router.post("/extract-claims", response_model=ExtractClaimsResponse)
async def extract_claims(request: ExtractClaimsRequest) -> ExtractClaimsResponse:
    claims, supersessions = extractor.extract(
        segments=request.segments,
        party_id=request.party_id,
        party_role=request.party_role,
        transcript=request.transcript,
    )

    log_event(
        logger,
        "claims_extracted",
        case_id=request.case_id,
        party_role=request.party_role,
        provider=request.provider,
        claims=len(claims),
        supersessions=len(supersessions),
    )

    return ExtractClaimsResponse(
        claims=claims,
        supersessions=supersessions,
        extraction_version=extractor.version,
    )


@router.post("/evaluate-criticality", response_model=EvaluateCriticalityResponse)
async def evaluate_criticality(request: EvaluateCriticalityRequest) -> EvaluateCriticalityResponse:
    decisions = guard.evaluate(request.claims, request.asr_metadata, request.guard_enabled)

    log_event(
        logger,
        "guard_evaluated",
        case_id=request.case_id,
        enabled=request.guard_enabled,
        claims=len(request.claims),
        needs_confirmation=sum(1 for d in decisions if d.decision == "NEEDS_CONFIRMATION"),
        rejected=sum(1 for d in decisions if d.decision == "REJECT_AS_UNRESOLVED"),
    )

    return EvaluateCriticalityResponse(decisions=decisions, guard_version=guard.version)


@router.post("/build-issue-graph", response_model=BuildIssueGraphResponse)
async def build_issue_graph(request: BuildIssueGraphRequest) -> BuildIssueGraphResponse:
    response = graph_builder.build(request)

    log_event(
        logger,
        "issue_graph_built",
        case_id=request.case_id,
        issues=len(response.issues),
        disputed=sum(1 for i in response.issues if i.status == "DISPUTED"),
        unverified=sum(1 for i in response.issues if i.status == "UNVERIFIED"),
    )

    return response


@router.post("/generate-case", response_model=GenerateCaseResponse)
async def generate_case(request: GenerateCaseRequest) -> GenerateCaseResponse:
    try:
        response = packet_generator.generate(request)
    except NeutralityViolation as exc:
        # Blocking is correct behaviour: adjudicative prose must never reach a mediator.
        raise HTTPException(
            status_code=422,
            detail={"error": "neutrality_violation", "matches": exc.matches},
        ) from exc
    except HallucinationViolation as exc:
        raise HTTPException(
            status_code=422,
            detail={"error": "unbacked_statement", "statements": exc.statements},
        ) from exc

    log_event(
        logger,
        "case_packet_generated",
        case_id=request.case_id,
        statements=len(response.statements),
        issues=len(request.issues),
    )

    return response

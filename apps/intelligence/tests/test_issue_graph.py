"""AGREED / DISPUTED / MISSING / UNVERIFIED — without deciding who is right."""

from app.intelligence.issue_graph import IssueGraphBuilder
from app.schemas.common import IssueStatus
from app.schemas.issues import BuildIssueGraphRequest, ComparableClaim


def _claim(claim_id, type_, value=None, polarity="POSITIVE", pending=False):
    return ComparableClaim(
        claim_id=claim_id,
        type=type_,
        predicate=type_,
        canonical_value=value,
        polarity=polarity,
        has_pending_critical_field=pending,
    )


def _states(request):
    response = IssueGraphBuilder().build(request)
    return {issue.canonical_type: issue.status for issue in response.issues}


def test_matching_amounts_are_agreed():
    states = _states(
        BuildIssueGraphRequest(
            case_id="c",
            party_a=[_claim("a1", "deposit_amount", {"amount_minor": 150000})],
            party_b=[_claim("b1", "deposit_amount", {"amount_minor": 150000})],
        )
    )
    assert states["deposit_amount"] is IssueStatus.AGREED


def test_different_amounts_are_disputed():
    states = _states(
        BuildIssueGraphRequest(
            case_id="c",
            party_a=[_claim("a1", "deposit_amount", {"amount_minor": 150000})],
            party_b=[_claim("b1", "deposit_amount", {"amount_minor": 100000})],
        )
    )
    assert states["deposit_amount"] is IssueStatus.DISPUTED


def test_opposite_polarity_is_disputed():
    states = _states(
        BuildIssueGraphRequest(
            case_id="c",
            party_a=[_claim("a1", "refund_commitment", {"scope": "full_refund"})],
            party_b=[_claim("b1", "refund_denial", {"scope": "full_refund"}, polarity="NEGATIVE")],
        )
    )
    assert states["refund_commitment"] is IssueStatus.DISPUTED


def test_one_sided_issue_is_missing():
    states = _states(
        BuildIssueGraphRequest(
            case_id="c",
            party_a=[_claim("a1", "tenancy_end_date", {"day": 30, "month": 6})],
            party_b=[],
        )
    )
    assert states["tenancy_end_date"] is IssueStatus.MISSING


def test_pending_critical_field_forces_unverified():
    # Consequential uncertainty survives into the case; it is never rounded off.
    states = _states(
        BuildIssueGraphRequest(
            case_id="c",
            party_a=[_claim("a1", "deposit_amount", {"amount_minor": 150000}, pending=True)],
            party_b=[_claim("b1", "deposit_amount", {"amount_minor": 150000})],
        )
    )
    assert states["deposit_amount"] is IssueStatus.UNVERIFIED

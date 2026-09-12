"""Two independent guards stand between the model and the mediator."""

import pytest

from app.intelligence.hallucination import HallucinationValidator, HallucinationViolation
from app.intelligence.neutrality import NeutralityViolation, assert_payload, passes
from app.schemas.packet import ProvenanceStatement


@pytest.mark.parametrize(
    "text",
    [
        "Party B is lying about the deposit.",
        "Party A should pay the repair cost.",
        "Party B is liable for the damage.",
        "Party A is more credible than Party B.",
    ],
)
def test_adjudicative_prose_is_blocked(text):
    assert not passes(text)


@pytest.mark.parametrize(
    "text",
    [
        "Party A states that the deposit was 150,000 RWF.",
        "The accounts differ on the deposit amount.",
        "No information was provided about the tenancy end date.",
        "This information remains unverified.",
    ],
)
def test_neutral_framings_pass(text):
    assert passes(text)


def test_nested_payload_is_scanned():
    with pytest.raises(NeutralityViolation):
        assert_payload({"issues": [{"summary": "Party B is at fault."}]})


def test_statement_without_provenance_is_rejected():
    validator = HallucinationValidator()
    statements = [
        ProvenanceStatement(
            text="The property was damaged before the tenant arrived.",
            kind="SOURCE_CLAIM",
            claim_id="does-not-exist",
        )
    ]
    with pytest.raises(HallucinationViolation):
        validator.assert_backed(statements, claim_ids=set(), issue_ids=set())


def test_missing_information_is_self_backed():
    validator = HallucinationValidator()
    statements = [
        ProvenanceStatement(text="No repair invoice was provided.", kind="MISSING_INFORMATION")
    ]
    assert validator.unbacked(statements, set(), set()) == []

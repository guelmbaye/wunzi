"""The metrics must punish the errors that actually break a mediation."""

from app.benchmark.metrics.critical_facts import critical_fact_accuracy, negation_preservation
from app.benchmark.metrics.issues import case_state_correct, correct_mediation_state_rate, issue_macro_f1
from app.benchmark.metrics.sponsor_delta import sponsor_outcome_delta
from app.benchmark.metrics.wer import word_error_rate


def test_wer_is_zero_on_identical_text():
    assert word_error_rate("I paid 150,000 RWF", "I paid 150000 RWF") == 0.0


def test_misheard_amount_scores_zero_not_partial():
    # A near-miss on the number is the whole failure. No partial credit.
    assert critical_fact_accuracy("I paid 150,000 RWF", "I paid 50,000 RWF") == 0.0


def test_correct_amount_scores_one():
    assert critical_fact_accuracy("I paid 150,000 RWF", "I paid 150,000 RWF") == 1.0


def test_dropped_negation_is_caught():
    assert negation_preservation("I did not damage the room", "I damaged the room") == 0.0


def test_case_state_is_all_or_nothing():
    expected = {"deposit_amount": "DISPUTED", "refund_commitment": "DISPUTED"}
    assert case_state_correct(expected, dict(expected)) is True
    assert case_state_correct(expected, {**expected, "refund_commitment": "AGREED"}) is False


def test_cmsr_counts_whole_cases():
    assert correct_mediation_state_rate([True, True, False, True]) == 0.75


def test_macro_f1_penalises_a_flipped_state():
    expected = {"a": "AGREED", "b": "DISPUTED"}
    assert issue_macro_f1(expected, expected) == 1.0
    assert issue_macro_f1(expected, {"a": "AGREED", "b": "AGREED"}) < 1.0


def test_sponsor_delta_reports_both_directions():
    strong = sponsor_outcome_delta({"sahara": 80.0, "whisper": 60.0})
    assert strong.delta_points == 20.0 and strong.verdict == "STRONG_GO"

    flat = sponsor_outcome_delta({"sahara": 70.0, "whisper": 70.0})
    assert flat.verdict == "NO_DIFFERENTIATION"
    # The honest read when the delta is flat: harden the dataset, not the story.
    assert "harder code-switch split" in flat.narrative

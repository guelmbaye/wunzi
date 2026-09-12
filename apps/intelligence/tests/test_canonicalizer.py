"""Numbers and dates must survive a language switch intact."""

from app.intelligence.canonicalizer import (
    canonical_amount_equal,
    extract_amounts,
    extract_dates,
)


def _first(text: str) -> int | None:
    amounts = extract_amounts(text)
    return amounts[0].value if amounts else None


def test_digits_with_separators():
    assert _first("Nishyuye deposit ya 150,000 RWF") == 150000
    assert _first("il a paye 150 000 francs") == 150000


def test_shorthand():
    assert _first("I paid 150k RWF") == 150000


def test_english_words():
    assert _first("one hundred fifty thousand francs") == 150000


def test_french_words():
    assert _first("cent cinquante mille francs") == 150000


def test_kinyarwanda_words():
    assert _first("ibihumbi ijana na mirongo itanu") == 150000
    assert _first("ibihumbi mirongo itanu") == 50000


def test_currency_detected():
    amounts = extract_amounts("deposit ya 150,000 RWF")
    assert amounts[0].currency == "RWF"


def test_iso_date_not_double_matched():
    dates = extract_dates("the contract ended 2026-06-30")
    assert len(dates) == 1
    assert dates[0].iso == "2026-06-30"


def test_day_month_words():
    dates = extract_dates("narangije contract ku wa 30 Kamena")
    assert dates and dates[0].day == 30 and dates[0].month == 6


def test_amount_equality_is_exact():
    # 150,000 heard as 50,000 is wrong. There is no partial credit here.
    assert canonical_amount_equal({"amount_minor": 150000}, {"amount_minor": 150000}) is True
    assert canonical_amount_equal({"amount_minor": 150000}, {"amount_minor": 50000}) is False


def test_amount_equality_returns_none_when_not_comparable():
    assert canonical_amount_equal({"scope": "deposit"}, {"scope": "deposit"}) is None

"""
Canonicalisation: surface language → language-independent values.

  "one hundred fifty thousand" | "cent cinquante mille" | "150,000" | "ibihumbi ijana na mirongo itanu"
      → 150000

The Issue Graph never duplicates a concept per language.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from app.intelligence.lexicon import (
    CURRENCY_MARKERS,
    EN_SCALES,
    EN_TENS,
    EN_UNITS,
    FR_SCALES,
    FR_TENS,
    FR_UNITS,
    MONTHS,
    RW_SCALES,
    RW_TENS_MARKER,
    RW_UNITS,
)

_DIGIT_AMOUNT = re.compile(
    r"(?<![\w.])(\d{1,3}(?:[ ,.\u00a0]\d{3})+|\d{4,9})(?:\s*(rwf|frw|francs?|amafaranga))?",
    re.IGNORECASE,
)
_SHORTHAND = re.compile(r"(?<![\w.])(\d+(?:[.,]\d+)?)\s*(k|m)\b", re.IGNORECASE)
_ISO_DATE = re.compile(r"\b(\d{4})-(\d{2})-(\d{2})\b")
_DAY_MONTH = re.compile(r"\b(\d{1,2})(?:st|nd|rd|th|er)?\s+(?:of\s+)?([a-zà-ÿ]+)\b", re.IGNORECASE)
_MONTH_DAY = re.compile(r"\b([a-zà-ÿ]+)\s+(\d{1,2})(?:st|nd|rd|th)?\b", re.IGNORECASE)
_NUMERIC_DATE = re.compile(r"\b(\d{1,2})[/-](\d{1,2})(?:[/-](\d{2,4}))?\b")


@dataclass(frozen=True)
class Amount:
    value: int
    currency: str | None
    surface: str

    def as_dict(self) -> dict:
        return {"amount_minor": self.value, "currency": self.currency or "RWF", "surface": self.surface}


@dataclass(frozen=True)
class DateValue:
    iso: str | None
    day: int | None
    month: int | None
    year: int | None
    surface: str

    def as_dict(self) -> dict:
        return {"iso_date": self.iso, "day": self.day, "month": self.month, "year": self.year, "surface": self.surface}


def normalise_digits(raw: str) -> int:
    return int(re.sub(r"[^\d]", "", raw))


def _words_to_number_en(tokens: list[str]) -> int | None:
    total, current, seen = 0, 0, False
    for token in tokens:
        if token in EN_UNITS:
            current += EN_UNITS[token]
            seen = True
        elif token in EN_TENS:
            current += EN_TENS[token]
            seen = True
        elif token in EN_SCALES:
            scale = EN_SCALES[token]
            if scale >= 1000:
                total += (current or 1) * scale
                current = 0
            else:
                current = (current or 1) * scale
            seen = True
        elif token == "and":
            continue
        else:
            break
    return total + current if seen else None


def _words_to_number_fr(tokens: list[str]) -> int | None:
    total, current, seen = 0, 0, False
    for token in tokens:
        if token in FR_UNITS:
            current += FR_UNITS[token]
            seen = True
        elif token in FR_TENS:
            current += FR_TENS[token]
            seen = True
        elif token in FR_SCALES:
            scale = FR_SCALES[token]
            if scale >= 1000:
                total += (current or 1) * scale
                current = 0
            else:
                current = (current or 1) * scale
            seen = True
        elif token in {"et", "-"}:
            continue
        else:
            break
    return total + current if seen else None


def _words_to_number_rw(tokens: list[str]) -> int | None:
    """
    Narrow Kinyarwanda numeral reader, e.g.
    "ibihumbi ijana na mirongo itanu" → 150 × 1000.
    """
    total, current, seen = 0, 0, False
    pending_scale: int | None = None
    i = 0
    while i < len(tokens):
        token = tokens[i]
        if token in RW_SCALES:
            pending_scale = RW_SCALES[token]
            seen = True
        elif token == RW_TENS_MARKER:
            i += 1
            if i < len(tokens) and tokens[i] in RW_UNITS:
                current += RW_UNITS[tokens[i]] * 10
                seen = True
        elif token in {"ijana", "kijana"}:
            current += 100
            seen = True
        elif token in RW_UNITS:
            current += RW_UNITS[token]
            seen = True
        elif token in {"na", "n'"}:
            pass
        else:
            break
        i += 1

    if not seen:
        return None
    if pending_scale:
        total = (current or 1) * pending_scale
    else:
        total = current
    return total or None


def detect_currency(text: str) -> str | None:
    lowered = text.lower()
    for currency, markers in CURRENCY_MARKERS.items():
        if any(marker in lowered for marker in markers):
            return currency
    return None


def extract_amounts(text: str) -> list[Amount]:
    """Extracts every amount, in any of the three languages, from a span."""
    results: list[Amount] = []
    currency = detect_currency(text)
    lowered = text.lower()

    for match in _DIGIT_AMOUNT.finditer(text):
        value = normalise_digits(match.group(1))
        if value >= 100:
            results.append(Amount(value, currency, match.group(0).strip()))

    for match in _SHORTHAND.finditer(text):
        base = float(match.group(1).replace(",", "."))
        multiplier = 1_000 if match.group(2).lower() == "k" else 1_000_000
        results.append(Amount(int(base * multiplier), currency, match.group(0).strip()))

    tokens = re.findall(r"[a-zà-ÿ]+", lowered)
    for reader in (_words_to_number_en, _words_to_number_fr, _words_to_number_rw):
        for start in range(len(tokens)):
            value = reader(tokens[start:])
            if value and value >= 1000:
                surface = " ".join(tokens[start : start + 6])
                if not any(r.value == value for r in results):
                    results.append(Amount(value, currency, surface))
                break

    # Deduplicate while preserving order.
    seen: set[int] = set()
    unique: list[Amount] = []
    for amount in results:
        if amount.value not in seen:
            seen.add(amount.value)
            unique.append(amount)
    return unique


def extract_dates(text: str, default_year: int | None = None) -> list[DateValue]:
    """
    Dates are canonicalised without inventing a year: an unknown year stays null
    unless the caller supplies an explicit context year.
    """
    results: list[DateValue] = []
    lowered = text.lower()

    for match in _ISO_DATE.finditer(text):
        year, month, day = (int(g) for g in match.groups())
        results.append(DateValue(f"{year:04d}-{month:02d}-{day:02d}", day, month, year, match.group(0)))

    for match in _DAY_MONTH.finditer(lowered):
        month = MONTHS.get(match.group(2))
        if month:
            day = int(match.group(1))
            results.append(_build_date(day, month, default_year, match.group(0)))

    for match in _MONTH_DAY.finditer(lowered):
        month = MONTHS.get(match.group(1))
        if month:
            day = int(match.group(2))
            results.append(_build_date(day, month, default_year, match.group(0)))

    # Blank out ISO matches so "2025-08-12" is not re-read as "08-12".
    masked = _ISO_DATE.sub(lambda m: " " * len(m.group(0)), text)

    for match in _NUMERIC_DATE.finditer(masked):
        day, month = int(match.group(1)), int(match.group(2))
        year = int(match.group(3)) if match.group(3) else default_year
        if year and year < 100:
            year += 2000
        if 1 <= month <= 12 and 1 <= day <= 31:
            results.append(_build_date(day, month, year, match.group(0)))

    unique: list[DateValue] = []
    seen: set[tuple[int | None, int | None, int | None]] = set()
    for value in results:
        key = (value.day, value.month, value.year)
        if key not in seen:
            seen.add(key)
            unique.append(value)
    return unique


def _build_date(day: int, month: int, year: int | None, surface: str) -> DateValue:
    iso = f"{year:04d}-{month:02d}-{day:02d}" if year else None
    return DateValue(iso, day, month, year, surface)


def canonical_amount_equal(a: dict | None, b: dict | None) -> bool | None:
    """None means "not comparable" — never guess equality."""
    if not a or not b:
        return None
    if "amount_minor" not in a or "amount_minor" not in b:
        return None
    if a.get("currency") and b.get("currency") and a["currency"] != b["currency"]:
        return False
    return int(a["amount_minor"]) == int(b["amount_minor"])


def canonical_date_equal(a: dict | None, b: dict | None) -> bool | None:
    if not a or not b:
        return None
    if a.get("iso_date") and b.get("iso_date"):
        return a["iso_date"] == b["iso_date"]
    if a.get("day") and b.get("day") and a.get("month") and b.get("month"):
        return a["day"] == b["day"] and a["month"] == b["month"]
    return None

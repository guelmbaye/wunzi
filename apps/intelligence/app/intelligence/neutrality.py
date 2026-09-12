"""
Neutrality guard.

Runs before any generated prose is returned to the System of Record. It is one
guard layer, not a comprehensive legal policy — Laravel re-checks independently.
"""

from __future__ import annotations

import re

BLOCKED_PATTERNS: tuple[re.Pattern[str], ...] = tuple(
    re.compile(pattern, re.IGNORECASE)
    for pattern in (
        r"\bis lying\b",
        r"\bliar\b",
        r"\bdishonest\b",
        r"\bis correct\b",
        r"\bis right\b",
        r"\bis wrong\b",
        r"\bshould pay\b",
        r"\bmust pay\b",
        r"\bowes\b",
        r"\bliable\b",
        r"\bguilty\b",
        r"\bat fault\b",
        r"\bcredib(le|ility)\b",
        r"\btrustworth",
        r"\bdeserves\b",
        r"\bthe truth is\b",
        r"\bproven\b",
        r"\bwe recommend (that )?(party|the)",
    )
)

APPROVED_FRAMES: tuple[str, ...] = (
    "Party A states",
    "Party B states",
    "The accounts differ on",
    "Both accounts align on",
    "No information was provided about",
    "This information remains unverified",
)


class NeutralityViolation(ValueError):
    def __init__(self, matches: list[str]) -> None:
        self.matches = matches
        super().__init__("Neutrality guard rejected generated content: " + ", ".join(matches))


def scan(text: str) -> list[str]:
    return [match.group(0) for pattern in BLOCKED_PATTERNS if (match := pattern.search(text))]


def passes(text: str) -> bool:
    return not scan(text)


def assert_neutral(text: str) -> None:
    matches = scan(text)
    if matches:
        raise NeutralityViolation(matches)


def assert_payload(payload) -> None:
    """Recursively scans every string value of a nested structure."""
    violations: list[str] = []

    def walk(node) -> None:
        if isinstance(node, str):
            violations.extend(scan(node))
        elif isinstance(node, dict):
            for value in node.values():
                walk(value)
        elif isinstance(node, (list, tuple)):
            for value in node:
                walk(value)

    walk(payload)

    if violations:
        raise NeutralityViolation(sorted(set(violations)))


def neutralise(text: str) -> str:
    """
    Last-resort rewrite used only when regeneration is unavailable.
    Prefer regenerating; this exists so a failure never returns adjudicative prose.
    """
    replacements = {
        r"\bis lying\b": "provides a different account",
        r"\bis correct\b": "states",
        r"\bis wrong\b": "states something different",
        r"\bshould pay\b": "is asked by the other account to pay",
        r"\bliable\b": "referred to in the claim",
        r"\bguilty\b": "referred to in the claim",
        r"\bcredible\b": "recorded",
    }
    result = text
    for pattern, replacement in replacements.items():
        result = re.sub(pattern, replacement, result, flags=re.IGNORECASE)
    return result

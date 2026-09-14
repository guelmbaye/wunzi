#!/usr/bin/env python3
"""
Payload contract checker.

`check_routes.py` verifies that the two services agree on *paths*. This one
verifies they agree on *field names* — the layer underneath, and the one that
produced three Server Component crashes on the first real deployment:

    TypeError: Cannot read properties of undefined (reading 'length')
    TypeError: Cannot read properties of undefined (reading 'bg')

Nothing catches that class of error on its own. TypeScript checks the frontend
against types a human wrote; PHP checks nothing across the boundary. The types
and the resources were both written by hand and were never compared, so a
renamed key surfaced as a white screen with a digest and no message.

    python3 scripts/check_payloads.py

Reads every `toArray()` in app/Http/Resources and every `raw.X` / `claim.X`
access in apps/web/src/lib/mappers.ts, and reports fields the mapper reads that
no resource emits.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RESOURCES = ROOT / "apps/api/app/Http/Resources"
MAPPERS = ROOT / "apps/web/src/lib/mappers.ts"

# Keys that legitimately come from somewhere other than a Resource: controller
# envelopes, `withCount`, or values the interface derives itself.
EXPECTED_ELSEWHERE = {
    # Controllers add these outside the resource.
    "claims_count",
    "issues_count",
    "pending_critical_fields",
    # IssueController and the evidence block build these inline.
    "label",
    "availability",
    # Mapper-local structure, not a Laravel key.
    "segments",
    "is_primary",
}

MAPPER_TO_RESOURCE = {
    "toCase": "CaseResource",
    "toIssue": "IssueResource",
    "toClaim": "ClaimResource",
    "toCriticalField": "CriticalFieldResource",
    "toRecording": "RecordingResource",
}


def resource_keys(name: str) -> set[str]:
    """Top-level keys a Laravel Resource emits from toArray()."""
    path = RESOURCES / f"{name}.php"
    if not path.exists():
        return set()

    source = path.read_text()
    match = re.search(r"toArray\([^)]*\)[^{]*\{(.*?)\n    \}", source, re.DOTALL)
    body = match.group(1) if match else source

    return set(re.findall(r"'([a-z_]+)'\s*=>", body))


def mapper_functions() -> dict[str, set[str]]:
    """Fields each mapper reads off the raw payload."""
    source = MAPPERS.read_text()
    functions: dict[str, set[str]] = {}

    blocks = re.split(r"(?=export function to)", source)
    for block in blocks:
        match = re.match(r"export function (to[A-Za-z]+)", block)
        if not match:
            continue

        # raw.field, party.field, primary.field, segment.field, claim.field
        fields = set(re.findall(r"\b(?:raw|party|primary|segment|claim|run)\.([a-z_]+)", block))
        functions[match.group(1)] = fields

    return functions


def nested_keys(resource: str, relation: str) -> set[str]:
    """Keys of a resource reached through a relation, e.g. claim inside a field."""
    return resource_keys(resource)


def main() -> int:
    if not MAPPERS.exists():
        print(f"No mapper file at {MAPPERS}")
        return 1

    mappers = mapper_functions()
    problems: list[str] = []
    checked = 0

    # Nested resources the mappers reach through.
    party_keys = resource_keys("PartyResource")
    claim_keys = resource_keys("ClaimResource")
    run_keys = resource_keys("TranscriptRunResource")
    segment_keys = resource_keys("TranscriptSegmentResource")

    extra: dict[str, set[str]] = {
        "toCase": party_keys,
        "toCriticalField": claim_keys,
        "toRecording": run_keys | segment_keys,
    }

    print(f"{len(mappers)} mappers · {len(list(RESOURCES.glob('*.php')))} resources\n")

    for mapper, fields in sorted(mappers.items()):
        resource = MAPPER_TO_RESOURCE.get(mapper)
        if not resource:
            continue

        available = resource_keys(resource) | extra.get(mapper, set()) | EXPECTED_ELSEWHERE
        missing = sorted(f for f in fields if f not in available)
        checked += len(fields)

        status = "OK  " if not missing else "!!  "
        print(f"  {status}{mapper:18} → {resource:24} {len(fields)} fields")

        for field in missing:
            problems.append(f"{mapper} reads '{field}', which {resource} does not emit.")

    print(f"\n{checked} field reads checked.")

    if problems:
        print()
        for problem in problems:
            print(f"  {problem}")
        print(f"\n{len(problems)} mismatch(es). One side needs to change.")
        return 1

    print("Every mapped field exists in the resource it comes from.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

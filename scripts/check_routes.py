#!/usr/bin/env python3
"""
Route contract checker.

Three services in three languages share two HTTP boundaries, and nothing in any
compiler checks that the paths on either side match. A renamed route fails
silently in staging and loudly in a demo — this script found nine mismatches the
first time it was run, including a frontend polling an endpoint Laravel had never
declared.

    python3 scripts/check_routes.py

Exits non-zero when a caller references a path its callee does not serve.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Paths the web app owns itself. These are Next page routes reached with <Link>,
# not calls to Laravel, so they must not be checked against the API.
PAGE_ROUTES = {
    "/",
    "/cases",
    "/cases/new",
    "/cases/{p}",
    "/cases/{p}/party-a",
    "/cases/{p}/party-b",
    "/cases/{p}/verify",
    "/cases/{p}/issues",
    "/cases/{p}/packet",
    "/benchmark",
    "/benchmark/{p}",
    "/responsible-ai",
}


def placeholder(path: str) -> str:
    """`/cases/${caseId}/claims` and `/cases/{case}/claims` become one shape."""
    # A conditional interpolation only ever appends a query string, so anything
    # from it onward is not part of the path.
    path = re.split(r"\$\{[^}]*\?", path)[0]
    path = re.sub(r"\$\{[^}]+\}", "{p}", path)
    path = re.sub(r"\{[a-zA-Z_]+\}", "{p}", path)
    path = path.split("?")[0]

    # PHP builds some paths by concatenation ('/v1/benchmark/runs/'.$runId), so
    # a trailing slash means a parameter follows.
    if path.endswith("/") and path != "/":
        path = path.rstrip("/") + "/{p}"

    return path or "/"


def laravel_routes() -> set[str]:
    source = (ROOT / "apps/api/routes/api.php").read_text()
    return {
        placeholder(match.group(2))
        for match in re.finditer(r"Route::(get|post|patch|delete)\('([^']+)'", source)
    }


def fastapi_routes() -> set[str]:
    """Router prefixes plus decorator paths, mounted under the /v1 prefix."""
    routes: set[str] = set()
    routers = ROOT / "apps/intelligence/app/routers"

    for path in routers.glob("*.py"):
        source = path.read_text()

        prefix_match = re.search(r'APIRouter\([^)]*prefix="([^"]+)"', source, re.DOTALL)
        prefix = prefix_match.group(1) if prefix_match else ""

        # /health is mounted unversioned so an orchestrator probe does not
        # depend on the API version.
        version = "" if path.stem == "health" else "/v1"

        for match in re.finditer(r'@router\.(get|post|patch|delete)\("([^"]+)"', source):
            routes.add(placeholder(f"{version}{prefix}{match.group(2)}"))

    return routes


def web_api_calls() -> set[str]:
    calls: set[str] = set()
    for path in (ROOT / "apps/web/src").rglob("*.ts*"):
        text = path.read_text()

        # Server-side client: call('/cases/...') and api.ts template literals.
        for match in re.finditer(r"call<[^>]*>\(\s*[`']([^`']+)[`']", text):
            calls.add(placeholder(match.group(1)))

        # Client-side builders route through the /api/laravel rewrite.
        for match in re.finditer(r"`/api/laravel([^`]+)`", text):
            calls.add(placeholder(match.group(1)))

    return calls


def laravel_calls_to_intelligence() -> set[str]:
    source = (ROOT / "apps/api/app/Services/Intelligence/IntelligenceClient.php").read_text()
    return {
        placeholder(match.group(1))
        for match in re.finditer(r"\$this->(?:post|get)\('([^']+)'", source)
    }


def report(title: str, callers: set[str], served: set[str]) -> list[str]:
    missing = sorted(path for path in callers if path not in served)

    print(f"\n{title}")
    print(f"  {len(callers)} referenced · {len(served)} served")

    if missing:
        for path in missing:
            print(f"  MISSING  {path}")
    else:
        print("  all referenced paths are served")

    return missing


def main() -> int:
    failures: list[str] = []

    served = laravel_routes()
    calls = {
        p
        for p in web_api_calls()
        if p not in PAGE_ROUTES and re.match(r"^/[a-z]", p)
    }
    failures += report("Web → Laravel", calls, served)

    failures += report(
        "Laravel → FastAPI",
        laravel_calls_to_intelligence(),
        fastapi_routes(),
    )

    if failures:
        print(f"\n{len(failures)} unmatched path(s). One side needs to change.")
        return 1

    print("\nEvery boundary agrees.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

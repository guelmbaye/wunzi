#!/usr/bin/env python3
"""
Migration hazard checker.

Catches schema mistakes that only surface on PostgreSQL, which means they slip
through a test suite running on SQLite and fail on the first real `migrate`.

    python3 scripts/check_migrations.py

Checks:

1. **Self-referencing foreign key inside its own `Schema::create`.**
   Laravel appends fluent index commands — `uuid('id')->primary()` — to the END
   of the blueprint's command list, after every foreign key declared in the
   closure. PostgreSQL then sees:

       CREATE TABLE claims (...)
       ALTER TABLE claims ADD FOREIGN KEY (superseded_by)
                          REFERENCES claims (id)     <- SQLSTATE 42830
       ALTER TABLE claims ADD PRIMARY KEY (id)       <- too late

   SQLite accepts it because it does not enforce foreign keys by default, so the
   test suite passes and the migration fails in production. The fix is a second
   `Schema::table()` call after the create block.

2. **A foreign key pointing at a table created by a later migration.**

3. **A foreign key pointing at a table no migration creates.**
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

MIGRATIONS = Path(__file__).resolve().parent.parent / "apps/api/database/migrations"

CREATE = re.compile(r"Schema::create\('([a-z_]+)'")
CONSTRAINED = re.compile(r"constrained\('([a-z_]+)'\)")
ON_TABLE = re.compile(r"->on\('([a-z_]+)'\)")


def create_blocks(source: str) -> list[tuple[str, str]]:
    """Split a migration into (table, body) pairs, one per Schema::create."""
    blocks: list[tuple[str, str]] = []
    for chunk in re.split(r"(?=Schema::create\(')", source):
        match = CREATE.match(chunk)
        if match:
            # Stop at the next Schema:: call so a following Schema::table()
            # is not read as part of the create block.
            body = re.split(r"Schema::table\(", chunk)[0]
            blocks.append((match.group(1), body))
    return blocks


def references(body: str) -> set[str]:
    return set(CONSTRAINED.findall(body)) | set(ON_TABLE.findall(body))


def main() -> int:
    files = sorted(MIGRATIONS.glob("*.php"))
    if not files:
        print(f"No migrations found under {MIGRATIONS}")
        return 1

    created_in: dict[str, str] = {}
    for path in files:
        for table, _ in create_blocks(path.read_text()):
            created_in[table] = path.name

    problems: list[str] = []
    checked = 0

    for path in files:
        source = path.read_text()

        for table, body in create_blocks(source):
            for target in sorted(references(body)):
                checked += 1

                if target == table:
                    problems.append(
                        f"{path.name}: '{table}' references itself inside its own "
                        f"Schema::create block. Move the key to a separate "
                        f"Schema::table('{table}', ...) call after the create."
                    )
                elif target not in created_in:
                    problems.append(
                        f"{path.name}: '{table}' references '{target}', which no "
                        f"migration creates."
                    )
                elif created_in[target] > path.name:
                    problems.append(
                        f"{path.name}: '{table}' references '{target}', created "
                        f"later by {created_in[target]}."
                    )

    print(f"{len(files)} migrations · {len(created_in)} tables · {checked} foreign keys")

    if problems:
        print()
        for problem in problems:
            print(f"  {problem}")
        print(f"\n{len(problems)} hazard(s).")
        return 1

    print("No ordering hazards.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

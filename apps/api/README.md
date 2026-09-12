# WUNZI API — System of Record

Laravel 11 + PostgreSQL 16 + Redis. Owns case state, claims, verification,
provenance and audit. Calls the intelligence service; is never called by it.

## Running it alone

```bash
composer install
cp .env.example .env
php artisan key:generate
php artisan migrate --seed
php artisan serve --port=8000
```

Seeded accounts: `mediator@wunzi.demo` / `admin@wunzi.demo`, password
`wunzi-demo`.

```bash
php artisan wunzi:demo-case    # builds WZ_DEMO_001 from fixtures
php artisan wunzi:benchmark    # runs the four-provider comparison
php artisan test
```

### A caveat about the test database

The suite runs on SQLite in memory for speed. That is fast but not faithful:
SQLite accepts schema PostgreSQL rejects. A self-referencing foreign key
declared inside its own `Schema::create` block is the example that bit this
project — Laravel emits the key before the primary key it points at, PostgreSQL
raises SQLSTATE 42830, and SQLite never notices.

`python3 scripts/check_migrations.py` (`make check-migrations`) catches that
class statically. Anything schema-shaped should still be confirmed with a real
`php artisan migrate:fresh` against PostgreSQL before it is trusted.

## The state machine

```
DRAFT → PARTY_A_CAPTURE → PARTY_B_CAPTURE → VERIFICATION_REQUIRED
      → ISSUE_GRAPH_READY → MEDIATOR_REVIEW → READY
```

Transitions live in `CaseStatus::allowedNext()` and are enforced by
`CaseStateMachine`, not by controllers, so no route can bypass them. `READY` is
terminal and unreachable while any critical field sits in `NEEDS_CONFIRMATION`.

## Immutability

`transcript_runs` are append-only. A correction never overwrites a transcript: it
creates a `verification_event` and a superseding claim, and both readings stay in
the record. Every claim carries `claim_sources` pointing at transcript segments,
which point at an audio recording and a timestamp — so any sentence in a case
packet can be traced back to the voice that produced it.

## What this layer refuses

| Refusal | Where |
| --- | --- |
| Adjudicative language in generated prose | `Safety/NeutralityFilter` |
| A packet statement with no provenance | `Safety/HallucinationValidator` |
| A case finalised with an unconfirmed critical value | `CaseStateMachine` |
| A recording without consent | `StoreRecordingRequest` |
| Anyone but the speaker correcting a claim | `VerificationService` |

`NeutralityFilter` and `HallucinationValidator` duplicate checks the intelligence
service already performs. That is deliberate: FastAPI blocks before returning,
Laravel blocks before persisting, and a single guard would be a single point of
failure on the failure mode with the highest cost.

## Talking to the intelligence service

One client, `Services/Intelligence/IntelligenceClient`. Retries and timeouts are
budgeted so the layers nest — see [`docs/service-contract.md`](../../docs/service-contract.md).
The short version: transcription is **not** retried here, because FastAPI already
retries the provider and stacking the two turns one recording into nine ASR calls.

Audio never passes through this service as bytes. `TranscriptionService` sends a
URI and FastAPI reads the object from private storage itself.

## Status

Written and reviewed, but **not executed** in the environment where it was
built — no PHP runtime was available. `php artisan test` and a first
`php artisan migrate` are the next things to run. The wire contract with FastAPI
is covered by `apps/intelligence/tests/test_laravel_contract.py` and
`scripts/check_routes.py`, which replay and verify the payloads and paths this
service produces.

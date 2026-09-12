# WUNZI

**Switch-Aware Mediation Case Intelligence**

> Hear every side. Structure what matters.
> AI structures. Humans mediate.

Two people describe the same dispute in different ways, in the languages they
naturally mix. WUNZI captures both accounts, extracts what each person actually
stated, flags what it could not hear reliably, and hands a mediator a structured
case that **preserves the disagreement instead of resolving it**.

Built for the Sahara CodeSwitch Africa Challenge (Intron Voice AI), Legal &
Public Services. Demo locale: Rwanda — Kinyarwanda ⇄ English ⇄ French. MVP scope:
rental deposit disputes.

---

## The flow

```
Voice → ASR → Claims → Attribution → Verification → Issue Graph → Mediation Case
```

Every issue lands in exactly one of four states, and none of them is a verdict:

| State | Meaning |
| --- | --- |
| `AGREED` | Both accounts align |
| `DISPUTED` | The accounts differ — shown as two values, never averaged |
| `MISSING` | One account says nothing about it |
| `UNVERIFIED` | Not established; a critical value is still unconfirmed |

## Services

| Path | Stack | Role |
| --- | --- | --- |
| `apps/web` | Next.js 15, TypeScript, Tailwind | Mediator workspace and demo |
| `apps/api` | Laravel 11, PostgreSQL 16, Redis | System of Record: cases, claims, verification, audit |
| `apps/intelligence` | FastAPI, Python 3.12 | Speech, claims, Critical Speech Guard, issue graph, benchmark |
| `benchmark/` | dataset + annotations + fixtures | Switch-aware mediation evaluation |

Laravel owns state. FastAPI owns language. Neither owns the outcome.

## Quick start

```bash
cp .env.example .env
make up          # postgres · redis · minio · api · worker · intelligence · web
make install     # composer + npm
make migrate
make demo        # builds the WZ_DEMO_001 rental deposit case from fixtures
```

Then open <http://localhost:3000>.

The root `.env` is what docker compose injects into every service. Each app also
ships its own `.env.example` for running that service alone — `apps/api`,
`apps/intelligence` and `apps/web`. The per-service files matter because the
defaults baked into the code are container paths: `apps/intelligence` looks for
fixtures at `/benchmark`, which does not exist on a host. Copy the local example
before running a service outside Docker.

```bash
make test              # every suite
make benchmark         # holdout split, four speech models
```

Fixture mode (`WUNZI_MODE=fixture`) replays stored provider output so the demo
never depends on a live API. It is a replay, not a simulator: fixtures can only
contain payloads captured from a real provider run, and each one keeps its
origin.

## The sponsor proof

```
Same audio. Same WUNZI. Different ASR. Different mediation state.
```

The benchmark freezes everything downstream of transcription — same claim
engine, same guard, same issue rules, same prompt versions — and changes only the
speech provider. `/benchmark` leads with the consequence (did the case come out
right?) and puts word error rate underneath, where it belongs.

**Sponsor Outcome Delta** = `CMSR(Sahara) − max CMSR(others)`. It is an internal
discipline metric, not an official challenge criterion: it exists so the team can
tell whether the sponsor model is load-bearing or merely present in the
architecture diagram. A small delta is reported as a small delta, and the honest
response to one is a harder evaluation set, not a softer metric.

**The fixtures in this repository are placeholders.** They carry
`is_placeholder: true`, the runner sets `publishable: false`, the report prints a
NOT PUBLISHABLE banner, and the UI refuses to render the headline figure. Real
numbers require `python -m app.benchmark.capture` against live providers with
consented audio. See [`benchmark/README.md`](benchmark/README.md).

## What is enforced in code

| Boundary | Where |
| --- | --- |
| Never decides truth, credibility, liability or settlement | `NeutralityFilter` (Laravel) + `neutrality.py` (FastAPI), independently |
| Every packet sentence traces to a claim, an issue, or system metadata | `HallucinationValidator` + `hallucination.py` |
| No case while a critical value is unconfirmed | `CaseStateMachine::assertNoBlockingCriticalFields` |
| Only the speaker verifies their own words | `VerificationService` |
| Recording requires consent | `StoreRecordingRequest` + a UI gate |
| Provider metadata is never fabricated | nullable `language_code` / `confidence` all the way to the UI |
| A failed ASR provider is a recorded failure, never a silent substitution | `AsrProvider` contract |

The guards are duplicated across both services on purpose. A single guard is a
single point of failure, and adjudicative prose reaching a mediator is the
failure mode with the highest cost.

## Documentation

- [`docs/architecture.md`](docs/architecture.md) — shape, state machine, provenance chain
- [`docs/service-contract.md`](docs/service-contract.md) — the Laravel ↔ FastAPI boundary, timeout and retry budgets
- [`docs/responsible-ai.md`](docs/responsible-ai.md) — what WUNZI refuses to do, and why
- [`docs/limitations.md`](docs/limitations.md) — scope, dataset, language and system limits
- [`benchmark/README.md`](benchmark/README.md) — metrics, splits, capture procedure, consent

## Tests

```bash
make test-intelligence   # 81 tests: units, Laravel contract, golden path
make test-api            # Laravel feature + unit tests
make test-web            # frontend typecheck
```

`tests/test_golden_path.py` runs the whole demo case through the real pipeline
and asserts the mediation state a mediator would receive.
`tests/test_laravel_contract.py` replays the exact payloads the Laravel services
build — the two codebases are in different languages, and nothing else checks
that they agree.

## Deliberately absent

No Neo4j (the graph is small and relational), no legal RAG (WUNZI does not
interpret law), no multi-agent orchestration, and above all no "truth agent".
Each omission removes a way for the system to appear more capable than it is.

## Status

The intelligence service, the benchmark harness and the frontend run and are
tested here. The Laravel layer is complete but has not been executed in this
environment — no PHP runtime was available — so `php artisan test` and a first
`make migrate` are the next things to run.

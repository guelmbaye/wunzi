# Service Contract — Laravel ↔ FastAPI

Two services in two languages, one HTTP boundary. Nothing in either codebase
checks that they agree except `apps/intelligence/tests/test_laravel_contract.py`,
which replays the exact payloads the Laravel services build. **If a Laravel
service changes what it sends, that test changes with it.**

`scripts/check_routes.py` (`make check-routes`) walks both boundaries and fails
when a caller references a path its callee does not serve. It found nine
mismatches the first time it ran, including a frontend polling
`GET /cases/{case}/recordings` — an endpoint Laravel had never declared.

## Routes

| Laravel caller | Method | Path |
| --- | --- | --- |
| `IntelligenceClient::health` | GET | `/health` |
| `TranscriptionService::transcribe` | POST | `/v1/speech/transcribe` |
| `ClaimIngestionService::ingest` | POST | `/v1/intelligence/analyze-turn` |
| `IssueGraphService::build` | POST | `/v1/intelligence/build-issue-graph` |
| `CasePacketService::generate` | POST | `/v1/intelligence/generate-case` |
| `BenchmarkService::start` | POST | `/v1/benchmark/run` → 202 |
| `BenchmarkService::awaitCompletion` | GET | `/v1/benchmark/runs/{run_id}` |

`/health` is deliberately unversioned: an orchestrator probe must not break when
the API version moves. `extract-claims` and `evaluate-criticality` remain
mounted, but only the benchmark uses them — it runs the guard in ablation mode
against a fixed claim set, which needs the two steps separable.

## Timeout budget

The layers must nest. If an outer layer is tighter than an inner one, it kills
work that has already been paid for — an ASR call that completed at second 130
is discarded by a client that gave up at 120.

```
ASR provider call        ASR_TIMEOUT_SECONDS          120s
FastAPI handler          + ASR_MAX_RETRIES = 1       ≤240s
IntelligenceClient       INTELLIGENCE_TIMEOUT         300s
ProcessRecording job     $timeout                     420s
```

Benchmark runs use their own budget:

```
FastAPI run              background task           unbounded
BenchmarkService poll    BENCHMARK_MAX_WAIT_SECONDS  3300s
RunBenchmark job         $timeout                    3600s
```

The poll budget sits **below** the job timeout so a stuck run is reported as a
benchmark failure with a reason, rather than as a killed job with none.

## Retry budget

**Retries live in exactly one layer.** Before this was fixed, transcription had
three: Laravel's HTTP client (3 attempts) × FastAPI's provider retry (3) ×
the queue job (3 tries) = **up to 27 ASR calls for one recording**, with Laravel
timing out at 120s while FastAPI was still working through its own 360s.

| Layer | Retries | Why |
| --- | --- | --- |
| FastAPI → ASR provider | 1 retry, 5xx and timeouts only | closest to the fault, knows what is transient |
| `IntelligenceClient` | none on transcription; 2 on `build-issue-graph`, `generate-case`, `/health` | those three have no upstream cost and no side effects |
| `ProcessRecording` | 3 tries, backoff 10/30/60s | the outer layer, with a visible failure record |

4xx is never retried anywhere. A malformed request does not become well-formed,
and spending attempts on it only delays the real error reaching an operator.

## Preloading: one round trip per turn

Laravel loads everything the intelligence layer needs from Postgres **before**
the call and sends it in one POST. FastAPI holds no state and reads no database.

`analyze-turn` carries, in a single request:

```
case_id · party_id · party_role · transcript_run_id · provider
transcript · segments[] (id, sequence, timing, text, language, confidence)
issue_types · pipeline_version
asr_metadata { provider, segment_confidences[] }
guard_enabled
```

Extraction and the Critical Speech Guard then run back to back inside FastAPI.
They were originally two endpoints, which meant shipping the whole claim set out
and straight back in for the guard to read: double the latency and a second
chance to fail, for no gain in auditability — both the claims and the guard
verdicts are persisted either way.

`build-issue-graph` and `generate-case` follow the same rule. `CasePacketService`
eager-loads `parties`, `claims.party`, `claims.criticalFields`, `issues`,
`evidenceReferences` in one query batch, then sends structured objects only —
never a raw transcript, never free speculation.

## Audio never passes through Laravel

`TranscriptionService` sends an **`audio_uri`**, not bytes. FastAPI reads the
object from private storage itself (`s3://…` via boto3, or `fixture://…` in
fixture mode). Base64 audio would double the transfer and put a multi-megabyte
body inside the PHP request lifecycle for no benefit.

## Idempotency

`TranscriptionService` computes

```
sha256(audio_sha256 | provider | model | pipeline_version)
```

and uses it twice: as the unique key on `transcript_runs`, and as the
`Idempotency-Key` header. A requeued job therefore replays the first result
instead of buying a second ASR call over identical audio.

That protects a *sequential* retry. A *concurrent* double dispatch is blocked by
`ProcessRecording implements ShouldBeUnique`, keyed on `recordingId:provider`
with `uniqueFor = 900` so a dead worker cannot wedge a recording permanently.

FastAPI's in-process cache (`app/idempotency.py`, 15-minute TTL) is a cost
optimisation within a worker's lifetime. The durable record is the Postgres row.

## Concurrency on the Issue Graph

`IssueGraphService::build` deletes and recreates the case's issues so the graph
always reflects the current claim set rather than accumulating stale states. That
makes it unsafe to run twice at once: two workers finishing Party A and Party B
at the same moment would both delete and both rebuild, and the loser's issues
would vanish.

`BuildIssueGraph` is therefore `ShouldBeUnique` on `caseId` **and** takes
`Cache::lock("issue-graph:{caseId}")` with `block(60, …)` — blocking rather than
skipping, because a rebuild triggered by the second party's claims must not be
dropped just because the first one is still running.

## Identifier ownership

FastAPI generates claim ids (`claim_<hex>`); `ClaimIngestionService` maps them to
Laravel UUIDs and keeps `externalToInternal` for supersessions. From that point
on, Laravel ids are the only ones that cross the boundary — `build-issue-graph`
and `generate-case` both send and receive Laravel UUIDs, which is why
`supporting_claim_ids` can be written straight into `issue_claims`.

**FastAPI never invents a party id.** Evidence names a *role*
(`mentioned_by_role: "PARTY_B"`) and `IssueGraphService` resolves it against the
case's own parties. Returning `"party_b"` into a `party_id` foreign key would
have failed the insert.

## Failure semantics

| Condition | FastAPI | Laravel |
| --- | --- | --- |
| Unknown provider / bad payload | 400 / 422 | fails fast, no retry |
| ASR provider failure | 502 | job retries with backoff, then marks the recording `FAILED` |
| Neutrality violation | 422 `neutrality_violation` | 422 to the caller, nothing persisted |
| Unbacked statement | 422 `unbacked_statement` | 422 to the caller, nothing persisted |
| Service unreachable | — | `IntelligenceServiceException` → 503 |

A provider failure is recorded as a failure. The system never silently falls back
to a different ASR: substitution would corrupt the benchmark and make the case
provenance false.

## Guards are duplicated on purpose

`NeutralityFilter` (Laravel) and `neutrality.py` (FastAPI) implement the same
rule independently, as do `HallucinationValidator` and `hallucination.py`. FastAPI
blocks before returning; Laravel blocks before persisting. A single guard is a
single point of failure, and adjudicative prose reaching a mediator is the failure
mode with the highest cost.

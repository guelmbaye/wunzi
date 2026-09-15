# WUNZI — Technical Architecture

## Shape

```
Next.js  ──►  Laravel 11  ──►  PostgreSQL 16
(capture)     (System of Record)
                   │
                   ▼
              FastAPI  ──►  ASR adapters (Sahara · Whisper · Model B · Model C)
              (intelligence)
```

Two services, one database, one direction of authority. Laravel owns state.
FastAPI owns language. Neither owns the outcome — a human mediator does.

## Why this split

Speech and semantics need Python; case state, audit, permissions and workflow
need a boring, durable system of record. Merging them would put transcription
retries and mediation state transitions in the same failure domain.

The rule that keeps it honest: **FastAPI never writes to the database.** It
receives structured input, returns structured output, and Laravel decides
whether that output is allowed to change the case.

## Data flow

| Step | Owner | What happens |
| --- | --- | --- |
| 1. Capture | Next.js → Laravel | consent recorded, audio stored in private S3, SHA-256 computed |
| 2. Transcription | Laravel → FastAPI → ASR | idempotent on `sha256 + provider + model + pipeline_version` |
| 3. Claim extraction | FastAPI | atomic, attributed propositions with source segment ids |
| 4. Critical Speech Guard | FastAPI | decides ACCEPT / NEEDS_CONFIRMATION / REJECT_AS_UNRESOLVED |
| 5. Verification | Laravel ↔ speaker | speaker confirms or corrects their own words |
| 6. Issue Graph | FastAPI | AGREED / DISPUTED / MISSING / UNVERIFIED |
| 7. Case Packet | FastAPI → Laravel | neutral prose, every sentence provenance-backed |
| 8. Mediation | human | WUNZI stops here |

## State machine

```
DRAFT → PARTY_A_CAPTURE → PARTY_B_CAPTURE → VERIFICATION_REQUIRED
      → ISSUE_GRAPH_READY → MEDIATOR_REVIEW → READY
```

`READY` is terminal and reachable only when no critical field is still in
`NEEDS_CONFIRMATION`. The gate lives in `CaseStateMachine`, not in a controller,
so no route can bypass it.

## Immutability and provenance

`transcript_runs` are append-only. A correction never overwrites a transcript;
it creates a `verification_event` and a superseding claim. Every claim carries
`claim_sources` pointing at transcript segments, which point at an audio
recording and a byte offset. From any sentence in a case packet a mediator can
reach the audio that produced it:

```
Case Packet statement → Issue → Claim → Transcript segment → Audio → timestamp
```

Nothing in a case packet exists without that chain. That is enforced by
`HallucinationValidator`, which rejects any statement whose provenance kind is
not one of `SOURCE_CLAIM`, `DERIVED_RELATION`, `MISSING_INFORMATION`,
`SYSTEM_METADATA`.

## Two guards, two services

`NeutralityFilter` (Laravel) and `neutrality.py` (FastAPI) implement the same
rule independently. The duplication is deliberate: a single guard is a single
point of failure, and adjudicative prose reaching a mediator is the failure mode
with the highest cost. FastAPI blocks before returning; Laravel blocks before
persisting.

## ASR adapter contract

Every provider implements `transcribe(audio_uri, config) -> NormalizedTranscript`.
No code downstream of the adapter branches on provider identity except benchmark
labelling. Swapping Sahara for Whisper changes one environment variable.

Provider metadata is never synthesised. Intron's `file/v1/upload/sync` returns a
flat transcript with no segments, no timestamps and no confidence; Whisper
reports one language per request. Those fields stay `null` rather than being
filled in — an invented confidence score would corrupt the Critical Speech
Guard, which reads them, and invented segment boundaries would falsify the
provenance chain every claim is traced through.

A provider failure is recorded as a failure. The system never silently falls back
to a different model: substitution would make the benchmark meaningless and the
case provenance false.

## Idempotency

Transcription keys on `sha256(audio) + provider + model + pipeline_version`. A
retried job returns the existing run rather than producing a second transcript of
the same audio. Bumping `PIPELINE_VERSION` intentionally invalidates the key,
which is how a pipeline change gets re-measured instead of silently inheriting
old results.

## What is deliberately absent

No graph database — the issue graph is small, relational and queried by case.
No RAG over legal corpora — WUNZI does not interpret law.
No multi-agent orchestration — more autonomy is the opposite of what this needs.
No "truth agent" — the entire product rests on not having one.

Each omission removes a way for the system to appear more capable than it is.

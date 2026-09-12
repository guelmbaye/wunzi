# WUNZI intelligence service

FastAPI. Owns speech, claims, criticality, comparison and case generation.

Owns no truth: Laravel is the System of Record and a human mediator is the
decision-maker. This service can refuse to answer; it can never decide a case.
It holds no state and never touches the database.

## Running it alone

```bash
pip install -r requirements.txt
cp .env.example .env          # container defaults point at /benchmark
uvicorn app.main:app --reload --port 8001
pytest
```

Without `.env`, `FIXTURE_ROOT` and `BENCHMARK_ROOT` keep their container values
(`/benchmark/...`), the fixture provider finds no cached output and the benchmark
finds no manifest. Under docker compose the file is ignored — the stack injects
the root `.env` instead, so the two must not drift.

## Endpoints

Everything is mounted under `/v1` except `/health`, which stays unversioned so an
orchestrator probe does not break when the API version moves. Every `/v1` route
requires the `X-Internal-Service-Token` header.

| Route | Purpose |
| --- | --- |
| `POST /v1/speech/transcribe` | one clip, one provider; honours `Idempotency-Key` |
| `POST /v1/intelligence/analyze-turn` | extraction + Critical Speech Guard in one round trip |
| `POST /v1/intelligence/extract-claims` | extraction alone (benchmark ablation) |
| `POST /v1/intelligence/evaluate-criticality` | guard alone (benchmark ablation) |
| `POST /v1/intelligence/build-issue-graph` | AGREED / DISPUTED / MISSING / UNVERIFIED |
| `POST /v1/intelligence/generate-case` | neutral, provenance-backed case packet |
| `POST /v1/benchmark/run` | 202 + run id; poll `GET /v1/benchmark/runs/{id}` |

## Layout

```
app/asr/           provider adapters — one contract, no mediation logic inside
app/intelligence/  lexicon · canonicalizer · negation · attribution ·
                   claim_extractor · criticality · issue_matcher · issue_graph ·
                   case_packet · neutrality · hallucination
app/llm/           optional semantic layer + versioned prompts
app/benchmark/     metrics, dataset loader, runner, CLI, fixture capture
app/schemas/       the wire contract with Laravel
```

## Rules that are not negotiable here

- **Provider metadata is never synthesised.** If a provider does not report
  per-segment language or confidence, the field stays `null`. An invented
  confidence would corrupt the Critical Speech Guard, which reads it.
- **A provider failure is a failure.** No silent fallback to another model:
  substitution would make the benchmark meaningless and a case's provenance
  false.
- **Uncertainty is returned, not resolved.** When rules cannot decide whether two
  propositions match, the answer is `UNCERTAIN`, which surfaces as `UNVERIFIED`.
- **Two guards run before anything leaves.** `neutrality.py` rejects adjudicative
  prose; `hallucination.py` rejects any statement without provenance. Laravel
  re-checks both independently.

## Tests

```bash
pytest                              # 81
pytest tests/test_golden_path.py    # the demo case, end to end, asserting meaning
pytest tests/test_laravel_contract.py
```

`test_laravel_contract.py` replays the exact payloads the Laravel services build.
The two codebases are in different languages and nothing else checks that they
agree — see also `scripts/check_routes.py` at the repo root.

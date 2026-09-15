# Submission package — Sahara CodeSwitch Africa Challenge

Category: **Legal & Public Services** · Rwanda · Kinyarwanda ⇄ English ⇄ French

| Required deliverable | Where |
| --- | --- |
| Solution Description | [`solution-description.md`](solution-description.md) |
| Benchmark Report | [`benchmark-report.md`](benchmark-report.md) |
| Ethics / Inclusion Note | [`ethics-inclusion-note.md`](ethics-inclusion-note.md) |
| Docs / technical documentation | [`../../README.md`](../../README.md) and `docs/` |
| Demo video | **to record** — see the runbook below |
| Benchmark audios (optional) | `benchmark/fixtures/audio/` — empty; see the report |

## Supporting documentation

| | |
| --- | --- |
| [`../architecture.md`](../architecture.md) | shape, state machine, provenance chain |
| [`../service-contract.md`](../service-contract.md) | the Laravel ↔ FastAPI boundary, timeout and retry budgets |
| [`../benchmark-methodology.md`](../benchmark-methodology.md) | both tiers in full |
| [`../responsible-ai.md`](../responsible-ai.md) | what is refused, and where it is enforced |
| [`../limitations.md`](../limitations.md) | every known limit |
| [`../guide-deploy-wunzi.md`](../guide-deploy-wunzi.md) | production deployment (French) |
| [`../../benchmark/README.md`](../../benchmark/README.md) | dataset, splits, capture, failure taxonomy |

## Before submitting

The benchmark carries the heaviest weight in the rubric (30%), and it is the one
thing still missing a live measurement.

```bash
# 1. Tier 1 — the measurement that is missing
huggingface-cli login          # then accept the AfriSwitch conditions
export WUNZI_MODE=live
export SAHARA_API_KEY=… WHISPER_API_KEY=… MODEL_B_API_KEY=… MODEL_C_API_KEY=…
python -m app.benchmark.afriswitch_cli run \
  --config kinyarwanda --limit 200 \
  --providers sahara,whisper,model_b,model_c \
  --out benchmark/reports

# 2. Paste the resulting table into benchmark-report.md § "Layer B — Results"
```

If that run cannot happen before the deadline, **submit the report as written**.
It states plainly which layer is measured and which is not. A benchmark that
declares its gap is worth more than one that presents a smoke test as a result —
and the software itself refuses to publish placeholder-derived numbers.

## Demo video runbook

Roughly five minutes, in this order. The sequence matters: consequence first,
mechanism second.

1. **The problem** (30s) — two accounts of one rental deposit dispute, spoken in
   mixed Kinyarwanda, English and French.
2. **Party A intake** (60s) — record or replay the demo account. Show the
   transcript with the language switches marked per segment.
3. **Party B intake** (45s) — the second account. Point out the denial spoken in
   Kinyarwanda immediately after an English sentence.
4. **Verification** (45s) — the Critical Speech Guard asking the speaker to
   confirm a value. Show that "Not sure" is an available answer, and that the
   case is blocked until it is resolved.
5. **Issue map** (60s) — the four states. Stop on `deposit_amount`: 150,000 next
   to 100,000, and say out loud that no third number appears anywhere.
6. **Case packet** (30s) — the mediator-ready document, and the boundary line
   printed on it.
7. **Benchmark** (60s) — the same-audio comparison, then the honest framing: the
   harness is complete, the numbers shown are a pipeline smoke test, and the
   interface refuses to render a headline figure from placeholder fixtures.

Say the placeholder caveat **on camera**. A judge who discovers it themselves
reads it as a gap; a team that states it first reads as one that can be trusted
with the numbers it does publish.

## Reproducing the build

```bash
cp .env.example .env
make up && make install && make migrate
make demo                      # builds WZ_DEMO_001 from fixtures
make test                      # 97 intelligence tests + 3 contract checkers
```

Three static checkers guard the seams between the services, and each was written
after the class of bug it catches reached a real deployment:

```bash
make check-routes        # do Web → Laravel → FastAPI agree on paths?
make check-payloads      # do the frontend mappers read fields Laravel emits?
make check-migrations    # PostgreSQL-only migration ordering hazards
```

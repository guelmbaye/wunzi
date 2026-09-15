# Submission package — Sahara CodeSwitch Africa Challenge

Category: **Legal & Public Services** · Rwanda · Kinyarwanda ⇄ English ⇄ French

| Required deliverable | Where |
| --- | --- |
| Solution Description | [`solution-description.md`](solution-description.md) |
| Benchmark Report | [`benchmark-report.md`](benchmark-report.md) |
| Ethics / Inclusion Note | [`ethics-inclusion-note.md`](ethics-inclusion-note.md) |
| Docs / technical documentation | [`../../README.md`](../../README.md) and `docs/` |
| Demo video | **to record** — [`demo-video-runbook.md`](demo-video-runbook.md) |
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

## Demo video

Shot-by-shot script, narration lines, browser setup and timing:
[`demo-video-runbook.md`](demo-video-runbook.md).

Two things to settle before filming:

**Which mode.** With a `SAHARA_API_KEY`, run in `live` and record real speech —
it is the most convincing shot available. Without one, run in `fixture` and use
the **"Use the stored recording"** button on the intake screen. Do **not** press
record on camera in fixture mode: a fresh file has no cached transcription, the
job fails, and the recording is marked `FAILED`.

**Reset first.** Neutral sentences are stored at ingestion, not computed at
display, so a case built before the latest deploy shows the old text:

```bash
php artisan migrate:fresh --force && php artisan db:seed --force
php artisan wunzi:demo-case
```

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

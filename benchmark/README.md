# WUNZI Benchmark — Switch-Aware Mediation Evaluation

This directory holds the evaluation dataset, the annotations, the cached provider
outputs and the generated reports.

## The claim being tested

> Same audio. Same WUNZI. Different ASR. Different mediation state.

Everything downstream of transcription is frozen during a run: the same claim
extractor, the same Critical Speech Guard, the same Issue Graph rules, the same
prompt versions. **Only the ASR provider changes.** That freeze is what makes the
comparison a measurement instead of a story.

## Layout

```
manifests/      dataset-v1.json — scenarios, clips, splits, consent metadata
annotations/    <scenario_id>.json — reference transcripts, expected claims, expected issue states
fixtures/asr/   <provider>/<clip_id>.json — cached provider outputs
fixtures/audio/ consented source audio
reports/        generated results.json, metrics.csv, report.md
```

## Splits

| Split | Size | Use |
| --- | --- | --- |
| `dev` | 5 disputes | development, tuning, inspection |
| `holdout` | 10 disputes | never used for tuning — all headline numbers come from here |

Tuning on the holdout split invalidates the run. The split exists so the team can
tell the difference between "we measured it" and "we tuned until it looked good".

## Metrics

**Speech layer** — Word Error Rate, Character Error Rate. Reported for
comparability with the wider ASR field, never as the headline. WER is lexical; a
mediation outcome is not.

**Mediation-critical layer**

| Metric | What it measures |
| --- | --- |
| Critical Fact Accuracy | exact canonical match on amounts and dates — no partial credit |
| Negation Preservation Rate | a dropped "not" flips an issue from AGREED to DISPUTED |
| Claim Attribution Accuracy | the claim is attached to the party who made it |
| Wrong-Party Attribution Rate | safety metric: manufacturing a false accusation |
| Issue Macro-F1 | per-status quality across AGREED / DISPUTED / MISSING / UNVERIFIED |
| **CMSR** | Correct Mediation State Rate — the fraction of cases whose *entire* mediation state is correct |

**Safety layer** — Critical Error Absorption Rate, Unverified Value Visibility
Rate, Silent Resolution Rate (target: zero), clarification precision and recall.

CMSR is all-or-nothing on purpose. A mediator handed one wrong DISPUTED among six
correct issues still walks into the room carrying a false conflict.

## Sponsor Outcome Delta

```
SOD = CMSR(Sahara) − max CMSR(all other providers)
```

An **internal discipline metric**, not an official Intron criterion. It exists so
the team is honest with itself about whether the sponsor model is genuinely
load-bearing or merely present in the architecture diagram.

Interpretation is two-sided. If the delta is small, the honest reading is that
the mediation layer absorbs ASR differences well — and the response is to
strengthen the code-switch difficulty of the evaluation set, not to quietly drop
the metric.

## ⚠ Placeholder fixtures

The fixtures currently shipped in `fixtures/asr/` are **placeholders**. Each one
carries:

```json
{ "is_placeholder": true, "fixture_origin": "PLACEHOLDER — NOT A REAL PROVIDER CAPTURE" }
```

They exist so the pipeline can be exercised end-to-end without network access.
The runner detects them and sets `publishable: false` on the response; the
generated report prints a **NOT PUBLISHABLE** banner. No number derived from a
placeholder may appear in a submission, a slide, or a claim about Sahara.

### Capturing real fixtures

```bash
export WUNZI_MODE=live
export SAHARA_API_KEY=... WHISPER_API_KEY=... MODEL_B_API_KEY=... MODEL_C_API_KEY=...
python -m app.benchmark.capture --dataset dataset-v1 --providers sahara,whisper,model_b,model_c
```

Each captured file records `captured_at`, `capture_run_id`, the provider model
string and the untouched raw payload. Replays keep that origin so a judge can
tell a replay from a live call at a glance.

## Running

```bash
make benchmark                        # holdout split, all four providers
python -m app.benchmark.cli run --split dev --providers sahara,whisper
python -m app.benchmark.cli run --split holdout --no-guard   # guard ablation
```

The guard ablation answers the question a judge will ask: *what does the system
let through without the Critical Speech Guard?*

## Consent and provenance

Every clip carries a recorded consent flag and a provenance note. Audio is
participant-recorded or acted from consented scripts — no scraped courtroom
material, no recordings of real disputes obtained without permission. Names in
reference transcripts are pseudonymised. A speaker may withdraw, which removes
the clip and every annotation derived from it.

## Failure taxonomy

| Code | Failure |
| --- | --- |
| E01 | Numeric error (amount misheard) |
| E02 | Date error |
| E03 | Negation loss |
| E04 | Attribution error (wrong party) |
| E05 | Reported speech flattened into direct fact |
| E06 | Code-switch boundary error |
| E07 | Named entity error |
| E08 | Claim omitted entirely |
| E09 | Claim invented (no source) |
| E10 | Issue state error |

Counting failures is cheap; explaining them is what makes the evaluation useful.

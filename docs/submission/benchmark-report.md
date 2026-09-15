# WUNZI — Benchmark Report

**Switch-Aware Mediation Evaluation** · Kinyarwanda ⇄ English ⇄ French
Four speech models · Same audio · Everything downstream frozen

---

## What this report claims, and what it does not

A benchmark is only worth its weakest layer of evidence, so the three layers are
separated here rather than blended into one table.

| | Evidence | Status |
| --- | --- | --- |
| **A** | Intron's published AfriHealth MultiBench results, Kinyarwanda | Third-party, published, cited below |
| **B** | WUNZI Tier 1 — AfriSwitch WER/CER + code-switch integrity | Harness complete and tested; **awaiting a live provider run** |
| **C** | WUNZI Tier 2 — mediation outcome (CMSR) | Pipeline verified end to end; **fixtures are placeholders** |

**Layer A is real data.** It is not ours, and we cite it as someone else's
measurement.

**Layers B and C are our harness.** The code runs, the metrics are implemented and
unit-tested, and the end-to-end path is verified. What is missing is a live run
against the four provider APIs on consented audio. Until that happens, no number
this repository produces describes any speech model's real behaviour — and the
software says so itself: the runner sets `publishable: false`, the generated
report prints a **NOT PUBLISHABLE** banner, and the web interface refuses to
render the headline figure.

We would rather submit a benchmark that states what it has not yet measured than
one that quietly presents a smoke test as a result.

---

## Layer A — What is already known about these models on Kinyarwanda

Intron's own AfriHealth MultiBench reports the following on Kinyarwanda. This is
their published measurement, on a clinical corpus, and it is the reason Sahara is
WUNZI's primary provider rather than a sponsor formality.

| Model | WER ↓ | CER ↓ |
| --- | --- | --- |
| **Sahara** | **0.258** | **0.084** |
| OmniLLM | 0.312 | 0.124 |
| OmniCTC | 0.375 | 0.136 |
| Gemini-Flash | 0.426 | 0.181 |
| Gemma4 | 0.716 | 0.269 |
| GPT-4o | 0.839 | 0.427 |
| Qwen3 | 1.000 | 0.607 |

Two uses. First, it establishes that provider choice is not arbitrary for this
language — the spread between best and worst is nearly fourfold on WER. Second,
it gives WUNZI's harness a **sanity check**: every Tier-1 run prints Sahara's
measured WER beside this figure. Different corpus, so a gap is expected; an order
of magnitude is not, and a run that lands far away means the harness is broken
before it means anything about a model.

---

## The four models compared

Selected so the comparison is fair rather than flattering: a strong global
baseline, a strong multimodal contender, and a third credible system, against the
sponsor.

### Sahara (Intron) — primary

**Strengths.** Best published Kinyarwanda accuracy of the models surveyed, by a
clear margin. Exposes **language spans per segment**, which no other adapter in
this set does — WUNZI reads those spans to mark code-switch boundaries in the
transcript view, and the Critical Speech Guard reads per-segment confidence.
Trained for African language varieties rather than adapted to them.

**Weaknesses.** Commercial API with per-call cost and a hard external dependency.
Smaller public track record than Whisper. Availability outside the challenge
context is unverified by us.

**Why it is primary.** The published Kinyarwanda gap, plus the per-segment
metadata that the guard actually consumes. A model that reports no confidence
forces the guard onto weaker structural signals.

### Whisper large-v3 (OpenAI) — comparator

**Strengths.** The most widely deployed multilingual baseline; strong on English
and French, well documented, easy to reproduce. Including it means the comparison
cannot be accused of picking weak opponents.

**Weaknesses.** Reports **one language per request, not per segment** — so
intra-utterance switching is invisible in its output, and WUNZI shows no language
tags for it rather than inventing them. Known to prefer fluent output, which in
code-switched speech is the exact pressure that produces translation instead of
transcription. Lower-resource African languages are far from its training
centre of mass.

### Model B — Gemini-class speech — comparator

**Strengths.** Strong multimodal contender with per-result language codes and
confidence. Long-context handling is good for extended accounts.

**Weaknesses.** Same fluency pressure as Whisper, arguably stronger. Published
Kinyarwanda performance (as Gemini-Flash, above) sits well behind Sahara. Output
shape varies between API revisions, which is a maintenance cost the adapter
absorbs.

### Model C — NVIDIA Nemotron-class ASR — comparator

**Strengths.** Open-weight lineage, so it can be self-hosted where sending
mediation audio to a third party is unacceptable — a real consideration for a
justice-adjacent deployment.

**Weaknesses.** Least African-language coverage of the four. Self-hosting shifts
cost from per-call to infrastructure rather than removing it.

### The comparison that matters

All four are good enough to produce a readable transcript. The question WUNZI
asks is narrower and harsher: **when the model gets something wrong, does a
mediator end up with a different case?**

---

## Layer B — Tier 1: AfriSwitch

### Corpus

`intronhealth/AfriSwitch`, Kinyarwanda config — in-the-wild conversational
code-switched speech, human-transcribed, evaluation-only `test` split,
CC BY-NC-SA 4.0.

| | |
| --- | --- |
| Hours | 5.00 |
| Utterances | 1,577 |
| Mean switch points per utterance | 4.51 |
| Code-Mixing Index | 16.95 |

Chosen over a self-authored set for three reasons: we did not choose which
utterances are hard; Intron has published provider numbers on the same language,
so the harness can be checked; and `transcription_tagged` annotates English spans
with `[[EN]]`…`[[/EN]]`, giving real switch-boundary ground truth rather than
something we inferred.

### Stratification

Reported per Code-Mixing Index band, not only as an average:

| Band | CMI |
| --- | --- |
| Light | < 10 |
| Moderate | 10–20 |
| Heavy | ≥ 20 |

Models tend to hold up on light mixing and come apart on heavy mixing. One
average across both splits the difference into a number that describes neither —
and hides exactly the finding a code-switching benchmark exists to surface.
Sampling below the full corpus is proportional across bands and deterministic.

### Metrics

**Standard.** WER and CER on the same normalisation Intron uses, so the numbers
sit alongside theirs rather than in a private scale.

**Code-switch integrity** — three measures WER cannot express:

| Metric | Question | Direction |
| --- | --- | --- |
| **Matrix Language Collapse Rate** | Did the model translate instead of transcribing? | lower |
| Switch Point Preservation | Did the English insertions survive? | higher |
| Span Language Fidelity | Did the matrix language survive? | higher |

**Matrix Language Collapse** is the contribution we think matters most here. A
model that hears Kinyarwanda and emits fluent English scores badly on WER — but
so does a model that simply misheard, and those two failures need completely
different responses. In mediation the difference is decisive: a translated account
is no longer the speaker's own words, so nothing built on it can be traced back
to what anyone said.

Collapse is detected from English function-word density, **not** from matching the
matrix orthography. That makes it immune to the spelling variation Intron flags
as a known WER problem in languages without settled conventions. We verified this
property directly:

| Degradation | Ref. EN ratio | Hyp. EN ratio | Collapse |
| --- | --- | --- | --- |
| Faithful transcription | 0.190 | 0.190 | 0 |
| Full translation to English | 0.190 | 0.556 | **1** |
| Partial translation | 0.190 | 0.450 | **1** |
| Misheard amount (150,000 → 50,000) | 0.190 | 0.190 | 0 |
| **Garbled matrix orthography** | 0.190 | 0.190 | **0** |
| English-only short output | 0.190 | 0.667 | **1** |
| Empty output | 0.190 | 0.000 | 0 |

The fifth row is the one to check: a phonetically garbled but linguistically
faithful Kinyarwanda transcript scores badly on WER and correctly reports no
collapse. The two metrics are measuring different failures, as intended.

Monolingual utterances are **excluded** from switch preservation rather than
scored 1.0 — there was nothing to preserve, and counting it as success would hand
every model free marks.

### Statistics

Bootstrap confidence intervals on every figure. Sahara is compared to each
alternative with a **paired** bootstrap over the same utterances: every model saw
identical audio, so the per-utterance difference carries the signal, and an
unpaired comparison of two averages would discard it and widen the interval for
nothing. Intervals spanning zero are reported as not significant, and on a sample
this size several will be.

### Reproducing

```bash
huggingface-cli login
# accept the conditions at
# https://huggingface.co/datasets/intronhealth/AfriSwitch

export WUNZI_MODE=live
export SAHARA_API_KEY=… WHISPER_API_KEY=… MODEL_B_API_KEY=… MODEL_C_API_KEY=…

python -m app.benchmark.afriswitch_cli run \
  --config kinyarwanda --limit 200 \
  --providers sahara,whisper,model_b,model_c \
  --out benchmark/reports
```

### Access

AfriSwitch is gated behind **manual author review**. Access was requested on
15 September 2026 and was still pending at submission time. That is stated here
rather than left as an unexplained gap.

### Results

**Pending.** The harness is complete: dataset loader, stratified sampling, all
five metrics, paired bootstrap, and the cross-check against Intron's published
figure. Results belong in this section and nowhere else, and no placeholder
numbers are presented in their place.

### Fallback source — a reachable Kinyarwanda corpus

Because AfriSwitch access may not arrive in time, the harness also runs against a
monolingual Kinyarwanda corpus. Which one is **discovered at runtime**: three
obvious candidates failed for three different reasons — `datasets` 3.x dropped
support for script-based repositories, which covers `mozilla-foundation/common_voice_17_0`,
`fsicoli/common_voice_17_0` and `google/fleurs`. Rather than guess a fourth, the
loader tries a ranked list, discovers the transcript and audio columns by name,
and records which dataset actually produced the numbers.

This is **read, monolingual speech**, and the report is explicit about what that
changes:

| Metric | On Common Voice |
| --- | --- |
| Word / Character Error Rate | **measured** — real Kinyarwanda, real providers |
| Matrix Language Collapse | **measured** — a model returning English for a Kinyarwanda utterance has translated rather than transcribed, and that is detectable without any switches |
| Span Language Fidelity | **measured** |
| Switch Point Preservation | **excluded** — there are no switches to preserve |

Switch preservation is excluded rather than scored 1.0. Scoring monolingual audio
as perfect would hand every model a free mark on the one axis this challenge is
about, and the exclusion is enforced in the runner, the paired comparison and the
rendered report, with tests pinning each.

Code-mixing stratification is suppressed for the same reason: every utterance has
a Code-Mixing Index of zero, so band tables would be one row pretending to be
three.

**What this fallback is worth.** It does not measure code-switch handling, and no
claim about code-switching should be drawn from it. What it does establish is
that the harness works end to end against live provider APIs on real Kinyarwanda
audio — and it triggers the cross-check against Intron's published Sahara WER of
0.258, which is how a broken harness gets caught before it becomes a wrong
conclusion.

```bash
python -m app.benchmark.afriswitch_cli run \
  --source fallback --limit 200 \
  --providers sahara,whisper,model_b,model_c \
  --out benchmark/reports
```

---

## Layer C — Tier 2: did the error change the mediation?

Tier 1 measures whether the model heard the speech. Tier 2 asks the question
neither AfriSwitch nor AfriHealth MultiBench asks.

Intron's own AfriHealth README names the gap:

> Intra-utterance code-switching is present but inconsistently annotated across
> languages.

AfriSwitch closes the annotation gap. Neither measures **downstream task
consequence**. The WER → CMSR link is WUNZI's contribution, and it is offered as a
contribution rather than a claim of superiority — Tier 1 is where the harness
earns the right to be believed.

### Metrics

| Metric | What it measures |
| --- | --- |
| Critical Fact Accuracy | exact canonical match on amounts and dates — **no partial credit** |
| Negation Preservation | measured clause by clause; a dropped "not" reverses an issue |
| Claim Attribution Accuracy | the claim is attached to the party who made it |
| Wrong-Party Attribution Rate | safety metric: manufacturing a false accusation |
| Issue Macro-F1 | per-status quality across the four mediation states |
| **CMSR** | Correct Mediation State Rate — the fraction of cases whose **entire** state is right |

Critical Fact Accuracy gives no partial credit on purpose. 150,000 heard as
50,000 is wrong; a system that scored it 0.66 for sharing digits would be lying
about the risk it creates.

CMSR is all-or-nothing per case for the same reason. A mediator handed one wrong
`DISPUTED` among six correct issues still walks into the room carrying a conflict
that does not exist.

### Splits

5 dev disputes for tuning and inspection; 10 holdout never tuned on. Tuning on
holdout invalidates the run.

### Pipeline verification

The end-to-end path is verified by `tests/test_golden_path.py`, which runs the
demo dispute through every stage and asserts **meaning**, not shape:

- the nine expected issue states are produced exactly
- 150,000 and 100,000 produce `DISPUTED` — no third number appears anywhere
- Party B's denial, spoken in Kinyarwanda after an English sentence, survives as
  a `NEGATIVE` claim; losing it would collapse the issue to `AGREED` and a
  mediator would walk in believing a promise was made
- Party A quoting Party B is recorded as reported speech, never as Party B
  speaking
- a mentioned-but-unprovided invoice stays `MISSING`
- the generated packet contains no adjudicative language

97 tests pass, including 16 on the code-switch metrics and 22 on the
service contract between Laravel and FastAPI.

### Results

**Pipeline smoke test only.** Running the current fixtures produces CMSR 100%
for Sahara against 0% for the comparators. **That number describes nothing about
Sahara.** The fixtures are hand-authored placeholders with deliberately chosen
degradations; what they demonstrate is that the mechanism works — a misheard
amount, a lost negation or a shifted date does propagate to a different mediation
state. A 100-point delta on a single scenario is a plumbing test, not a
measurement, and the software refuses to publish it as one.

---

## Sponsor Outcome Delta

```
SOD = CMSR(Sahara) − max CMSR(all other providers)
```

An **internal discipline metric, not a challenge criterion.** It exists so the
team can tell whether the sponsor model is load-bearing or merely present in the
architecture diagram.

It is read two-sided. If the delta turns out small on real audio, the honest
conclusion is that the mediation layer absorbs ASR differences well and the
evaluation set needs to be harder — not that the metric should quietly disappear
from the report.

---

## Integrity rules

- **Only the ASR provider varies.** Same claim engine, same guard, same issue
  rules, same prompt versions, frozen for the duration of a run.
- **A failed provider is recorded as a failure.** No silent substitution —
  swapping models mid-run would make every comparison meaningless.
- **Provider metadata is never synthesised.** A model that does not report
  per-segment language or confidence leaves those fields null, all the way
  through to the interface.
- **Placeholder fixtures cannot produce a published number.** Enforced in the
  runner, the report generator and the UI independently.
- **The harness is cross-checked before it is trusted.** Every Tier-1 run prints
  Sahara's WER beside Intron's published Kinyarwanda figure.
- **Holdout is never tuned on.**

---

## Licensing and consent

AfriSwitch is CC BY-NC-SA 4.0, sourced from publicly available media under
permissive licences, transcribed by bilingual annotators, released with no links
back to the original media. WUNZI redistributes none of it — the loader pulls
from Hugging Face under the user's own accepted licence terms.

WUNZI's own mediation audio is participant-recorded or acted from consented
scripts. No scraped courtroom material, no recordings of real disputes obtained
without permission. Names in reference transcripts are pseudonymised, and a
speaker may withdraw, which removes the clip and every annotation derived from it.

---

## What we would do next

1. **Run Tier 1 live** on the full 1,577 Kinyarwanda utterances across all four
   providers. This is the missing measurement and everything else is secondary to
   it.
2. **Capture authentic fixtures** with `app/benchmark/capture.py`, the only
   sanctioned way to produce a file under `benchmark/fixtures/asr/`, so the demo
   replays real provider output with its origin recorded.
3. **Record the remaining 14 mediation scenarios** with consented speakers and a
   native Kinyarwanda annotator in the loop.
4. **Harden the evaluation set** if the Sponsor Outcome Delta comes back small —
   more heavy-CMI utterances, more negation carried across switches.

Methodology in full: `docs/benchmark-methodology.md`.
Dataset, splits, capture procedure and failure taxonomy: `benchmark/README.md`.

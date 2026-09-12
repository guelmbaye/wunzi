# Benchmark Methodology

Two tiers. The first earns the right to be believed; the second says something
new.

| | Tier 1 | Tier 2 |
| --- | --- | --- |
| Data | `intronhealth/AfriSwitch`, Kinyarwanda | WUNZI mediation scenarios |
| Provenance | External, human-transcribed, published | Ours |
| Measures | WER · CER · code-switch integrity | Mediation state correctness |
| Answers | Did the model hear the speech? | Did the error change the outcome? |

A benchmark built only on scenarios we wrote ourselves asks a reader to take our
word for their difficulty. A benchmark built only on an external corpus measures
transcription and stops short of the thing this product exists to protect. Both
tiers run on identical audio with everything downstream of transcription frozen.

---

## Tier 1 — AfriSwitch

### The corpus

AfriSwitch is 54.41 hours of in-the-wild conversational code-switched speech
across 14 African languages, human-transcribed, released as an evaluation-only
`test` split under CC BY-NC-SA 4.0.

WUNZI uses the Kinyarwanda config:

| | |
| --- | --- |
| Hours | 5.00 |
| Utterances | 1,577 |
| Mean switch points per utterance | 4.51 |
| Code-Mixing Index | 16.95 |

It is real conversational speech, not read prompts, and the switching is natural
rather than staged — which is the only kind of switching a mediation intake will
actually encounter.

### Why not only our own scenarios

Three things AfriSwitch supplies that a self-authored set cannot:

1. **Independent difficulty.** We did not choose which utterances are hard.
2. **A published cross-check.** Intron's AfriHealth MultiBench reports
   Kinyarwanda WER of 0.258 for Sahara. A harness that lands an order of
   magnitude away is broken, and we find that out before drawing a conclusion
   rather than after.
3. **Real language-span ground truth.** `transcription_tagged` wraps English
   spans in `[[EN]]`…`[[/EN]]`. Switch boundaries are annotated by bilingual
   humans, not inferred by us.

### Stratification

Results are reported per Code-Mixing Index band, not only as an average:

| Band | CMI |
| --- | --- |
| Light | < 10 |
| Moderate | 10–20 |
| Heavy | ≥ 20 |

Models tend to hold up on light mixing and come apart on heavy mixing. One
average over both splits the difference into a number that describes neither,
and hides exactly the finding a code-switching benchmark exists to surface.

Sampling below the full 1,577 utterances is proportional across bands and
deterministic — taking the head of the list would silently select whichever band
happens to sort first.

### Metrics

**Standard.** WER and CER, computed on the same normalisation Intron uses, so
the numbers sit alongside theirs rather than in a private scale.

**Code-switch integrity** — what WER cannot express:

| Metric | Question | Direction |
| --- | --- | --- |
| Matrix Language Collapse Rate | Did the model translate instead of transcribing? | lower |
| Switch Point Preservation | Did the English insertions survive? | higher |
| Span Language Fidelity | Did the matrix language survive? | higher |

**Matrix Language Collapse** is the one that matters most and the reason the
module exists. A model that hears Kinyarwanda and emits fluent English scores
badly on WER — but so does a model that simply misheard, and those two failures
need completely different responses. In mediation the difference is decisive: a
translated account is no longer the speaker's own words, so nothing built on it
can be traced back to what anyone said.

Collapse is detected from the density of English function words, not from
matching the matrix orthography. That makes it immune to the spelling variation
Intron flags as a known WER problem in languages without settled conventions:
a garbled-but-faithful Kinyarwanda transcript scores badly on WER and correctly
reports no collapse.

Switch preservation and span fidelity separate the two opposite failures that
both look like high WER — dropping the English insertions, and dropping the
matrix language.

Monolingual utterances are **excluded** from switch preservation rather than
scored 1.0. There was nothing to preserve, and counting it as a success would
hand every model free marks.

### Statistics

Bootstrap confidence intervals on every figure. Sahara is compared to each
alternative with a **paired** bootstrap over the same utterances: every model saw
identical audio, so the per-utterance difference carries the signal, and an
unpaired comparison of two averages would discard it and widen the interval for
nothing.

An interval spanning zero is reported as not significant. On a sample this size
several will, and saying so is the point.

---

## Tier 2 — Mediation outcome

Tier 1 measures whether the model heard the speech. Tier 2 asks the question
neither AfriSwitch nor AfriHealth MultiBench asks: **did the difference change
what a mediator would be handed?**

| Metric | What it measures |
| --- | --- |
| Critical Fact Accuracy | exact canonical match on amounts and dates — no partial credit |
| Negation Preservation | measured clause by clause; a dropped "not" reverses an issue |
| Claim Attribution Accuracy | the claim is attached to the party who made it |
| Wrong-Party Attribution Rate | safety metric: manufacturing a false accusation |
| Issue Macro-F1 | per-status quality across the four mediation states |
| **CMSR** | Correct Mediation State Rate — the fraction of cases whose *entire* state is right |

CMSR is all-or-nothing per case on purpose. A mediator handed one wrong
`DISPUTED` among six correct issues still walks into the room carrying a
conflict that does not exist.

Splits: 5 dev disputes for tuning and inspection, 10 holdout that are never
tuned on. Tuning on holdout invalidates the run.

### The gap this fills

Intron's own AfriHealth README names the limitation:

> Intra-utterance code-switching is present but inconsistently annotated across
> languages.

AfriSwitch closes the annotation gap. Neither measures downstream task
consequence. The WER → CMSR link is WUNZI's contribution, and it is stated as a
contribution rather than a claim of superiority: Tier 1 is where the harness is
validated against work that already exists.

---

## Sponsor Outcome Delta

```
SOD = CMSR(Sahara) − max CMSR(all other providers)
```

An **internal discipline metric**, not a challenge criterion. It exists so the
team can tell whether the sponsor model is load-bearing or merely present in the
architecture diagram.

Read two-sided. If the delta is small, the honest conclusion is that the
mediation layer absorbs ASR differences well and the evaluation set needs to be
harder — not that the metric should go away.

---

## Reproducing

```bash
huggingface-cli login
# accept the conditions at
# https://huggingface.co/datasets/intronhealth/AfriSwitch

make benchmark-afriswitch    # tier 1
make benchmark               # tier 2, holdout
make benchmark-ablation      # tier 2 with the Critical Speech Guard disabled
```

The ablation answers the question a technical judge will ask: what does the
system let through when the guard is removed?

## Integrity rules

- **Only the ASR provider varies.** Same claim engine, same guard, same issue
  rules, same prompt versions, frozen for the duration of a run.
- **A failed provider is recorded as a failure.** No silent substitution —
  swapping models mid-run would make every comparison meaningless.
- **Provider metadata is never synthesised.** A model that does not report
  per-segment language or confidence leaves those fields null.
- **Placeholder fixtures cannot produce a published number.** The runner sets
  `publishable: false`, the report prints a banner, and the UI refuses to render
  the headline figure.
- **The harness is cross-checked before it is trusted.** Every Tier-1 run prints
  Sahara's WER beside Intron's published Kinyarwanda figure.

## Licensing and consent

AfriSwitch is CC BY-NC-SA 4.0, sourced from publicly available media under
permissive licences, transcribed by bilingual annotators, released with no links
back to the original media and no annotator demographics. WUNZI redistributes
none of it — the loader pulls from Hugging Face under the user's own accepted
licence terms.

WUNZI's own mediation audio is participant-recorded or acted from consented
scripts. No scraped courtroom material, no recordings of real disputes obtained
without permission. Names in reference transcripts are pseudonymised, and a
speaker may withdraw, which removes the clip and every annotation derived from
it.

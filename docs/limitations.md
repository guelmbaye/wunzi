# Limitations

Stated here so they are not discovered by a judge.

## Scope

**One dispute type.** Rental deposit disputes only. The ontology has thirteen
issue types and none of them generalise to employment, land or family disputes
without new annotation work.

**One jurisdiction's assumptions.** Built around Rwandan rental practice and
RWF amounts. Currency parsing, date conventions and the two-party structure all
assume that context.

**Two parties.** Several claim-resolution rules — including the pronoun
convention that maps a third-person referent to "the other party" — hold only
because there are exactly two accounts. A three-party dispute breaks them.

## Evaluation

**Small dataset.** 15 disputes (5 dev, 10 holdout). Bootstrap confidence
intervals are reported precisely because the sample is small enough that point
estimates alone would overstate certainty.

**Placeholder fixtures ship in this repository.** The cached provider outputs in
`benchmark/fixtures/asr/` are marked `is_placeholder: true`. The runner detects
them and marks the run `publishable: false`. Any number produced from them is a
pipeline smoke test, not a measurement of any ASR provider.

**Sponsor Outcome Delta is internal.** It is a discipline metric the team uses to
check whether the sponsor model is load-bearing. It is not an official Intron
criterion and is not evidence of general provider superiority.

**Annotation is a judgement.** Ground-truth issue states were set by two
annotators with a third-pass adjudication. Items still contested are excluded
rather than forced, which slightly shrinks the effective sample.

## Language

**Kinyarwanda numerals are handled by an explicit lexicon**, not a general
morphological parser. Forms outside the rental-deposit vocabulary will not
canonicalise. The same applies to the first-person verb forms used for
attribution: the list is explicit and MVP-scoped because guessing a subject
invents an accusation.

**Code-switch handling is span-level, not token-level.** Claims are not broken at
language boundaries, but the system does not model borrowing or morphological
blending inside a single word.

**Dialectal and regional variation is untested.** The evaluation audio does not
systematically cover regional accents.

## Speech

**Confidence is only as good as the provider.** Providers that do not report
per-segment confidence leave the field `null`. The Critical Speech Guard then
falls back to structural signals — negation ambiguity, attribution uncertainty,
implausible amounts — which are weaker than a real confidence score. Inventing a
number would be worse.

**Diarization is not used.** Each party records separately, so speaker separation
comes from the recording structure rather than the model. Multi-speaker audio in
one file is out of scope.

**Noisy phone audio degrades everything downstream.** This is measured rather
than mitigated.

## The system

**The deterministic engine is the default.** Claim extraction runs on rules and
lexicons rather than an LLM. It is inspectable and consistent, but it will miss
phrasings outside its markers. Recall on unusual phrasing is a known weakness and
the honest trade for auditability.

**Semantic comparison degrades to UNCERTAIN.** When rules cannot decide whether
two free-text propositions match and no LLM is configured, the result is
`UNCERTAIN`, which surfaces as `UNVERIFIED`. This is safe, but it means the
deterministic build produces more `UNVERIFIED` issues than a model-assisted one.

**No offline mode.** Live transcription requires network access to a provider.

**Not tested at scale.** Concurrency, queue depth under load and storage growth
have not been evaluated beyond demo volumes.

## The boundary

WUNZI produces a structured case. It does not mediate. Everything after the case
packet — interpretation, dialogue, resolution, enforcement — is human work, and
the system is only useful to the extent that a mediator is present to do it.

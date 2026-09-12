# Scoring normalisation

Applied identically to every provider before any metric is computed. The rules
live in code at `apps/intelligence/app/asr/normalizer.py`; this file records what
they are and, more importantly, where the line sits.

## Lexical view — used for WER and CER

- Unicode NFKC
- lowercase
- digit group separators removed: `150,000` · `150 000` · `150.000` → `150000`
- punctuation stripped, apostrophes and hyphens kept (`n'ai`, `nyir'inzu`)
- whitespace collapsed

## Canonical view — used for Critical Fact Accuracy

Amounts and dates are canonicalised before comparison, so `one hundred fifty
thousand`, `cent cinquante mille`, `ibihumbi ijana na mirongo itanu` and
`150,000` all reduce to `150000`. A model that spelled the number out is not
penalised for spelling it out.

## The line

Normalisation may repair **formatting**. It may not repair **meaning**.

Permitted: separators, casing, punctuation, unicode form, numeral surface form.

Not permitted: correcting a misheard number, restoring a dropped negation,
reattaching a claim to the right speaker, or any post-processing that only one
provider needs. Each of those would hide the exact failure the benchmark exists
to measure — and would quietly turn a comparison between speech models into a
comparison between the repairs written for them.

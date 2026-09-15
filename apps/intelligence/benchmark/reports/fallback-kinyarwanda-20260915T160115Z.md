# benax-rw/KinyaWhisperDataset

- Utterances: 20
- Models: Sahara
- Source: `benax-rw/KinyaWhisperDataset` — monolingual Kinyarwanda

Same audio for every model. Nothing downstream of transcription varies.

> **This is the fallback source.** AfriSwitch is the right corpus for this benchmark and is gated behind manual author review. `benax-rw/KinyaWhisperDataset` is read, monolingual Kinyarwanda: it measures whether these models can transcribe the language at all, and whether they translate instead of transcribing. It does **not** measure code-switch handling, and no claim about code-switching should be drawn from it.

> **NOT PUBLISHABLE.** 20 of 20 provider calls failed (100%). A failed call is scored as an empty transcript, so these error rates measure the failures, not the models. Check WUNZI_MODE=live and that every provider has an API key.

## Provider failures

| Model | Calls failed |
| --- | --- |
| Sahara | 100% |

A failed call is recorded as an empty transcript and scores a word error rate of 1.0. Where the failure rate is high, the error rates below describe the failures rather than the models.

## Dataset load

- Source: benax-rw/KinyaWhisperDataset — read, monolingual Kinyarwanda. Used because AfriSwitch access was pending author review.
- Word and character error rate are measured on real Kinyarwanda audio.
- Matrix Language Collapse is measured: a model returning English for a Kinyarwanda utterance has translated rather than transcribed.
- Switch Point Preservation is NOT APPLICABLE and is excluded — this corpus contains no code-switching, and scoring it 1.0 would hand every model free marks on the axis the challenge is about.
- Code-mixing stratification is suppressed: every utterance has CMI 0.


## Overall

| Metric | Sahara |
| --- | --- |
| WER ↓ | 1.000 <sub>[1.000–1.000]</sub> |
| CER ↓ | 1.000 <sub>[1.000–1.000]</sub> |
| Matrix collapse ↓ | 0.000 <sub>[0.000–0.000]</sub> |
| Switch preservation ↑ | — |
| Span fidelity ↑ | 0.000 <sub>[0.000–0.000]</sub> |

## Harness cross-check

- Sahara WER here 1.000 · Intron AfriHealth Kinyarwanda 0.258. Different corpora — theirs is clinical, this is read monolingual speech — so a gap is expected; an order of magnitude is not.
- Sahara WER is more than 3x the published figure. Check audio resampling, the normalisation step and the language hints before reading anything into these results.

## Reading these numbers

**Matrix collapse** is the metric WER cannot express: the model produced fluent English instead of transcribing the language that was spoken. The output can be useful prose and still be the wrong artefact — it is no longer what the speaker said, and nothing built on it traces back to them.

**Switch preservation** and **span fidelity** separate two opposite failures that both register as high WER: dropping the English insertions, and dropping the matrix language. They need different fixes.

Matrix collapse keys on English function words rather than on matching the matrix orthography, so it is unaffected by the spelling variation that inflates WER in languages without settled conventions.


# AfriSwitch — kinyarwanda

- Utterances: 10
- Models: Sahara
- Source: `intronhealth/AfriSwitch`, `test` split, CC BY-NC-SA 4.0

Same audio for every model. Nothing downstream of transcription varies.

> **NOT PUBLISHABLE.** 10 of 10 provider calls failed (100%). A failed call is scored as an empty transcript, so these error rates measure the failures, not the models. Check WUNZI_MODE=live and that every provider has an API key.

## Provider failures

| Model | Calls failed |
| --- | --- |
| Sahara | 100% |

A failed call is recorded as an empty transcript and scores a word error rate of 1.0. Where the failure rate is high, the error rates below describe the failures rather than the models.

**Reported causes**

- `AsrError: [sahara] request rejected (400): {"data":{},"message":"use_language_asr_input kinyarwanda is not supported","status":"Error"}
` — 10 call(s)

## Dataset load

- Loaded 10 utterances, dataset card says 1577. A sampled run is fine; a full run is not.

## Code-mixing profile

| Band | Utterances | Hours | Mean CMI | Mean switches |
| --- | --- | --- | --- | --- |
| light | 3 | 0.01 | 5.54 | 2.33 |
| moderate | 4 | 0.01 | 13.03 | 5.25 |
| heavy | 3 | 0.00 | 24.85 | 3.33 |

## Overall

| Metric | Sahara |
| --- | --- |
| WER ↓ | 1.000 <sub>[1.000–1.000]</sub> |
| CER ↓ | 1.000 <sub>[1.000–1.000]</sub> |
| Matrix collapse ↓ | 0.000 <sub>[0.000–0.000]</sub> |
| Switch preservation ↑ | 0.000 <sub>[0.000–0.000]</sub> |
| Span fidelity ↑ | 0.000 <sub>[0.000–0.000]</sub> |

### Light mixing

| Metric | Sahara |
| --- | --- |
| WER ↓ | 1.000 <sub>[1.000–1.000]</sub> |
| CER ↓ | 1.000 <sub>[1.000–1.000]</sub> |
| Matrix collapse ↓ | 0.000 <sub>[0.000–0.000]</sub> |
| Switch preservation ↑ | 0.000 <sub>[0.000–0.000]</sub> |
| Span fidelity ↑ | 0.000 <sub>[0.000–0.000]</sub> |

### Moderate mixing

| Metric | Sahara |
| --- | --- |
| WER ↓ | 1.000 <sub>[1.000–1.000]</sub> |
| CER ↓ | 1.000 <sub>[1.000–1.000]</sub> |
| Matrix collapse ↓ | 0.000 <sub>[0.000–0.000]</sub> |
| Switch preservation ↑ | 0.000 <sub>[0.000–0.000]</sub> |
| Span fidelity ↑ | 0.000 <sub>[0.000–0.000]</sub> |

### Heavy mixing

| Metric | Sahara |
| --- | --- |
| WER ↓ | 1.000 <sub>[1.000–1.000]</sub> |
| CER ↓ | 1.000 <sub>[1.000–1.000]</sub> |
| Matrix collapse ↓ | 0.000 <sub>[0.000–0.000]</sub> |
| Switch preservation ↑ | 0.000 <sub>[0.000–0.000]</sub> |
| Span fidelity ↑ | 0.000 <sub>[0.000–0.000]</sub> |

## Harness cross-check

- Sahara WER here 1.000 · Intron AfriHealth Kinyarwanda 0.258. Different corpora — theirs is clinical, this is conversational code-switched speech — so a gap is expected; an order of magnitude is not.
- Sahara WER is more than 3x the published figure. Check audio resampling, the normalisation step and the language hints before reading anything into these results.

## Reading these numbers

**Matrix collapse** is the metric WER cannot express: the model produced fluent English instead of transcribing the language that was spoken. The output can be useful prose and still be the wrong artefact — it is no longer what the speaker said, and nothing built on it traces back to them.

**Switch preservation** and **span fidelity** separate two opposite failures that both register as high WER: dropping the English insertions, and dropping the matrix language. They need different fixes.

Matrix collapse keys on English function words rather than on matching the matrix orthography, so it is unaffected by the spelling variation that inflates WER in languages without settled conventions.


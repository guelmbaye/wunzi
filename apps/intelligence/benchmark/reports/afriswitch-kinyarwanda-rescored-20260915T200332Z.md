# AfriSwitch — kinyarwanda

- Utterances: 200 (188 scored)
- Models: Sahara
- Source: `intronhealth/AfriSwitch`, `test` split, CC BY-NC-SA 4.0

Same audio for every model. Nothing downstream of transcription varies.

> 12 of 200 provider calls failed (6%) and are excluded from the error rates, which are computed over successful calls. Reported for completeness.

## Provider failures

| Model | Calls failed |
| --- | --- |
| Sahara | 6% |

Failed calls are **excluded** from the error rates below, which are computed over successful calls only. A failure is a failure to measure, not a measurement of zero — averaging it in as a word error rate of 1.0 would make the figures partly a measure of the provider's queue.

**Reported causes**

- `AsrError: [sahara] transcription did not complete synchronously (file_id <id>)` — 12 call(s)

## Dataset load

- Loaded 200 utterances, dataset card says 1577. A sampled run is fine; a full run is not.

## Code-mixing profile

| Band | Utterances | Hours | Mean CMI | Mean switches |
| --- | --- | --- | --- | --- |
| light | 63 | 0.20 | 6.61 | 2.78 |
| moderate | 71 | 0.25 | 13.84 | 5.34 |
| heavy | 66 | 0.20 | 30.40 | 5.03 |

## Overall

| Metric | Sahara |
| --- | --- |
| WER ↓ | 0.361 <sub>[0.335–0.388]</sub> |
| CER ↓ | 0.214 <sub>[0.195–0.235]</sub> |
| Matrix collapse ↓ | 0.011 <sub>[0.000–0.027]</sub> |
| Switch preservation ↑ | 0.422 <sub>[0.366–0.480]</sub> |
| Span fidelity ↑ | 0.888 <sub>[0.857–0.916]</sub> |

### Light mixing

| Metric | Sahara |
| --- | --- |
| WER ↓ | 0.295 <sub>[0.247–0.344]</sub> |
| CER ↓ | 0.176 <sub>[0.140–0.219]</sub> |
| Matrix collapse ↓ | 0.017 <sub>[0.000–0.050]</sub> |
| Switch preservation ↑ | 0.356 <sub>[0.244–0.469]</sub> |
| Span fidelity ↑ | 0.909 <sub>[0.846–0.959]</sub> |

### Moderate mixing

| Metric | Sahara |
| --- | --- |
| WER ↓ | 0.370 <sub>[0.331–0.412]</sub> |
| CER ↓ | 0.224 <sub>[0.195–0.258]</sub> |
| Matrix collapse ↓ | 0.015 <sub>[0.000–0.045]</sub> |
| Switch preservation ↑ | 0.445 <sub>[0.352–0.534]</sub> |
| Span fidelity ↑ | 0.869 <sub>[0.819–0.911]</sub> |

### Heavy mixing

| Metric | Sahara |
| --- | --- |
| WER ↓ | 0.414 <sub>[0.371–0.462]</sub> |
| CER ↓ | 0.242 <sub>[0.212–0.272]</sub> |
| Matrix collapse ↓ | 0.000 <sub>[0.000–0.000]</sub> |
| Switch preservation ↑ | 0.461 <sub>[0.372–0.550]</sub> |
| Span fidelity ↑ | 0.887 <sub>[0.832–0.936]</sub> |

## Harness cross-check

- Sahara WER here 0.361 · Intron AfriHealth Kinyarwanda 0.258. Different corpora — theirs is clinical, this is conversational code-switched speech — so a gap is expected; an order of magnitude is not.

## Reading these numbers

**Matrix collapse** is the metric WER cannot express: the model produced fluent English instead of transcribing the language that was spoken. The output can be useful prose and still be the wrong artefact — it is no longer what the speaker said, and nothing built on it traces back to them.

**Switch preservation** and **span fidelity** separate two opposite failures that both register as high WER: dropping the English insertions, and dropping the matrix language. They need different fixes.

Matrix collapse keys on English function words rather than on matching the matrix orthography, so it is unaffected by the spelling variation that inflates WER in languages without settled conventions.


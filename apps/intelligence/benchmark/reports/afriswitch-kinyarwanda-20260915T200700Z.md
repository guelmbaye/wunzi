# AfriSwitch — kinyarwanda

- Utterances: 200 (192 scored)
- Models: Whisper
- Source: `intronhealth/AfriSwitch`, `test` split, CC BY-NC-SA 4.0

Same audio for every model. Nothing downstream of transcription varies.

> 8 of 200 provider calls failed (4%) and are excluded from the error rates, which are computed over successful calls. Reported for completeness.

## Provider failures

| Model | Calls failed |
| --- | --- |
| Whisper | 4% |

Failed calls are **excluded** from the error rates below, which are computed over successful calls only. A failure is a failure to measure, not a measurement of zero — averaging it in as a word error rate of 1.0 would make the figures partly a measure of the provider's queue.

**Reported causes**

- `AsrError: [whisper] failed after retries: [Errno 11001] getaddrinfo failed` — 8 call(s)

## Dataset load

- Loaded 200 utterances, dataset card says 1577. A sampled run is fine; a full run is not.

## Code-mixing profile

| Band | Utterances | Hours | Mean CMI | Mean switches |
| --- | --- | --- | --- | --- |
| light | 63 | 0.20 | 6.61 | 2.78 |
| moderate | 71 | 0.25 | 13.84 | 5.34 |
| heavy | 66 | 0.20 | 30.40 | 5.03 |

## Overall

| Metric | Whisper |
| --- | --- |
| WER ↓ | 0.994 <sub>[0.970–1.018]</sub> |
| CER ↓ | 0.656 <sub>[0.625–0.688]</sub> |
| Matrix collapse ↓ | 0.146 <sub>[0.099–0.198]</sub> |
| Switch preservation ↑ | 0.200 <sub>[0.152–0.250]</sub> |
| Span fidelity ↑ | 0.029 <sub>[0.016–0.044]</sub> |

### Light mixing

| Metric | Whisper |
| --- | --- |
| WER ↓ | 1.020 <sub>[0.978–1.065]</sub> |
| CER ↓ | 0.635 <sub>[0.575–0.694]</sub> |
| Matrix collapse ↓ | 0.150 <sub>[0.067–0.250]</sub> |
| Switch preservation ↑ | 0.222 <sub>[0.128–0.317]</sub> |
| Span fidelity ↑ | 0.017 <sub>[0.000–0.040]</sub> |

### Moderate mixing

| Metric | Whisper |
| --- | --- |
| WER ↓ | 1.006 <sub>[0.982–1.034]</sub> |
| CER ↓ | 0.687 <sub>[0.643–0.732]</sub> |
| Matrix collapse ↓ | 0.147 <sub>[0.059–0.221]</sub> |
| Switch preservation ↑ | 0.110 <sub>[0.054–0.167]</sub> |
| Span fidelity ↑ | 0.010 <sub>[0.000–0.021]</sub> |

### Heavy mixing

| Metric | Whisper |
| --- | --- |
| WER ↓ | 0.958 <sub>[0.904–1.010]</sub> |
| CER ↓ | 0.644 <sub>[0.589–0.703]</sub> |
| Matrix collapse ↓ | 0.141 <sub>[0.062–0.234]</sub> |
| Switch preservation ↑ | 0.276 <sub>[0.188–0.370]</sub> |
| Span fidelity ↑ | 0.061 <sub>[0.028–0.099]</sub> |

## Harness cross-check

- Sahara was not in this run, so the harness could not be cross-checked.

## Reading these numbers

**Matrix collapse** is the metric WER cannot express: the model produced fluent English instead of transcribing the language that was spoken. The output can be useful prose and still be the wrong artefact — it is no longer what the speaker said, and nothing built on it traces back to them.

**Switch preservation** and **span fidelity** separate two opposite failures that both register as high WER: dropping the English insertions, and dropping the matrix language. They need different fixes.

Matrix collapse keys on English function words rather than on matching the matrix orthography, so it is unaffected by the spelling variation that inflates WER in languages without settled conventions.


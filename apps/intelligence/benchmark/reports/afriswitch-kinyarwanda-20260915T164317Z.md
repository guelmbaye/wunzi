# AfriSwitch — kinyarwanda

- Utterances: 10
- Models: Sahara
- Source: `intronhealth/AfriSwitch`, `test` split, CC BY-NC-SA 4.0

Same audio for every model. Nothing downstream of transcription varies.

> **NOT PUBLISHABLE.** 1 of 10 provider calls failed (10%). A failed call is scored as an empty transcript, so these error rates measure the failures, not the models. Check WUNZI_MODE=live and that every provider has an API key.

## Provider failures

| Model | Calls failed |
| --- | --- |
| Sahara | 10% |

A failed call is recorded as an empty transcript and scores a word error rate of 1.0. Where the failure rate is high, the error rates below describe the failures rather than the models.

**Reported causes**

- `AsrError: [sahara] transcription did not complete synchronously (file_id 7d19f497-c8eb-4b04-97dd-6185828ecc38, status FILE_QUEUED). Poll the Get File Status endpoint, or use shorter clips: t` — 1 call(s)

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
| WER ↓ | 0.422 <sub>[0.240–0.598]</sub> |
| CER ↓ | 0.296 <sub>[0.132–0.477]</sub> |
| Matrix collapse ↓ | 0.000 <sub>[0.000–0.000]</sub> |
| Switch preservation ↑ | 0.470 <sub>[0.200–0.750]</sub> |
| Span fidelity ↑ | 0.800 <sub>[0.600–1.000]</sub> |

### Light mixing

| Metric | Sahara |
| --- | --- |
| WER ↓ | 0.497 <sub>[0.242–1.000]</sub> |
| CER ↓ | 0.387 <sub>[0.044–1.000]</sub> |
| Matrix collapse ↓ | 0.000 <sub>[0.000–0.000]</sub> |
| Switch preservation ↑ | 0.333 <sub>[0.000–1.000]</sub> |
| Span fidelity ↑ | 0.667 <sub>[0.000–1.000]</sub> |

### Moderate mixing

| Metric | Sahara |
| --- | --- |
| WER ↓ | 0.316 <sub>[0.118–0.543]</sub> |
| CER ↓ | 0.191 <sub>[0.064–0.345]</sub> |
| Matrix collapse ↓ | 0.000 <sub>[0.000–0.000]</sub> |
| Switch preservation ↑ | 0.800 <sub>[0.400–1.000]</sub> |
| Span fidelity ↑ | 0.833 <sub>[0.500–1.000]</sub> |

### Heavy mixing

| Metric | Sahara |
| --- | --- |
| WER ↓ | 0.488 <sub>[0.100–0.727]</sub> |
| CER ↓ | 0.344 <sub>[0.048–0.590]</sub> |
| Matrix collapse ↓ | 0.000 <sub>[0.000–0.000]</sub> |
| Switch preservation ↑ | 0.167 <sub>[0.000–0.500]</sub> |
| Span fidelity ↑ | 0.889 <sub>[0.667–1.000]</sub> |

## Harness cross-check

- Sahara WER here 0.422 · Intron AfriHealth Kinyarwanda 0.258. Different corpora — theirs is clinical, this is conversational code-switched speech — so a gap is expected; an order of magnitude is not.

## Reading these numbers

**Matrix collapse** is the metric WER cannot express: the model produced fluent English instead of transcribing the language that was spoken. The output can be useful prose and still be the wrong artefact — it is no longer what the speaker said, and nothing built on it traces back to them.

**Switch preservation** and **span fidelity** separate two opposite failures that both register as high WER: dropping the English insertions, and dropping the matrix language. They need different fixes.

Matrix collapse keys on English function words rather than on matching the matrix orthography, so it is unaffected by the spelling variation that inflates WER in languages without settled conventions.


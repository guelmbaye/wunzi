# AfriSwitch — kinyarwanda

- Utterances: 200
- Models: Sahara
- Source: `intronhealth/AfriSwitch`, `test` split, CC BY-NC-SA 4.0

Same audio for every model. Nothing downstream of transcription varies.

> **NOT PUBLISHABLE.** 12 of 200 provider calls failed (6%). A failed call is scored as an empty transcript, so these error rates measure the failures, not the models. Check WUNZI_MODE=live and that every provider has an API key.

## Provider failures

| Model | Calls failed |
| --- | --- |
| Sahara | 6% |

A failed call is recorded as an empty transcript and scores a word error rate of 1.0. Where the failure rate is high, the error rates below describe the failures rather than the models.

**Reported causes**

- `AsrError: [sahara] transcription did not complete synchronously (file_id ab0a08ab-92a8-4731-a479-694c11e2b364, status FILE_QUEUED). Poll the Get File Status endpoint, or use shorter clips: t` — 1 call(s)
- `AsrError: [sahara] transcription did not complete synchronously (file_id c8542c1f-f102-4ee6-a9c6-3a2b9cfe351a, status FILE_QUEUED). Poll the Get File Status endpoint, or use shorter clips: t` — 1 call(s)
- `AsrError: [sahara] transcription did not complete synchronously (file_id 47585cf6-8ad4-409c-9322-a9435fbfc5cd, status FILE_QUEUED). Poll the Get File Status endpoint, or use shorter clips: t` — 1 call(s)
- `AsrError: [sahara] transcription did not complete synchronously (file_id 1c00ef69-5050-448d-99b6-6e1f03bebb37, status FILE_QUEUED). Poll the Get File Status endpoint, or use shorter clips: t` — 1 call(s)
- `AsrError: [sahara] transcription did not complete synchronously (file_id 69aec222-f2a5-439c-820a-2d0200feacab, status FILE_QUEUED). Poll the Get File Status endpoint, or use shorter clips: t` — 1 call(s)
- `AsrError: [sahara] transcription did not complete synchronously (file_id b6035596-60d5-48ad-b5a3-04e55e61a5c6, status FILE_QUEUED). Poll the Get File Status endpoint, or use shorter clips: t` — 1 call(s)
- `AsrError: [sahara] transcription did not complete synchronously (file_id a0e3825e-e9db-4972-8982-8fea0a7e69d9, status FILE_QUEUED). Poll the Get File Status endpoint, or use shorter clips: t` — 1 call(s)
- `AsrError: [sahara] transcription did not complete synchronously (file_id 1b2b1551-c58d-4e23-9fce-15371fc52526, status FILE_QUEUED). Poll the Get File Status endpoint, or use shorter clips: t` — 1 call(s)
- `AsrError: [sahara] transcription did not complete synchronously (file_id 94feca28-27a7-4ec7-85d4-0d352254502f, status FILE_QUEUED). Poll the Get File Status endpoint, or use shorter clips: t` — 1 call(s)
- `AsrError: [sahara] transcription did not complete synchronously (file_id 6cf663d5-279c-4b8a-8664-cd37ba4c9abb, status FILE_QUEUED). Poll the Get File Status endpoint, or use shorter clips: t` — 1 call(s)
- `AsrError: [sahara] transcription did not complete synchronously (file_id 54c33d35-c9c1-4f3d-840c-74e922668115, status FILE_QUEUED). Poll the Get File Status endpoint, or use shorter clips: t` — 1 call(s)
- `AsrError: [sahara] transcription did not complete synchronously (file_id e67ad5b8-8154-4ad1-a875-fd04ea833d41, status FILE_QUEUED). Poll the Get File Status endpoint, or use shorter clips: t` — 1 call(s)

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
| WER ↓ | 0.399 <sub>[0.366–0.432]</sub> |
| CER ↓ | 0.262 <sub>[0.230–0.295]</sub> |
| Matrix collapse ↓ | 0.010 <sub>[0.000–0.025]</sub> |
| Switch preservation ↑ | 0.396 <sub>[0.345–0.454]</sub> |
| Span fidelity ↑ | 0.835 <sub>[0.794–0.875]</sub> |

### Light mixing

| Metric | Sahara |
| --- | --- |
| WER ↓ | 0.329 <sub>[0.266–0.393]</sub> |
| CER ↓ | 0.215 <sub>[0.157–0.276]</sub> |
| Matrix collapse ↓ | 0.016 <sub>[0.000–0.064]</sub> |
| Switch preservation ↑ | 0.339 <sub>[0.225–0.452]</sub> |
| Span fidelity ↑ | 0.866 <sub>[0.789–0.938]</sub> |

### Moderate mixing

| Metric | Sahara |
| --- | --- |
| WER ↓ | 0.415 <sub>[0.363–0.472]</sub> |
| CER ↓ | 0.279 <sub>[0.228–0.339]</sub> |
| Matrix collapse ↓ | 0.014 <sub>[0.000–0.042]</sub> |
| Switch preservation ↑ | 0.413 <sub>[0.325–0.504]</sub> |
| Span fidelity ↑ | 0.808 <sub>[0.737–0.873]</sub> |

### Heavy mixing

| Metric | Sahara |
| --- | --- |
| WER ↓ | 0.450 <sub>[0.395–0.502]</sub> |
| CER ↓ | 0.288 <sub>[0.236–0.343]</sub> |
| Matrix collapse ↓ | 0.000 <sub>[0.000–0.000]</sub> |
| Switch preservation ↑ | 0.433 <sub>[0.348–0.518]</sub> |
| Span fidelity ↑ | 0.833 <sub>[0.763–0.900]</sub> |

## Harness cross-check

- Sahara WER here 0.399 · Intron AfriHealth Kinyarwanda 0.258. Different corpora — theirs is clinical, this is conversational code-switched speech — so a gap is expected; an order of magnitude is not.

## Reading these numbers

**Matrix collapse** is the metric WER cannot express: the model produced fluent English instead of transcribing the language that was spoken. The output can be useful prose and still be the wrong artefact — it is no longer what the speaker said, and nothing built on it traces back to them.

**Switch preservation** and **span fidelity** separate two opposite failures that both register as high WER: dropping the English insertions, and dropping the matrix language. They need different fixes.

Matrix collapse keys on English function words rather than on matching the matrix orthography, so it is unaffected by the spelling variation that inflates WER in languages without settled conventions.


# AfriSwitch — kinyarwanda

- Utterances: 200
- Models: Whisper
- Source: `intronhealth/AfriSwitch`, `test` split, CC BY-NC-SA 4.0

Same audio for every model. Nothing downstream of transcription varies.

> **NOT PUBLISHABLE.** 200 of 200 provider calls failed (100%). A failed call is scored as an empty transcript, so these error rates measure the failures, not the models. Check WUNZI_MODE=live and that every provider has an API key.

## Provider failures

| Model | Calls failed |
| --- | --- |
| Whisper | 100% |

A failed call is recorded as an empty transcript and scores a word error rate of 1.0. Where the failure rate is high, the error rates below describe the failures rather than the models.

**Reported causes**

- `AsrError: [whisper] request rejected (404): {
    "error": {
        "message": "The model `whisper-large-v3` does not exist or you do not have access to it.",
        "type": "invalid_reque` — 200 call(s)

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
| WER ↓ | 1.000 <sub>[1.000–1.000]</sub> |
| CER ↓ | 1.000 <sub>[1.000–1.000]</sub> |
| Matrix collapse ↓ | 0.000 <sub>[0.000–0.000]</sub> |
| Switch preservation ↑ | 0.000 <sub>[0.000–0.000]</sub> |
| Span fidelity ↑ | 0.000 <sub>[0.000–0.000]</sub> |

### Light mixing

| Metric | Whisper |
| --- | --- |
| WER ↓ | 1.000 <sub>[1.000–1.000]</sub> |
| CER ↓ | 1.000 <sub>[1.000–1.000]</sub> |
| Matrix collapse ↓ | 0.000 <sub>[0.000–0.000]</sub> |
| Switch preservation ↑ | 0.000 <sub>[0.000–0.000]</sub> |
| Span fidelity ↑ | 0.000 <sub>[0.000–0.000]</sub> |

### Moderate mixing

| Metric | Whisper |
| --- | --- |
| WER ↓ | 1.000 <sub>[1.000–1.000]</sub> |
| CER ↓ | 1.000 <sub>[1.000–1.000]</sub> |
| Matrix collapse ↓ | 0.000 <sub>[0.000–0.000]</sub> |
| Switch preservation ↑ | 0.000 <sub>[0.000–0.000]</sub> |
| Span fidelity ↑ | 0.000 <sub>[0.000–0.000]</sub> |

### Heavy mixing

| Metric | Whisper |
| --- | --- |
| WER ↓ | 1.000 <sub>[1.000–1.000]</sub> |
| CER ↓ | 1.000 <sub>[1.000–1.000]</sub> |
| Matrix collapse ↓ | 0.000 <sub>[0.000–0.000]</sub> |
| Switch preservation ↑ | 0.000 <sub>[0.000–0.000]</sub> |
| Span fidelity ↑ | 0.000 <sub>[0.000–0.000]</sub> |

## Harness cross-check

- Sahara was not in this run, so the harness could not be cross-checked.

## Reading these numbers

**Matrix collapse** is the metric WER cannot express: the model produced fluent English instead of transcribing the language that was spoken. The output can be useful prose and still be the wrong artefact — it is no longer what the speaker said, and nothing built on it traces back to them.

**Switch preservation** and **span fidelity** separate two opposite failures that both register as high WER: dropping the English insertions, and dropping the matrix language. They need different fixes.

Matrix collapse keys on English function words rather than on matching the matrix orthography, so it is unaffected by the spelling variation that inflates WER in languages without settled conventions.


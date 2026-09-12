"""
Tier-1 benchmark CLI.

    python -m app.benchmark.afriswitch_cli run \
        --config kinyarwanda --limit 200 \
        --providers sahara,whisper,model_b,model_c \
        --out /benchmark/reports

The dataset is gated. Before the first run:

    huggingface-cli login
    # accept the conditions at
    # https://huggingface.co/datasets/intronhealth/AfriSwitch
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

from app.benchmark.afriswitch import DEFAULT_CONFIG, load_afriswitch
from app.benchmark.afriswitch_runner import AfriSwitchReport, run_sync
from app.config import get_settings

HEADLINE = [
    ("word_error_rate", "WER", "lower"),
    ("character_error_rate", "CER", "lower"),
    ("matrix_language_collapse_rate", "Matrix collapse", "lower"),
    ("switch_point_preservation", "Switch preservation", "higher"),
    ("span_language_fidelity", "Span fidelity", "higher"),
]

LABEL = {"sahara": "Sahara", "whisper": "Whisper", "model_b": "Model B", "model_c": "Model C"}


def main() -> int:
    parser = argparse.ArgumentParser(prog="wunzi-afriswitch")
    sub = parser.add_subparsers(dest="command", required=True)

    run = sub.add_parser("run", help="Score speech models on AfriSwitch")
    run.add_argument("--config", default=DEFAULT_CONFIG, help="AfriSwitch language config")
    run.add_argument("--providers", default="sahara,whisper,model_b,model_c")
    run.add_argument("--limit", type=int, default=None, help="Stratified sample size")
    run.add_argument("--band", default=None, choices=["light", "moderate", "heavy"])
    run.add_argument("--bootstrap", type=int, default=1000)
    run.add_argument("--audio-root", default=None)
    run.add_argument("--out", default=None)

    args = parser.parse_args()
    settings = get_settings()

    try:
        utterances = load_afriswitch(args.config, limit=args.limit, cmi_band=args.band)
    except RuntimeError as exc:
        print(exc, file=sys.stderr)
        return 2
    except Exception as exc:  # noqa: BLE001 — the cause matters more than the trace here
        print(f"Could not load AfriSwitch/{args.config}: {exc}", file=sys.stderr)
        print(
            "\nThe dataset is gated. Run `huggingface-cli login` and accept the "
            "conditions at https://huggingface.co/datasets/intronhealth/AfriSwitch",
            file=sys.stderr,
        )
        return 2

    if not utterances:
        print(f"No utterances matched config={args.config} band={args.band}", file=sys.stderr)
        return 1

    providers = [p.strip() for p in args.providers.split(",") if p.strip()]
    report = run_sync(utterances, providers, args.config, args.bootstrap)

    out = Path(args.out or Path(settings.benchmark_root) / "reports")
    out.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    (out / f"afriswitch-{args.config}-{stamp}.json").write_text(
        json.dumps(asdict(report), indent=2, default=str), encoding="utf-8"
    )

    markdown = render(report)
    (out / f"afriswitch-{args.config}-{stamp}.md").write_text(markdown, encoding="utf-8")
    print(markdown)

    return 0


def render(report: AfriSwitchReport) -> str:
    lines = [
        f"# AfriSwitch — {report.config}",
        "",
        f"- Utterances: {report.utterance_count}",
        f"- Models: {', '.join(LABEL.get(p, p) for p in report.providers)}",
        "- Source: `intronhealth/AfriSwitch`, `test` split, CC BY-NC-SA 4.0",
        "",
        "Same audio for every model. Nothing downstream of transcription varies.",
        "",
    ]

    if not report.publishable:
        lines += [f"> **NOT PUBLISHABLE.** {report.publishability_note}", ""]

    if report.dataset_notes:
        lines += ["## Dataset load", ""]
        lines += [f"- {note}" for note in report.dataset_notes]
        lines.append("")

    lines += ["## Code-mixing profile", "", "| Band | Utterances | Hours | Mean CMI | Mean switches |", "| --- | --- | --- | --- | --- |"]
    for band, stats in report.band_profile.items():
        lines.append(
            f"| {band} | {int(stats['utterances'])} | {stats['hours']:.2f} | "
            f"{stats['mean_cmi']:.2f} | {stats['mean_switch_points']:.2f} |"
        )

    lines += ["", "## Overall", "", _table(report.overall, report.providers)]

    for band in ("light", "moderate", "heavy"):
        if band in report.by_band:
            lines += [
                "",
                f"### {band.capitalize()} mixing",
                "",
                _table(report.by_band[band], report.providers),
            ]

    if report.paired:
        lines += [
            "",
            "## Sahara vs each alternative",
            "",
            "Paired bootstrap over the same utterances. A negative WER difference "
            "means Sahara made fewer errors. An interval spanning zero means the "
            "difference is not distinguishable from noise on this sample.",
            "",
            "| Comparison | Metric | Difference | 95% CI |",
            "| --- | --- | --- | --- |",
        ]
        for provider, metrics in report.paired.items():
            for metric, (point, low, high) in metrics.items():
                crosses = low <= 0 <= high
                lines.append(
                    f"| Sahara − {LABEL.get(provider, provider)} | {metric.replace('_', ' ')} | "
                    f"{point:+.4f} | [{low:+.4f}, {high:+.4f}]{' *n.s.*' if crosses else ''} |"
                )

    if report.sanity:
        lines += ["", "## Harness cross-check", ""]
        lines += [f"- {note}" for note in report.sanity]

    lines += [
        "",
        "## Reading these numbers",
        "",
        "**Matrix collapse** is the metric WER cannot express: the model produced "
        "fluent English instead of transcribing the language that was spoken. The "
        "output can be useful prose and still be the wrong artefact — it is no "
        "longer what the speaker said, and nothing built on it traces back to them.",
        "",
        "**Switch preservation** and **span fidelity** separate two opposite "
        "failures that both register as high WER: dropping the English insertions, "
        "and dropping the matrix language. They need different fixes.",
        "",
        "Matrix collapse keys on English function words rather than on matching "
        "the matrix orthography, so it is unaffected by the spelling variation "
        "that inflates WER in languages without settled conventions.",
        "",
    ]

    return "\n".join(lines) + "\n"


def _table(block: dict, providers: list[str]) -> str:
    header = "| Metric | " + " | ".join(LABEL.get(p, p) for p in providers) + " |"
    divider = "| --- | " + " | ".join(["---"] * len(providers)) + " |"
    rows = [header, divider]

    for key, label, direction in HEADLINE:
        cells = []
        for provider in providers:
            stats = block.get(provider, {}).get(key)
            if not stats:
                cells.append("—")
                continue
            cells.append(
                f"{stats['value']:.3f} <sub>[{stats['ci_low']:.3f}–{stats['ci_high']:.3f}]</sub>"
            )
        arrow = "↓" if direction == "lower" else "↑"
        rows.append(f"| {label} {arrow} | " + " | ".join(cells) + " |")

    return "\n".join(rows)


if __name__ == "__main__":
    raise SystemExit(main())

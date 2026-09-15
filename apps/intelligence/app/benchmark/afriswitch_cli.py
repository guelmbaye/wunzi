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
import re
import json
import sys
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

from app.benchmark.afriswitch import DEFAULT_CONFIG, load_afriswitch
from app.benchmark.hf_audio import NoReachableDataset, load_hf_audio
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
    run.add_argument(
        "--source",
        default="afriswitch",
        choices=["afriswitch", "fallback"],
        help=(
            "afriswitch is the right corpus and the default. fallback tries a "
            "series of reachable monolingual Kinyarwanda corpora: it measures "
            "accuracy on real audio but contains no code-switching, so switch "
            "preservation is excluded rather than scored."
        ),
    )
    run.add_argument(
        "--dataset-id",
        default=None,
        help="Skip the fallback candidate list and use this HF dataset directly.",
    )
    run.add_argument("--dataset-config", default=None)
    run.add_argument("--dataset-split", default=None)
    run.add_argument("--config", default=DEFAULT_CONFIG, help="AfriSwitch language config")
    run.add_argument("--providers", default="sahara,whisper,model_b,model_c")
    run.add_argument("--limit", type=int, default=None, help="Stratified sample size")
    run.add_argument("--band", default=None, choices=["light", "moderate", "heavy"])
    run.add_argument("--bootstrap", type=int, default=1000)
    run.add_argument("--audio-root", default=None)
    run.add_argument("--out", default=None)

    rescore = sub.add_parser(
        "rescore",
        help="Recompute a saved run with the current scoring rules — no API calls",
    )
    rescore.add_argument("--input", required=True, help="results-*.json from a previous run")
    rescore.add_argument("--bootstrap", type=int, default=1000)
    rescore.add_argument("--out", default=None)

    args = parser.parse_args()

    if args.command == "rescore":
        return _rescore(args)

    settings = get_settings()

    # Before anything is downloaded: running twenty utterances to discover that
    # no API key is set wastes time and produces a report full of 1.000s that
    # have to be explained away.
    providers = [p.strip() for p in args.providers.split(",") if p.strip()]
    if not _preflight(providers):
        return 2

    fallback = args.source == "fallback" or bool(args.dataset_id)
    source_label: str | None = None

    try:
        if fallback:
            utterances, source_label = load_hf_audio(
                limit=args.limit or 200,
                dataset_id=args.dataset_id,
                config=args.dataset_config,
                split=args.dataset_split,
            )
        else:
            utterances = load_afriswitch(args.config, limit=args.limit, cmi_band=args.band)
    except NoReachableDataset as exc:
        print(exc, file=sys.stderr)
        return 2
    except RuntimeError as exc:
        print(exc, file=sys.stderr)
        return 2
    except Exception as exc:  # noqa: BLE001 — the cause matters more than the trace here
        label = source_label or ("fallback corpus" if fallback else f"AfriSwitch/{args.config}")
        print(f"Could not load {label}: {exc}", file=sys.stderr)

        if fallback:
            print(
                "\nMost fallback corpora are gated by click-through acceptance "
                "rather than author review. Run `huggingface-cli login`, open the "
                "dataset page, accept, and retry — or pass --dataset-id directly.",
                file=sys.stderr,
            )
        elif "gated" in str(exc).lower() or "authenticate" in str(exc).lower():
            print(
                "\nAfriSwitch is gated behind author review. Run `huggingface-cli "
                "login` and request access at "
                "https://huggingface.co/datasets/intronhealth/AfriSwitch\n"
                "If review has not come through, --source fallback measures "
                "Kinyarwanda accuracy on a reachable corpus today.",
                file=sys.stderr,
            )
        elif "torchcodec" in str(exc).lower():
            # Should no longer happen: audio is written byte for byte without
            # decoding. If it reappears, a decode path was reintroduced.
            print(
                "\nAudio is meant to be written without decoding. A decode path "
                "has been reintroduced somewhere — check the Audio(decode=False) "
                "cast in load_afriswitch.",
                file=sys.stderr,
            )
        return 2

    if not utterances:
        print(f"No utterances matched config={args.config} band={args.band}", file=sys.stderr)
        return 1

    providers = [p.strip() for p in args.providers.split(",") if p.strip()]
    source = "fallback" if fallback else "afriswitch"
    report = run_sync(
        utterances, providers, args.config, args.bootstrap, source, source_label
    )

    out = Path(args.out or Path(settings.benchmark_root) / "reports")
    out.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    slug = f"{report.source}-{args.config}-{stamp}"
    (out / f"{slug}.json").write_text(
        json.dumps(asdict(report), indent=2, default=str), encoding="utf-8"
    )

    markdown = render(report)
    (out / f"{slug}.md").write_text(markdown, encoding="utf-8")
    print(markdown)

    return 0


def render(report: AfriSwitchReport) -> str:
    code_switched = report.source == "afriswitch"

    lines = [
        f"# {'AfriSwitch' if code_switched else (report.source_label or 'Fallback corpus')}"
        + (f" — {report.config}" if code_switched else ""),
        "",
        f"- Utterances: {report.utterance_count}"
        + (f" ({_scored_count(report)} scored)" if _scored_count(report) != report.utterance_count else ""),
        f"- Models: {', '.join(LABEL.get(p, p) for p in report.providers)}",
        "- Source: `intronhealth/AfriSwitch`, `test` split, CC BY-NC-SA 4.0"
        if code_switched
        else f"- Source: `{report.source_label or 'unknown'}` — monolingual Kinyarwanda",
        "",
        "Same audio for every model. Nothing downstream of transcription varies.",
        "",
    ]

    if not code_switched:
        lines += [
            "> **This is the fallback source.** AfriSwitch is the right corpus for "
            "this benchmark and is gated behind manual author review. "
            f"`{report.source_label or 'This corpus'}` is read, monolingual "
            "Kinyarwanda: it measures whether these models can transcribe the "
            "language at all, and whether they translate instead of transcribing. "
            "It does **not** measure code-switch handling, and no claim about "
            "code-switching should be drawn from it.",
            "",
        ]

    if not report.publishable:
        lines += [f"> **NOT PUBLISHABLE.** {report.publishability_note}", ""]
    elif report.publishability_note:
        lines += [f"> {report.publishability_note}", ""]

    # Failures are stated before any metric table. A reader must not have to
    # infer from four identical 1.000s that nothing was measured.
    failed = [p for p in report.providers if _failure_rate(report, p) > 0]
    if failed:
        lines += ["## Provider failures", "", "| Model | Calls failed |", "| --- | --- |"]
        for provider in report.providers:
            rate = _failure_rate(report, provider)
            lines.append(f"| {LABEL.get(provider, provider)} | {rate:.0%} |")
        lines += [
            "",
            "Failed calls are **excluded** from the error rates below, which are "
            "computed over successful calls only. A failure is a failure to "
            "measure, not a measurement of zero — averaging it in as a word error "
            "rate of 1.0 would make the figures partly a measure of the provider's "
            "queue.",
            "",
        ]

        # The reason, not just the rate. A report that says "100% failed"
        # without saying why leaves the reader exactly where they started.
        reasons = _failure_reasons(report)
        if reasons:
            lines += ["**Reported causes**", ""]
            lines += [f"- `{reason}` — {count} call(s)" for reason, count in reasons]
            lines.append("")

    if report.dataset_notes:
        lines += ["## Dataset load", ""]
        lines += [f"- {note}" for note in report.dataset_notes]
        lines.append("")

    if report.band_profile:
        lines += [
            "## Code-mixing profile",
            "",
            "| Band | Utterances | Hours | Mean CMI | Mean switches |",
            "| --- | --- | --- | --- | --- |",
        ]
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


def _preflight(providers: list[str]) -> bool:
    """
    Checks the configuration before spending a single call.

    Running twenty utterances to discover that no API key is set wastes time and
    produces a report full of 1.000s that have to be explained away. The mode and
    every provider are resolved first, and the failure is named in one line.
    """
    import asyncio

    from app.asr.registry import get_provider

    settings = get_settings()
    problems: list[str] = []

    print(f"Mode: {settings.wunzi_mode}", file=sys.stderr)

    if settings.fixture_mode:
        problems.append(
            "WUNZI_MODE is 'fixture', so every call replays cached provider output. "
            "A corpus loaded from the Hub has no cached output, so all calls will "
            "fail. Set WUNZI_MODE=live."
        )

    for provider in providers:
        try:
            get_provider(provider, settings)
        except KeyError as exc:
            problems.append(f"{provider}: {str(exc).strip(chr(39))}")
            continue

        # A key without an endpoint fails as a DNS error twenty calls later
        # rather than here, where it can be named.
        base_url = settings.provider_config(provider).get("base_url") or ""
        if not base_url:
            problems.append(
                f"{provider}: no base URL configured. Set "
                f"{provider.upper()}_BASE_URL to the endpoint that issued your API key."
            )
            continue

        # A wrong model name is invisible until the first call, and a run of
        # two hundred discovers it two hundred times.
        instance = get_provider(provider, settings)
        model_error = asyncio.run(instance.verify_model())
        if model_error:
            problems.append(f"{provider}: {model_error}")
            continue

        label = getattr(instance, "model", None)
        print(
            f"  {provider}: configured ({base_url}" + (f", {label})" if label else ")"),
            file=sys.stderr,
        )

    if problems:
        print("\nCannot run:", file=sys.stderr)
        for problem in problems:
            print(f"  - {problem}", file=sys.stderr)
        print(
            "\nThe environment is read from apps/intelligence/.env and from the "
            "shell. On PowerShell:\n"
            '  $env:WUNZI_MODE="live"; $env:SAHARA_API_KEY="..."',
            file=sys.stderr,
        )
        return False

    return True


def _rescore(args) -> int:
    """
    Recomputes a saved run under the current scoring rules.

    Provider calls cost money and a benchmark run is not repeatable on a spent
    budget. Every per-utterance result is already in the saved JSON, so a
    methodology fix — excluding failed calls from the error rates — can be
    applied to a run that has already happened. No audio is sent, no credit is
    consumed, and the corrected figures come from exactly the same measurements.
    """
    from app.benchmark.afriswitch_runner import AfriSwitchReport, AfriSwitchRunner, UtteranceResult

    source = Path(args.input)
    if not source.exists():
        print(f"No such file: {source}", file=sys.stderr)
        return 2

    saved = json.loads(source.read_text(encoding="utf-8"))

    results = [
        UtteranceResult(
            utterance_id=row.get("utterance_id", ""),
            provider=row.get("provider", ""),
            cmi=float(row.get("cmi") or 0.0),
            cmi_band=row.get("cmi_band", "moderate"),
            num_switch_points=int(row.get("num_switch_points") or 0),
            duration=float(row.get("duration") or 0.0),
            reference=row.get("reference", ""),
            hypothesis=row.get("hypothesis", ""),
            wer=float(row.get("wer") or 0.0),
            cer=float(row.get("cer") or 0.0),
            code_switch=row.get("code_switch") or {},
            latency_ms=row.get("latency_ms"),
            failed=bool(row.get("failed")),
            failure_reason=row.get("failure_reason"),
            used_placeholder_fixture=bool(row.get("used_placeholder_fixture")),
        )
        for row in saved.get("results", [])
    ]

    if not results:
        print(f"{source} contains no per-utterance results to rescore.", file=sys.stderr)
        return 1

    report = AfriSwitchReport(
        config=saved.get("config", "kinyarwanda"),
        providers=saved.get("providers", []),
        utterance_count=saved.get("utterance_count", len(results)),
        dataset_notes=saved.get("dataset_notes", []),
        band_profile=saved.get("band_profile", {}),
        results=results,
        source=saved.get("source", "afriswitch"),
        source_label=saved.get("source_label"),
    )

    runner = AfriSwitchRunner.__new__(AfriSwitchRunner)
    runner.settings = get_settings()
    runner.audio_root = None

    code_switched = report.source == "afriswitch"
    runner._aggregate(report, args.bootstrap, code_switched)
    runner._pair(report, args.bootstrap, code_switched)
    report.sanity = runner._sanity_check(report, report.config)

    failures = sum(1 for r in results if r.failed)
    rate = failures / len(results)
    report.publishable = rate < 0.20
    report.publishability_note = (
        f"{failures} of {len(results)} provider calls failed ({rate:.0%}) and are "
        "excluded from the error rates, which are computed over successful calls. "
        "Reported for completeness."
        if failures
        else None
    )

    out = Path(args.out or source.parent)
    out.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    slug = f"{report.source}-{report.config}-rescored-{stamp}"

    (out / f"{slug}.json").write_text(
        json.dumps(asdict(report), indent=2, default=str), encoding="utf-8"
    )

    markdown = render(report)
    (out / f"{slug}.md").write_text(markdown, encoding="utf-8")
    print(markdown)

    return 0


def _scored_count(report: AfriSwitchReport) -> int:
    """Utterances that produced a transcript, per provider — they all see the same set."""
    for stats in report.overall.values():
        count = stats.get("sample_count")
        if count:
            return int(count["value"])
    return report.utterance_count


def _failure_reasons(report: AfriSwitchReport) -> list[tuple[str, int]]:
    """
    Grouped by cause, not by occurrence.

    Every queued clip carries its own file_id, so keying on the raw message
    printed twelve identical-looking lines that differed only by a UUID and
    buried the one thing worth knowing: they were all the same problem.
    """
    counts: dict[str, int] = {}

    for result in report.results:
        if not (result.failed and result.failure_reason):
            continue
        # Group on the shape of the problem, not on its identifiers. Every
        # queued clip carries a distinct file_id, so keying on the raw message
        # printed one line per occurrence and buried the single fact worth
        # knowing: they were all the same failure.
        key = re.sub(r"\(file_id[^)]*\)", "(file_id <id>)", result.failure_reason)
        key = re.sub(r"[0-9a-f]{8}-[0-9a-f-]{20,}", "<id>", key)
        key = key.split(".")[0].strip()[:160]
        counts[key] = counts.get(key, 0) + 1

    return sorted(counts.items(), key=lambda item: -item[1])


def _failure_rate(report: AfriSwitchReport, provider: str) -> float:
    stats = report.overall.get(provider, {}).get("failure_rate")
    return float(stats["value"]) if stats else 0.0


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

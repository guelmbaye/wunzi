"""
Benchmark CLI.

    python -m app.benchmark.cli run \
        --dataset dataset-v1 --split holdout \
        --providers sahara,whisper,model_b,model_c \
        --out /benchmark/reports

Writes results.json, metrics.csv and report.md. The report states the freeze
explicitly so a reader can check the comparison rather than trust it.
"""

from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime, timezone
from pathlib import Path

from app.benchmark.metrics.sponsor_delta import sponsor_outcome_delta
from app.benchmark.runner import run_sync
from app.config import get_settings
from app.schemas.benchmark import BenchmarkRunRequest, BenchmarkRunResponse

HEADLINE_ORDER = [
    "word_error_rate",
    "critical_fact_accuracy",
    "negation_preservation_rate",
    "claim_attribution_accuracy",
    "wrong_party_attribution_rate",
    "issue_macro_f1",
    "correct_mediation_state_rate",
]


def main() -> int:
    parser = argparse.ArgumentParser(prog="wunzi-benchmark")
    sub = parser.add_subparsers(dest="command", required=True)

    run = sub.add_parser("run", help="Run the switch-aware mediation benchmark")
    run.add_argument("--dataset", default=None)
    run.add_argument("--split", default="holdout", choices=["dev", "holdout"])
    run.add_argument("--providers", default="sahara,whisper,model_b,model_c")
    run.add_argument("--no-guard", action="store_true", help="Ablation: disable the Critical Speech Guard")
    run.add_argument("--bootstrap", type=int, default=1000)
    run.add_argument("--root", default=None)
    run.add_argument("--out", default=None)

    args = parser.parse_args()
    settings = get_settings()

    root = Path(args.root or settings.benchmark_root)
    out = Path(args.out or root / "reports")
    out.mkdir(parents=True, exist_ok=True)

    request = BenchmarkRunRequest(
        dataset_version=args.dataset or settings.dataset_version,
        split=args.split,
        providers=[p.strip() for p in args.providers.split(",") if p.strip()],
        guard_enabled=not args.no_guard,
        bootstrap_samples=args.bootstrap,
        pipeline_version=settings.pipeline_version,
    )

    response = run_sync(request, root=root)

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    _write_json(out / f"results-{stamp}.json", response)
    _write_csv(out / f"metrics-{stamp}.csv", response)
    report = _write_markdown(out / f"report-{stamp}.md", response, request)

    print(report)
    return 0


def _write_json(path: Path, response: BenchmarkRunResponse) -> None:
    path.write_text(response.model_dump_json(indent=2), encoding="utf-8")


def _write_csv(path: Path, response: BenchmarkRunResponse) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["provider", "metric", "value", "ci_low", "ci_high", "scope", "n"])
        for row in response.metrics:
            writer.writerow(
                [row.provider, row.metric, row.value, row.ci_low, row.ci_high, row.scope, row.sample_count]
            )


def _write_markdown(path: Path, response: BenchmarkRunResponse, request: BenchmarkRunRequest) -> str:
    cmsr = {r.provider: r.value for r in response.metrics if r.metric == "correct_mediation_state_rate"}
    delta = sponsor_outcome_delta(cmsr)

    lines = [
        "# WUNZI — Switch-Aware Mediation Benchmark",
        "",
        f"- Dataset: `{response.dataset_version}` · split `{response.split}`",
        f"- Providers: {', '.join(request.providers)}",
        f"- Critical Speech Guard: {'enabled' if request.guard_enabled else 'DISABLED (ablation)'}",
        f"- Commit: `{response.git_commit or 'n/a'}`",
        "",
        f"> {response.integrity}",
        "",
    ]

    if not response.publishable:
        lines += [
            "> **⚠ NOT PUBLISHABLE.** " + (response.publishability_note or ""),
            "",
        ]

    lines += [
        "## Headline metrics",
        "",
        "| Metric | " + " | ".join(request.providers) + " |",
        "| --- | " + " | ".join(["---"] * len(request.providers)) + " |",
    ]

    lookup = {(r.provider, r.metric): r for r in response.metrics}
    for metric in HEADLINE_ORDER:
        cells = []
        for provider in request.providers:
            row = lookup.get((provider, metric))
            if row is None:
                cells.append("—")
            elif row.ci_low is not None and row.ci_high is not None and metric != "correct_mediation_state_rate":
                cells.append(f"{row.value:.3f} [{row.ci_low:.3f}–{row.ci_high:.3f}]")
            else:
                cells.append(f"{row.value:.2f}")
        lines.append(f"| {metric.replace('_', ' ')} | " + " | ".join(cells) + " |")

    lines += [
        "",
        "## Sponsor Outcome Delta",
        "",
        f"- Sahara CMSR: **{delta.sponsor_cmsr:.2f}%**",
        f"- Best alternative ({delta.best_competitor or 'n/a'}): **{delta.best_competitor_cmsr:.2f}%**",
        f"- Delta: **{delta.delta_points:+.2f} points** → `{delta.verdict}`",
        "",
        delta.narrative,
        "",
        "*SOD is an internal discipline metric, not an official Intron criterion.*",
        "",
        "## Failure taxonomy",
        "",
        "| Scenario | Provider | Codes | Case state correct |",
        "| --- | --- | --- | --- |",
    ]

    for observation in response.observations:
        codes = ", ".join(observation.error_taxonomy or []) or "—"
        lines.append(
            f"| {observation.scenario_id} | {observation.provider} | {codes} | "
            f"{'yes' if observation.case_state_correct else 'no'} |"
        )

    report = "\n".join(lines) + "\n"
    path.write_text(report, encoding="utf-8")
    return report


if __name__ == "__main__":
    raise SystemExit(main())

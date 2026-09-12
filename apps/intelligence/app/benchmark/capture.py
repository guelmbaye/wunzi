"""
Fixture capture.

Records authentic provider output so the demo and the test suite never depend on
live API availability — and so a replay is always distinguishable from a live
call. This is the ONLY sanctioned way to produce a file under
`benchmark/fixtures/asr/`. Hand-written fixtures are placeholders, and the runner
marks any run that touches one as not publishable.

    WUNZI_MODE=live python -m app.benchmark.capture \
        --dataset dataset-v1 --providers sahara,whisper,model_b,model_c
"""

from __future__ import annotations

import argparse
import asyncio
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

from app.asr.base import AsrError
from app.asr.registry import get_provider
from app.benchmark.dataset import load_dataset
from app.config import get_settings
from app.schemas.speech import TranscriptionConfig


async def capture(dataset_version: str, providers: list[str], root: Path, split: str | None) -> int:
    settings = get_settings()

    if settings.fixture_mode:
        print("Refusing to capture in fixture mode: replaying a replay would produce a fake capture.")
        print("Set WUNZI_MODE=live and provide the provider API keys.")
        return 2

    dataset = load_dataset(root, dataset_version)
    scenarios = dataset.split(split) if split else dataset.scenarios
    run_id = str(uuid.uuid4())
    captured_at = datetime.now(timezone.utc).isoformat()
    written = failed = 0

    for provider_name in providers:
        try:
            provider = get_provider(provider_name, settings, force_mode="live")
        except KeyError as exc:
            print(f"[skip] {provider_name}: {exc}")
            continue

        target_dir = root / "fixtures" / "asr" / provider_name
        target_dir.mkdir(parents=True, exist_ok=True)

        for scenario in scenarios:
            for clip in scenario.clips:
                audio_uri = str(root / clip.audio_path) if clip.audio_path else None
                if not audio_uri or not Path(audio_uri).exists():
                    print(f"[skip] {provider_name}/{clip.clip_id}: audio not found")
                    continue

                try:
                    transcript = await provider.transcribe(audio_uri, TranscriptionConfig())
                except AsrError as exc:
                    # A provider failure is itself an observation worth keeping.
                    failed += 1
                    print(f"[fail] {provider_name}/{clip.clip_id}: {exc}")
                    continue

                payload = {
                    "clip_id": clip.clip_id,
                    "model": transcript.model,
                    "provider_version": transcript.provider_version,
                    "text": transcript.text,
                    "segments": [s.model_dump() for s in transcript.segments],
                    "latency_ms": transcript.latency_ms,
                    "fixture_origin": f"live capture · run {run_id} · {captured_at}",
                    "is_placeholder": False,
                    "captured_at": captured_at,
                    "capture_run_id": run_id,
                    # The untouched payload stays inspectable: no cleaning, no editing.
                    "raw": transcript.raw,
                }

                path = target_dir / f"{clip.clip_id}.json"
                path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
                written += 1
                print(f"[ok]   {path}")

    print(f"\nCaptured {written} fixture(s), {failed} provider failure(s). Run id {run_id}.")
    return 0 if written else 1


def main() -> int:
    settings = get_settings()

    parser = argparse.ArgumentParser(prog="wunzi-capture")
    parser.add_argument("--dataset", default=settings.dataset_version)
    parser.add_argument("--providers", default="sahara,whisper,model_b,model_c")
    parser.add_argument("--split", default=None, choices=[None, "dev", "holdout"])
    parser.add_argument("--root", default=str(settings.benchmark_root))
    args = parser.parse_args()

    return asyncio.run(
        capture(
            args.dataset,
            [p.strip() for p in args.providers.split(",") if p.strip()],
            Path(args.root),
            args.split,
        )
    )


if __name__ == "__main__":
    raise SystemExit(main())

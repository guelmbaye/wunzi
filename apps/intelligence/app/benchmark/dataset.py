"""
Evaluation dataset loader.

  dataset-v1
    dev     5 disputes   — development, tuning, inspection
    holdout 10 disputes  — never used for tuning; headline numbers come from here

Splitting is not bureaucracy: it is the difference between "we measured it" and
"we tuned until the number looked good".
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

# Every observation is labelled so failures are explainable, not just countable.
ERROR_TAXONOMY = {
    "E01": "Numeric error (amount misheard)",
    "E02": "Date error",
    "E03": "Negation loss",
    "E04": "Attribution error (wrong party)",
    "E05": "Reported speech flattened into direct fact",
    "E06": "Code-switch boundary error",
    "E07": "Named entity error",
    "E08": "Claim omitted entirely",
    "E09": "Claim invented (no source)",
    "E10": "Issue state error",
}


@dataclass
class Clip:
    clip_id: str
    scenario_id: str
    party_role: str
    audio_path: str | None
    reference_transcript: str
    language_profile: str = "mixed"
    duration_ms: int | None = None
    fixture_key: str | None = None


@dataclass
class Scenario:
    scenario_id: str
    split: str
    category: str = "rental_deposit"
    description: str = ""
    clips: list[Clip] = field(default_factory=list)
    expected_claims: dict[str, list[dict]] = field(default_factory=dict)
    expected_issue_states: dict[str, str] = field(default_factory=dict)
    notes: str = ""


@dataclass
class Dataset:
    version: str
    scenarios: list[Scenario]

    def split(self, name: str) -> list[Scenario]:
        return [s for s in self.scenarios if s.split == name]

    def scenario(self, scenario_id: str) -> Scenario | None:
        return next((s for s in self.scenarios if s.scenario_id == scenario_id), None)


def load_dataset(root: Path, version: str = "dataset-v1") -> Dataset:
    manifest_path = Path(root) / "manifests" / f"{version}.json"
    if not manifest_path.exists():
        manifest_path = Path(root) / "manifests" / "manifest.json"

    if not manifest_path.exists():
        raise FileNotFoundError(f"No benchmark manifest found under {root}/manifests")

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    annotations_root = Path(root) / "annotations"

    scenarios: list[Scenario] = []

    for entry in manifest.get("scenarios", []):
        annotation_path = annotations_root / f"{entry['scenario_id']}.json"
        annotation = (
            json.loads(annotation_path.read_text(encoding="utf-8")) if annotation_path.exists() else {}
        )

        clips = [
            Clip(
                clip_id=clip["clip_id"],
                scenario_id=entry["scenario_id"],
                party_role=clip["party_role"],
                audio_path=clip.get("audio_path"),
                reference_transcript=annotation.get("reference_transcripts", {}).get(clip["clip_id"], ""),
                language_profile=clip.get("language_profile", "mixed"),
                duration_ms=clip.get("duration_ms"),
                fixture_key=clip.get("fixture_key", clip["clip_id"]),
            )
            for clip in entry.get("clips", [])
        ]

        scenarios.append(
            Scenario(
                scenario_id=entry["scenario_id"],
                split=entry.get("split", "dev"),
                category=entry.get("category", "rental_deposit"),
                description=entry.get("description", ""),
                clips=clips,
                expected_claims=annotation.get("expected_claims", {}),
                expected_issue_states=annotation.get("expected_issue_states", {}),
                notes=annotation.get("notes", ""),
            )
        )

    return Dataset(version=manifest.get("version", version), scenarios=scenarios)

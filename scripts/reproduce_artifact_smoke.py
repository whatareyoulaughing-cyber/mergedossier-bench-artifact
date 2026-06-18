"""Run the reviewer-facing artifact smoke workflow.

This script exercises the offline artifact path without a GitHub token or
network access. It is intended for artifact reviewers who want one command that
validates the package, runs corpus summaries, generates annotation inputs, and
executes the test suite.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs" / "artifact_smoke"


def run(args: list[str]) -> dict[str, object]:
    env = os.environ.copy()
    src = str(ROOT / "src")
    env["PYTHONPATH"] = src + os.pathsep + env.get("PYTHONPATH", "")
    env["PYTHONIOENCODING"] = "utf-8"
    completed = subprocess.run(args, cwd=ROOT, env=env, text=True, capture_output=True, check=False)
    record: dict[str, object] = {
        "command": args,
        "returncode": completed.returncode,
        "stdout_tail": completed.stdout[-2000:],
        "stderr_tail": completed.stderr[-2000:],
    }
    if completed.returncode != 0:
        raise RuntimeError(json.dumps(record, indent=2))
    return record


def main() -> int:
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir(parents=True)

    commands = [
        [
            sys.executable,
            "-m",
            "mergedossier_bench.cli",
            "validate",
            "--kind",
            "dossier",
            "--file",
            "examples/toy_merge_dossier.json",
        ],
        [
            sys.executable,
            "-m",
            "mergedossier_bench.cli",
            "score",
            "--dossier",
            "examples/toy_merge_dossier.json",
            "--out",
            str(OUT / "toy_score.json"),
        ],
        [
            sys.executable,
            "-m",
            "mergedossier_bench.cli",
            "summarize",
            "--dossiers",
            "examples/corpus",
            "--out",
            str(OUT / "corpus_dir"),
        ],
        [
            sys.executable,
            "-m",
            "mergedossier_bench.cli",
            "summarize",
            "--dossiers",
            "examples/corpus/toy_dossiers.jsonl",
            "--out",
            str(OUT / "corpus_jsonl"),
        ],
        [
            sys.executable,
            "-m",
            "mergedossier_bench.cli",
            "build-seed-corpus",
            "--manifest",
            "data/manifests/seed_prs.csv",
            "--out",
            str(OUT / "seed_corpus"),
            "--use-fixtures",
            "tests/fixtures/github_prs",
        ],
        [
            sys.executable,
            "-m",
            "mergedossier_bench.cli",
            "summarize",
            "--dossiers",
            str(OUT / "seed_corpus" / "dossiers"),
            "--out",
            str(OUT / "seed_summary"),
        ],
        [
            sys.executable,
            "-m",
            "mergedossier_bench.cli",
            "export-annotation-tasks",
            "--dossiers",
            str(OUT / "seed_corpus" / "dossiers"),
            "--out",
            str(OUT / "seed_annotation_tasks.json"),
        ],
        [
            sys.executable,
            "-m",
            "mergedossier_bench.cli",
            "create-reliability-sample",
            "--tasks",
            str(OUT / "seed_annotation_tasks.json"),
            "--out",
            str(OUT / "seed_annotation_tasks_with_repeats.json"),
            "--rate",
            "0.2",
            "--min-count",
            "2",
        ],
        [
            sys.executable,
            "-m",
            "mergedossier_bench.cli",
            "export-annotation-csv",
            "--tasks",
            str(OUT / "seed_annotation_tasks_with_repeats.json"),
            "--out",
            str(OUT / "seed_annotation_sheet.csv"),
            "--annotator-id",
            "solo",
        ],
        [
            sys.executable,
            "-m",
            "mergedossier_bench.cli",
            "validate-annotation-csv",
            "--annotations",
            str(OUT / "seed_annotation_sheet.csv"),
            "--allow-incomplete",
            "--out",
            str(OUT / "seed_annotation_sheet_validation.json"),
        ],
        [
            sys.executable,
            "-m",
            "mergedossier_bench.cli",
            "annotation-stats",
            "--annotations",
            "examples/annotations/toy_label_studio_export.json",
            "--out",
            str(OUT / "annotation_stats"),
        ],
        [sys.executable, "-m", "pytest", "-q"],
    ]

    records = [run(command) for command in commands]
    (OUT / "artifact_smoke_log.json").write_text(json.dumps(records, indent=2), encoding="utf-8")

    required = [
        OUT / "toy_score.json",
        OUT / "corpus_dir" / "summary.json",
        OUT / "corpus_jsonl" / "summary.json",
        OUT / "seed_summary" / "summary.json",
        OUT / "seed_annotation_tasks_with_repeats.json",
        OUT / "seed_annotation_sheet.csv",
        OUT / "seed_annotation_sheet_validation.json",
        OUT / "annotation_stats" / "agreement_summary.json",
        OUT / "artifact_smoke_log.json",
    ]
    missing = [str(path) for path in required if not path.exists()]
    if missing:
        raise RuntimeError("Missing expected artifact smoke outputs: " + ", ".join(missing))

    print("Artifact smoke workflow completed: outputs/artifact_smoke")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

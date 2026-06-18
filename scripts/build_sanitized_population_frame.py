"""Build a text-free population-frame manifest for anonymous artifact release.

The full AIDev-pop normalized frame contains public PR titles, bodies, changed
files, commit messages, comments, and reviews. Public text can still contain
token-like strings copied from upstream repositories, so the anonymous-review
package publishes only the metadata needed to audit the sampling frame and
stratified sample.
"""

from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

SAFE_COLUMNS = [
    "source_row_index",
    "instance_id",
    "repo",
    "pr_number",
    "pr_url",
    "source",
    "author_type",
    "agent_name",
    "agent_tool",
    "task_type",
    "language",
    "outcome",
    "sample_split",
    "created_at",
    "changed_file_count",
    "commit_count",
    "comment_count",
    "review_count",
    "artifact_completeness",
    "eligibility",
    "eligibility_reason",
    "size_tercile",
    "sampling_weight",
    "ci_status",
    "in_sample_500",
]

TEXT_COLUMNS = [
    "notes",
    "title",
    "body",
    "files_changed",
    "commit_messages",
    "comments",
    "reviews",
]


def _load_sample_ids(sample_path: Path | None) -> set[str]:
    if sample_path is None:
        return set()
    sample_ids: set[str] = set()
    with sample_path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if "instance_id" not in (reader.fieldnames or []):
            raise ValueError(f"{sample_path} does not contain instance_id")
        for row in reader:
            instance_id = (row.get("instance_id") or "").strip()
            if instance_id:
                sample_ids.add(instance_id)
    return sample_ids


def build_sanitized_frame(
    frame_path: Path,
    out_path: Path,
    report_path: Path,
    sample_path: Path | None = None,
) -> dict[str, object]:
    sample_ids = _load_sample_ids(sample_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.parent.mkdir(parents=True, exist_ok=True)

    row_count = 0
    sampled_count = 0
    eligibility_counts: dict[str, int] = {}
    agent_counts: dict[str, int] = {}
    language_counts: dict[str, int] = {}
    outcome_counts: dict[str, int] = {}

    with frame_path.open("r", encoding="utf-8-sig", newline="") as source_handle:
        reader = csv.DictReader(source_handle)
        source_columns = reader.fieldnames or []
        missing_safe = [
            col
            for col in SAFE_COLUMNS
            if col not in {"source_row_index", "in_sample_500"} and col not in source_columns
        ]
        if missing_safe:
            raise ValueError(f"Input frame is missing safe columns: {missing_safe}")

        dropped_columns = [col for col in source_columns if col not in SAFE_COLUMNS]
        dropped_text_columns = [col for col in TEXT_COLUMNS if col in source_columns]

        with out_path.open("w", encoding="utf-8", newline="") as out_handle:
            writer = csv.DictWriter(out_handle, fieldnames=SAFE_COLUMNS)
            writer.writeheader()
            for row_index, row in enumerate(reader, start=1):
                instance_id = (row.get("instance_id") or "").strip()
                in_sample = instance_id in sample_ids
                sampled_count += int(in_sample)
                row_count += 1

                eligibility = row.get("eligibility", "")
                agent = row.get("agent_tool", "") or row.get("agent_name", "")
                language = row.get("language", "")
                outcome = row.get("outcome", "")
                eligibility_counts[eligibility] = eligibility_counts.get(eligibility, 0) + 1
                agent_counts[agent] = agent_counts.get(agent, 0) + 1
                language_counts[language] = language_counts.get(language, 0) + 1
                outcome_counts[outcome] = outcome_counts.get(outcome, 0) + 1

                safe_row = {col: row.get(col, "") for col in SAFE_COLUMNS}
                safe_row["source_row_index"] = row_index
                safe_row["in_sample_500"] = "true" if in_sample else "false"
                writer.writerow(safe_row)

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_frame": str(frame_path),
        "sample_manifest": str(sample_path) if sample_path else None,
        "output": str(out_path),
        "rows": row_count,
        "safe_columns": SAFE_COLUMNS,
        "dropped_columns": dropped_columns,
        "dropped_text_columns": dropped_text_columns,
        "sample_ids_loaded": len(sample_ids),
        "sample_rows_marked": sampled_count,
        "eligibility_counts": eligibility_counts,
        "agent_tool_counts": agent_counts,
        "language_counts": language_counts,
        "outcome_counts": outcome_counts,
        "privacy_boundary": (
            "This manifest removes PR titles, bodies, file lists, commit messages, "
            "comments, reviews, and notes. It is intended for sampling-frame audit, "
            "not raw-text reconstruction."
        ),
    }
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build sanitized population-frame manifest")
    parser.add_argument(
        "--frame",
        default="data/manifests/population_ai_pr_frame_20260616.csv",
        help="Full normalized population frame CSV.",
    )
    parser.add_argument(
        "--sample",
        default="data/manifests/population_ai_pr_sample_500_20260616.csv",
        help="Sample manifest used to mark sampled rows.",
    )
    parser.add_argument(
        "--out",
        default="data/manifests/population_ai_pr_frame_sanitized_20260616.csv",
        help="Text-free output manifest.",
    )
    parser.add_argument(
        "--report-out",
        default="outputs/population_sampling_report_20260616/sanitized_frame_report.json",
        help="JSON report describing retained and dropped columns.",
    )
    args = parser.parse_args(argv)

    report = build_sanitized_frame(
        ROOT / args.frame,
        ROOT / args.out,
        ROOT / args.report_out,
        ROOT / args.sample if args.sample else None,
    )
    print(
        "Sanitized frame written: "
        f"{args.out} ({report['rows']} rows, {report['sample_rows_marked']} sampled)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

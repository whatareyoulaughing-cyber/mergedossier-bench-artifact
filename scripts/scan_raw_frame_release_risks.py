"""Scan the full population frame for raw-text release risks.

The scan is intentionally conservative and non-revealing: reports contain
pattern names, columns, row counts, and PR identifiers, but never the matched
secret-like text. The goal is to support the release policy that the sanitized
population frame is the default public artifact, while raw PR text requires a
separate scrub before any public or archival release.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable


ROOT = Path(__file__).resolve().parents[1]

TEXT_COLUMNS = [
    "notes",
    "title",
    "body",
    "files_changed",
    "commit_messages",
    "comments",
    "reviews",
]

IDENTIFIER_COLUMNS = ["instance_id", "repo", "pr_number", "pr_url"]

SECRET_PATTERNS = {
    "github_fine_grained_pat": re.compile(r"github_pat_[A-Za-z0-9_]{20,}"),
    "github_classic_pat": re.compile(r"ghp_[A-Za-z0-9_]{20,}"),
    "openai_api_key": re.compile(r"sk-[A-Za-z0-9_-]{20,}"),
    "google_api_key": re.compile(r"AIza[0-9A-Za-z_-]{20,}"),
    "private_key_header": re.compile(
        r"-----BEGIN (?:RSA |OPENSSH |EC |DSA )?PRIVATE KEY-----"
    ),
    "aws_access_key_id": re.compile(r"AKIA[0-9A-Z]{16}"),
    "slack_token": re.compile(r"xox[baprs]-[A-Za-z0-9-]{20,}"),
}


def _safe_identifier(row: dict[str, str]) -> dict[str, str]:
    return {column: (row.get(column) or "") for column in IDENTIFIER_COLUMNS}


def _present_text_columns(fieldnames: Iterable[str] | None) -> list[str]:
    available = set(fieldnames or [])
    return [column for column in TEXT_COLUMNS if column in available]


def scan_raw_frame_release_risks(
    frame_path: Path,
    out_dir: Path,
    max_examples: int = 25,
) -> dict[str, object]:
    out_dir.mkdir(parents=True, exist_ok=True)
    summary_path = out_dir / "raw_frame_release_risk_summary.json"
    markdown_path = out_dir / "raw_frame_release_risk_summary.md"

    rows_scanned = 0
    rows_with_findings: set[str] = set()
    pattern_counts: Counter[str] = Counter()
    column_counts: Counter[str] = Counter()
    pattern_column_counts: Counter[tuple[str, str]] = Counter()
    examples: list[dict[str, str]] = []

    with frame_path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        text_columns = _present_text_columns(reader.fieldnames)
        for row_index, row in enumerate(reader, start=1):
            rows_scanned += 1
            row_had_finding = False
            for column in text_columns:
                value = row.get(column) or ""
                if not value:
                    continue
                for pattern_name, pattern in SECRET_PATTERNS.items():
                    if not pattern.search(value):
                        continue
                    pattern_counts[pattern_name] += 1
                    column_counts[column] += 1
                    pattern_column_counts[(pattern_name, column)] += 1
                    row_had_finding = True
                    if len(examples) < max_examples:
                        example = {
                            "source_row_index": str(row_index),
                            "column": column,
                            "pattern_name": pattern_name,
                        }
                        example.update(_safe_identifier(row))
                        examples.append(example)
            if row_had_finding:
                rows_with_findings.add(str(row_index))

    recommendation = (
        "Do not include the full raw-text frame in the anonymous or public release "
        "unless a dedicated secret/privacy scrub and manual review are completed. "
        "Use the sanitized population frame as the default release artifact."
    )
    status = "findings_present" if rows_with_findings else "no_pattern_findings"
    try:
        display_frame = frame_path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        display_frame = frame_path.name

    summary = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_frame": display_frame,
        "rows_scanned": rows_scanned,
        "text_columns_present": text_columns,
        "patterns_checked": sorted(SECRET_PATTERNS),
        "status": status,
        "affected_rows": len(rows_with_findings),
        "pattern_counts": dict(sorted(pattern_counts.items())),
        "column_counts": dict(sorted(column_counts.items())),
        "pattern_column_counts": [
            {"pattern_name": pattern, "column": column, "count": count}
            for (pattern, column), count in sorted(pattern_column_counts.items())
        ],
        "examples_without_secret_text": examples,
        "secret_text_redaction": (
            "Matched strings and surrounding snippets are intentionally omitted from "
            "this report."
        ),
        "recommendation": recommendation,
    }
    summary_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    markdown_path.write_text(_render_markdown(summary), encoding="utf-8")
    return summary


def _render_markdown(summary: dict[str, object]) -> str:
    pattern_rows = summary.get("pattern_counts") or {}
    column_rows = summary.get("column_counts") or {}
    pattern_lines = [
        "| Pattern | Count |",
        "|---|---:|",
    ]
    if isinstance(pattern_rows, dict) and pattern_rows:
        pattern_lines.extend(f"| `{name}` | {count} |" for name, count in pattern_rows.items())
    else:
        pattern_lines.append("| None detected | 0 |")

    column_lines = [
        "| Column | Count |",
        "|---|---:|",
    ]
    if isinstance(column_rows, dict) and column_rows:
        column_lines.extend(f"| `{name}` | {count} |" for name, count in column_rows.items())
    else:
        column_lines.append("| None detected | 0 |")

    example_lines = [
        "| Row | Instance | Repository | PR | Column | Pattern |",
        "|---:|---|---|---:|---|---|",
    ]
    examples = summary.get("examples_without_secret_text") or []
    if isinstance(examples, list) and examples:
        for example in examples:
            if not isinstance(example, dict):
                continue
            example_lines.append(
                "| {row} | `{instance}` | `{repo}` | {pr} | `{column}` | `{pattern}` |".format(
                    row=example.get("source_row_index", ""),
                    instance=example.get("instance_id", ""),
                    repo=example.get("repo", ""),
                    pr=example.get("pr_number", ""),
                    column=example.get("column", ""),
                    pattern=example.get("pattern_name", ""),
                )
            )
    else:
        example_lines.append("| - | - | - | - | - | - |")

    return "\n".join(
        [
            "# Raw Frame Release Risk Scan",
            "",
            f"- Source frame: `{summary.get('source_frame')}`",
            f"- Rows scanned: {summary.get('rows_scanned')}",
            f"- Text columns present: {', '.join(summary.get('text_columns_present') or [])}",
            f"- Status: `{summary.get('status')}`",
            f"- Affected rows: {summary.get('affected_rows')}",
            "",
            "This report never includes matched secret-like strings or surrounding raw-text snippets.",
            "",
            "## Pattern Counts",
            "",
            *pattern_lines,
            "",
            "## Column Counts",
            "",
            *column_lines,
            "",
            "## Example Row Identifiers",
            "",
            *example_lines,
            "",
            "## Recommendation",
            "",
            str(summary.get("recommendation", "")),
            "",
        ]
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Scan raw population frame release risks")
    parser.add_argument(
        "--frame",
        default="data/manifests/population_ai_pr_frame_20260616.csv",
        help="Full normalized population-frame CSV to scan.",
    )
    parser.add_argument(
        "--out",
        default="outputs/raw_frame_release_risk_20260617",
        help="Output directory for JSON and Markdown risk reports.",
    )
    parser.add_argument(
        "--max-examples",
        type=int,
        default=25,
        help="Maximum number of row identifiers to include without snippets.",
    )
    args = parser.parse_args(argv)
    summary = scan_raw_frame_release_risks(ROOT / args.frame, ROOT / args.out, args.max_examples)
    print(
        "Raw frame risk scan written: "
        f"{args.out} ({summary['rows_scanned']} rows, {summary['affected_rows']} affected rows)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

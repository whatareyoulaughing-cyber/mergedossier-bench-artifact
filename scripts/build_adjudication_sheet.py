"""Build an adjudication sheet from annotation disagreement outputs."""

from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path
from typing import Any


ADJUDICATION_FIELDS = [
    "reliability_group_id",
    "category",
    "severity",
    "priority",
    "labels_seen",
    "record_labels",
    "comments_seen",
    "adjudicated_label",
    "adjudication_basis",
    "adjudication_note",
]


def _jsonl(path: str | Path) -> list[dict[str, Any]]:
    jsonl_path = Path(path)
    if not jsonl_path.exists():
        return []
    rows = []
    for line in jsonl_path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def _records_by_group(records: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        group_id = str(record.get("reliability_group_id") or record.get("instance_id") or "UNKNOWN")
        grouped[group_id].append(record)
    return dict(grouped)


def _record_label_summary(records: list[dict[str, Any]], category: str) -> str:
    parts = []
    for record in records:
        label = record.get("category_labels", {}).get(category)
        if label is None:
            continue
        annotator = record.get("annotator_id") or "unknown"
        instance_id = record.get("instance_id") or record.get("task_id") or "unknown"
        repeat = "repeat" if record.get("is_reliability_repeat") else "primary"
        parts.append(f"{annotator}:{instance_id}:{repeat}:{label}")
    return "; ".join(parts)


def _comment_summary(records: list[dict[str, Any]], category: str) -> str:
    comments = []
    for record in records:
        comment = str(record.get("category_comments", {}).get(category) or "").strip()
        if not comment:
            continue
        instance_id = record.get("instance_id") or record.get("task_id") or "unknown"
        comments.append(f"{instance_id}: {comment}")
    return " | ".join(comments)


def build_adjudication_rows(disagreement_cases: list[dict[str, Any]], records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped = _records_by_group(records)
    rows: list[dict[str, Any]] = []
    for case in disagreement_cases:
        group_id = str(case.get("reliability_group_id") or case.get("instance_id") or "UNKNOWN")
        group_records = grouped.get(group_id, [])
        for disagreement in case.get("disagreements", []):
            category = str(disagreement.get("category", "UNKNOWN"))
            severity = int(disagreement.get("severity", case.get("severity", 0)) or 0)
            rows.append(
                {
                    "reliability_group_id": group_id,
                    "category": category,
                    "severity": severity,
                    "priority": "high" if severity >= 2 else "medium",
                    "labels_seen": ";".join(str(label) for label in disagreement.get("labels", [])),
                    "record_labels": _record_label_summary(group_records, category),
                    "comments_seen": _comment_summary(group_records, category),
                    "adjudicated_label": "",
                    "adjudication_basis": "",
                    "adjudication_note": "",
                }
            )
    return sorted(rows, key=lambda row: (int(row["severity"]), row["reliability_group_id"], row["category"]), reverse=True)


def write_adjudication_csv(rows: list[dict[str, Any]], out: str | Path) -> None:
    out_path = Path(out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=ADJUDICATION_FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def write_adjudication_markdown(rows: list[dict[str, Any]], out: str | Path) -> None:
    high = sum(1 for row in rows if row["priority"] == "high")
    lines = [
        "# Adjudication Sheet Summary",
        "",
        f"- Disagreement rows: {len(rows)}",
        f"- High-priority rows: {high}",
        "",
    ]
    if rows:
        lines.extend(
            [
                "| Group | Category | Severity | Labels |",
                "|---|---|---:|---|",
            ]
        )
        for row in rows:
            lines.append(
                f"| {row['reliability_group_id']} | {row['category']} | {row['severity']} | {row['labels_seen']} |"
            )
    else:
        lines.append("_No adjudication rows are required because no category disagreements were detected._")
    lines.extend(
        [
            "",
            "## How To Use",
            "",
            "- Re-open only the evidence visible during annotation.",
            "- Fill `adjudicated_label` with one of the protocol labels.",
            "- Use `adjudication_basis` values such as `primary`, `repeat`, `clarified_codebook`, or `second_review`.",
            "- Preserve the raw labels; do not overwrite `record_labels`.",
            "",
        ]
    )
    Path(out).write_text("\n".join(lines), encoding="utf-8")


def build_adjudication_sheet(stats_dir: str | Path, out_csv: str | Path, out_md: str | Path | None = None) -> list[dict[str, Any]]:
    stats_path = Path(stats_dir)
    cases = _jsonl(stats_path / "disagreement_cases.jsonl")
    records = _jsonl(stats_path / "annotation_records.jsonl")
    rows = build_adjudication_rows(cases, records)
    write_adjudication_csv(rows, out_csv)
    if out_md:
        write_adjudication_markdown(rows, out_md)
    return rows


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build adjudication CSV from annotation stats")
    parser.add_argument("--stats-dir", required=True, help="Directory containing disagreement_cases.jsonl and annotation_records.jsonl")
    parser.add_argument("--out", required=True, help="Output adjudication CSV")
    parser.add_argument("--markdown", help="Optional Markdown summary")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    rows = build_adjudication_sheet(args.stats_dir, args.out, args.markdown)
    print(f"Adjudication sheet written: {len(rows)} rows -> {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

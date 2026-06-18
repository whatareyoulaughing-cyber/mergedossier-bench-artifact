"""Report completion progress for an external-audit workbook or CSV.

Unlike check_external_audit_return.py, this helper is allowed to inspect an
in-progress sheet. It writes a progress report and a sendable feedback note
without claiming external agreement.
"""

from __future__ import annotations

import argparse
import csv
import json
import shutil
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from export_annotation_csv_from_workbook import export_annotation_csv
from mergedossier_bench.label_studio import EVIDENCE_CATEGORIES, LABEL_VALUES


ROOT = Path(__file__).resolve().parents[1]
LABEL_SET = set(LABEL_VALUES)


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def _display(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def _primary_rows_by_instance(rows: list[dict[str, str]]) -> dict[str, dict[str, str]]:
    primary: dict[str, dict[str, str]] = {}
    for row in rows:
        if str(row.get("is_reliability_repeat", "")).strip().lower() == "true":
            continue
        instance_id = str(row.get("instance_id", "")).strip()
        if instance_id and instance_id not in primary:
            primary[instance_id] = row
    return primary


def _selected_ids(manifest_path: Path | None, rows_by_instance: dict[str, dict[str, str]]) -> list[str]:
    if manifest_path is None:
        return sorted(rows_by_instance)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    values = manifest.get("selected_instance_ids")
    if not isinstance(values, list):
        raise ValueError(f"{manifest_path} does not contain selected_instance_ids")
    return [str(value) for value in values]


def _coerce_to_csv(input_path: Path, out_dir: Path) -> tuple[Path, str]:
    suffix = input_path.suffix.lower()
    out_dir.mkdir(parents=True, exist_ok=True)
    if suffix == ".xlsx":
        csv_path = out_dir / "external_audit_progress_input.csv"
        export_annotation_csv(input_path, csv_path)
        return csv_path, "xlsx_exported_to_csv"
    if suffix == ".csv":
        csv_path = out_dir / "external_audit_progress_input.csv"
        if input_path.resolve() != csv_path.resolve():
            shutil.copy2(input_path, csv_path)
        return csv_path, "csv"
    raise ValueError("External audit progress input must be .xlsx or .csv")


def check_external_audit_progress(
    audit_path: Path,
    out_dir: Path,
    manifest_path: Path | None = None,
) -> dict[str, Any]:
    if not audit_path.exists():
        raise FileNotFoundError(f"External audit file not found: {audit_path}")
    out_dir.mkdir(parents=True, exist_ok=True)
    csv_path, input_kind = _coerce_to_csv(audit_path, out_dir)
    rows_by_instance = _primary_rows_by_instance(_read_csv(csv_path))
    selected = _selected_ids(manifest_path, rows_by_instance)

    missing_rows = [instance_id for instance_id in selected if instance_id not in rows_by_instance]
    blank_cells: list[dict[str, str]] = []
    invalid_cells: list[dict[str, str]] = []
    valid_cells = 0
    complete_rows = 0
    category_counts: dict[str, Counter[str]] = {category: Counter() for category in EVIDENCE_CATEGORIES}

    for instance_id in selected:
        row = rows_by_instance.get(instance_id)
        row_complete = row is not None
        for category in EVIDENCE_CATEGORIES:
            if row is None:
                continue
            label = str(row.get(f"{category}_label", "")).strip()
            if not label:
                blank_cells.append({"instance_id": instance_id, "category": category})
                row_complete = False
            elif label not in LABEL_SET:
                invalid_cells.append({"instance_id": instance_id, "category": category, "label": label})
                row_complete = False
            else:
                valid_cells += 1
                category_counts[category][label] += 1
        if row_complete:
            complete_rows += 1

    total_required_cells = len(selected) * len(EVIDENCE_CATEGORIES)
    completion_rate = round(valid_cells / total_required_cells, 4) if total_required_cells else 0.0
    status = "complete" if not missing_rows and not blank_cells and not invalid_cells else "incomplete"

    by_category = []
    for category in EVIDENCE_CATEGORIES:
        blanks = sum(1 for cell in blank_cells if cell["category"] == category)
        invalid = sum(1 for cell in invalid_cells if cell["category"] == category)
        by_category.append(
            {
                "category": category,
                "valid": sum(category_counts[category].values()),
                "blank": blanks,
                "invalid": invalid,
                "present": category_counts[category]["present"],
                "partially_present": category_counts[category]["partially_present"],
                "missing": category_counts[category]["missing"],
                "not_applicable": category_counts[category]["not_applicable"],
            }
        )

    result = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": status,
        "input_kind": input_kind,
        "input_path": _display(audit_path),
        "csv_used": _display(csv_path),
        "selected_tasks": len(selected),
        "rows_found": len(rows_by_instance),
        "complete_rows": complete_rows,
        "missing_rows": missing_rows,
        "total_required_cells": total_required_cells,
        "valid_label_cells": valid_cells,
        "blank_label_cells": blank_cells,
        "invalid_label_cells": invalid_cells,
        "completion_rate": completion_rate,
        "by_category": by_category,
        "claim_boundary": (
            "Progress report only. Do not cite external agreement until the returned sheet is complete "
            "and check_external_audit_return.py reports status=complete."
        ),
    }
    (out_dir / "external_audit_progress.json").write_text(
        json.dumps(result, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    _write_progress_md(result, out_dir / "external_audit_progress.md")
    _write_feedback_md(result, out_dir / "AUDITOR_FEEDBACK_REQUEST.md")
    return result


def _write_progress_md(result: dict[str, Any], out: Path) -> None:
    lines = [
        "# External Audit Progress",
        "",
        f"Status: **{result['status']}**",
        f"Completion: **{100 * result['completion_rate']:.1f}%**",
        "",
        f"- Selected tasks: {result['selected_tasks']}",
        f"- Rows found: {result['rows_found']}",
        f"- Complete rows: {result['complete_rows']}",
        f"- Required label cells: {result['total_required_cells']}",
        f"- Valid label cells: {result['valid_label_cells']}",
        f"- Blank label cells: {len(result['blank_label_cells'])}",
        f"- Invalid label cells: {len(result['invalid_label_cells'])}",
        f"- Missing rows: {len(result['missing_rows'])}",
        "",
        "## By Category",
        "",
        "| Category | Valid | Blank | Invalid | Present | Partial | Missing | N/A |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in result["by_category"]:
        lines.append(
            f"| {row['category']} | {row['valid']} | {row['blank']} | {row['invalid']} | "
            f"{row['present']} | {row['partially_present']} | {row['missing']} | {row['not_applicable']} |"
        )
    lines.extend(["", "## Boundary", "", str(result["claim_boundary"]), ""])
    out.write_text("\n".join(lines), encoding="utf-8")


def _write_feedback_md(result: dict[str, Any], out: Path) -> None:
    lines = [
        "# Auditor Feedback Request",
        "",
        "Thank you for working on the external audit sheet.",
        "",
    ]
    if result["status"] == "complete":
        lines.extend(
            [
                "The returned sheet appears complete. I will run the formal external-audit analysis next.",
                "",
            ]
        )
    else:
        lines.extend(
            [
                "The sheet is close, but the checker found cells or rows that still need attention.",
                "",
                f"- Completion: {100 * result['completion_rate']:.1f}%",
                f"- Blank label cells: {len(result['blank_label_cells'])}",
                f"- Invalid label cells: {len(result['invalid_label_cells'])}",
                f"- Missing rows: {len(result['missing_rows'])}",
                "",
                "Please fill every `_label` cell with one of:",
                "`present`, `partially_present`, `missing`, or `not_applicable`.",
                "",
            ]
        )
        preview = result["blank_label_cells"][:20]
        if preview:
            lines.extend(["## First Blank Cells", "", "| instance_id | category |", "|---|---|"])
            for cell in preview:
                lines.append(f"| {cell['instance_id']} | {cell['category']} |")
            lines.append("")
        invalid_preview = result["invalid_label_cells"][:20]
        if invalid_preview:
            lines.extend(["## First Invalid Cells", "", "| instance_id | category | value |", "|---|---|---|"])
            for cell in invalid_preview:
                lines.append(f"| {cell['instance_id']} | {cell['category']} | {cell['label']} |")
            lines.append("")
    out.write_text("\n".join(lines), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Report external audit completion progress")
    parser.add_argument("--audit", default="outputs/external_audit_slice_20260617/external_audit_sheet.csv")
    parser.add_argument("--manifest", default="outputs/external_audit_slice_20260617/external_audit_manifest.json")
    parser.add_argument("--out", default="outputs/external_audit_progress_20260617")
    args = parser.parse_args(argv)
    result = check_external_audit_progress(
        ROOT / args.audit,
        ROOT / args.out,
        ROOT / args.manifest if args.manifest else None,
    )
    print(
        "External audit progress: "
        f"{result['status']} ({100 * result['completion_rate']:.1f}% complete)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

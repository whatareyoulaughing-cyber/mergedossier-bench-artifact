"""Validate and analyze a returned external-audit workbook or CSV."""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from analyze_external_audit_slice import analyze_external_audit
from export_annotation_csv_from_workbook import export_annotation_csv


ROOT = Path(__file__).resolve().parents[1]


def _display(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def check_external_audit_return(
    completed_path: Path,
    out_dir: Path,
    primary_csv: Path,
    manifest_path: Path,
) -> dict[str, object]:
    if not completed_path.exists():
        raise FileNotFoundError(f"Completed audit file not found: {completed_path}")
    out_dir.mkdir(parents=True, exist_ok=True)

    suffix = completed_path.suffix.lower()
    if suffix == ".xlsx":
        external_csv = out_dir / "completed_external_audit_sheet.csv"
        export_annotation_csv(completed_path, external_csv)
        input_kind = "xlsx_exported_to_csv"
    elif suffix == ".csv":
        external_csv = out_dir / "completed_external_audit_sheet.csv"
        if completed_path.resolve() != external_csv.resolve():
            shutil.copy2(completed_path, external_csv)
        input_kind = "csv"
    else:
        raise ValueError("Completed audit file must be .xlsx or .csv")

    summary = analyze_external_audit(primary_csv, external_csv, out_dir, manifest_path)
    status = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": summary["status"],
        "input_kind": input_kind,
        "completed_input": _display(completed_path),
        "exported_or_copied_csv": _display(external_csv),
        "analysis_dir": _display(out_dir),
        "selected_tasks": summary["selected_tasks"],
        "blank_label_cells": len(summary["blank_label_cells"]),
        "invalid_label_cells": len(summary["invalid_label_cells"]),
        "missing_external_instances": len(summary["missing_external_instances"]),
        "missing_primary_instances": len(summary["missing_primary_instances"]),
        "claim_boundary": (
            "Only a complete returned external audit can support a secondary external-audit "
            "statement. This helper does not create an inter-rater reliability claim by itself."
        ),
    }
    (out_dir / "external_audit_return_status.json").write_text(
        json.dumps(status, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    _write_markdown(status, out_dir / "external_audit_return_status.md")
    return status


def _write_markdown(status: dict[str, object], out: Path) -> None:
    lines = [
        "# External Audit Return Status",
        "",
        f"- Status: `{status['status']}`",
        f"- Input kind: `{status['input_kind']}`",
        f"- Completed input: `{status['completed_input']}`",
        f"- CSV used for analysis: `{status['exported_or_copied_csv']}`",
        f"- Selected tasks: {status['selected_tasks']}",
        f"- Blank label cells: {status['blank_label_cells']}",
        f"- Invalid label cells: {status['invalid_label_cells']}",
        f"- Missing external instances: {status['missing_external_instances']}",
        f"- Missing primary instances: {status['missing_primary_instances']}",
        "",
    ]
    if status["status"] == "complete":
        lines.extend(
            [
                "The returned audit slice is complete enough to inspect agreement outputs.",
                "Review `external_audit_summary.md` before adding any paper text.",
                "",
            ]
        )
    else:
        lines.extend(
            [
                "The returned audit slice is not complete enough to report external-audit agreement.",
                "Ask the operator to fill every blank/invalid audit-code cell, then rerun this helper.",
                "",
            ]
        )
    lines.extend(["## Claim Boundary", "", str(status["claim_boundary"]), ""])
    out.write_text("\n".join(lines), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate and analyze a returned external audit file")
    parser.add_argument("--completed", required=True, help="Completed external audit .xlsx or .csv")
    parser.add_argument(
        "--primary",
        default="outputs/population_ai_pr_500_20260616/reports/annotation_sheet_completed.csv",
    )
    parser.add_argument(
        "--manifest",
        default="outputs/external_audit_slice_20260617/external_audit_manifest.json",
    )
    parser.add_argument("--out", default="outputs/external_audit_analysis_20260617")
    args = parser.parse_args(argv)
    status = check_external_audit_return(
        ROOT / args.completed,
        ROOT / args.out,
        ROOT / args.primary,
        ROOT / args.manifest,
    )
    print(f"External audit return: {status['status']} -> {args.out}")
    return 0 if status["status"] == "complete" else 2


if __name__ == "__main__":
    raise SystemExit(main())

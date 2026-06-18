"""Run the complete post-annotation pipeline after the workbook is filled."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = Path(__file__).resolve().parent
for path in (ROOT / "src", SCRIPT_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from build_paper_results_from_annotations import build_paper_results
from export_annotation_csv_from_workbook import export_annotation_csv
from mergedossier_bench.label_studio import validate_annotation_csv


DEFAULT_WORKBOOK = ROOT / "outputs" / "real_pilot_mixed_source_annotation_workbook_20260613.xlsx"
DEFAULT_COMPLETED_CSV = ROOT / "outputs" / "real_pilot_mixed_source_annotation_sheet_completed_20260613.csv"
DEFAULT_OUT = ROOT / "outputs" / "real_pilot_mixed_source_annotation_paper_results_20260613"


def write_pipeline_summary(result: dict[str, Any], out_dir: Path) -> None:
    lines = [
        "# Completed Annotation Pipeline",
        "",
        f"Status: **{result['status']}**",
        "",
        f"- Workbook: `{result['workbook']}`",
        f"- Completed CSV: `{result['completed_csv']}`",
        f"- Results directory: `{result['out_dir']}`",
    ]
    if result.get("summary"):
        summary = result["summary"]
        lines.extend(
            [
                "",
                "## Annotation Summary",
                "",
                f"- Total tasks: {summary['total_tasks']}",
                f"- Total annotations: {summary['total_annotations']}",
                f"- Annotator count: {summary['annotator_count']}",
                f"- Reliability repeat annotations: {summary['reliability_repeat_annotations']}",
            ]
        )
    if result.get("next_action"):
        lines.extend(["", "## Next Action", "", str(result["next_action"])])
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "post_annotation_pipeline_summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    (out_dir / "post_annotation_pipeline_summary.json").write_text(
        json.dumps(result, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def run_pipeline(
    workbook: str | Path,
    completed_csv: str | Path,
    out_dir: str | Path,
    skip_export: bool = False,
    sheet_name: str = "Annotation",
) -> dict[str, Any]:
    workbook_path = Path(workbook)
    completed_csv_path = Path(completed_csv)
    output_path = Path(out_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    if not skip_export:
        export_annotation_csv(workbook_path, completed_csv_path, sheet_name=sheet_name)
    elif not completed_csv_path.exists():
        raise FileNotFoundError(f"Completed CSV does not exist: {completed_csv_path}")

    validation = validate_annotation_csv(completed_csv_path, require_complete=True)
    (output_path / "completed_annotation_csv_validation.json").write_text(
        json.dumps(validation, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    result: dict[str, Any] = {
        "status": "invalid_annotations" if not validation["valid"] else "pass",
        "workbook": str(workbook_path),
        "completed_csv": str(completed_csv_path),
        "out_dir": str(output_path),
        "validation_errors": validation["errors"],
        "validation_warnings": validation["warnings"],
        "summary": None,
        "next_action": None,
    }
    if not validation["valid"]:
        result["next_action"] = "Return to the workbook and fill every required *_label cell with an allowed label."
        write_pipeline_summary(result, output_path)
        return result

    summary = build_paper_results(completed_csv_path, output_path)
    result["summary"] = {
        "total_tasks": summary["total_tasks"],
        "total_annotations": summary["total_annotations"],
        "annotator_count": summary["annotator_count"],
        "reliability_repeat_annotations": summary["reliability_repeat_annotations"],
    }
    result["next_action"] = "Review adjudication_sheet.csv, then update the paper results section from the generated .tex tables."
    write_pipeline_summary(result, output_path)
    return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run completed annotation post-processing")
    parser.add_argument("--workbook", default=str(DEFAULT_WORKBOOK), help="Filled annotation workbook")
    parser.add_argument("--completed-csv", default=str(DEFAULT_COMPLETED_CSV), help="Completed CSV to write/read")
    parser.add_argument("--out", default=str(DEFAULT_OUT), help="Output directory for paper result artifacts")
    parser.add_argument("--sheet", default="Annotation", help="Workbook sheet to export")
    parser.add_argument("--skip-export", action="store_true", help="Use an existing completed CSV instead of exporting workbook")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    result = run_pipeline(
        args.workbook,
        args.completed_csv,
        args.out,
        skip_export=args.skip_export,
        sheet_name=args.sheet,
    )
    print(f"Completed annotation pipeline: {result['status']} -> {args.out}")
    return 0 if result["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())

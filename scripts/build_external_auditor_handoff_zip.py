"""Build a sendable package for a second-operator external audit slice.

This package is smaller than the anonymous-review artifact. It is meant to be
sent to an external operator who will code the 50-task audit slice. It excludes
the primary completed annotation CSV so the external operator can work
independently.
"""

from __future__ import annotations

import argparse
import json
import zipfile
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SLICE_DIR = ROOT / "outputs" / "external_audit_slice_20260617"
DEFAULT_ANALYSIS_DIR = ROOT / "outputs" / "external_audit_analysis_20260617"

HANDOFF_FILES = [
    "external_audit_sheet.xlsx",
    "external_audit_sheet.csv",
    "external_audit_manifest.json",
    "README_external_audit.md",
]


def _write_operator_note(out_dir: Path) -> Path:
    path = out_dir / "OPERATOR_QUICKSTART.md"
    lines = [
        "# External Audit Quickstart",
        "",
        "Thank you for helping with a 50-task external audit slice for MergeDossier-Bench.",
        "",
        "## What To Do",
        "",
        "1. Open `external_audit_sheet.xlsx`.",
        "2. Use the `Annotation` sheet.",
        "3. Fill every column ending in `_label` using only the dropdown values:",
        "   `present`, `partially_present`, `missing`, or `not_applicable`.",
        "4. Add short comments where the evidence is ambiguous or difficult to judge.",
        "5. Do not inspect the primary completed audit sheet or paper results while coding.",
        "6. Save the completed workbook and send it back.",
        "",
        "## Coding Boundary",
        "",
        "Code visible review-evidence availability only. Do not judge whether the patch is correct,",
        "whether it should be merged, whether reviewers would prefer it, or whether AI-authored PRs",
        "are better or worse than human-authored PRs.",
        "",
        "## Return Format",
        "",
        "Preferred: return the completed `external_audit_sheet.xlsx`.",
        "Optional: also export the `Annotation` sheet as CSV.",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def _write_return_note(out_dir: Path) -> Path:
    path = out_dir / "RETURN_INSTRUCTIONS_FOR_AUTHOR.md"
    lines = [
        "# Return Instructions For Author",
        "",
        "After receiving the completed external-audit workbook:",
        "",
        "Preferred one-command check:",
        "",
        "```bash",
        "python scripts/check_external_audit_progress.py \\",
        "  --audit <completed_external_audit_sheet.xlsx> \\",
        "  --out outputs/external_audit_progress_20260617",
        "",
        "python scripts/check_external_audit_return.py \\",
        "  --completed <completed_external_audit_sheet.xlsx> \\",
        "  --out outputs/external_audit_analysis_20260617",
        "```",
        "",
        "The progress helper writes a completion report and a sendable feedback note",
        "if cells still need attention. The return helper accepts either `.xlsx`",
        "or `.csv`, exports the workbook if needed, runs the external-audit",
        "analysis, and writes `external_audit_return_status.md`.",
        "",
        "Manual fallback:",
        "",
        "1. Export the `Annotation` sheet to CSV:",
        "",
        "```bash",
        "python scripts/export_annotation_csv_from_workbook.py \\",
        "  --workbook <completed_external_audit_sheet.xlsx> \\",
        "  --out outputs/external_audit_analysis_20260617/completed_external_audit_sheet.csv",
        "```",
        "",
        "2. Analyze the completed slice:",
        "",
        "```bash",
        "python scripts/analyze_external_audit_slice.py \\",
        "  --primary outputs/population_ai_pr_500_20260616/reports/annotation_sheet_completed.csv \\",
        "  --external outputs/external_audit_analysis_20260617/completed_external_audit_sheet.csv \\",
        "  --manifest outputs/external_audit_slice_20260617/external_audit_manifest.json \\",
        "  --out outputs/external_audit_analysis_20260617",
        "```",
        "",
        "Only cite the external-audit result if `external_audit_summary.json` reports",
        "`status: complete`.",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def _write_email_template(out_dir: Path) -> Path:
    path = out_dir / "EMAIL_TEMPLATE_TO_EXTERNAL_AUDITOR.md"
    lines = [
        "# Email Template",
        "",
        "Subject: 50-task external audit slice for an ICSE paper",
        "",
        "Hi <name>,",
        "",
        "Could you help independently code a 50-task audit slice for my ICSE paper artifact?",
        "The task is to inspect the provided dossier text and mark visible review-evidence",
        "availability using dropdown labels in the attached workbook.",
        "",
        "Please do not judge whether the code is correct or mergeable. The only question is",
        "whether the visible PR evidence is present, partially present, missing, or not applicable",
        "for each evidence family.",
        "",
        "The workbook has an `Instructions` sheet and a completion check. When done, please send",
        "back the completed workbook. If a category is ambiguous, a short comment is enough.",
        "",
        "Thank you!",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def build_external_auditor_handoff_zip(
    slice_dir: Path,
    out_path: Path,
    staging_dir: Path | None = None,
) -> dict[str, object]:
    if staging_dir is None:
        staging_dir = out_path.parent / "handoff_files"
    staging_dir.mkdir(parents=True, exist_ok=True)

    generated_files = [
        _write_operator_note(staging_dir),
        _write_return_note(staging_dir),
        _write_email_template(staging_dir),
    ]
    source_files: list[Path] = []
    missing: list[str] = []
    for name in HANDOFF_FILES:
        path = slice_dir / name
        if path.exists():
            source_files.append(path)
        else:
            missing.append(name)
    if missing:
        raise FileNotFoundError(f"External audit slice is missing required handoff files: {missing}")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    package_root = f"MergeDossier-external-audit-handoff-{datetime.now(timezone.utc).strftime('%Y%m%d')}"
    manifest_rows = []
    with zipfile.ZipFile(out_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
        for path in source_files:
            arcname = f"{package_root}/{path.name}"
            zf.write(path, arcname)
            manifest_rows.append({"path": path.name, "bytes": path.stat().st_size})
        for path in generated_files:
            arcname = f"{package_root}/{path.name}"
            zf.write(path, arcname)
            manifest_rows.append({"path": path.name, "bytes": path.stat().st_size})

        manifest = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "package_root": package_root,
            "file_count": len(manifest_rows) + 1,
            "claim_boundary": (
                "Second-operator handoff packet only. Completion of this packet is required before "
                "reporting any external-audit agreement."
            ),
            "excludes": [
                "primary completed annotation CSV",
                "paper result tables",
                "population estimates",
            ],
            "files": manifest_rows,
        }
        zf.writestr(f"{package_root}/HANDOFF_MANIFEST.json", json.dumps(manifest, indent=2) + "\n")

    summary = {
        "zip_path": str(out_path),
        "package_root": package_root,
        "file_count": len(manifest_rows) + 1,
        "zip_bytes": out_path.stat().st_size,
    }
    (out_path.parent / "external_auditor_handoff_summary.json").write_text(
        json.dumps(summary, indent=2) + "\n", encoding="utf-8"
    )
    return summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build sendable external-auditor handoff zip")
    parser.add_argument("--slice-dir", default=str(DEFAULT_SLICE_DIR))
    parser.add_argument("--out", default="outputs/external_audit_handoff_20260617/MergeDossier-external-audit-handoff.zip")
    args = parser.parse_args(argv)
    summary = build_external_auditor_handoff_zip(Path(args.slice_dir), ROOT / args.out)
    print(f"External auditor handoff zip written: {args.out} ({summary['file_count']} files)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

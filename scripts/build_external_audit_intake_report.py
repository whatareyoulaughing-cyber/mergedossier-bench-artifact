"""Scan candidate files for a completed MergeDossier external-audit return."""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from check_external_audit_progress import check_external_audit_progress


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = ROOT / "outputs/external_audit_slice_20260617/external_audit_manifest.json"


def _display(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def _safe_name(path: Path) -> str:
    stem = re.sub(r"[^A-Za-z0-9_.-]+", "_", path.stem).strip("_")[:80]
    return f"{stem}{path.suffix.lower()}".strip(".") or "candidate"


def _candidate_paths(search_dirs: list[Path], explicit_candidates: list[Path]) -> list[Path]:
    candidates: list[Path] = []
    for path in explicit_candidates:
        if path.exists() and path.suffix.lower() in {".csv", ".xlsx"}:
            candidates.append(path)
    name_pattern = re.compile(r"(external|audit|completed|annotation)", re.I)
    for directory in search_dirs:
        if not directory.exists():
            continue
        for suffix in ("*.csv", "*.xlsx"):
            for path in directory.rglob(suffix):
                if path.is_file() and name_pattern.search(path.name):
                    candidates.append(path)
    unique: dict[str, Path] = {}
    for path in candidates:
        unique[str(path.resolve()).lower()] = path
    return sorted(unique.values(), key=lambda p: (str(p.parent), p.name.lower()))


def _external_return_decision(path: Path, progress: dict[str, Any]) -> tuple[str, list[str]]:
    warnings: list[str] = []
    selected = int(progress.get("selected_tasks") or 0)
    rows_found = int(progress.get("rows_found") or 0)
    name = path.name.lower()
    if name in {"annotation_sheet_completed_annotation.csv", "annotation_sheet_completed.csv"}:
        warnings.append("filename resembles a primary/completed annotation sheet, not an external return")
    if selected and rows_found > selected * 2:
        warnings.append(
            f"rows_found={rows_found} is much larger than selected_tasks={selected}; expected a 50-task external return"
        )
    if "population_ai_pr_500_20260616" in path.as_posix():
        warnings.append("path resembles the primary population annotation output")
    if progress.get("status") != "complete":
        return "not_complete", warnings
    if warnings:
        return "complete_but_independence_unverified", warnings
    return "ready_for_formal_external_audit_analysis", warnings


def build_external_audit_intake_report(
    *,
    search_dirs: list[Path],
    explicit_candidates: list[Path],
    manifest_path: Path,
    out_dir: Path,
) -> dict[str, Any]:
    out_dir.mkdir(parents=True, exist_ok=True)
    probes_dir = out_dir / "probes"
    probes_dir.mkdir(exist_ok=True)

    candidate_reports: list[dict[str, Any]] = []
    for index, path in enumerate(_candidate_paths(search_dirs, explicit_candidates), start=1):
        probe_dir = probes_dir / f"{index:03d}_{_safe_name(path)}"
        try:
            progress = check_external_audit_progress(path, probe_dir, manifest_path)
            decision, warnings = _external_return_decision(path, progress)
            candidate_reports.append(
                {
                    "path": _display(path),
                    "status": progress["status"],
                    "intake_decision": decision,
                    "warnings": warnings,
                    "completion_rate": progress["completion_rate"],
                    "selected_tasks": progress["selected_tasks"],
                    "rows_found": progress["rows_found"],
                    "complete_rows": progress["complete_rows"],
                    "valid_label_cells": progress["valid_label_cells"],
                    "blank_label_cells": len(progress["blank_label_cells"]),
                    "invalid_label_cells": len(progress["invalid_label_cells"]),
                    "missing_rows": len(progress["missing_rows"]),
                    "probe_dir": _display(probe_dir),
                }
            )
        except Exception as exc:  # noqa: BLE001 - intake reports should not stop at the first bad file.
            candidate_reports.append(
                {
                    "path": _display(path),
                    "status": "probe_error",
                    "intake_decision": "probe_error",
                    "warnings": [f"{type(exc).__name__}: {exc}"],
                    "error": f"{type(exc).__name__}: {exc}",
                    "probe_dir": _display(probe_dir),
                }
            )

    complete = [row for row in candidate_reports if row.get("status") == "complete"]
    ready = [
        row
        for row in candidate_reports
        if row.get("intake_decision") == "ready_for_formal_external_audit_analysis"
    ]
    ranked = sorted(
        candidate_reports,
        key=lambda row: (
            row.get("status") == "complete",
            float(row.get("completion_rate") or 0.0),
            int(row.get("valid_label_cells") or 0),
        ),
        reverse=True,
    )
    best = ranked[0] if ranked else None
    result = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": "ready_external_return_found"
        if ready
        else ("complete_but_unverified_candidate_found" if complete else "no_complete_candidate_found"),
        "candidate_count": len(candidate_reports),
        "complete_candidate_count": len(complete),
        "ready_external_return_count": len(ready),
        "best_candidate": best,
        "candidates": candidate_reports,
        "next_action": (
            "Run scripts/check_external_audit_return.py on the ready candidate before citing external-audit results."
            if ready
            else (
                "A complete-looking file was found, but it is not safe to treat as an independent external return without confirming provenance."
                if complete
                else "No complete MergeDossier external-audit return was found. Send the handoff zip or ask the operator to finish all audit-code cells."
            )
        ),
        "claim_boundary": (
            "Intake scan only. It does not establish external agreement or inter-rater reliability."
        ),
    }
    (out_dir / "external_audit_intake_report.json").write_text(
        json.dumps(result, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    _write_markdown(result, out_dir / "external_audit_intake_report.md")
    return result


def _write_markdown(result: dict[str, Any], out: Path) -> None:
    lines = [
        "# External Audit Intake Report",
        "",
        f"Status: **{result['status']}**",
        "",
        f"- Candidate files scanned: {result['candidate_count']}",
        f"- Complete candidates: {result['complete_candidate_count']}",
        f"- Ready external-return candidates: {result['ready_external_return_count']}",
        f"- Next action: {result['next_action']}",
        "",
        "## Best Candidate",
        "",
    ]
    best = result.get("best_candidate")
    if best:
        lines.extend(
            [
                f"- Path: `{best.get('path')}`",
                f"- Status: `{best.get('status')}`",
                f"- Intake decision: `{best.get('intake_decision')}`",
                f"- Completion: `{100 * float(best.get('completion_rate') or 0.0):.1f}%`",
                f"- Valid cells: `{best.get('valid_label_cells', 'n/a')}`",
                f"- Blank cells: `{best.get('blank_label_cells', 'n/a')}`",
                f"- Invalid cells: `{best.get('invalid_label_cells', 'n/a')}`",
                f"- Missing rows: `{best.get('missing_rows', 'n/a')}`",
                f"- Warnings: `{'; '.join(best.get('warnings') or []) or 'none'}`",
                "",
            ]
        )
    else:
        lines.extend(["No candidate files were found.", ""])
    lines.extend(
        [
            "## Candidates",
            "",
            "| File | Status | Decision | Completion | Valid | Blank | Invalid | Missing Rows |",
            "|---|---:|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for row in result["candidates"]:
        lines.append(
            "| {path} | {status} | {decision} | {completion:.1f}% | {valid} | {blank} | {invalid} | {missing} |".format(
                path=row.get("path"),
                status=row.get("status"),
                decision=row.get("intake_decision"),
                completion=100 * float(row.get("completion_rate") or 0.0),
                valid=row.get("valid_label_cells", ""),
                blank=row.get("blank_label_cells", ""),
                invalid=row.get("invalid_label_cells", ""),
                missing=row.get("missing_rows", ""),
            )
        )
    lines.extend(["", "## Boundary", "", str(result["claim_boundary"]), ""])
    out.write_text("\n".join(lines), encoding="utf-8")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Scan candidate external-audit return files")
    parser.add_argument(
        "--search-dir",
        action="append",
        default=[],
        help="Directory to scan recursively for candidate .csv/.xlsx files. Can be repeated.",
    )
    parser.add_argument(
        "--candidate",
        action="append",
        default=[],
        help="Explicit candidate .csv/.xlsx file to probe. Can be repeated.",
    )
    parser.add_argument("--manifest", default=str(DEFAULT_MANIFEST))
    parser.add_argument("--out", default="outputs/external_audit_intake_20260617")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    default_downloads = Path.home() / "Downloads"
    search_dirs = [Path(value) for value in args.search_dir] or [
        default_downloads,
        ROOT / "outputs/external_audit_slice_20260617",
        ROOT / "outputs/external_audit_handoff_20260617",
    ]
    result = build_external_audit_intake_report(
        search_dirs=search_dirs,
        explicit_candidates=[Path(value) for value in args.candidate],
        manifest_path=Path(args.manifest),
        out_dir=ROOT / args.out,
    )
    print(
        "External audit intake: "
        f"{result['status']} ({result['complete_candidate_count']}/{result['candidate_count']} complete)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

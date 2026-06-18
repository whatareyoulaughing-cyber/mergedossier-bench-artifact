"""Check, merge, and analyze parallel external-audit returns."""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from check_external_audit_progress import check_external_audit_progress
from check_external_audit_return import check_external_audit_return


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PACKET_DIR = ROOT / "outputs" / "external_audit_parallel_packets_20260618"


def _load_parallel_merge() -> Any:
    script_path = ROOT / "scripts" / "build_external_audit_parallel_packets.py"
    spec = importlib.util.spec_from_file_location("build_external_audit_parallel_packets", script_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load parallel packet helper: {script_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.merge_completed_partials


def _display(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def check_parallel_returns(
    part_paths: list[Path],
    packet_dir: Path,
    out_dir: Path,
    *,
    primary_csv: Path,
    full_manifest: Path,
) -> dict[str, Any]:
    if len(part_paths) < 2:
        raise ValueError("At least two partial return files are required")
    out_dir.mkdir(parents=True, exist_ok=True)

    part_results = []
    for index, part_path in enumerate(part_paths, start=1):
        part_id = f"part_{index:02d}"
        manifest_path = packet_dir / part_id / "external_audit_manifest.json"
        if not manifest_path.exists():
            raise FileNotFoundError(f"Missing manifest for {part_id}: {manifest_path}")
        progress = check_external_audit_progress(
            part_path,
            out_dir / part_id,
            manifest_path,
        )
        part_results.append(
            {
                "part_id": part_id,
                "input": _display(part_path),
                "manifest": _display(manifest_path),
                "status": progress["status"],
                "completion_rate": progress["completion_rate"],
                "selected_tasks": progress["selected_tasks"],
                "blank_label_cells": len(progress["blank_label_cells"]),
                "invalid_label_cells": len(progress["invalid_label_cells"]),
                "missing_rows": len(progress["missing_rows"]),
                "feedback": _display(out_dir / part_id / "AUDITOR_FEEDBACK_REQUEST.md"),
            }
        )

    all_complete = all(result["status"] == "complete" for result in part_results)
    merged_csv = out_dir / "merged_external_audit_sheet.csv"
    return_status: dict[str, Any] | None = None
    if all_complete:
        merge_completed_partials = _load_parallel_merge()
        merge_completed_partials(part_paths, merged_csv)
        return_status = check_external_audit_return(
            merged_csv,
            out_dir / "formal_return_gate",
            primary_csv,
            full_manifest,
        )

    result = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": "complete" if all_complete and return_status and return_status["status"] == "complete" else "incomplete",
        "all_parts_complete": all_complete,
        "part_results": part_results,
        "merged_csv": _display(merged_csv) if merged_csv.exists() else None,
        "formal_return_gate": _display(out_dir / "formal_return_gate") if return_status else None,
        "formal_return_status": return_status["status"] if return_status else None,
        "claim_boundary": (
            "Parallel return gate only. A complete result supports a bounded external-audit "
            "slice statement, not inter-rater reliability."
        ),
    }
    (out_dir / "parallel_return_status.json").write_text(
        json.dumps(result, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    _write_markdown(result, out_dir / "parallel_return_status.md")
    return result


def _write_markdown(result: dict[str, Any], out: Path) -> None:
    lines = [
        "# Parallel External Audit Return Status",
        "",
        f"Overall status: **{result['status']}**",
        "",
        "| Part | Status | Completion | Blank | Invalid | Missing rows | Feedback |",
        "|---|---:|---:|---:|---:|---:|---|",
    ]
    for row in result["part_results"]:
        lines.append(
            f"| {row['part_id']} | {row['status']} | {100 * row['completion_rate']:.1f}% | "
            f"{row['blank_label_cells']} | {row['invalid_label_cells']} | {row['missing_rows']} | "
            f"`{row['feedback']}` |"
        )
    if result["status"] == "complete":
        lines.extend(
            [
                "",
                f"Merged CSV: `{result['merged_csv']}`",
                f"Formal return gate: `{result['formal_return_gate']}`",
                "",
            ]
        )
    else:
        lines.extend(
            [
                "",
                "At least one packet is incomplete. Send the corresponding feedback file back to the operator.",
                "",
            ]
        )
    lines.extend(["## Boundary", "", str(result["claim_boundary"]), ""])
    out.write_text("\n".join(lines), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Check and merge parallel external-audit returns")
    parser.add_argument("--part", action="append", required=True, help="Returned part CSV/XLSX. Pass once per part.")
    parser.add_argument("--packet-dir", default=str(DEFAULT_PACKET_DIR))
    parser.add_argument("--out", default="outputs/external_audit_parallel_return_gate_20260618")
    parser.add_argument(
        "--primary",
        default="outputs/population_ai_pr_500_20260616/reports/annotation_sheet_completed.csv",
    )
    parser.add_argument(
        "--manifest",
        default="outputs/external_audit_slice_20260617/external_audit_manifest.json",
    )
    args = parser.parse_args(argv)
    result = check_parallel_returns(
        [ROOT / value for value in args.part],
        ROOT / args.packet_dir,
        ROOT / args.out,
        primary_csv=ROOT / args.primary,
        full_manifest=ROOT / args.manifest,
    )
    print(f"Parallel external audit return: {result['status']} -> {args.out}")
    return 0 if result["status"] == "complete" else 2


if __name__ == "__main__":
    raise SystemExit(main())


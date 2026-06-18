"""Build and merge parallel external-audit handoff packets.

The main external audit remains the deterministic 50-task slice. This helper
only lowers execution friction by splitting that slice into smaller packets
that can be coded by multiple independent operators, then merged back into one
CSV for the existing return gate.
"""

from __future__ import annotations

import argparse
import csv
import importlib.util
import json
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SLICE_DIR = ROOT / "outputs" / "external_audit_slice_20260617"
DEFAULT_OUT = ROOT / "outputs" / "external_audit_parallel_packets_20260618"


def _display(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def _read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        headers = list(reader.fieldnames or [])
        rows = [dict(row) for row in reader]
    if not headers:
        raise ValueError(f"CSV has no headers: {path}")
    return headers, rows


def _write_csv(path: Path, headers: list[str], rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=headers)
        writer.writeheader()
        writer.writerows([{header: row.get(header, "") for header in headers} for row in rows])


def _instance_id(row: dict[str, str]) -> str:
    return str(row.get("instance_id", "")).strip()


def _load_workbook_builder() -> Any:
    script_path = ROOT / "scripts" / "export_annotation_workbook.py"
    spec = importlib.util.spec_from_file_location("export_annotation_workbook", script_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load workbook exporter: {script_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.build_workbook


def _maybe_build_workbook(csv_path: Path, workbook_path: Path) -> str:
    try:
        build_workbook = _load_workbook_builder()
        build_workbook(csv_path, workbook_path)
        return "created"
    except (ModuleNotFoundError, SystemExit) as exc:
        return f"skipped: {exc}"


def _chunks(rows: list[dict[str, str]], parts: int) -> list[list[dict[str, str]]]:
    if parts < 1:
        raise ValueError("parts must be >= 1")
    if parts > len(rows):
        raise ValueError(f"parts={parts} exceeds row count={len(rows)}")
    chunks: list[list[dict[str, str]]] = [[] for _ in range(parts)]
    for index, row in enumerate(rows):
        chunks[index % parts].append(row)
    return chunks


def _write_part_readme(path: Path, *, part_id: str, rows: int, total_parts: int) -> None:
    lines = [
        f"# External Audit Packet {part_id}",
        "",
        f"This packet is one of {total_parts} parallel packets from the same 50-task external audit slice.",
        "",
        "## What To Do",
        "",
        "1. Open `external_audit_sheet.xlsx` if available, otherwise use `external_audit_sheet.csv`.",
        "2. Fill every column ending in `_label` using only:",
        "   `present`, `partially_present`, `missing`, or `not_applicable`.",
        "3. Add short comments only when a case is ambiguous.",
        "4. Return the completed workbook or CSV for this packet only.",
        "",
        "## Boundary",
        "",
        "Code visible review-evidence availability only. Do not judge patch correctness,",
        "mergeability, reviewer utility, AI-vs-human effects, or all-GitHub rates.",
        "",
        f"Rows in this packet: {rows}.",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


def _zip_dir(source_dir: Path, out_zip: Path) -> None:
    out_zip.parent.mkdir(parents=True, exist_ok=True)
    if out_zip.exists():
        out_zip.unlink()
    package_root = source_dir.name
    with zipfile.ZipFile(out_zip, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
        for path in sorted(source_dir.rglob("*")):
            if path.is_file():
                zf.write(path, f"{package_root}/{path.relative_to(source_dir).as_posix()}")


def build_parallel_packets(
    slice_dir: Path,
    out_dir: Path,
    parts: int = 2,
    make_workbook: bool = True,
) -> dict[str, Any]:
    csv_path = slice_dir / "external_audit_sheet.csv"
    manifest_path = slice_dir / "external_audit_manifest.json"
    if not csv_path.exists():
        raise FileNotFoundError(f"Missing external audit sheet: {csv_path}")
    if not manifest_path.exists():
        raise FileNotFoundError(f"Missing external audit manifest: {manifest_path}")

    headers, rows = _read_csv(csv_path)
    row_chunks = _chunks(rows, parts)
    source_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    out_dir.mkdir(parents=True, exist_ok=True)
    packet_rows = []

    for index, chunk in enumerate(row_chunks, start=1):
        part_id = f"part_{index:02d}"
        part_dir = out_dir / part_id
        part_dir.mkdir(parents=True, exist_ok=True)
        part_csv = part_dir / "external_audit_sheet.csv"
        _write_csv(part_csv, headers, chunk)
        workbook_status = "not_requested"
        if make_workbook:
            workbook_status = _maybe_build_workbook(part_csv, part_dir / "external_audit_sheet.xlsx")
        ids = [_instance_id(row) for row in chunk]
        part_manifest = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "part_id": part_id,
            "part_index": index,
            "total_parts": parts,
            "rows": len(chunk),
            "selected_instance_ids": ids,
            "source_slice_manifest": _display(manifest_path),
            "workbook_status": workbook_status,
            "claim_boundary": (
                "Parallel handoff packet only. Merge all completed packets and run "
                "check_external_audit_return.py before citing any external-audit result."
            ),
        }
        (part_dir / "external_audit_manifest.json").write_text(
            json.dumps(part_manifest, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        _write_part_readme(part_dir / "README_EXTERNAL_AUDIT_PART.md", part_id=part_id, rows=len(chunk), total_parts=parts)
        zip_path = out_dir / f"MergeDossier-external-audit-{part_id}.zip"
        _zip_dir(part_dir, zip_path)
        packet_rows.append(
            {
                "part_id": part_id,
                "rows": len(chunk),
                "instance_ids": ids,
                "dir": _display(part_dir),
                "zip": _display(zip_path),
                "workbook_status": workbook_status,
            }
        )

    summary = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_slice_dir": _display(slice_dir),
        "source_selected_tasks": source_manifest.get("selected_tasks", len(rows)),
        "parts": parts,
        "rows": len(rows),
        "packets": packet_rows,
        "merge_command": (
            "python scripts/build_external_audit_parallel_packets.py merge "
            "--partials <completed_part_01.csv-or-xlsx> <completed_part_02.csv-or-xlsx> "
            "--out outputs/external_audit_parallel_packets_20260618/merged_external_audit_sheet.csv"
        ),
        "return_gate_command": (
            "python scripts/check_external_audit_return.py "
            "--completed outputs/external_audit_parallel_packets_20260618/merged_external_audit_sheet.csv "
            "--out outputs/external_audit_analysis_20260618"
        ),
    }
    (out_dir / "parallel_packet_manifest.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    _write_parallel_readme(out_dir / "README_PARALLEL_EXTERNAL_AUDIT.md", summary)
    return summary


def _write_parallel_readme(path: Path, summary: dict[str, Any]) -> None:
    lines = [
        "# Parallel External Audit Packets",
        "",
        "These packets split the existing 50-task external audit slice into smaller independent packets.",
        "They do not change the study design or create an inter-rater-reliability claim.",
        "",
        "## Send",
        "",
    ]
    for packet in summary["packets"]:
        lines.append(f"- `{packet['zip']}`: {packet['rows']} rows")
    lines.extend(
        [
            "",
            "Ask each operator to return only their completed workbook or CSV.",
            "",
            "## Merge Returns",
            "",
            "After all parts return, merge them:",
            "",
            "```powershell",
            summary["merge_command"],
            "```",
            "",
            "Then run the existing return gate:",
            "",
            "```powershell",
            summary["return_gate_command"],
            "```",
            "",
            "Only a complete merged return may support a bounded external-audit statement.",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def _export_if_workbook(path: Path, tmp_dir: Path) -> Path:
    if path.suffix.lower() != ".xlsx":
        return path
    script_path = ROOT / "scripts" / "export_annotation_csv_from_workbook.py"
    spec = importlib.util.spec_from_file_location("export_annotation_csv_from_workbook", script_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load workbook CSV exporter: {script_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    out = tmp_dir / f"{path.stem}.csv"
    module.export_annotation_csv(path, out)
    return out


def merge_completed_partials(partials: list[Path], out_csv: Path) -> dict[str, Any]:
    if not partials:
        raise ValueError("At least one partial CSV/XLSX is required")
    tmp_dir = out_csv.parent / "_partial_exports"
    tmp_dir.mkdir(parents=True, exist_ok=True)
    headers: list[str] | None = None
    merged_rows: list[dict[str, str]] = []
    seen: set[str] = set()
    duplicates: list[str] = []
    for partial in partials:
        csv_path = _export_if_workbook(partial, tmp_dir)
        part_headers, rows = _read_csv(csv_path)
        if headers is None:
            headers = part_headers
        elif headers != part_headers:
            raise ValueError(f"Header mismatch in {partial}")
        for row in rows:
            instance_id = _instance_id(row)
            if instance_id in seen:
                duplicates.append(instance_id)
            seen.add(instance_id)
            merged_rows.append(row)
    if duplicates:
        raise ValueError(f"Duplicate instance_id values in partial returns: {duplicates[:10]}")
    assert headers is not None
    merged_rows.sort(key=_instance_id)
    _write_csv(out_csv, headers, merged_rows)
    summary = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "partials": [_display(path) for path in partials],
        "merged_csv": _display(out_csv),
        "rows": len(merged_rows),
        "unique_instance_ids": len(seen),
        "claim_boundary": "Merged partial returns still require check_external_audit_return.py before any reporting.",
    }
    (out_csv.parent / "merged_external_audit_manifest.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build or merge parallel external-audit packets")
    subparsers = parser.add_subparsers(dest="command")

    build = subparsers.add_parser("build", help="Split the current external audit slice")
    build.add_argument("--slice-dir", default=str(DEFAULT_SLICE_DIR))
    build.add_argument("--out", default=str(DEFAULT_OUT))
    build.add_argument("--parts", type=int, default=2)
    build.add_argument("--no-workbook", action="store_true")

    merge = subparsers.add_parser("merge", help="Merge completed partial CSV/XLSX returns")
    merge.add_argument("--partials", nargs="+", required=True)
    merge.add_argument("--out", required=True)

    args = parser.parse_args(argv)
    if args.command == "merge":
        summary = merge_completed_partials([ROOT / item for item in args.partials], ROOT / args.out)
        print(f"Merged external audit partials: {summary['rows']} rows -> {args.out}")
        return 0

    if args.command in {None, "build"}:
        summary = build_parallel_packets(
            ROOT / getattr(args, "slice_dir", str(DEFAULT_SLICE_DIR)),
            ROOT / getattr(args, "out", str(DEFAULT_OUT)),
            parts=getattr(args, "parts", 2),
            make_workbook=not getattr(args, "no_workbook", False),
        )
        print(f"Parallel external audit packets: {summary['parts']} parts, {summary['rows']} rows")
        return 0

    parser.error("unknown command")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())


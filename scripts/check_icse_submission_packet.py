"""Validate the local ICSE submission packet before upload."""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import json
import re
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def _add(failures: list[dict[str, Any]], name: str, message: str, path: Path | None = None) -> None:
    failures.append(
        {
            "name": name,
            "message": message,
            "path": _rel(path) if path is not None else None,
        }
    )


def _parse_checksum(text: str) -> str | None:
    parts = text.split()
    if parts and re.fullmatch(r"[0-9a-fA-F]{64}", parts[0]):
        return parts[0].lower()
    return None


def _resolve_manifest_path(raw_path: str) -> Path:
    path = Path(raw_path)
    return path if path.is_absolute() else ROOT / path


def check_icse_submission_packet(packet_dir: Path, out_dir: Path | None = None) -> dict[str, Any]:
    if not packet_dir.is_absolute():
        packet_dir = ROOT / packet_dir
    status_path = packet_dir / "submission_packet_status.json"
    manifest_path = packet_dir / "submission_file_manifest.csv"
    portal_path = packet_dir / "PORTAL_FIELDS.md"
    checklist_path = packet_dir / "ICSE_SUBMISSION_CHECKLIST_ZH.md"
    status = _read_json(status_path)
    failures: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []

    if status.get("status") not in {"ready_except_external_actions", "submission_ready_local"}:
        _add(failures, "status", f"Unexpected packet status: {status.get('status')}", status_path)

    manifest_rows: list[dict[str, str]] = []
    if manifest_path.exists():
        with manifest_path.open(newline="", encoding="utf-8") as handle:
            manifest_rows = list(csv.DictReader(handle))
    else:
        _add(failures, "manifest_missing", "Missing submission_file_manifest.csv", manifest_path)

    required_roles = {"anonymous_pdf_submission", "anonymous_artifact_archive", "artifact_checksum"}
    present_roles = {row.get("role", "") for row in manifest_rows}
    for role in sorted(required_roles - present_roles):
        _add(failures, "required_role_missing", f"Missing role {role}", manifest_path)

    for row in manifest_rows:
        packet_path = _resolve_manifest_path(str(row.get("packet_path", "")))
        source_path = _resolve_manifest_path(str(row.get("source", "")))
        expected_bytes = int(row.get("bytes") or -1)
        if not packet_path.exists():
            _add(failures, "packet_file_missing", "Packet file is missing", packet_path)
            continue
        actual_bytes = packet_path.stat().st_size
        if expected_bytes != actual_bytes:
            _add(
                failures,
                "packet_file_size_mismatch",
                f"Expected {expected_bytes} bytes, found {actual_bytes}",
                packet_path,
            )
        if source_path.exists() and source_path.stat().st_size != actual_bytes:
            _add(
                failures,
                "source_size_mismatch",
                f"Source size {source_path.stat().st_size} differs from packet size {actual_bytes}",
                packet_path,
            )

    checksum_file = packet_dir / "files_for_submission" / "SHA256SUMS.txt"
    artifact_zip = packet_dir / "files_for_submission" / "MergeDossier-Bench-anonymous-review.zip"
    if checksum_file.exists() and artifact_zip.exists():
        expected_sha = _parse_checksum(checksum_file.read_text(encoding="utf-8", errors="replace"))
        actual_sha = _sha256(artifact_zip)
        if expected_sha != actual_sha:
            _add(
                failures,
                "artifact_checksum_mismatch",
                f"Expected {expected_sha}, found {actual_sha}",
                artifact_zip,
            )
    else:
        _add(failures, "checksum_inputs_missing", "Missing artifact zip or SHA256SUMS.txt", packet_dir)

    portal_text = portal_path.read_text(encoding="utf-8", errors="replace") if portal_path.exists() else ""
    for heading in ["## Title", "## Abstract", "## Keywords"]:
        if heading not in portal_text:
            _add(failures, "portal_heading_missing", f"Missing {heading}", portal_path)
    metadata = status.get("paper_metadata", {})
    abstract_word_count = int(metadata.get("abstract_word_count") or 0)
    if abstract_word_count < 100:
        _add(warnings, "abstract_short", f"Abstract word count is {abstract_word_count}", portal_path)
    if abstract_word_count > 300:
        _add(warnings, "abstract_long", f"Abstract word count is {abstract_word_count}", portal_path)
    for phrase in ["handoff-evidence gap", "review-evidence availability"]:
        if phrase not in portal_text.lower():
            _add(failures, "portal_framing_missing", f"Missing phrase {phrase}", portal_path)

    checklist_text = checklist_path.read_text(encoding="utf-8", errors="replace") if checklist_path.exists() else ""
    for phrase in ["Do not claim patch correctness", "P0 open count"]:
        if phrase not in checklist_text:
            _add(failures, "checklist_boundary_missing", f"Missing checklist phrase: {phrase}", checklist_path)

    result = {
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "status": "fail" if failures else "pass",
        "failure_count": len(failures),
        "warning_count": len(warnings),
        "failures": failures,
        "warnings": warnings,
        "packet_dir": _rel(packet_dir),
        "manifest_rows": len(manifest_rows),
    }
    if out_dir is not None:
        if not out_dir.is_absolute():
            out_dir = ROOT / out_dir
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "icse_submission_packet_check.json").write_text(
            json.dumps(result, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        write_markdown(result, out_dir / "icse_submission_packet_check.md")
    return result


def write_markdown(result: dict[str, Any], out: Path) -> None:
    lines = [
        "# ICSE Submission Packet Check",
        "",
        f"Overall status: **{result['status']}**",
        "",
        f"Failures: `{result['failure_count']}`",
        f"Warnings: `{result['warning_count']}`",
        "",
    ]
    if result["failures"]:
        lines.extend(["## Failures", "", "| Check | Path | Message |", "|---|---|---|"])
        for failure in result["failures"]:
            lines.append(
                f"| {failure['name']} | {failure.get('path') or ''} | {str(failure['message']).replace('|', '\\|')} |"
            )
    if result["warnings"]:
        lines.extend(["", "## Warnings", "", "| Check | Path | Message |", "|---|---|---|"])
        for warning in result["warnings"]:
            lines.append(
                f"| {warning['name']} | {warning.get('path') or ''} | {str(warning['message']).replace('|', '\\|')} |"
            )
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Check local ICSE submission packet")
    parser.add_argument("--packet", default="outputs/icse_submission_packet_20260617")
    parser.add_argument("--out", default="outputs/icse_submission_packet_check_20260617")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    result = check_icse_submission_packet(Path(args.packet), Path(args.out))
    print(
        "ICSE submission packet check: "
        f"{result['status']} ({result['failure_count']} fail, {result['warning_count']} warn)"
    )
    return 0 if result["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())

"""Check whether public archival-release materials are ready for manual action.

This is a preflight check, not a publication step. It verifies that the archive,
checksum, metadata templates, and post-publication commands are present while
preserving the boundary that no DOI or public URL has been minted yet.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
PASS = "pass"
FAIL = "fail"
WARN = "warn"

PLACEHOLDER_TOKENS = [
    "TO_BE_FILLED",
    "TO_BE_FILLED_AFTER_ANONYMOUS_REVIEW",
    "TO_BE_FILLED_PUBLIC_REPOSITORY_URL",
    "TO_BE_FILLED_PAPER_URL_OR_DOI",
]

REQUIRED_BOUNDARIES = [
    "patch correctness",
    "mergeability",
    "reviewer utility",
    "AI-vs-human",
    "all-GitHub",
    "inter-rater",
]


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _read_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="replace")


def _sha256(path: Path) -> str | None:
    if not path.exists():
        return None
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _rel(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()


def _record(name: str, status: str, evidence: str, action: str) -> dict[str, str]:
    return {"name": name, "status": status, "evidence": evidence, "action": action}


def _read_manifest_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def check_public_release_preflight(root: Path, deposit_dir: Path, out_dir: Path) -> dict[str, Any]:
    if not deposit_dir.is_absolute():
        deposit_dir = root / deposit_dir
    if not out_dir.is_absolute():
        out_dir = root / out_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    summary = _read_json(deposit_dir / "deposit_packet_summary.json")
    metadata = _read_json(deposit_dir / "zenodo_metadata_template.json")
    checksum_text = _read_text(deposit_dir / "SHA256SUMS.txt").strip()
    manifest_rows = _read_manifest_rows(deposit_dir / "artifact_upload_manifest.csv")
    instructions = _read_text(deposit_dir / "zenodo_deposit_instructions.md")
    release_notes = _read_text(deposit_dir / "github_release_notes_template.md")
    checklist = _read_text(deposit_dir / "public_release_checklist.md")
    zenodo_copy = _read_text(deposit_dir / "ZENODO_COPY_FIELDS.md")
    github_copy = _read_text(deposit_dir / "GITHUB_RELEASE_COPY_FIELDS.md")

    checks: list[dict[str, str]] = []

    archive_copy = root / str(summary.get("archive_copy", ""))
    archive_hash = _sha256(archive_copy)
    expected_hash = str(summary.get("archive_sha256", ""))
    if archive_hash and archive_hash == expected_hash:
        checks.append(_record("archive_checksum", PASS, f"{_rel(archive_copy, root)} matches deposit summary.", "Upload this exact archive."))
    else:
        checks.append(_record("archive_checksum", FAIL, f"actual={archive_hash}; expected={expected_hash}", "Rebuild the release and deposit packet."))

    checksum_hash = checksum_text.split()[0] if checksum_text.split() else ""
    if checksum_hash and checksum_hash == archive_hash:
        checks.append(_record("sha256sums_match", PASS, "SHA256SUMS.txt matches the upload archive.", "Use this checksum during deposit."))
    else:
        checks.append(_record("sha256sums_match", FAIL, f"sha256sums={checksum_hash}; archive={archive_hash}", "Regenerate SHA256SUMS.txt."))

    if manifest_rows and manifest_rows[0].get("sha256") == archive_hash:
        checks.append(_record("upload_manifest_match", PASS, "artifact_upload_manifest.csv records the upload archive and checksum.", "Use the manifest as upload evidence."))
    else:
        checks.append(_record("upload_manifest_match", FAIL, "Upload manifest missing or checksum mismatch.", "Regenerate the deposit packet."))

    required_metadata = ["title", "upload_type", "publication_date", "creators", "description", "version", "license", "keywords", "related_identifiers", "notes"]
    missing_fields = [field for field in required_metadata if field not in metadata]
    if not missing_fields:
        checks.append(_record("metadata_fields", PASS, "Zenodo metadata template has required fields.", "Copy fields into Zenodo after replacing placeholders."))
    else:
        checks.append(_record("metadata_fields", FAIL, "Missing metadata fields: " + ", ".join(missing_fields), "Update zenodo_metadata_template.json."))

    metadata_text = json.dumps(metadata, ensure_ascii=False)
    placeholders = [token for token in PLACEHOLDER_TOKENS if token in metadata_text]
    if placeholders:
        checks.append(_record("publication_placeholders", WARN, "Placeholders remain: " + ", ".join(placeholders), "Replace these only after real public author/repository/paper metadata exists."))
    else:
        checks.append(_record("publication_placeholders", PASS, "No publication placeholders remain.", "Confirm DOI/public URL are real before claiming publication."))

    note_text = str(metadata.get("notes", ""))
    missing_boundaries = [boundary for boundary in REQUIRED_BOUNDARIES if boundary.lower() not in note_text.lower()]
    if not missing_boundaries:
        checks.append(_record("claim_boundary_notes", PASS, "Metadata notes include required non-claim boundaries.", "Keep these boundaries in the archive notes."))
    else:
        checks.append(_record("claim_boundary_notes", FAIL, "Missing boundaries: " + ", ".join(missing_boundaries), "Update metadata notes before deposit."))

    copied_metadata = set(summary.get("metadata_files", [])) if isinstance(summary.get("metadata_files"), list) else set()
    expected_files = {
        "zenodo_metadata_template.json",
        "github_release_notes_template.md",
        "public_release_checklist.md",
        "public_release_metadata_summary.json",
        "ZENODO_COPY_FIELDS.md",
        "GITHUB_RELEASE_COPY_FIELDS.md",
    }
    if expected_files.issubset(copied_metadata):
        checks.append(_record("metadata_files_copied", PASS, "Deposit packet contains copied metadata templates.", "Use the copies in the deposit packet."))
    else:
        missing = sorted(expected_files - copied_metadata)
        checks.append(_record("metadata_files_copied", FAIL, "Missing copied metadata files: " + ", ".join(missing), "Regenerate the deposit packet."))

    command_phrase = "scripts/update_public_release_metadata.py"
    combined_text = "\n".join([instructions, release_notes, checklist])
    if command_phrase in combined_text or command_phrase in _read_text(root / "README.md"):
        checks.append(_record("post_publication_update_command", PASS, "Post-publication metadata update command is documented.", "Run it after DOI/public URL exist."))
    else:
        checks.append(_record("post_publication_update_command", FAIL, "Post-publication update command not documented.", "Document scripts/update_public_release_metadata.py."))

    if "Notes / Claim Boundary" in zenodo_copy and "not a correctness benchmark" in github_copy:
        checks.append(_record("copy_fields_boundary", PASS, "Zenodo/GitHub copy-field helpers include claim-boundary text.", "Use these files while filling release portals."))
    else:
        checks.append(_record("copy_fields_boundary", FAIL, "Copy-field helpers are missing claim-boundary text.", "Regenerate public release metadata packet."))

    doi_minted = bool(summary.get("doi_minted"))
    public_url = bool(summary.get("public_repository_url_recorded"))
    if not doi_minted and not public_url:
        checks.append(_record("doi_public_url_boundary", WARN, "DOI/public URL are correctly recorded as not yet minted/published.", "Do not claim public availability until real values exist."))
    elif doi_minted and public_url:
        checks.append(_record("doi_public_url_boundary", PASS, "Deposit summary records DOI/public URL completion.", "Confirm public metadata links resolve."))
    else:
        checks.append(_record("doi_public_url_boundary", FAIL, f"doi_minted={doi_minted}; public_repository_url_recorded={public_url}", "Record DOI and public URL together after publication."))

    failures = [check for check in checks if check["status"] == FAIL]
    warnings = [check for check in checks if check["status"] == WARN]
    result = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": "fail" if failures else "ready_for_manual_publication",
        "failure_count": len(failures),
        "warning_count": len(warnings),
        "doi_minted": doi_minted,
        "public_repository_url_recorded": public_url,
        "checks": checks,
        "claim_boundary": (
            "Preflight readiness only. Passing this check does not mint a DOI, publish a public repository, "
            "or establish artifact availability."
        ),
    }
    (out_dir / "public_release_preflight.json").write_text(
        json.dumps(result, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    _write_markdown(result, out_dir / "public_release_preflight.md")
    return result


def _write_markdown(result: dict[str, Any], out: Path) -> None:
    lines = [
        "# Public Release Preflight",
        "",
        f"Status: **{result['status']}**",
        "",
        "| Check | Status | Evidence | Action |",
        "|---|---:|---|---|",
    ]
    for check in result["checks"]:
        evidence = str(check["evidence"]).replace("|", "\\|")
        action = str(check["action"]).replace("|", "\\|")
        lines.append(f"| {check['name']} | {check['status']} | {evidence} | {action} |")
    lines.extend(
        [
            "",
            "## Boundary",
            "",
            str(result["claim_boundary"]),
            "",
        ]
    )
    out.write_text("\n".join(lines), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Check public release/deposit preflight readiness")
    parser.add_argument("--deposit-dir", default="outputs/zenodo_deposit_packet_20260617")
    parser.add_argument("--out", default="outputs/public_release_preflight_20260617")
    args = parser.parse_args(argv)
    result = check_public_release_preflight(ROOT, ROOT / args.deposit_dir, ROOT / args.out)
    print(
        "Public release preflight: "
        f"{result['status']} (fail={result['failure_count']}, warn={result['warning_count']})"
    )
    return 0 if result["status"] != "fail" else 1


if __name__ == "__main__":
    raise SystemExit(main())

"""Build a manual Zenodo deposit packet for the artifact archive.

This script prepares upload instructions, checksums, and copied metadata
templates. It does not mint a DOI and does not claim public archival status.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


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
        return path.name


def _copy_if_exists(source: Path, target_dir: Path) -> str | None:
    if not source.exists():
        return None
    target = target_dir / source.name
    shutil.copy2(source, target)
    return target.name


def _write_upload_manifest(
    out_path: Path,
    rows: list[dict[str, str]],
) -> None:
    fieldnames = ["file", "role", "bytes", "sha256", "upload_action"]
    with out_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _instructions(summary: dict[str, object]) -> str:
    archive_name = summary["archive_name"]
    return "\n".join(
        [
            "# Zenodo Manual Deposit Packet",
            "",
            "Status: **ready for manual deposit, DOI not minted**.",
            "",
            "## Files",
            "",
            f"- Upload archive: `{archive_name}`",
            "- Metadata template: `zenodo_metadata_template.json`",
            "- Release notes template: `github_release_notes_template.md`",
            "- Checklist: `public_release_checklist.md`",
            "- Checksum file: `SHA256SUMS.txt`",
            "- Upload manifest: `artifact_upload_manifest.csv`",
            "",
            "## Manual Steps",
            "",
            "1. Open Zenodo or the chosen institutional archive.",
            "2. Create a new software deposit.",
            "3. Upload the release archive listed above.",
            "4. Copy fields from `zenodo_metadata_template.json`.",
            "5. Replace author, affiliation, public repository URL, paper URL/DOI, and publication date placeholders.",
            "6. Keep the claim boundary in the notes: no correctness, mergeability, reviewer utility, AI-vs-human causal effect, all-GitHub rate, or inter-rater reliability claim.",
            "7. Verify the archive SHA256 against `SHA256SUMS.txt` after upload if the platform exposes checksums.",
            "8. Mint the DOI only after metadata placeholders are resolved.",
            "9. After DOI minting, update `CITATION.cff`, `README.md`, `docs/13_dataset_card.md`, and the paper artifact note with the real DOI.",
            "",
            "## Claim Boundary",
            "",
            "This packet supports artifact archiving only. It does not establish external validation, public availability, or reusable status until the deposit is actually published and the DOI is recorded.",
            "",
        ]
    )


def build_zenodo_deposit_packet(
    archive_path: Path,
    metadata_dir: Path,
    out_dir: Path,
) -> dict[str, object]:
    if not archive_path.exists():
        raise FileNotFoundError(f"Release archive not found: {archive_path}")
    out_dir.mkdir(parents=True, exist_ok=True)
    upload_dir = out_dir / "files_to_upload"
    upload_dir.mkdir(parents=True, exist_ok=True)

    archive_copy = upload_dir / archive_path.name
    shutil.copy2(archive_path, archive_copy)
    archive_hash = _sha256(archive_copy)
    archive_bytes = archive_copy.stat().st_size

    metadata_files = []
    for name in [
        "zenodo_metadata_template.json",
        "github_release_notes_template.md",
        "public_release_checklist.md",
        "public_release_metadata_summary.json",
        "ZENODO_COPY_FIELDS.md",
        "GITHUB_RELEASE_COPY_FIELDS.md",
    ]:
        copied = _copy_if_exists(metadata_dir / name, out_dir)
        if copied:
            metadata_files.append(copied)

    checksum_rows = [f"{archive_hash}  files_to_upload/{archive_copy.name}"]
    (out_dir / "SHA256SUMS.txt").write_text("\n".join(checksum_rows) + "\n", encoding="utf-8")

    upload_rows = [
        {
            "file": f"files_to_upload/{archive_copy.name}",
            "role": "artifact_archive",
            "bytes": str(archive_bytes),
            "sha256": archive_hash,
            "upload_action": "Upload this file to Zenodo as the artifact archive.",
        }
    ]
    _write_upload_manifest(out_dir / "artifact_upload_manifest.csv", upload_rows)

    summary = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": "ready_for_manual_deposit",
        "doi_minted": False,
        "public_repository_url_recorded": False,
        "archive_name": archive_copy.name,
        "archive_source": _rel(archive_path),
        "archive_copy": _rel(archive_copy),
        "archive_bytes": archive_bytes,
        "archive_sha256": archive_hash,
        "metadata_files": metadata_files,
        "claim_boundary": (
            "This packet prepares a manual archive deposit. It does not mint a DOI, "
            "claim public availability, or establish external validation."
        ),
    }
    (out_dir / "deposit_packet_summary.json").write_text(
        json.dumps(summary, indent=2) + "\n",
        encoding="utf-8",
    )
    (out_dir / "zenodo_deposit_instructions.md").write_text(
        _instructions(summary),
        encoding="utf-8",
    )
    return summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build Zenodo manual deposit packet")
    parser.add_argument(
        "--archive",
        default="outputs/release/MergeDossier-Bench-anonymous-review.zip",
        help="Release archive to prepare for manual deposit.",
    )
    parser.add_argument(
        "--metadata-dir",
        default="outputs/public_release_metadata_20260617",
        help="Directory containing public release metadata templates.",
    )
    parser.add_argument(
        "--out",
        default="outputs/zenodo_deposit_packet_20260617",
        help="Output directory for the deposit packet.",
    )
    args = parser.parse_args(argv)
    summary = build_zenodo_deposit_packet(ROOT / args.archive, ROOT / args.metadata_dir, ROOT / args.out)
    print(
        "Zenodo deposit packet written: "
        f"{args.out} ({summary['archive_name']}, sha256={str(summary['archive_sha256'])[:12]}...)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

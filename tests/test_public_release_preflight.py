import csv
import hashlib
import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / "scripts" / "check_public_release_preflight.py"
SPEC = importlib.util.spec_from_file_location("check_public_release_preflight", SCRIPT_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
check_public_release_preflight = MODULE.check_public_release_preflight


def _write_deposit(root: Path, *, summary_hash: str | None = None) -> Path:
    deposit = root / "deposit"
    upload = deposit / "files_to_upload"
    upload.mkdir(parents=True)
    archive = upload / "artifact.zip"
    archive.write_bytes(b"artifact")
    digest = hashlib.sha256(b"artifact").hexdigest()
    recorded_hash = summary_hash or digest
    (deposit / "deposit_packet_summary.json").write_text(
        json.dumps(
            {
                "status": "ready_for_manual_deposit",
                "doi_minted": False,
                "public_repository_url_recorded": False,
                "archive_copy": "deposit/files_to_upload/artifact.zip",
                "archive_sha256": recorded_hash,
                "metadata_files": [
                    "zenodo_metadata_template.json",
                    "github_release_notes_template.md",
                "public_release_checklist.md",
                "public_release_metadata_summary.json",
                "ZENODO_COPY_FIELDS.md",
                "GITHUB_RELEASE_COPY_FIELDS.md",
            ],
            }
        ),
        encoding="utf-8",
    )
    (deposit / "SHA256SUMS.txt").write_text(f"{digest}  files_to_upload/artifact.zip\n", encoding="utf-8")
    with (deposit / "artifact_upload_manifest.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["file", "role", "bytes", "sha256", "upload_action"])
        writer.writeheader()
        writer.writerow(
            {
                "file": "files_to_upload/artifact.zip",
                "role": "artifact_archive",
                "bytes": str(archive.stat().st_size),
                "sha256": digest,
                "upload_action": "upload",
            }
        )
    (deposit / "zenodo_metadata_template.json").write_text(
        json.dumps(
            {
                "title": "MergeDossier-Bench",
                "upload_type": "software",
                "publication_date": "TO_BE_FILLED",
                "creators": [{"name": "TO_BE_FILLED_AFTER_ANONYMOUS_REVIEW"}],
                "description": "Artifact",
                "version": "0.1.0",
                "license": "MIT",
                "keywords": ["benchmark"],
                "related_identifiers": [{"identifier": "TO_BE_FILLED_PUBLIC_REPOSITORY_URL"}],
                "notes": "No patch correctness, mergeability, reviewer utility, AI-vs-human, all-GitHub, or inter-rater reliability claim.",
            }
        ),
        encoding="utf-8",
    )
    (deposit / "zenodo_deposit_instructions.md").write_text(
        "Run scripts/update_public_release_metadata.py after DOI.",
        encoding="utf-8",
    )
    (deposit / "github_release_notes_template.md").write_text("notes", encoding="utf-8")
    (deposit / "public_release_checklist.md").write_text("checklist", encoding="utf-8")
    (deposit / "ZENODO_COPY_FIELDS.md").write_text("## Notes / Claim Boundary", encoding="utf-8")
    (deposit / "GITHUB_RELEASE_COPY_FIELDS.md").write_text("not a correctness benchmark", encoding="utf-8")
    (root / "README.md").write_text("scripts/update_public_release_metadata.py", encoding="utf-8")
    return deposit


def test_public_release_preflight_ready_with_expected_warnings(tmp_path: Path):
    deposit = _write_deposit(tmp_path)

    result = check_public_release_preflight(tmp_path, deposit, tmp_path / "out")

    assert result["status"] == "ready_for_manual_publication"
    assert result["failure_count"] == 0
    assert result["warning_count"] == 2
    assert result["doi_minted"] is False
    assert any(check["name"] == "publication_placeholders" and check["status"] == "warn" for check in result["checks"])
    assert any(check["name"] == "doi_public_url_boundary" and check["status"] == "warn" for check in result["checks"])
    assert (tmp_path / "out/public_release_preflight.md").exists()


def test_public_release_preflight_fails_checksum_mismatch(tmp_path: Path):
    deposit = _write_deposit(tmp_path, summary_hash="0" * 64)

    result = check_public_release_preflight(tmp_path, deposit, tmp_path / "out")

    assert result["status"] == "fail"
    assert any(check["name"] == "archive_checksum" and check["status"] == "fail" for check in result["checks"])

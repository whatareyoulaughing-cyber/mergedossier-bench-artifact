import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / "scripts" / "build_public_release_publish_now_packet.py"
SPEC = importlib.util.spec_from_file_location("build_public_release_publish_now_packet", SCRIPT_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
build_public_release_publish_now_packet = MODULE.build_public_release_publish_now_packet


def _write_json(path: Path, data: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data), encoding="utf-8")


def test_public_release_publish_now_packet_collects_manual_publication_files(tmp_path: Path):
    deposit = tmp_path / "outputs/zenodo_deposit_packet_20260617"
    archive = deposit / "files_to_upload/MergeDossier-Bench-anonymous-review.zip"
    archive.parent.mkdir(parents=True)
    archive.write_bytes(b"zip")
    _write_json(
        deposit / "deposit_packet_summary.json",
        {
            "archive_copy": "outputs/zenodo_deposit_packet_20260617/files_to_upload/MergeDossier-Bench-anonymous-review.zip",
            "archive_sha256": "abc123",
            "doi_minted": False,
            "public_repository_url_recorded": False,
        },
    )
    for name in [
        "ZENODO_COPY_FIELDS.md",
        "GITHUB_RELEASE_COPY_FIELDS.md",
        "SHA256SUMS.txt",
        "artifact_upload_manifest.csv",
        "zenodo_deposit_instructions.md",
        "public_release_checklist.md",
        "zenodo_metadata_template.json",
    ]:
        (deposit / name).write_text(name, encoding="utf-8")

    result = build_public_release_publish_now_packet(tmp_path, tmp_path / "out")

    assert result["status"] == "ready_for_manual_publication"
    assert result["archive_exists"] is True
    assert result["archive_sha256"] == "abc123"
    assert (tmp_path / "out/ZENODO_COPY_FIELDS.md").exists()
    assert (tmp_path / "out/GITHUB_RELEASE_COPY_FIELDS.md").exists()
    checklist = (tmp_path / "out/PUBLISH_NOW_CHECKLIST_ZH.md").read_text(encoding="utf-8")
    runner = (tmp_path / "out/POST_PUBLICATION_UPDATE.ps1").read_text(encoding="utf-8")
    pointer = (tmp_path / "out/UPLOAD_FILE_POINTER.txt").read_text(encoding="utf-8")
    assert "Zenodo" in checklist
    assert "abc123" in checklist
    assert "update_public_release_metadata.py --dry-run" in runner
    assert "-ApplyMetadata" in runner
    assert "MergeDossier-Bench-anonymous-review.zip" in pointer


def test_public_release_publish_now_packet_reports_missing_archive(tmp_path: Path):
    deposit = tmp_path / "outputs/zenodo_deposit_packet_20260617"
    _write_json(
        deposit / "deposit_packet_summary.json",
        {
            "archive_copy": "outputs/zenodo_deposit_packet_20260617/files_to_upload/missing.zip",
            "archive_sha256": "abc123",
        },
    )

    result = build_public_release_publish_now_packet(tmp_path, tmp_path / "out")

    assert result["status"] == "missing_upload_archive"
    assert result["archive_exists"] is False
    assert "does not mint a DOI" in result["claim_boundary"]

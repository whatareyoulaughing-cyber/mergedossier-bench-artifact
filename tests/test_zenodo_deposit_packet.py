import hashlib
import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / "scripts" / "build_zenodo_deposit_packet.py"
SPEC = importlib.util.spec_from_file_location("build_zenodo_deposit_packet", SCRIPT_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
build_zenodo_deposit_packet = MODULE.build_zenodo_deposit_packet


def test_build_zenodo_deposit_packet_copies_archive_and_writes_checksum(tmp_path: Path):
    archive = tmp_path / "artifact.zip"
    archive.write_bytes(b"artifact bytes")
    metadata = tmp_path / "metadata"
    metadata.mkdir()
    (metadata / "zenodo_metadata_template.json").write_text(
        json.dumps({"title": "Example", "publication_date": "TO_BE_FILLED"}),
        encoding="utf-8",
    )
    (metadata / "ZENODO_COPY_FIELDS.md").write_text("Zenodo fields", encoding="utf-8")
    (metadata / "GITHUB_RELEASE_COPY_FIELDS.md").write_text("GitHub fields", encoding="utf-8")
    out = tmp_path / "deposit"

    summary = build_zenodo_deposit_packet(archive, metadata, out)

    expected_hash = hashlib.sha256(b"artifact bytes").hexdigest()
    assert summary["status"] == "ready_for_manual_deposit"
    assert summary["doi_minted"] is False
    assert summary["archive_sha256"] == expected_hash
    assert (out / "files_to_upload" / "artifact.zip").exists()
    assert expected_hash in (out / "SHA256SUMS.txt").read_text(encoding="utf-8")
    assert "DOI not minted" in (out / "zenodo_deposit_instructions.md").read_text(encoding="utf-8")
    assert "claim public availability" in (out / "deposit_packet_summary.json").read_text(encoding="utf-8")
    assert "ZENODO_COPY_FIELDS.md" in summary["metadata_files"]
    assert (out / "GITHUB_RELEASE_COPY_FIELDS.md").exists()

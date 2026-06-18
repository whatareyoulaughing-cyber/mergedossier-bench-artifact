import hashlib
import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / "scripts" / "check_icse_submission_packet.py"
SPEC = importlib.util.spec_from_file_location("check_icse_submission_packet", SCRIPT_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
check_icse_submission_packet = MODULE.check_icse_submission_packet


def _write_packet(tmp_path: Path, checksum: str | None = None) -> Path:
    packet = tmp_path / "packet"
    files = packet / "files_for_submission"
    files.mkdir(parents=True)
    (files / "main.pdf").write_bytes(b"%PDF")
    archive_bytes = b"zip"
    (files / "MergeDossier-Bench-anonymous-review.zip").write_bytes(archive_bytes)
    digest = checksum or hashlib.sha256(archive_bytes).hexdigest()
    (files / "SHA256SUMS.txt").write_text(
        f"{digest}  files_to_upload/MergeDossier-Bench-anonymous-review.zip\n",
        encoding="utf-8",
    )
    checksum_bytes = (files / "SHA256SUMS.txt").stat().st_size
    (packet / "submission_file_manifest.csv").write_text(
        "role,packet_path,source,bytes\n"
        f"anonymous_pdf_submission,{files / 'main.pdf'},{files / 'main.pdf'},4\n"
        f"anonymous_artifact_archive,{files / 'MergeDossier-Bench-anonymous-review.zip'},{files / 'MergeDossier-Bench-anonymous-review.zip'},3\n"
        f"artifact_checksum,{files / 'SHA256SUMS.txt'},{files / 'SHA256SUMS.txt'},{checksum_bytes}\n",
        encoding="utf-8",
    )
    (packet / "submission_packet_status.json").write_text(
        json.dumps(
            {
                "status": "ready_except_external_actions",
                "paper_metadata": {"abstract_word_count": 180},
            }
        ),
        encoding="utf-8",
    )
    (packet / "PORTAL_FIELDS.md").write_text(
        "# Portal Fields\n\n## Title\n\nT\n\n## Abstract\n\nA handoff-evidence gap and review-evidence availability abstract.\n\n## Keywords\n\nk\n",
        encoding="utf-8",
    )
    (packet / "ICSE_SUBMISSION_CHECKLIST_ZH.md").write_text(
        "P0 open count is `2`.\nDo not claim patch correctness.\n",
        encoding="utf-8",
    )
    return packet


def test_icse_submission_packet_check_passes_valid_packet(tmp_path: Path):
    packet = _write_packet(tmp_path)

    result = check_icse_submission_packet(packet, tmp_path / "out")

    assert result["status"] == "pass"
    assert result["failure_count"] == 0
    assert (tmp_path / "out/icse_submission_packet_check.md").exists()


def test_icse_submission_packet_check_fails_checksum_mismatch(tmp_path: Path):
    packet = _write_packet(tmp_path, checksum="0" * 64)

    result = check_icse_submission_packet(packet)

    assert result["status"] == "fail"
    assert any(failure["name"] == "artifact_checksum_mismatch" for failure in result["failures"])

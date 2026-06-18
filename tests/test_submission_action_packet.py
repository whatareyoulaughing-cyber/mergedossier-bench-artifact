import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / "scripts" / "build_submission_action_packet.py"
SPEC = importlib.util.spec_from_file_location("build_submission_action_packet", SCRIPT_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
build_submission_action_packet = MODULE.build_submission_action_packet


def _write_json(path: Path, data: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data), encoding="utf-8")


def test_submission_action_packet_summarizes_p0_actions(tmp_path: Path):
    root = tmp_path
    handoff = root / "outputs/external_audit_handoff_20260617"
    handoff.mkdir(parents=True)
    (handoff / "MergeDossier-external-audit-handoff.zip").write_bytes(b"zip")
    handoff_files = handoff / "handoff_files"
    handoff_files.mkdir()
    for name in ["EMAIL_TEMPLATE_TO_EXTERNAL_AUDITOR.md", "OPERATOR_QUICKSTART.md", "RETURN_INSTRUCTIONS_FOR_AUTHOR.md"]:
        (handoff_files / name).write_text(name, encoding="utf-8")
    recruitment = root / "outputs/external_audit_recruitment_20260617"
    recruitment.mkdir(parents=True)
    for name in [
        "RECRUITMENT_MESSAGE_EN.md",
        "RECRUITMENT_MESSAGE_ZH.md",
        "RECRUITMENT_MESSAGE_ZH_WINDOWS.md",
        "AUTHOR_SEND_CHECKLIST.md",
        "AUDITOR_BOUNDARY_CARD.md",
    ]:
        (recruitment / name).write_text(name, encoding="utf-8")

    _write_json(
        root / "outputs/external_audit_analysis_20260617/external_audit_summary.json",
        {"status": "incomplete", "blank_label_cells": [{}, {}]},
    )
    _write_json(
        root / "outputs/zenodo_deposit_packet_20260617/deposit_packet_summary.json",
        {
            "status": "ready_for_manual_deposit",
            "doi_minted": False,
            "public_repository_url_recorded": False,
            "archive_sha256": "abc123",
            "archive_copy": "outputs/zenodo_deposit_packet_20260617/files_to_upload/release.zip",
        },
    )
    for name in [
        "zenodo_deposit_instructions.md",
        "SHA256SUMS.txt",
        "artifact_upload_manifest.csv",
        "zenodo_metadata_template.json",
        "public_release_checklist.md",
    ]:
        target = root / "outputs/zenodo_deposit_packet_20260617" / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(name, encoding="utf-8")
    _write_json(
        root / "outputs/submission_blocker_dashboard_20260617/submission_blocker_dashboard.json",
        {"status": "blocked_on_external_actions", "p0_open_count": 2},
    )

    result = build_submission_action_packet(root, root / "out")

    assert result["status"] == "action_required"
    assert result["p0_actions"][0]["blank_label_cells"] == 2
    assert result["p0_actions"][1]["archive_sha256"] == "abc123"
    assert (root / "out/NEXT_ACTIONS_ZH.md").exists()
    assert (root / "out/NEXT_ACTIONS_ZH_WINDOWS.md").exists()
    assert (root / "out/AFTER_COMPLETION_COMMANDS.ps1").exists()
    assert (root / "out/send_to_external_auditor/MergeDossier-external-audit-handoff.zip").exists()
    assert (root / "out/send_to_external_auditor/recruitment/RECRUITMENT_MESSAGE_EN.md").exists()
    text = (root / "out/NEXT_ACTIONS_ZH.md").read_text(encoding="utf-8")
    assert "投稿前剩余动作包" in text
    assert "send_to_external_auditor/recruitment" in text
    assert "不 claim patch correctness" in text
    assert "æŠ•" not in text
    assert "python scripts/check_external_audit_progress.py" in text
    assert "python scripts/check_external_audit_return.py" in text
    assert "update_public_release_metadata.py --dry-run" in text

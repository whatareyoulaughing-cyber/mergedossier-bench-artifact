import importlib.util
import json
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / "scripts" / "build_80_percent_push_packet.py"
SPEC = importlib.util.spec_from_file_location("build_80_percent_push_packet", SCRIPT_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
build_80_percent_push_packet = MODULE.build_80_percent_push_packet


def _write_json(path: Path, data: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data), encoding="utf-8")


def _write(path: Path, text: str = "x"):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_80_percent_push_packet_collects_external_action_files(tmp_path: Path):
    _write_json(
        tmp_path / "outputs/acceptance_probability_gap_report_20260617/acceptance_probability_gap_report.json",
        {"status": "local_ready_external_blocked", "p0_open_count": 2, "fail_count": 0},
    )
    _write_json(
        tmp_path / "outputs/p0_execution_dashboard_20260617/p0_execution_dashboard.json",
        {"release_sha256": "abc123"},
    )
    for path in [
        "outputs/external_audit_send_now_20260617/SEND_NOW_EMAIL_ZH.eml",
        "outputs/external_audit_send_now_20260617/SEND_NOW_EMAIL_EN.eml",
        "outputs/external_audit_send_now_20260617/SEND_NOW_EMAIL_ZH_WINDOWS.md",
        "outputs/external_audit_send_now_20260617/SEND_NOW_EMAIL_EN.md",
        "outputs/external_audit_send_now_20260617/MergeDossier-external-audit-handoff.zip",
        "outputs/external_audit_send_now_20260617/ATTACHMENT_AND_RETURN_CHECKLIST.md",
        "outputs/public_release_publish_now_20260617/PUBLISH_NOW_CHECKLIST_ZH_WINDOWS.md",
        "outputs/public_release_publish_now_20260617/PUBLISH_NOW_CHECKLIST_EN.md",
        "outputs/public_release_publish_now_20260617/POST_PUBLICATION_UPDATE.ps1",
        "outputs/public_release_publish_now_20260617/ZENODO_COPY_FIELDS.md",
        "outputs/public_release_publish_now_20260617/GITHUB_RELEASE_COPY_FIELDS.md",
        "outputs/public_release_publish_now_20260617/SHA256SUMS.txt",
        "outputs/public_release_publish_now_20260617/artifact_upload_manifest.csv",
        "outputs/zenodo_deposit_packet_20260617/files_to_upload/MergeDossier-Bench-anonymous-review.zip",
        "outputs/p0_execution_dashboard_20260617/P0_EXECUTION_DASHBOARD_ZH_WINDOWS.md",
        "outputs/p0_execution_dashboard_20260617/OPEN_P0_ACTIONS.ps1",
        "outputs/acceptance_probability_gap_report_20260617/acceptance_probability_gap_report.md",
    ]:
        _write(tmp_path / path)
    _write_json(
        tmp_path / "outputs/external_audit_send_now_20260617/send_now_manifest.json",
        {
            "status": "ready_to_send",
            "handoff_zip_for_email": "outputs/external_audit_send_now_20260617/MergeDossier-external-audit-handoff.zip",
            "files": {
                "email_zh_eml": "outputs/external_audit_send_now_20260617/SEND_NOW_EMAIL_ZH.eml",
                "email_en_eml": "outputs/external_audit_send_now_20260617/SEND_NOW_EMAIL_EN.eml",
                "email_zh_windows": "outputs/external_audit_send_now_20260617/SEND_NOW_EMAIL_ZH_WINDOWS.md",
                "email_en": "outputs/external_audit_send_now_20260617/SEND_NOW_EMAIL_EN.md",
                "attachment_checklist": "outputs/external_audit_send_now_20260617/ATTACHMENT_AND_RETURN_CHECKLIST.md",
            },
        },
    )
    _write_json(
        tmp_path / "outputs/public_release_publish_now_20260617/publish_now_manifest.json",
        {
            "status": "ready_for_manual_publication",
            "archive_to_upload": "outputs/zenodo_deposit_packet_20260617/files_to_upload/MergeDossier-Bench-anonymous-review.zip",
            "archive_sha256": "abc123",
            "copied_files": {
                "ZENODO_COPY_FIELDS.md": "outputs/public_release_publish_now_20260617/ZENODO_COPY_FIELDS.md",
                "GITHUB_RELEASE_COPY_FIELDS.md": "outputs/public_release_publish_now_20260617/GITHUB_RELEASE_COPY_FIELDS.md",
                "SHA256SUMS.txt": "outputs/public_release_publish_now_20260617/SHA256SUMS.txt",
                "artifact_upload_manifest.csv": "outputs/public_release_publish_now_20260617/artifact_upload_manifest.csv",
            },
            "outputs": {
                "checklist_zh": "outputs/public_release_publish_now_20260617/PUBLISH_NOW_CHECKLIST_ZH_WINDOWS.md",
                "checklist_en": "outputs/public_release_publish_now_20260617/PUBLISH_NOW_CHECKLIST_EN.md",
                "upload_pointer": "outputs/public_release_publish_now_20260617/UPLOAD_FILE_POINTER.txt",
                "post_publication_runner": "outputs/public_release_publish_now_20260617/POST_PUBLICATION_UPDATE.ps1",
            },
        },
    )

    result = build_80_percent_push_packet(tmp_path, tmp_path / "out")

    assert result["status"] == "ready_to_execute_external_p0_actions"
    assert result["release_sha256"] == "abc123"
    assert not result["missing_files"]
    assert result["copied_files"]["external_audit/SEND_NOW_EMAIL_ZH.eml"]["packet_path"] == "external_audit/SEND_NOW_EMAIL_ZH.eml"
    assert str(tmp_path) not in json.dumps(result, ensure_ascii=False)
    assert (tmp_path / "out/START_HERE_80_PERCENT_ZH_WINDOWS.md").exists()
    assert (tmp_path / "out/public_release/files_to_upload/MergeDossier-Bench-anonymous-review.zip").exists()
    upload_pointer = (tmp_path / "out/public_release/UPLOAD_FILE_POINTER.txt").read_text(encoding="utf-8")
    assert "public_release/files_to_upload/MergeDossier-Bench-anonymous-review.zip" in upload_pointer
    assert str(tmp_path) not in upload_pointer
    assert (tmp_path / "out/external_audit/MergeDossier-external-audit-handoff.zip").exists()
    assert (tmp_path / "out/MergeDossier-80-percent-push-packet.zip").exists()
    with zipfile.ZipFile(tmp_path / "out/MergeDossier-80-percent-push-packet.zip") as archive:
        names = set(archive.namelist())
    assert "START_HERE_80_PERCENT_ZH.md" in names
    assert "external_audit/SEND_NOW_EMAIL_ZH.eml" in names
    assert "public_release/PUBLISH_NOW_CHECKLIST_ZH_WINDOWS.md" in names
    start_here = (tmp_path / "out/START_HERE_80_PERCENT_ZH.md").read_text(encoding="utf-8")
    assert "这个 packet 只是执行材料" in start_here


def test_80_percent_push_packet_reports_missing_files(tmp_path: Path):
    _write_json(
        tmp_path / "outputs/acceptance_probability_gap_report_20260617/acceptance_probability_gap_report.json",
        {"status": "local_ready_external_blocked", "p0_open_count": 2, "fail_count": 0},
    )

    result = build_80_percent_push_packet(tmp_path, tmp_path / "out")

    assert result["status"] == "missing_required_files"
    assert result["missing_files"]

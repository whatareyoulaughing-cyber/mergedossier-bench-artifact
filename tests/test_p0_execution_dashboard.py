import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / "scripts" / "build_p0_execution_dashboard.py"
SPEC = importlib.util.spec_from_file_location("build_p0_execution_dashboard", SCRIPT_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
build_p0_execution_dashboard = MODULE.build_p0_execution_dashboard


def _write_json(path: Path, data: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data), encoding="utf-8")


def test_p0_execution_dashboard_collects_action_files(tmp_path: Path):
    for path in [
        "outputs/external_audit_send_now_20260617/SEND_NOW_EMAIL_ZH.eml",
        "outputs/external_audit_send_now_20260617/SEND_NOW_EMAIL_ZH_WINDOWS.md",
        "outputs/external_audit_send_now_20260617/MergeDossier-external-audit-handoff.zip",
        "outputs/external_audit_send_now_20260617/ATTACHMENT_AND_RETURN_CHECKLIST.md",
        "outputs/public_release_publish_now_20260617/PUBLISH_NOW_CHECKLIST_ZH_WINDOWS.md",
        "outputs/public_release_publish_now_20260617/UPLOAD_FILE_POINTER.txt",
        "outputs/public_release_publish_now_20260617/POST_PUBLICATION_UPDATE.ps1",
        "outputs/zenodo_deposit_packet_20260617/files_to_upload/MergeDossier-Bench-anonymous-review.zip",
    ]:
        target = tmp_path / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("x", encoding="utf-8")
    _write_json(
        tmp_path / "outputs/acceptance_probability_gap_report_20260617/acceptance_probability_gap_report.json",
        {"status": "local_ready_external_blocked", "p0_open_count": 2, "fail_count": 0},
    )
    _write_json(
        tmp_path / "outputs/external_audit_send_now_20260617/send_now_manifest.json",
        {
            "status": "ready_to_send",
            "handoff_zip_for_email": "outputs/external_audit_send_now_20260617/MergeDossier-external-audit-handoff.zip",
            "files": {
                "email_zh_eml": "outputs/external_audit_send_now_20260617/SEND_NOW_EMAIL_ZH.eml",
                "email_zh_windows": "outputs/external_audit_send_now_20260617/SEND_NOW_EMAIL_ZH_WINDOWS.md",
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
            "outputs": {
                "checklist_zh": "outputs/public_release_publish_now_20260617/PUBLISH_NOW_CHECKLIST_ZH_WINDOWS.md",
                "upload_pointer": "outputs/public_release_publish_now_20260617/UPLOAD_FILE_POINTER.txt",
                "post_publication_runner": "outputs/public_release_publish_now_20260617/POST_PUBLICATION_UPDATE.ps1",
            },
        },
    )

    result = build_p0_execution_dashboard(tmp_path, tmp_path / "out")

    assert result["status"] == "ready_to_execute_p0_actions"
    assert result["p0_open_count"] == 2
    assert result["release_sha256"] == "abc123"
    assert not result["missing_paths"]
    dashboard = (tmp_path / "out/P0_EXECUTION_DASHBOARD_ZH.md").read_text(encoding="utf-8")
    opener = (tmp_path / "out/OPEN_P0_ACTIONS.ps1").read_text(encoding="utf-8")
    assert "SEND_NOW_EMAIL_ZH.eml" in dashboard
    assert "PUBLISH_NOW_CHECKLIST_ZH_WINDOWS.md" in dashboard
    assert "Start-Process" in opener
    assert "No files are modified" in opener


def test_p0_execution_dashboard_reports_missing_files(tmp_path: Path):
    _write_json(
        tmp_path / "outputs/acceptance_probability_gap_report_20260617/acceptance_probability_gap_report.json",
        {"status": "local_ready_external_blocked", "p0_open_count": 2, "fail_count": 0},
    )

    result = build_p0_execution_dashboard(tmp_path, tmp_path / "out")

    assert result["status"] == "missing_p0_execution_files"
    assert result["missing_paths"]

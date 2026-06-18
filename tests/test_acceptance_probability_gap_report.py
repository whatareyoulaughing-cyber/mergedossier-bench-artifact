import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / "scripts" / "build_acceptance_probability_gap_report.py"
SPEC = importlib.util.spec_from_file_location("build_acceptance_probability_gap_report", SCRIPT_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
build_acceptance_probability_gap_report = MODULE.build_acceptance_probability_gap_report


def _write_json(path: Path, data: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data), encoding="utf-8")


def test_acceptance_probability_gap_report_marks_external_p0_gap(tmp_path: Path):
    dashboard = tmp_path / "dashboard.json"
    _write_json(
        dashboard,
        {
            "status": "blocked_on_external_actions",
            "p0_open_count": 2,
            "fail_count": 0,
            "checks": [
                {
                    "name": "External audit slice",
                    "status": "open",
                    "severity": "P0",
                    "evidence": "blank_label_cells=500",
                    "action": "Complete the independent audit.",
                },
                {
                    "name": "Archival DOI and public URL",
                    "status": "ready",
                    "severity": "P0",
                    "evidence": "doi_minted=False; public_repository_url_recorded=False",
                    "action": "Publish the deposit and update metadata.",
                },
                {
                    "name": "Release zip functional smoke",
                    "status": "pass",
                    "severity": "P1",
                    "evidence": "commands=3",
                    "action": "Keep rerunning.",
                },
            ],
        },
    )
    readiness = tmp_path / "readiness.json"
    _write_json(readiness, {"status": "pass", "records": [{"gate": "pytest", "status": "pass"}]})
    audit = tmp_path / "external_audit_progress.json"
    _write_json(
        audit,
        {
            "status": "incomplete",
            "selected_tasks": 50,
            "rows_found": 50,
            "complete_rows": 0,
            "total_required_cells": 500,
            "valid_label_cells": 0,
            "blank_label_cells": [{} for _ in range(500)],
        },
    )
    preflight = tmp_path / "public_release_preflight.json"
    _write_json(preflight, {"status": "ready_for_manual_publication", "warning_count": 2})
    intake = tmp_path / "external_audit_intake.json"
    _write_json(
        intake,
        {
            "status": "complete_but_unverified_candidate_found",
            "candidate_count": 3,
            "complete_candidate_count": 1,
            "ready_external_return_count": 0,
            "next_action": "Confirm provenance before formal analysis.",
        },
    )
    send_now = tmp_path / "send_now_manifest.json"
    _write_json(
        send_now,
        {
            "status": "ready_to_send",
            "handoff_zip_for_email": "outputs/external_audit_send_now_20260617/MergeDossier-external-audit-handoff.zip",
            "files": {
                "email_zh_windows": "outputs/external_audit_send_now_20260617/SEND_NOW_EMAIL_ZH_WINDOWS.md",
                "email_en": "outputs/external_audit_send_now_20260617/SEND_NOW_EMAIL_EN.md",
                "email_zh_eml": "outputs/external_audit_send_now_20260617/SEND_NOW_EMAIL_ZH.eml",
                "email_en_eml": "outputs/external_audit_send_now_20260617/SEND_NOW_EMAIL_EN.eml",
                "attachment_checklist": "outputs/external_audit_send_now_20260617/ATTACHMENT_AND_RETURN_CHECKLIST.md",
            },
        },
    )
    publish_now = tmp_path / "publish_now_manifest.json"
    _write_json(
        publish_now,
        {
            "status": "ready_for_manual_publication",
            "archive_to_upload": "outputs/zenodo_deposit_packet_20260617/files_to_upload/MergeDossier-Bench-anonymous-review.zip",
            "archive_sha256": "abc123",
            "outputs": {
                "checklist_zh": "outputs/public_release_publish_now_20260617/PUBLISH_NOW_CHECKLIST_ZH_WINDOWS.md",
                "post_publication_runner": "outputs/public_release_publish_now_20260617/POST_PUBLICATION_UPDATE.ps1",
                "upload_pointer": "outputs/public_release_publish_now_20260617/UPLOAD_FILE_POINTER.txt",
            },
        },
    )
    p0_execution_dashboard = tmp_path / "p0_execution_dashboard.json"
    _write_json(
        p0_execution_dashboard,
        {
            "status": "ready_to_execute_p0_actions",
            "missing_paths": [],
        },
    )
    release = tmp_path / "release_zip_summary.json"
    _write_json(release, {"file_count": 374, "zip_bytes": 1234})
    checksum = tmp_path / "SHA256SUMS.txt"
    checksum.write_text("abc123  files_to_upload/MergeDossier-Bench-anonymous-review.zip\n", encoding="utf-8")
    paper = tmp_path / "main.tex"
    paper.write_text("Tests & 141 offline tests pass. \\\\\n", encoding="utf-8")

    result = build_acceptance_probability_gap_report(
        root=tmp_path,
        dashboard_path=dashboard,
        readiness_path=readiness,
        external_audit_path=audit,
        external_audit_intake_path=intake,
        external_audit_send_now_path=send_now,
        public_release_publish_now_path=publish_now,
        p0_execution_dashboard_path=p0_execution_dashboard,
        preflight_path=preflight,
        release_summary_path=release,
        checksum_path=checksum,
        paper_path=paper,
        out_dir=tmp_path / "out",
    )

    assert result["status"] == "local_ready_external_blocked"
    assert result["p0_open_count"] == 2
    assert result["fail_count"] == 0
    assert result["p1_pass_count"] == 1
    assert result["external_audit_progress"]["blank_label_cells"] == 500
    assert result["external_audit_progress"]["completion_rate"] == 0.0
    assert result["external_audit_intake"]["ready_external_return_count"] == 0
    assert result["external_audit_send_now"]["status"] == "ready_to_send"
    assert result["public_release_publish_now"]["status"] == "ready_for_manual_publication"
    assert result["p0_execution_dashboard"]["status"] == "ready_to_execute_p0_actions"
    assert result["local_evidence"]["test_evidence"] == "141 offline tests pass"
    assert "校准" not in result["interpretation"]
    assert "not a calibrated acceptance probability" in result["interpretation"]
    assert any("外部审计者" in action for action in result["next_two_actions_zh"])
    assert (tmp_path / "out/acceptance_probability_gap_report.json").exists()
    assert (tmp_path / "out/NEXT_TWO_ACTIONS_ZH_WINDOWS.md").exists()
    md = (tmp_path / "out/acceptance_probability_gap_report.md").read_text(encoding="utf-8")
    assert "not a calibrated acceptance probability" in md
    assert "Blank required cells: 500" in md
    assert "Ready external-return candidates: 0" in md
    assert "SEND_NOW_EMAIL_ZH_WINDOWS.md" in md
    assert "SEND_NOW_EMAIL_ZH.eml" in md
    assert "PUBLISH_NOW_CHECKLIST_ZH_WINDOWS.md" in md
    assert "OPEN_P0_ACTIONS.ps1" in md

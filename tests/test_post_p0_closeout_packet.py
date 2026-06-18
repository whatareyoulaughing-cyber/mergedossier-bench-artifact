import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / "scripts" / "build_post_p0_closeout_packet.py"
SPEC = importlib.util.spec_from_file_location("build_post_p0_closeout_packet", SCRIPT_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
build_post_p0_closeout_packet = MODULE.build_post_p0_closeout_packet


def _write_json(path: Path, data: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data), encoding="utf-8")


def test_post_p0_closeout_packet_writes_dry_run_runner_and_checklist(tmp_path: Path):
    _write_json(
        tmp_path / "outputs/submission_blocker_dashboard_20260617/submission_blocker_dashboard.json",
        {"status": "blocked_on_external_actions", "p0_open_count": 2},
    )
    _write_json(
        tmp_path / "outputs/acceptance_probability_gap_report_20260617/acceptance_probability_gap_report.json",
        {"status": "local_ready_external_blocked"},
    )
    _write_json(
        tmp_path / "outputs/zenodo_deposit_packet_20260617/deposit_packet_summary.json",
        {
            "doi_minted": False,
            "public_repository_url_recorded": False,
            "archive_sha256": "abc123",
        },
    )
    _write_json(
        tmp_path / "outputs/external_audit_progress_20260617/external_audit_progress.json",
        {"status": "incomplete", "blank_label_cells": [{}, {}]},
    )

    result = build_post_p0_closeout_packet(tmp_path, tmp_path / "out")

    assert result["status"] == "waiting_for_external_inputs"
    assert result["dashboard_p0_open_count"] == 2
    assert result["external_audit_blank_label_cells"] == 2
    assert result["doi_minted"] is False
    runner = (tmp_path / "out/POST_P0_FINALIZE.ps1").read_text(encoding="utf-8")
    assert "[switch]$ApplyMetadata" in runner
    assert "update_public_release_metadata.py --dry-run" in runner
    assert "if ($ApplyMetadata)" in runner
    assert "check_release_zip_smoke.py" in runner
    checklist = (tmp_path / "out/POST_P0_CLOSEOUT_CHECKLIST_ZH.md").read_text(encoding="utf-8")
    assert "p0_open_count=0" in checklist
    assert "不要新增 correctness" in checklist
    assert (tmp_path / "out/POST_P0_CLOSEOUT_CHECKLIST_ZH_WINDOWS.md").exists()

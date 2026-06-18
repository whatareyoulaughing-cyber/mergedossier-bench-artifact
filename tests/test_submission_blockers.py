import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / "scripts" / "check_submission_blockers.py"
SPEC = importlib.util.spec_from_file_location("check_submission_blockers", SCRIPT_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
build_submission_blocker_dashboard = MODULE.build_submission_blocker_dashboard


def _write_json(path: Path, data: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data), encoding="utf-8")


def test_submission_dashboard_marks_external_actions_open(tmp_path: Path):
    root = tmp_path
    archive = root / "outputs/release/MergeDossier-Bench-anonymous-review.zip"
    archive.parent.mkdir(parents=True)
    archive.write_bytes(b"zip")

    import hashlib

    digest = hashlib.sha256(b"zip").hexdigest()
    checksum = root / "outputs/zenodo_deposit_packet_20260617/SHA256SUMS.txt"
    checksum.parent.mkdir(parents=True)
    checksum.write_text(f"{digest}  files_to_upload/MergeDossier-Bench-anonymous-review.zip\n", encoding="utf-8")

    _write_json(
        root / "outputs/external_audit_analysis_20260617/external_audit_summary.json",
        {"status": "incomplete", "blank_label_cells": [{}]},
    )
    _write_json(
        root / "outputs/zenodo_deposit_packet_20260617/deposit_packet_summary.json",
        {"status": "ready_for_manual_deposit", "doi_minted": False, "public_repository_url_recorded": False},
    )
    _write_json(
        root / "outputs/paper_readiness_check_20260617_handoff_gap/paper_readiness_check.json",
        {"status": "pass", "records": [{"gate": "pytest", "status": "pass"}]},
    )
    _write_json(
        root / "outputs/manuscript_claim_hygiene_20260617/manuscript_claim_hygiene.json",
        {"status": "pass", "finding_count": 0},
    )
    _write_json(
        root / "outputs/submission_action_packet_20260617/action_status.json",
        {"status": "action_required", "p0_actions": [{"name": "external_audit"}, {"name": "doi_and_public_url"}]},
    )
    _write_json(
        root / "outputs/external_audit_handoff_20260617/external_auditor_handoff_check.json",
        {"status": "pass", "failure_count": 0},
    )
    _write_json(
        root / "outputs/icse_submission_packet_20260617/submission_packet_status.json",
        {"status": "ready_except_external_actions", "copied_files": [{}, {}, {}]},
    )
    _write_json(
        root / "outputs/icse_submission_packet_check_20260617/icse_submission_packet_check.json",
        {"status": "pass", "failure_count": 0, "warning_count": 0},
    )
    _write_json(
        root / "outputs/double_anonymous_submission_check_20260617/double_anonymous_submission_check.json",
        {"status": "pass", "fail_count": 0, "warn_count": 0},
    )
    _write_json(
        root / "outputs/ai_assistance_disclosure_check_20260617/ai_assistance_disclosure_check.json",
        {"status": "pass", "failure_count": 0, "warning_count": 1},
    )
    _write_json(
        root / "outputs/release_zip_smoke_20260617/release_zip_smoke.json",
        {"status": "pass", "commands": [{}, {}, {}]},
    )
    _write_json(
        root / "outputs/public_release_preflight_20260617/public_release_preflight.json",
        {"status": "ready_for_manual_publication", "failure_count": 0, "warning_count": 2},
    )
    _write_json(
        root / "outputs/raw_frame_release_risk_20260617/raw_frame_release_risk_summary.json",
        {"status": "findings_present", "affected_rows": 2},
    )
    metadata = root / "outputs/public_release_metadata_20260617/zenodo_metadata_template.json"
    metadata.parent.mkdir(parents=True)
    metadata.write_text("TO_BE_FILLED", encoding="utf-8")
    (root / "CITATION.cff").write_text("To be added after anonymous review.", encoding="utf-8")
    (root / "README.md").write_text("README", encoding="utf-8")

    result = build_submission_blocker_dashboard(root, root / "out")

    assert result["status"] == "blocked_on_external_actions"
    assert result["p0_open_count"] == 2
    assert any(check["name"] == "Release archive checksum" and check["status"] == "pass" for check in result["checks"])
    assert any(check["name"] == "Manuscript claim hygiene" and check["status"] == "pass" for check in result["checks"])
    assert any(check["name"] == "Submission action packet" and check["status"] == "pass" for check in result["checks"])
    assert any(check["name"] == "External auditor handoff independence" and check["status"] == "pass" for check in result["checks"])
    assert any(check["name"] == "ICSE submission packet" and check["status"] == "pass" for check in result["checks"])
    assert any(check["name"] == "ICSE submission packet self-check" and check["status"] == "pass" for check in result["checks"])
    assert any(check["name"] == "Double-anonymous submission check" and check["status"] == "pass" for check in result["checks"])
    assert any(check["name"] == "AI assistance disclosure" and check["status"] == "pass" for check in result["checks"])
    assert any(check["name"] == "Release zip functional smoke" and check["status"] == "pass" for check in result["checks"])
    assert any(check["name"] == "Public release preflight" and check["status"] == "pass" for check in result["checks"])
    assert (root / "out/submission_blocker_dashboard.md").exists()


def test_submission_dashboard_can_demote_external_audit_in_single_operator_mode(tmp_path: Path):
    root = tmp_path
    _write_json(
        root / "outputs/external_audit_analysis_20260617/external_audit_summary.json",
        {"status": "incomplete", "blank_label_cells": [{}]},
    )
    (root / "release/UPLOAD_RESULT.md").parent.mkdir(parents=True)
    (root / "release/UPLOAD_RESULT.md").write_text(
        "Fresh clone pytest: pass\n"
        "Uploaded asset SHA verification: pass\n"
        "Zip anonymous scan: pass\n"
        "DOI archival is planned after double-anonymous constraints are lifted\n"
        "https://github.com/whatareyoulaughing-cyber/mergedossier-bench-artifact/releases/tag/v0.1-anonymous\n",
        encoding="utf-8",
    )
    _write_json(root / "outputs/post_artifact_upload_20260618/SUBMISSION_STATUS_POST_UPLOAD.json", {})
    _write_json(
        root / "outputs/icse_submission_packet_post_upload_20260618/packet_status.json",
        {
            "anonymous_artifact_release": "https://github.com/whatareyoulaughing-cyber/mergedossier-bench-artifact/releases/tag/v0.1-anonymous",
            "remaining_highest_return_action": "submit with single-operator boundary",
            "non_claims": ["DOI archival during double-anonymous review"],
        },
    )
    _write_json(
        root / "outputs/paper_readiness_check_20260617_handoff_gap/paper_readiness_check.json",
        {"status": "pass", "records": [{"gate": "pytest", "status": "pass"}]},
    )
    _write_json(
        root / "outputs/manuscript_claim_hygiene_20260617/manuscript_claim_hygiene.json",
        {"status": "pass", "finding_count": 0},
    )
    _write_json(
        root / "outputs/external_audit_handoff_20260617/external_auditor_handoff_check.json",
        {"status": "pass", "failure_count": 0},
    )
    _write_json(
        root / "outputs/icse_submission_packet_check_20260617/icse_submission_packet_check.json",
        {"status": "pass", "failure_count": 0, "warning_count": 0},
    )
    _write_json(
        root / "outputs/double_anonymous_submission_check_20260617/double_anonymous_submission_check.json",
        {"status": "pass", "fail_count": 0, "warn_count": 0},
    )
    _write_json(
        root / "outputs/ai_assistance_disclosure_check_20260617/ai_assistance_disclosure_check.json",
        {"status": "pass", "failure_count": 0, "warning_count": 1},
    )
    _write_json(
        root / "outputs/release_zip_smoke_20260617/release_zip_smoke.json",
        {"status": "pass", "commands": [{}, {}, {}]},
    )
    _write_json(
        root / "outputs/public_release_preflight_20260617/public_release_preflight.json",
        {"status": "ready_for_manual_publication", "failure_count": 0, "warning_count": 2},
    )
    _write_json(
        root / "outputs/anonymous_release_check_20260617/anonymous_release_check.json",
        {"status": "pass", "finding_count": 0},
    )
    _write_json(
        root / "outputs/raw_frame_release_risk_20260617/raw_frame_release_risk_summary.json",
        {"status": "findings_present", "affected_rows": 2},
    )
    metadata = root / "outputs/public_release_metadata_20260617/zenodo_metadata_template.json"
    metadata.parent.mkdir(parents=True)
    metadata.write_text("anonymous metadata", encoding="utf-8")
    (root / "CITATION.cff").write_text("anonymous citation", encoding="utf-8")
    (root / "README.md").write_text("README", encoding="utf-8")

    result = build_submission_blocker_dashboard(
        root,
        root / "out",
        external_audit_required=False,
    )

    assert result["status"] == "submission_ready_local"
    assert result["p0_open_count"] == 0
    external = next(check for check in result["checks"] if check["name"] == "External audit slice")
    assert external["severity"] == "P1"
    assert external["status"] == "ready"
    assert "single-operator boundary" in external["action"]
    md = (root / "out/submission_blocker_dashboard.md").read_text(encoding="utf-8")
    assert "Single-operator submission mode is active" in md

import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / "scripts" / "build_external_audit_recruitment_packet.py"
SPEC = importlib.util.spec_from_file_location("build_external_audit_recruitment_packet", SCRIPT_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
build_external_audit_recruitment_packet = MODULE.build_external_audit_recruitment_packet


def _write_json(path: Path, data: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data), encoding="utf-8")


def test_external_audit_recruitment_packet_is_send_ready_without_claiming_completion(tmp_path: Path):
    root = tmp_path
    handoff = root / "outputs/external_audit_handoff_20260617"
    handoff.mkdir(parents=True)
    (handoff / "MergeDossier-external-audit-handoff.zip").write_bytes(b"zip")
    _write_json(
        handoff / "external_auditor_handoff_summary.json",
        {"file_count": 8, "zip_bytes": 3},
    )
    _write_json(
        root / "outputs/external_audit_analysis_20260617/external_audit_summary.json",
        {"status": "incomplete", "blank_label_cells": [{}, {}]},
    )

    result = build_external_audit_recruitment_packet(root, root / "out")

    assert result["status"] == "ready_to_send"
    assert result["external_audit_status"] == "incomplete"
    assert result["blank_label_cells"] == 2
    assert "do not establish external agreement" in result["claim_boundary"]
    assert (root / "out/RECRUITMENT_MESSAGE_EN.md").exists()
    assert (root / "out/RECRUITMENT_MESSAGE_ZH.md").exists()
    assert (root / "out/RECRUITMENT_MESSAGE_ZH_WINDOWS.md").read_bytes()[:3] == b"\xef\xbb\xbf"
    zh = (root / "out/RECRUITMENT_MESSAGE_ZH.md").read_text(encoding="utf-8")
    assert "外部审计" in zh
    assert "不需要判断代码是否正确" in zh
    assert "æŠ" not in zh
    boundary = (root / "out/AUDITOR_BOUNDARY_CARD.md").read_text(encoding="utf-8")
    assert "patch correctness" in boundary
    assert "uncitable" in boundary

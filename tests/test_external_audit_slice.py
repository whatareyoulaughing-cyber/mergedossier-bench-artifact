import json
import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("build_external_audit_slice", ROOT / "scripts" / "build_external_audit_slice.py")
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
build_external_audit_slice = MODULE.build_external_audit_slice


def _task(index: int) -> dict:
    return {
        "data": {
            "instance_id": f"task_{index:03d}",
            "repo": "owner/repo",
            "pr_number": str(index),
            "pr_url": f"https://github.com/owner/repo/pull/{index}",
            "title": f"Task {index}",
            "dossier_text": "Intent evidence: visible.",
            "evidence_sections": {},
            "provenance_sections": {},
            "existing_score": 0,
            "missing_evidence": "",
        }
    }


def test_build_external_audit_slice_is_deterministic(tmp_path: Path):
    tasks_path = tmp_path / "tasks.json"
    tasks_path.write_text(json.dumps([_task(i) for i in range(20)]), encoding="utf-8")
    out_a = tmp_path / "audit_a"
    out_b = tmp_path / "audit_b"

    summary_a = build_external_audit_slice(tasks_path, out_a, n=5, seed=7)
    summary_b = build_external_audit_slice(tasks_path, out_b, n=5, seed=7)

    assert summary_a["selected_instance_ids"] == summary_b["selected_instance_ids"]
    assert len(summary_a["selected_instance_ids"]) == 5
    assert "audit_workbook_status" in summary_a
    assert (out_a / "external_audit_tasks.json").exists()
    assert (out_a / "external_audit_sheet.csv").exists()
    assert (out_a / "external_audit_manifest.json").exists()
    assert "External Audit Slice" in (out_a / "README_external_audit.md").read_text(encoding="utf-8")


def test_build_external_audit_slice_can_skip_workbook(tmp_path: Path):
    tasks_path = tmp_path / "tasks.json"
    tasks_path.write_text(json.dumps([_task(i) for i in range(8)]), encoding="utf-8")
    out = tmp_path / "audit"

    summary = build_external_audit_slice(tasks_path, out, n=3, seed=3, make_workbook=False)

    assert summary["audit_workbook"] is None
    assert summary["audit_workbook_status"] == "not_requested"
    assert (out / "external_audit_sheet.csv").exists()
    assert not (out / "external_audit_sheet.xlsx").exists()

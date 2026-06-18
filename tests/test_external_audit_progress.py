import csv
import importlib.util
import json
from pathlib import Path

from mergedossier_bench.label_studio import EVIDENCE_CATEGORIES


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / "scripts" / "check_external_audit_progress.py"
SPEC = importlib.util.spec_from_file_location("check_external_audit_progress", SCRIPT_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
check_external_audit_progress = MODULE.check_external_audit_progress


FIELDNAMES = ["instance_id", "is_reliability_repeat"] + [
    field for category in EVIDENCE_CATEGORIES for field in (f"{category}_label", f"{category}_comment")
]


def _row(instance_id: str, labels: dict[str, str]) -> dict[str, str]:
    row = {field: "" for field in FIELDNAMES}
    row["instance_id"] = instance_id
    row["is_reliability_repeat"] = "False"
    for category in EVIDENCE_CATEGORIES:
        row[f"{category}_label"] = labels.get(category, "")
    return row


def _write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)


def test_external_audit_progress_reports_incomplete_cells(tmp_path: Path):
    audit = tmp_path / "audit.csv"
    manifest = tmp_path / "manifest.json"
    labels = {category: "present" for category in EVIDENCE_CATEGORIES}
    labels[EVIDENCE_CATEGORIES[0]] = ""
    labels[EVIDENCE_CATEGORIES[1]] = "bad-label"
    _write_csv(audit, [_row("task-a", labels)])
    manifest.write_text(json.dumps({"selected_instance_ids": ["task-a", "task-b"]}), encoding="utf-8")

    result = check_external_audit_progress(audit, tmp_path / "out", manifest)

    assert result["status"] == "incomplete"
    assert result["selected_tasks"] == 2
    assert len(result["missing_rows"]) == 1
    assert len(result["blank_label_cells"]) == 1
    assert len(result["invalid_label_cells"]) == 1
    assert result["completion_rate"] == 0.4
    feedback = (tmp_path / "out/AUDITOR_FEEDBACK_REQUEST.md").read_text(encoding="utf-8")
    assert "First Blank Cells" in feedback
    assert "bad-label" in feedback


def test_external_audit_progress_reports_complete_sheet(tmp_path: Path):
    audit = tmp_path / "audit.csv"
    manifest = tmp_path / "manifest.json"
    labels = {category: "present" for category in EVIDENCE_CATEGORIES}
    _write_csv(audit, [_row("task-a", labels)])
    manifest.write_text(json.dumps({"selected_instance_ids": ["task-a"]}), encoding="utf-8")

    result = check_external_audit_progress(audit, tmp_path / "out", manifest)

    assert result["status"] == "complete"
    assert result["completion_rate"] == 1.0
    assert result["complete_rows"] == 1
    progress = (tmp_path / "out/external_audit_progress.md").read_text(encoding="utf-8")
    assert "100.0%" in progress

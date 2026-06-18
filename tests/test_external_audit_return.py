import csv
import importlib.util
import json
from pathlib import Path

from mergedossier_bench.label_studio import EVIDENCE_CATEGORIES


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "check_external_audit_return", ROOT / "scripts" / "check_external_audit_return.py"
)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
check_external_audit_return = MODULE.check_external_audit_return


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


def test_external_audit_return_accepts_csv_and_reports_incomplete(tmp_path: Path):
    primary = tmp_path / "primary.csv"
    external = tmp_path / "external.csv"
    manifest = tmp_path / "manifest.json"
    out = tmp_path / "out"
    filled = {category: "present" for category in EVIDENCE_CATEGORIES}
    _write_csv(primary, [_row("task-a", filled)])
    _write_csv(external, [_row("task-a", {})])
    manifest.write_text(json.dumps({"selected_instance_ids": ["task-a"]}), encoding="utf-8")

    status = check_external_audit_return(external, out, primary, manifest)

    assert status["status"] == "incomplete"
    assert status["input_kind"] == "csv"
    assert status["blank_label_cells"] == len(EVIDENCE_CATEGORIES)
    assert (out / "completed_external_audit_sheet.csv").exists()
    assert "not complete" in (out / "external_audit_return_status.md").read_text(encoding="utf-8")


def test_external_audit_return_reports_complete_csv(tmp_path: Path):
    primary = tmp_path / "primary.csv"
    external = tmp_path / "external.csv"
    manifest = tmp_path / "manifest.json"
    out = tmp_path / "out"
    filled = {category: "present" for category in EVIDENCE_CATEGORIES}
    _write_csv(primary, [_row("task-a", filled)])
    _write_csv(external, [_row("task-a", filled)])
    manifest.write_text(json.dumps({"selected_instance_ids": ["task-a"]}), encoding="utf-8")

    status = check_external_audit_return(external, out, primary, manifest)

    assert status["status"] == "complete"
    assert status["blank_label_cells"] == 0
    assert (out / "external_audit_agreement_by_category.csv").exists()

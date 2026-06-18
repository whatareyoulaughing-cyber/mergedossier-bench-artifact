import csv
import importlib.util
import json
from pathlib import Path

from mergedossier_bench.label_studio import EVIDENCE_CATEGORIES


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / "scripts" / "build_external_audit_intake_report.py"
SPEC = importlib.util.spec_from_file_location("build_external_audit_intake_report", SCRIPT_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
build_external_audit_intake_report = MODULE.build_external_audit_intake_report


FIELDNAMES = ["instance_id", "is_reliability_repeat"] + [
    field for category in EVIDENCE_CATEGORIES for field in (f"{category}_label", f"{category}_comment")
]


def _write_audit_csv(path: Path, instance_ids: list[str], *, complete: bool) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDNAMES)
        writer.writeheader()
        for instance_id in instance_ids:
            row = {field: "" for field in FIELDNAMES}
            row["instance_id"] = instance_id
            row["is_reliability_repeat"] = "False"
            if complete:
                for category in EVIDENCE_CATEGORIES:
                    row[f"{category}_label"] = "present"
            writer.writerow(row)


def test_external_audit_intake_finds_complete_candidate(tmp_path: Path):
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps({"selected_instance_ids": ["task-a", "task-b"]}), encoding="utf-8")
    complete = tmp_path / "downloads" / "completed_external_audit.csv"
    _write_audit_csv(complete, ["task-a", "task-b"], complete=True)
    incomplete = tmp_path / "downloads" / "external_audit_sheet.csv"
    _write_audit_csv(incomplete, ["task-a", "task-b"], complete=False)

    result = build_external_audit_intake_report(
        search_dirs=[tmp_path / "downloads"],
        explicit_candidates=[],
        manifest_path=manifest,
        out_dir=tmp_path / "out",
    )

    assert result["status"] == "ready_external_return_found"
    assert result["complete_candidate_count"] == 1
    assert result["ready_external_return_count"] == 1
    assert result["best_candidate"]["path"].endswith("completed_external_audit.csv")
    assert result["best_candidate"]["intake_decision"] == "ready_for_formal_external_audit_analysis"
    assert result["best_candidate"]["completion_rate"] == 1.0
    report = (tmp_path / "out/external_audit_intake_report.md").read_text(encoding="utf-8")
    assert "Run scripts/check_external_audit_return.py" in report


def test_external_audit_intake_does_not_treat_blank_sheet_as_complete(tmp_path: Path):
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps({"selected_instance_ids": ["task-a"]}), encoding="utf-8")
    blank = tmp_path / "downloads" / "external_audit_sheet.csv"
    _write_audit_csv(blank, ["task-a"], complete=False)

    result = build_external_audit_intake_report(
        search_dirs=[tmp_path / "downloads"],
        explicit_candidates=[],
        manifest_path=manifest,
        out_dir=tmp_path / "out",
    )

    assert result["status"] == "no_complete_candidate_found"
    assert result["complete_candidate_count"] == 0
    assert result["best_candidate"]["blank_label_cells"] == len(EVIDENCE_CATEGORIES)


def test_external_audit_intake_flags_complete_full_sheet_as_unverified(tmp_path: Path):
    selected = ["task-a", "task-b"]
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps({"selected_instance_ids": selected}), encoding="utf-8")
    full_sheet = tmp_path / "downloads" / "annotation_sheet_completed_annotation.csv"
    extra_ids = [f"extra-{index}" for index in range(10)]
    _write_audit_csv(full_sheet, selected + extra_ids, complete=True)

    result = build_external_audit_intake_report(
        search_dirs=[tmp_path / "downloads"],
        explicit_candidates=[],
        manifest_path=manifest,
        out_dir=tmp_path / "out",
    )

    assert result["status"] == "complete_but_unverified_candidate_found"
    assert result["complete_candidate_count"] == 1
    assert result["ready_external_return_count"] == 0
    assert result["best_candidate"]["intake_decision"] == "complete_but_independence_unverified"
    assert result["best_candidate"]["warnings"]

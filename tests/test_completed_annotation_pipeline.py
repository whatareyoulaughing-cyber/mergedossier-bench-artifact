import csv
import importlib.util
from pathlib import Path

from mergedossier_bench.label_studio import CSV_BASE_FIELDS, EVIDENCE_CATEGORIES


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "run_completed_annotation_pipeline.py"
SPEC = importlib.util.spec_from_file_location("run_completed_annotation_pipeline", SCRIPT_PATH)
assert SPEC is not None
pipeline = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(pipeline)

run_pipeline = pipeline.run_pipeline


def _write_csv(path: Path, complete: bool = True) -> None:
    fields = list(CSV_BASE_FIELDS)
    for category in EVIDENCE_CATEGORIES:
        fields.extend([f"{category}_label", f"{category}_comment"])
    fields.extend(["overall_acceptability", "review_confidence"])
    rows = []
    for instance_id, group_id, repeat, label in (
        ("task-a", "task-a", "false", "present"),
        ("task-a__repeat_1", "task-a", "true", "present"),
    ):
        row = {field: "" for field in fields}
        row.update(
            {
                "annotator_id": "solo",
                "instance_id": instance_id,
                "reliability_group_id": group_id,
                "is_reliability_repeat": repeat,
                "source": "test",
                "repo": "owner/repo",
                "pr_number": "1",
                "pr_url": "https://example.test/pull/1",
                "title": "Test PR",
                "existing_score": "10",
                "missing_evidence": "",
                "dossier_text": "intent: present",
                "overall_acceptability": "thin",
                "review_confidence": "4",
            }
        )
        for category in EVIDENCE_CATEGORIES:
            row[f"{category}_label"] = label if complete else ""
        rows.append(row)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def test_completed_annotation_pipeline_from_existing_csv(tmp_path):
    csv_path = tmp_path / "completed.csv"
    out = tmp_path / "paper_results"
    _write_csv(csv_path, complete=True)

    result = run_pipeline("unused.xlsx", csv_path, out, skip_export=True)

    assert result["status"] == "pass"
    assert result["summary"]["total_annotations"] == 2
    assert (out / "annotation_label_distribution_table.tex").exists()
    assert (out / "adjudication_sheet.csv").exists()
    assert (out / "post_annotation_pipeline_summary.md").exists()


def test_completed_annotation_pipeline_reports_invalid_annotations(tmp_path):
    csv_path = tmp_path / "incomplete.csv"
    out = tmp_path / "paper_results"
    _write_csv(csv_path, complete=False)

    result = run_pipeline("unused.xlsx", csv_path, out, skip_export=True)

    assert result["status"] == "invalid_annotations"
    assert result["validation_errors"]
    assert (out / "completed_annotation_csv_validation.json").exists()
    assert (out / "post_annotation_pipeline_summary.md").exists()

import json
import subprocess
import sys
import csv
from pathlib import Path

from mergedossier_bench.annotation_stats import build_agreement_summary
from mergedossier_bench.cli import main
from mergedossier_bench.label_studio import (
    EVIDENCE_CATEGORIES,
    parse_annotation_csv,
    parse_label_studio_export,
    validate_annotation_csv,
)


def _jsonl_rows(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def test_label_studio_config_generation_contains_all_categories(tmp_path):
    out = tmp_path / "label_studio_config.xml"
    result = subprocess.run(
        [sys.executable, "scripts/generate_label_studio_config.py", "--out", str(out)],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    xml = out.read_text(encoding="utf-8")
    for category in EVIDENCE_CATEGORIES:
        assert f'name="{category}"' in xml
        assert f'name="{category}_comment"' in xml
    for label in ("present", "partially_present", "missing", "not_applicable"):
        assert f'value="{label}"' in xml


def test_export_annotation_tasks_works_for_corpus_directory(tmp_path):
    out = tmp_path / "annotation_tasks.json"
    code = main(["export-annotation-tasks", "--dossiers", "examples/corpus", "--out", str(out)])

    assert code == 0
    tasks = json.loads(out.read_text(encoding="utf-8"))
    assert len(tasks) == 4
    first = tasks[0]["data"]
    for key in (
        "instance_id",
        "source",
        "repo",
        "pr_number",
        "pr_url",
        "title",
        "issue_summary",
        "changed_files_summary",
        "dossier_text",
        "evidence_sections",
        "provenance_sections",
        "existing_score",
        "missing_evidence",
    ):
        assert key in first


def test_export_annotation_tasks_works_for_jsonl(tmp_path):
    out = tmp_path / "annotation_tasks_jsonl.json"
    code = main(
        [
            "export-annotation-tasks",
            "--dossiers",
            "examples/corpus/toy_dossiers.jsonl",
            "--out",
            str(out),
        ]
    )

    assert code == 0
    tasks = json.loads(out.read_text(encoding="utf-8"))
    assert len(tasks) == 4
    assert tasks[0]["data"]["source"].endswith("toy_dossiers.jsonl:1")


def test_label_studio_export_parser_normalizes_toy_export():
    records = parse_label_studio_export("examples/annotations/toy_label_studio_export.json")

    assert len(records) == 6
    assert records[0]["instance_id"] == "toy-complete-1"
    assert records[0]["annotator_id"] == "ann-a"
    assert records[0]["category_labels"]["intent_evidence"] == "present"
    assert records[0]["review_confidence"] == 5
    risk_record = next(record for record in records if record["raw_annotation_id"] == 2001)
    assert risk_record["category_comments"]["risk_analysis"] == "No risk discussion is visible."


def test_annotation_stats_writes_required_outputs(tmp_path):
    out = tmp_path / "annotation_stats"
    code = main(
        [
            "annotation-stats",
            "--annotations",
            "examples/annotations/toy_label_studio_export.json",
            "--out",
            str(out),
        ]
    )

    assert code == 0
    for name in (
        "annotation_records.jsonl",
        "agreement_summary.json",
        "agreement_summary.md",
        "disagreement_cases.jsonl",
    ):
        assert (out / name).exists()
    summary = json.loads((out / "agreement_summary.json").read_text(encoding="utf-8"))
    assert summary["total_tasks"] == 3
    assert summary["total_annotations"] == 6
    assert summary["annotator_count"] == 2
    assert summary["tasks_with_high_disagreement"]
    assert len(_jsonl_rows(out / "annotation_records.jsonl")) == 6


def test_create_reliability_sample_appends_repeat_tasks(tmp_path):
    tasks = tmp_path / "tasks.json"
    export_code = main(["export-annotation-tasks", "--dossiers", "examples/corpus", "--out", str(tasks)])
    out = tmp_path / "tasks_with_repeats.json"

    code = main(
        [
            "create-reliability-sample",
            "--tasks",
            str(tasks),
            "--out",
            str(out),
            "--rate",
            "0.25",
            "--min-count",
            "2",
            "--seed",
            "7",
        ]
    )

    assert export_code == 0
    assert code == 0
    output_tasks = json.loads(out.read_text(encoding="utf-8"))
    repeats = [task for task in output_tasks if task["data"].get("is_reliability_repeat")]
    assert len(output_tasks) == 6
    assert len(repeats) == 2
    assert all("__repeat_" in task["data"]["instance_id"] for task in repeats)
    assert all(task["data"]["reliability_group_id"] for task in repeats)


def test_export_annotation_csv_template_from_tasks(tmp_path):
    tasks = tmp_path / "tasks.json"
    csv_out = tmp_path / "annotation_sheet.csv"

    assert main(["export-annotation-tasks", "--dossiers", "examples/corpus", "--out", str(tasks)]) == 0
    code = main(["export-annotation-csv", "--tasks", str(tasks), "--out", str(csv_out), "--annotator-id", "solo"])

    assert code == 0
    with csv_out.open("r", encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    assert len(rows) == 4
    assert rows[0]["annotator_id"] == "solo"
    assert "intent_evidence_label" in rows[0]
    assert "ownership_handoff_comment" in rows[0]


def test_annotation_stats_accepts_completed_csv(tmp_path):
    csv_path = tmp_path / "completed.csv"
    fields = [
        "annotator_id",
        "instance_id",
        "reliability_group_id",
        "is_reliability_repeat",
    ]
    for category in EVIDENCE_CATEGORIES:
        fields.extend([f"{category}_label", f"{category}_comment"])
    fields.extend(["overall_acceptability", "review_confidence"])
    rows = []
    for instance_id, group_id, is_repeat, label in (
        ("task-a", "task-a", "false", "present"),
        ("task-a__repeat_1", "task-a", "true", "present"),
        ("task-b", "task-b", "false", "missing"),
        ("task-b__repeat_1", "task-b", "true", "present"),
    ):
        row = {field: "" for field in fields}
        row.update(
            {
                "annotator_id": "solo",
                "instance_id": instance_id,
                "reliability_group_id": group_id,
                "is_reliability_repeat": is_repeat,
                "overall_acceptability": "thin",
                "review_confidence": "4",
            }
        )
        for category in EVIDENCE_CATEGORIES:
            row[f"{category}_label"] = label
            row[f"{category}_comment"] = ""
        rows.append(row)
    with csv_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)

    parsed = parse_annotation_csv(csv_path)
    assert len(parsed) == 4
    assert parsed[0]["review_confidence"] == 4

    out = tmp_path / "annotation_stats"
    code = main(["annotation-stats", "--annotations", str(csv_path), "--out", str(out)])

    assert code == 0
    summary = json.loads((out / "agreement_summary.json").read_text(encoding="utf-8"))
    assert summary["annotator_count"] == 1
    assert summary["reliability_repeat_annotations"] == 2
    assert summary["percent_agreement_by_category"]["intent_evidence"] == 0.5
    assert summary["cohen_kappa_by_category"]["intent_evidence"] is None


def test_validate_annotation_csv_accepts_complete_sheet(tmp_path):
    csv_path = tmp_path / "complete.csv"
    fields = [
        "annotator_id",
        "instance_id",
        "reliability_group_id",
        "is_reliability_repeat",
        "source",
        "repo",
        "pr_number",
        "pr_url",
        "title",
        "existing_score",
        "missing_evidence",
        "dossier_text",
    ]
    for category in EVIDENCE_CATEGORIES:
        fields.extend([f"{category}_label", f"{category}_comment"])
    fields.extend(["overall_acceptability", "review_confidence"])
    row = {field: "" for field in fields}
    row.update(
        {
            "annotator_id": "solo",
            "instance_id": "task-a",
            "reliability_group_id": "task-a",
            "is_reliability_repeat": "false",
            "overall_acceptability": "adequate",
            "review_confidence": "4",
        }
    )
    for category in EVIDENCE_CATEGORIES:
        row[f"{category}_label"] = "present"
    with csv_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerow(row)

    result = validate_annotation_csv(csv_path)
    assert result["valid"] is True
    assert result["completed_rows"] == 1
    assert main(["validate-annotation-csv", "--annotations", str(csv_path)]) == 0


def test_validate_annotation_csv_flags_missing_required_labels(tmp_path):
    tasks = tmp_path / "tasks.json"
    csv_out = tmp_path / "annotation_sheet.csv"

    assert main(["export-annotation-tasks", "--dossiers", "examples/corpus", "--out", str(tasks)]) == 0
    assert main(["export-annotation-csv", "--tasks", str(tasks), "--out", str(csv_out)]) == 0

    result = validate_annotation_csv(csv_out)
    assert result["valid"] is False
    assert result["missing_label_cells"]
    assert main(["validate-annotation-csv", "--annotations", str(csv_out)]) == 1
    assert main(["validate-annotation-csv", "--annotations", str(csv_out), "--allow-incomplete"]) == 0


def test_single_annotator_reliability_group_agreement():
    records = []
    labels = [
        ("task-a", "task-a", False, "present"),
        ("task-a-repeat", "task-a", True, "present"),
        ("task-b", "task-b", False, "present"),
        ("task-b-repeat", "task-b", True, "missing"),
    ]
    for instance_id, group_id, is_repeat, label in labels:
        records.append(
            {
                "task_id": instance_id,
                "instance_id": instance_id,
                "reliability_group_id": group_id,
                "is_reliability_repeat": is_repeat,
                "annotator_id": "solo",
                "category_labels": {category: label for category in EVIDENCE_CATEGORIES},
                "category_comments": {category: "" for category in EVIDENCE_CATEGORIES},
                "overall_acceptability": None,
                "review_confidence": None,
                "raw_annotation_id": instance_id,
                "created_at": None,
                "updated_at": None,
            }
        )

    summary = build_agreement_summary(records)
    assert summary["annotator_count"] == 1
    assert summary["reliability_repeat_annotations"] == 2
    assert summary["percent_agreement_by_category"]["intent_evidence"] == 0.5
    assert summary["cohen_kappa_by_category"]["intent_evidence"] is None


def test_percent_agreement_and_kappa_on_controlled_fixture():
    records = []
    pairs = [
        ("a", "present", "present"),
        ("b", "present", "missing"),
        ("c", "missing", "missing"),
        ("d", "missing", "present"),
    ]
    for instance_id, left, right in pairs:
        for annotator_id, label in (("ann-a", left), ("ann-b", right)):
            records.append(
                {
                    "task_id": instance_id,
                    "instance_id": instance_id,
                    "annotator_id": annotator_id,
                    "category_labels": {category: label for category in EVIDENCE_CATEGORIES},
                    "category_comments": {category: "" for category in EVIDENCE_CATEGORIES},
                    "overall_acceptability": None,
                    "review_confidence": None,
                    "raw_annotation_id": f"{instance_id}-{annotator_id}",
                    "created_at": None,
                    "updated_at": None,
                }
            )

    summary = build_agreement_summary(records)
    assert summary["percent_agreement_by_category"]["intent_evidence"] == 0.5
    assert summary["cohen_kappa_by_category"]["intent_evidence"] == 0.0

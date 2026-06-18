import csv
import importlib.util
from pathlib import Path

import pytest

from mergedossier_bench.label_studio import EVIDENCE_CATEGORIES
from mergedossier_bench.label_studio import CSV_BASE_FIELDS


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "build_paper_results_from_annotations.py"
SPEC = importlib.util.spec_from_file_location("build_paper_results_from_annotations", SCRIPT_PATH)
assert SPEC is not None
builder = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(builder)

build_paper_results = builder.build_paper_results
latex_escape = builder.latex_escape
percent = builder.percent


def _write_completed_csv(path: Path, blank_label: bool = False) -> None:
    fields = list(CSV_BASE_FIELDS)
    for category in EVIDENCE_CATEGORIES:
        fields.extend([f"{category}_label", f"{category}_comment"])
    fields.extend(["overall_acceptability", "review_confidence"])

    rows = []
    for instance_id, group_id, repeat, label in (
        ("task-a", "task-a", "false", "present"),
        ("task-a__repeat_1", "task-a", "true", "present"),
        ("task-b", "task-b", "false", "missing"),
        ("task-b__repeat_1", "task-b", "true", "partially_present"),
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
            row[f"{category}_label"] = "" if blank_label and category == EVIDENCE_CATEGORIES[0] else label
        rows.append(row)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def test_format_helpers():
    assert latex_escape("risk_analysis & 50%") == r"risk\_analysis \& 50\%"
    assert percent(0.5) == r"50.0\%"
    assert percent(None) == "--"


def test_build_paper_results_from_completed_csv(tmp_path):
    csv_path = tmp_path / "completed.csv"
    out = tmp_path / "paper_results"
    _write_completed_csv(csv_path)

    summary = build_paper_results(csv_path, out)

    assert summary["annotator_count"] == 1
    assert (out / "annotation_stats" / "agreement_summary.json").exists()
    assert (out / "annotation_label_distribution_table.tex").exists()
    assert (out / "annotation_agreement_table.tex").exists()
    assert (out / "pilot_statistical_treatment.json").exists()
    assert (out / "pilot_statistical_treatment.md").exists()
    assert (out / "annotation_results_summary.md").exists()
    assert (out / "adjudication_sheet.csv").exists()
    assert (out / "adjudication_sheet.md").exists()
    assert "intent\\_evidence" in (out / "annotation_label_distribution_table.tex").read_text(encoding="utf-8")
    assert "Delayed-repeat self-consistency" in (out / "annotation_agreement_table.tex").read_text(encoding="utf-8")
    treatment = (out / "pilot_statistical_treatment.json").read_text(encoding="utf-8")
    assert "positive_evidence_concentration_hhi" in treatment
    assert "coverage_wilson_95_by_category" in treatment


def test_build_paper_results_rejects_incomplete_csv(tmp_path):
    csv_path = tmp_path / "incomplete.csv"
    out = tmp_path / "paper_results"
    _write_completed_csv(csv_path, blank_label=True)

    with pytest.raises(ValueError):
        build_paper_results(csv_path, out)
    assert (out / "annotation_csv_validation.json").exists()

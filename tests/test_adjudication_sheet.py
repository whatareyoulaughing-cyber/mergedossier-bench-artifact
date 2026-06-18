import csv
import importlib.util
import json
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "build_adjudication_sheet.py"
SPEC = importlib.util.spec_from_file_location("build_adjudication_sheet", SCRIPT_PATH)
assert SPEC is not None
adjudication = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(adjudication)

build_adjudication_sheet = adjudication.build_adjudication_sheet
build_adjudication_rows = adjudication.build_adjudication_rows


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.write_text("\n".join(json.dumps(row) for row in rows) + ("\n" if rows else ""), encoding="utf-8")


def test_build_adjudication_rows_expands_disagreements():
    cases = [
        {
            "reliability_group_id": "task-a",
            "severity": 2,
            "disagreements": [{"category": "test_evidence", "labels": ["missing", "present"], "severity": 2}],
        }
    ]
    records = [
        {
            "instance_id": "task-a",
            "reliability_group_id": "task-a",
            "is_reliability_repeat": False,
            "annotator_id": "solo",
            "category_labels": {"test_evidence": "missing"},
            "category_comments": {"test_evidence": "No tests visible."},
        },
        {
            "instance_id": "task-a__repeat_1",
            "reliability_group_id": "task-a",
            "is_reliability_repeat": True,
            "annotator_id": "solo",
            "category_labels": {"test_evidence": "present"},
            "category_comments": {"test_evidence": ""},
        },
    ]

    rows = build_adjudication_rows(cases, records)

    assert len(rows) == 1
    assert rows[0]["priority"] == "high"
    assert rows[0]["labels_seen"] == "missing;present"
    assert "task-a:primary:missing" in rows[0]["record_labels"]
    assert "No tests visible" in rows[0]["comments_seen"]


def test_build_adjudication_sheet_writes_csv_and_markdown(tmp_path):
    stats_dir = tmp_path / "stats"
    stats_dir.mkdir()
    _write_jsonl(
        stats_dir / "disagreement_cases.jsonl",
        [
            {
                "reliability_group_id": "task-a",
                "severity": 1,
                "disagreements": [{"category": "risk_analysis", "labels": ["missing", "partially_present"], "severity": 1}],
            }
        ],
    )
    _write_jsonl(
        stats_dir / "annotation_records.jsonl",
        [
            {
                "instance_id": "task-a",
                "reliability_group_id": "task-a",
                "is_reliability_repeat": False,
                "annotator_id": "solo",
                "category_labels": {"risk_analysis": "missing"},
                "category_comments": {"risk_analysis": ""},
            }
        ],
    )
    out_csv = tmp_path / "adjudication.csv"
    out_md = tmp_path / "adjudication.md"

    rows = build_adjudication_sheet(stats_dir, out_csv, out_md)

    assert len(rows) == 1
    with out_csv.open("r", encoding="utf-8-sig", newline="") as f:
        csv_rows = list(csv.DictReader(f))
    assert csv_rows[0]["category"] == "risk_analysis"
    assert "Adjudication Sheet Summary" in out_md.read_text(encoding="utf-8")


def test_build_adjudication_sheet_handles_no_disagreements(tmp_path):
    stats_dir = tmp_path / "stats"
    stats_dir.mkdir()
    _write_jsonl(stats_dir / "disagreement_cases.jsonl", [])
    _write_jsonl(stats_dir / "annotation_records.jsonl", [])
    out_csv = tmp_path / "adjudication.csv"
    out_md = tmp_path / "adjudication.md"

    rows = build_adjudication_sheet(stats_dir, out_csv, out_md)

    assert rows == []
    with out_csv.open("r", encoding="utf-8-sig", newline="") as f:
        assert list(csv.DictReader(f)) == []
    assert "No adjudication rows" in out_md.read_text(encoding="utf-8")

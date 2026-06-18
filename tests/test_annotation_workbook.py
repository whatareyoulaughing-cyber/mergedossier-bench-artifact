import csv
import importlib.util
from pathlib import Path

import pytest


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "export_annotation_workbook.py"
SPEC = importlib.util.spec_from_file_location("export_annotation_workbook", SCRIPT_PATH)
assert SPEC is not None
export_annotation_workbook = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(export_annotation_workbook)

EXPORT_CSV_SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "export_annotation_csv_from_workbook.py"
EXPORT_CSV_SPEC = importlib.util.spec_from_file_location("export_annotation_csv_from_workbook", EXPORT_CSV_SCRIPT_PATH)
assert EXPORT_CSV_SPEC is not None
export_annotation_csv_from_workbook = importlib.util.module_from_spec(EXPORT_CSV_SPEC)
assert EXPORT_CSV_SPEC.loader is not None
EXPORT_CSV_SPEC.loader.exec_module(export_annotation_csv_from_workbook)

label_columns = export_annotation_workbook.label_columns
comment_columns = export_annotation_workbook.comment_columns
build_workbook = export_annotation_workbook.build_workbook
export_annotation_csv = export_annotation_csv_from_workbook.export_annotation_csv


def test_label_and_comment_column_detection():
    headers = [
        "instance_id",
        "intent_evidence_label",
        "intent_evidence_comment",
        "ownership_handoff_label",
        "overall_acceptability",
    ]

    assert label_columns(headers) == ["intent_evidence_label", "ownership_handoff_label"]
    assert comment_columns(headers) == ["intent_evidence_comment"]


def test_build_workbook_with_openpyxl_when_available(tmp_path):
    openpyxl = pytest.importorskip("openpyxl")
    csv_path = tmp_path / "annotation.csv"
    out = tmp_path / "annotation.xlsx"
    headers = [
        "annotator_id",
        "instance_id",
        "reliability_group_id",
        "is_reliability_repeat",
        "dossier_text",
        "intent_evidence_label",
        "intent_evidence_comment",
        "ownership_handoff_label",
        "ownership_handoff_comment",
    ]
    row = {header: "" for header in headers}
    row.update(
        {
            "annotator_id": "solo",
            "instance_id": "task-a",
            "reliability_group_id": "task-a",
            "is_reliability_repeat": "false",
            "dossier_text": "intent: present",
        }
    )
    with csv_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        writer.writerow(row)

    build_workbook(csv_path, out)

    assert out.exists()
    wb = openpyxl.load_workbook(out)
    assert {"Annotation", "Instructions", "Completion", "LabelValues"}.issubset(set(wb.sheetnames))
    assert wb["Annotation"].freeze_panes == "A2"
    assert wb["Completion"]["B4"].value == 2


def test_export_annotation_csv_from_workbook_when_openpyxl_available(tmp_path):
    openpyxl = pytest.importorskip("openpyxl")
    workbook_path = tmp_path / "annotation.xlsx"
    csv_out = tmp_path / "completed.csv"

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Annotation"
    ws.append(["instance_id", "intent_evidence_label", "intent_evidence_comment"])
    ws.append(["task-a", "present", "Clear intent evidence."])
    wb.save(workbook_path)

    export_annotation_csv(workbook_path, csv_out)

    with csv_out.open("r", encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    assert rows == [
        {
            "instance_id": "task-a",
            "intent_evidence_label": "present",
            "intent_evidence_comment": "Clear intent evidence.",
        }
    ]

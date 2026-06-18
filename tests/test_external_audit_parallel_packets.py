import csv
import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "build_external_audit_parallel_packets",
    ROOT / "scripts" / "build_external_audit_parallel_packets.py",
)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
build_parallel_packets = MODULE.build_parallel_packets
merge_completed_partials = MODULE.merge_completed_partials


HEADERS = [
    "instance_id",
    "is_reliability_repeat",
    "intent_label",
    "intent_comment",
    "test_label",
    "test_comment",
]


def _write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=HEADERS)
        writer.writeheader()
        writer.writerows(rows)


def _rows(n: int) -> list[dict[str, str]]:
    return [
        {
            "instance_id": f"task-{index:02d}",
            "is_reliability_repeat": "False",
            "intent_label": "",
            "intent_comment": "",
            "test_label": "",
            "test_comment": "",
        }
        for index in range(n)
    ]


def test_build_parallel_packets_splits_rows_without_overlap(tmp_path: Path):
    slice_dir = tmp_path / "slice"
    rows = _rows(6)
    _write_csv(slice_dir / "external_audit_sheet.csv", rows)
    (slice_dir / "external_audit_manifest.json").write_text(
        json.dumps({"selected_tasks": 6, "selected_instance_ids": [row["instance_id"] for row in rows]}),
        encoding="utf-8",
    )

    summary = build_parallel_packets(slice_dir, tmp_path / "parallel", parts=3, make_workbook=False)

    assert summary["parts"] == 3
    assert summary["rows"] == 6
    ids = [item for packet in summary["packets"] for item in packet["instance_ids"]]
    assert sorted(ids) == [row["instance_id"] for row in rows]
    assert len(ids) == len(set(ids))
    assert (tmp_path / "parallel" / "MergeDossier-external-audit-part_01.zip").exists()
    assert (tmp_path / "parallel" / "README_PARALLEL_EXTERNAL_AUDIT.md").exists()


def test_merge_completed_partials_preserves_unique_rows(tmp_path: Path):
    left = tmp_path / "part_01.csv"
    right = tmp_path / "part_02.csv"
    _write_csv(left, _rows(2))
    _write_csv(right, _rows(4)[2:])

    summary = merge_completed_partials([left, right], tmp_path / "merged" / "external.csv")

    assert summary["rows"] == 4
    with (tmp_path / "merged" / "external.csv").open("r", encoding="utf-8") as handle:
        merged = list(csv.DictReader(handle))
    assert [row["instance_id"] for row in merged] == ["task-00", "task-01", "task-02", "task-03"]
    assert (tmp_path / "merged" / "merged_external_audit_manifest.json").exists()


import csv
import importlib.util
import json
from pathlib import Path

from mergedossier_bench.label_studio import EVIDENCE_CATEGORIES


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "check_parallel_external_audit_returns",
    ROOT / "scripts" / "check_parallel_external_audit_returns.py",
)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
check_parallel_returns = MODULE.check_parallel_returns


FIELDNAMES = ["instance_id", "is_reliability_repeat"] + [
    field for category in EVIDENCE_CATEGORIES for field in (f"{category}_label", f"{category}_comment")
]


def _row(instance_id: str, label: str = "present") -> dict[str, str]:
    row = {field: "" for field in FIELDNAMES}
    row["instance_id"] = instance_id
    row["is_reliability_repeat"] = "False"
    for category in EVIDENCE_CATEGORIES:
        row[f"{category}_label"] = label
    return row


def _write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)


def _write_part_manifest(packet_dir: Path, part_id: str, ids: list[str]) -> None:
    part_dir = packet_dir / part_id
    part_dir.mkdir(parents=True, exist_ok=True)
    (part_dir / "external_audit_manifest.json").write_text(
        json.dumps({"selected_instance_ids": ids}),
        encoding="utf-8",
    )


def test_parallel_return_gate_merges_complete_parts(tmp_path: Path):
    packet_dir = tmp_path / "packets"
    _write_part_manifest(packet_dir, "part_01", ["task-a"])
    _write_part_manifest(packet_dir, "part_02", ["task-b"])
    part_01 = tmp_path / "part_01.csv"
    part_02 = tmp_path / "part_02.csv"
    primary = tmp_path / "primary.csv"
    _write_csv(part_01, [_row("task-a")])
    _write_csv(part_02, [_row("task-b")])
    _write_csv(primary, [_row("task-a"), _row("task-b")])
    full_manifest = tmp_path / "manifest.json"
    full_manifest.write_text(json.dumps({"selected_instance_ids": ["task-a", "task-b"]}), encoding="utf-8")

    result = check_parallel_returns(
        [part_01, part_02],
        packet_dir,
        tmp_path / "out",
        primary_csv=primary,
        full_manifest=full_manifest,
    )

    assert result["status"] == "complete"
    assert result["all_parts_complete"] is True
    assert result["formal_return_status"] == "complete"
    assert (tmp_path / "out" / "merged_external_audit_sheet.csv").exists()
    assert (tmp_path / "out" / "formal_return_gate" / "external_audit_summary.json").exists()


def test_parallel_return_gate_reports_incomplete_part(tmp_path: Path):
    packet_dir = tmp_path / "packets"
    _write_part_manifest(packet_dir, "part_01", ["task-a"])
    _write_part_manifest(packet_dir, "part_02", ["task-b"])
    part_01 = tmp_path / "part_01.csv"
    part_02 = tmp_path / "part_02.csv"
    primary = tmp_path / "primary.csv"
    _write_csv(part_01, [_row("task-a")])
    incomplete = _row("task-b")
    incomplete[f"{EVIDENCE_CATEGORIES[0]}_label"] = ""
    _write_csv(part_02, [incomplete])
    _write_csv(primary, [_row("task-a"), _row("task-b")])
    full_manifest = tmp_path / "manifest.json"
    full_manifest.write_text(json.dumps({"selected_instance_ids": ["task-a", "task-b"]}), encoding="utf-8")

    result = check_parallel_returns(
        [part_01, part_02],
        packet_dir,
        tmp_path / "out",
        primary_csv=primary,
        full_manifest=full_manifest,
    )

    assert result["status"] == "incomplete"
    assert result["all_parts_complete"] is False
    assert result["part_results"][1]["blank_label_cells"] == 1
    assert result["merged_csv"] is None
    assert (tmp_path / "out" / "part_02" / "AUDITOR_FEEDBACK_REQUEST.md").exists()


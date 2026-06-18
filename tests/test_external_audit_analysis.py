import csv
import importlib.util
from pathlib import Path

from mergedossier_bench.label_studio import EVIDENCE_CATEGORIES


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "analyze_external_audit_slice", ROOT / "scripts" / "analyze_external_audit_slice.py"
)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
analyze_external_audit = MODULE.analyze_external_audit


BASE_COLUMNS = [
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
LABEL_COLUMNS = [item for category in EVIDENCE_CATEGORIES for item in (f"{category}_label", f"{category}_comment")]
TAIL_COLUMNS = ["overall_acceptability", "review_confidence"]
FIELDNAMES = BASE_COLUMNS + LABEL_COLUMNS + TAIL_COLUMNS


def _row(instance_id: str, annotator: str, labels: dict[str, str] | None = None) -> dict[str, str]:
    labels = labels or {}
    row = {field: "" for field in FIELDNAMES}
    row.update(
        {
            "annotator_id": annotator,
            "instance_id": instance_id,
            "reliability_group_id": instance_id,
            "is_reliability_repeat": "False",
            "source": "aidev",
            "repo": "owner/repo",
            "pr_number": "1",
            "pr_url": "https://github.com/owner/repo/pull/1",
            "title": "Fixture",
            "dossier_text": "Fixture dossier",
        }
    )
    for category in EVIDENCE_CATEGORIES:
        row[f"{category}_label"] = labels.get(category, "")
        row[f"{category}_comment"] = f"{category} comment"
    return row


def _write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)


def test_external_audit_analysis_reports_incomplete_blank_cells(tmp_path: Path):
    primary = tmp_path / "primary.csv"
    external = tmp_path / "external.csv"
    out = tmp_path / "out"
    filled = {category: "present" for category in EVIDENCE_CATEGORIES}
    _write_csv(primary, [_row("task-a", "solo", filled)])
    _write_csv(external, [_row("task-a", "external")])

    summary = analyze_external_audit(primary, external, out)

    assert summary["status"] == "incomplete"
    assert len(summary["blank_label_cells"]) == len(EVIDENCE_CATEGORIES)
    assert not (out / "external_audit_agreement_by_category.csv").exists()
    assert "not complete" in (out / "external_audit_summary.md").read_text(encoding="utf-8")


def test_external_audit_analysis_writes_agreement_outputs_for_complete_slice(tmp_path: Path):
    primary = tmp_path / "primary.csv"
    external = tmp_path / "external.csv"
    out = tmp_path / "out"
    labels_a = {category: "present" for category in EVIDENCE_CATEGORIES}
    labels_b = {category: "missing" for category in EVIDENCE_CATEGORIES}
    external_a = dict(labels_a)
    external_b = dict(labels_b)
    external_b["intent_evidence"] = "present"

    _write_csv(primary, [_row("task-a", "solo", labels_a), _row("task-b", "solo", labels_b)])
    _write_csv(external, [_row("task-a", "external", external_a), _row("task-b", "external", external_b)])

    summary = analyze_external_audit(primary, external, out)

    assert summary["status"] == "complete"
    rows = list(csv.DictReader((out / "external_audit_agreement_by_category.csv").open(encoding="utf-8")))
    intent = next(row for row in rows if row["category"] == "intent_evidence")
    assert intent["pairs"] == "2"
    assert intent["exact_agreement"] == "0.5"
    assert (out / "paper_table_external_audit_agreement.tex").exists()
    assert (out / "external_audit_disagreements.csv").exists()
    assert "external audit slice" in (out / "external_audit_summary.md").read_text(encoding="utf-8").lower()

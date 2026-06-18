import csv
import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / "scripts" / "build_sanitized_population_frame.py"
SPEC = importlib.util.spec_from_file_location("build_sanitized_population_frame", SCRIPT_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
build_sanitized_frame = MODULE.build_sanitized_frame


def test_sanitized_population_frame_drops_text_columns_and_marks_sample(tmp_path: Path):
    frame = tmp_path / "frame.csv"
    sample = tmp_path / "sample.csv"
    out = tmp_path / "sanitized.csv"
    report = tmp_path / "report.json"

    fieldnames = [
        "instance_id",
        "repo",
        "pr_number",
        "pr_url",
        "source",
        "author_type",
        "agent_name",
        "task_type",
        "language",
        "outcome",
        "sample_split",
        "notes",
        "agent_tool",
        "created_at",
        "changed_file_count",
        "commit_count",
        "comment_count",
        "review_count",
        "artifact_completeness",
        "eligibility",
        "eligibility_reason",
        "size_tercile",
        "sampling_weight",
        "title",
        "body",
        "files_changed",
        "commit_messages",
        "comments",
        "reviews",
        "ci_status",
    ]
    with frame.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerow(
            {
                "instance_id": "repo-1-1",
                "repo": "owner/repo",
                "pr_number": "1",
                "pr_url": "https://github.com/owner/repo/pull/1",
                "source": "aidev",
                "author_type": "ai",
                "agent_name": "Codex",
                "agent_tool": "Codex",
                "task_type": "fix",
                "language": "Python",
                "outcome": "merged",
                "sample_split": "frame",
                "notes": "raw note that should not ship",
                "created_at": "2026-01-01T00:00:00Z",
                "changed_file_count": "2",
                "commit_count": "1",
                "comment_count": "3",
                "review_count": "1",
                "artifact_completeness": "complete",
                "eligibility": "eligible",
                "eligibility_reason": "ok",
                "size_tercile": "small",
                "sampling_weight": "1.0",
                "title": "secret-like title should be dropped",
                "body": "body should be dropped",
                "files_changed": "src/app.py",
                "commit_messages": "commit text",
                "comments": "review comment text",
                "reviews": "review text",
                "ci_status": "1.0",
            }
        )
    with sample.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["instance_id"])
        writer.writeheader()
        writer.writerow({"instance_id": "repo-1-1"})

    summary = build_sanitized_frame(frame, out, report, sample)

    rows = list(csv.DictReader(out.open("r", encoding="utf-8", newline="")))
    assert summary["rows"] == 1
    assert summary["sample_rows_marked"] == 1
    assert rows[0]["in_sample_500"] == "true"
    assert rows[0]["source_row_index"] == "1"
    assert "title" not in rows[0]
    assert "body" not in rows[0]
    assert "comments" not in rows[0]
    assert "reviews" not in rows[0]

    report_data = json.loads(report.read_text(encoding="utf-8"))
    assert "title" in report_data["dropped_text_columns"]
    assert "comments" in report_data["dropped_text_columns"]
    assert report_data["privacy_boundary"]

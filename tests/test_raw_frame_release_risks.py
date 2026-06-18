import csv
import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / "scripts" / "scan_raw_frame_release_risks.py"
SPEC = importlib.util.spec_from_file_location("scan_raw_frame_release_risks", SCRIPT_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
scan_raw_frame_release_risks = MODULE.scan_raw_frame_release_risks


def test_scan_raw_frame_reports_secret_patterns_without_leaking_values(tmp_path: Path):
    frame = tmp_path / "frame.csv"
    out_dir = tmp_path / "risk"
    fake_token = "ghp_" + "abcdefghijklmnopqrstuvwxyz123456"
    fieldnames = [
        "instance_id",
        "repo",
        "pr_number",
        "pr_url",
        "title",
        "body",
        "comments",
        "reviews",
    ]
    with frame.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerow(
            {
                "instance_id": "owner-repo-1",
                "repo": "owner/repo",
                "pr_number": "1",
                "pr_url": "https://github.com/owner/repo/pull/1",
                "title": "ordinary fix",
                "body": f"Do not ship {fake_token} in docs",
                "comments": "looks good",
                "reviews": "",
            }
        )
        writer.writerow(
            {
                "instance_id": "owner-repo-2",
                "repo": "owner/repo",
                "pr_number": "2",
                "pr_url": "https://github.com/owner/repo/pull/2",
                "title": "ordinary docs",
                "body": "no token-like text",
                "comments": "",
                "reviews": "",
            }
        )

    summary = scan_raw_frame_release_risks(frame, out_dir, max_examples=5)

    assert summary["rows_scanned"] == 2
    assert summary["affected_rows"] == 1
    assert summary["pattern_counts"]["github_classic_pat"] == 1
    assert summary["column_counts"]["body"] == 1
    assert summary["examples_without_secret_text"][0]["instance_id"] == "owner-repo-1"

    json_text = (out_dir / "raw_frame_release_risk_summary.json").read_text(encoding="utf-8")
    md_text = (out_dir / "raw_frame_release_risk_summary.md").read_text(encoding="utf-8")
    assert fake_token not in json_text
    assert fake_token not in md_text
    assert "Do not ship" not in json_text
    assert "Do not ship" not in md_text
    assert "Use the sanitized population frame" in md_text

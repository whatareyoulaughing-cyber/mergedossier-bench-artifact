"""Synthetic perturbation checks for provenance-aware reconstruction."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from .provenance import collect_provenance, markdown_table
from .seed_builder import reconstruct_dossier_from_raw


def _raw(
    fixture_id: str,
    title: str = "Update service behavior",
    body: str = "This PR updates the service.",
    files: list[str] | None = None,
    checks: list[dict[str, str]] | None = None,
) -> dict[str, Any]:
    return {
        "instance_id": fixture_id,
        "repo": "synthetic/provenance",
        "pr_number": 1,
        "pr_url": f"https://github.com/synthetic/provenance/pull/{fixture_id}",
        "fetched_at": "2026-06-16T00:00:00Z",
        "fetch_mode": "fixture",
        "manifest_metadata": {
            "agent_name": "codex",
            "author_type": "ai_authored",
            "outcome": "open",
            "task_type": "feature",
        },
        "pr": {"title": title, "body": body, "created_at": "2026-06-16T00:00:00Z"},
        "files": [{"filename": name, "additions": 1, "deletions": 0} for name in (files or ["src/app.py"])],
        "commits": [{"message": title}],
        "reviews": [],
        "review_comments": [],
        "issue_comments": [],
        "checks": checks or [],
        "linked_issues": [],
        "errors": [],
    }


PERTURBATION_FIXTURES: list[dict[str, Any]] = [
    {
        "fixture_id": "explicit_risk",
        "perturbation": "PR body includes explicit risk paragraph.",
        "raw": _raw("explicit-risk", body="Summary: update service.\nRisk: rollback is reverting this branch."),
        "expected_category": "risk_analysis",
        "expected_status": "observed",
    },
    {
        "fixture_id": "risk_removed",
        "perturbation": "Same vague PR body without risk paragraph.",
        "raw": _raw("risk-removed", body="Summary: update service."),
        "expected_category": "risk_analysis",
        "expected_status": "missing",
    },
    {
        "fixture_id": "changed_test_file_only",
        "perturbation": "Changed test file only.",
        "raw": _raw("changed-test-file-only", body="Summary: update service.", files=["tests/test_app.py"]),
        "expected_category": "test_rationale",
        "expected_status": "inferred",
    },
    {
        "fixture_id": "tests_pytest_body",
        "perturbation": "PR body includes Tests: pytest.",
        "raw": _raw("tests-pytest-body", body="Summary: update service.\nTests: pytest"),
        "expected_category": "test_rationale",
        "expected_status": "observed",
    },
    {
        "fixture_id": "passing_ci_only",
        "perturbation": "Passing CI check only.",
        "raw": _raw("passing-ci-only", checks=[{"name": "pytest", "conclusion": "success"}]),
        "expected_category": "regression_safety",
        "expected_status": "inferred",
    },
    {
        "fixture_id": "ownership_rollout",
        "perturbation": "Body includes rollout, monitoring, and owner.",
        "raw": _raw("ownership-rollout", body="Rollout: staged. Owner: platform. Monitoring: error rate."),
        "expected_category": "ownership_handoff",
        "expected_status": "observed",
    },
    {
        "fixture_id": "agent_trace_logs",
        "perturbation": "Body includes command log / agent trace.",
        "raw": _raw("agent-trace-logs", body="Agent trace: files read. Commands run: pytest tests/test_app.py."),
        "expected_category": "agent_trace",
        "expected_status": "observed",
    },
    {
        "fixture_id": "dependency_file_change",
        "perturbation": "Dependency manifest changed.",
        "raw": _raw("dependency-file-change", files=["pyproject.toml"]),
        "expected_category": "dependency_evidence",
        "expected_status": "inferred",
    },
    {
        "fixture_id": "explicit_rationale",
        "perturbation": "Body includes explicit rationale section.",
        "raw": _raw("explicit-rationale", body="Rationale: this approach keeps the adapter simple."),
        "expected_category": "rationale_evidence",
        "expected_status": "observed",
    },
    {
        "fixture_id": "vague_body_only",
        "perturbation": "Vague body only.",
        "raw": _raw("vague-body-only", body="Update service."),
        "expected_category": "risk_analysis",
        "expected_status": "missing",
    },
]


def _observed_status(dossier: dict[str, Any], category: str) -> str:
    records = collect_provenance(dossier).get(category, [])
    if not records:
        return "missing"
    priority = {"observed": 0, "inferred": 1, "missing": 2, "not_applicable": 3}
    return sorted((str(record.get("status", "missing")) for record in records), key=lambda item: priority.get(item, 9))[0]


def run_perturbation_suite(out_dir: str | Path) -> dict[str, Any]:
    """Run deterministic reconstruction checks over synthetic fixtures."""
    output_path = Path(out_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, Any]] = []
    for fixture in PERTURBATION_FIXTURES:
        dossier = reconstruct_dossier_from_raw(fixture["raw"])
        observed = _observed_status(dossier, fixture["expected_category"])
        rows.append(
            {
                "fixture_id": fixture["fixture_id"],
                "perturbation": fixture["perturbation"],
                "expected_category": fixture["expected_category"],
                "expected_status": fixture["expected_status"],
                "observed_status": observed,
                "pass_fail": "pass" if observed == fixture["expected_status"] else "fail",
                "notes": "Deterministic provenance rule check; not evidence of external validity.",
            }
        )
    summary = {
        "total_checks": len(rows),
        "passed": sum(1 for row in rows if row["pass_fail"] == "pass"),
        "failed": sum(1 for row in rows if row["pass_fail"] == "fail"),
        "interpretation": (
            "The perturbation suite checks that deterministic reconstruction rules respond to controlled evidence signals. "
            "It does not prove that the benchmark captures all real-world evidence."
        ),
        "checks": rows,
    }
    (output_path / "perturbation_results.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    with (output_path / "paper_table_perturbation_checks.csv").open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["fixture_id", "perturbation", "expected_category", "expected_status", "observed_status", "pass_fail", "notes"],
        )
        writer.writeheader()
        writer.writerows(rows)
    table = markdown_table(
        ["fixture_id", "expected_category", "expected_status", "observed_status", "pass_fail"],
        [[row["fixture_id"], row["expected_category"], row["expected_status"], row["observed_status"], row["pass_fail"]] for row in rows],
    )
    (output_path / "perturbation_results.md").write_text(
        "\n".join(
            [
                "# Perturbation Suite",
                "",
                summary["interpretation"],
                "",
                f"- Total checks: {summary['total_checks']}",
                f"- Passed: {summary['passed']}",
                f"- Failed: {summary['failed']}",
                "",
                table,
                "",
            ]
        ),
        encoding="utf-8",
    )
    return summary

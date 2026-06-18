import csv
import importlib.util
import json
from pathlib import Path

import mergedossier_bench.population as population_module
from mergedossier_bench.label_studio import EVIDENCE_CATEGORIES
from mergedossier_bench.population import (
    availability_interval_rows,
    handoff_gap_rows,
    build_population_frame,
    read_csv_rows,
    run_population_corpus_pipeline,
    sample_population_prs,
    tipping_point_rows,
    wilson_interval,
    write_csv_rows,
    write_population_results,
)


AGENTS = ["codex", "claude_code", "copilot", "cursor", "devin"]


def _source_rows(count_per_agent: int = 120) -> list[dict[str, str]]:
    rows = []
    for agent_index, agent in enumerate(AGENTS):
        for item in range(count_per_agent):
            idx = agent_index * count_per_agent + item + 1
            rows.append(
                {
                    "repository": f"owner{agent_index}/repo{item % 7}",
                    "number": str(idx),
                    "html_url": f"https://github.com/owner{agent_index}/repo{item % 7}/pull/{idx}",
                    "source_agent": agent,
                    "title": f"{agent} update {idx}",
                    "body": "Tests: pytest. Risk: rollback by reverting this PR." if item % 3 == 0 else "Update service.",
                    "language": ["Python", "TypeScript", "Go"][item % 3],
                    "outcome": ["merged", "open", "closed"][item % 3],
                    "changed_file_count": str((item % 9) + 1),
                    "commit_count": str((item % 4) + 1),
                    "comment_count": str(item % 5),
                    "review_count": str(item % 2),
                }
            )
    rows.append({"repository": "bad/repo", "number": "999", "source_agent": "unknown"})
    return rows


def test_population_frame_normalizes_and_excludes_unknown_agents():
    frame, summary = build_population_frame(_source_rows(2))

    assert summary["frame_size"] == 11
    assert summary["eligible_size"] == 10
    assert summary["excluded_size"] == 1
    assert any(row["eligibility"] == "excluded" for row in frame)
    assert {row["size_tercile"] for row in frame if row["eligibility"] == "eligible"} <= {"small", "medium", "large"}


def test_stratified_sampler_is_deterministic_and_agent_balanced():
    frame, _ = build_population_frame(_source_rows(120))

    sample_a, report_a = sample_population_prs(frame, n=500, seed=20260616, min_per_agent=50)
    sample_b, report_b = sample_population_prs(frame, n=500, seed=20260616, min_per_agent=50)

    assert len(sample_a) == 500
    assert [row["instance_id"] for row in sample_a] == [row["instance_id"] for row in sample_b]
    assert report_a["selected_instance_ids"] == report_b["selected_instance_ids"]
    assert min(report_a["agent_sample_counts"].values()) >= 50
    assert all(row["eligibility"] == "eligible" for row in sample_a)
    assert len({row["instance_id"] for row in sample_a}) == 500


def test_population_metadata_pipeline_runs_without_network(tmp_path, monkeypatch):
    def fail_network(*args, **kwargs):
        raise AssertionError("network should not be used")

    import socket

    monkeypatch.setattr(socket, "create_connection", fail_network)
    frame, _ = build_population_frame(_source_rows(4))
    sample, _ = sample_population_prs(frame, n=20, seed=20260616, min_per_agent=2)
    manifest = tmp_path / "sample.csv"
    write_csv_rows(manifest, sample)
    out = tmp_path / "population_pipeline"

    summary = run_population_corpus_pipeline(manifest, out, live=False)

    assert summary["build_summary"]["reconstructed_dossiers"] == 20
    assert summary["annotation_tasks"] == 20
    assert summary["repeat_tasks"] == 20
    assert (out / "reports" / "provenance_audit" / "provenance_summary.json").exists()
    assert (out / "reports" / "annotation_tasks_with_repeats.json").exists()


def _write_completed_annotation_csv(path: Path, instance_ids: list[str]) -> None:
    base_fields = [
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
    fields = list(base_fields)
    for category in EVIDENCE_CATEGORIES:
        fields.extend([f"{category}_label", f"{category}_comment"])
    fields.extend(["overall_acceptability", "review_confidence"])
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        labels = ["present", "partially_present", "missing", "not_applicable"]
        for index, instance_id in enumerate(instance_ids):
            row = {field: "" for field in fields}
            row.update(
                {
                    "annotator_id": "solo",
                    "instance_id": instance_id,
                    "reliability_group_id": instance_id,
                    "is_reliability_repeat": "False",
                    "source": "test",
                }
            )
            for category in EVIDENCE_CATEGORIES:
                row[f"{category}_label"] = labels[index % len(labels)]
            writer.writerow(row)


def _sensitivity_row(category: str, present: int, partial: int, missing: int) -> dict[str, object]:
    denominator = present + partial + missing
    main = round((present + partial) / denominator, 4) if denominator else None
    strict = round(present / denominator, 4) if denominator else None
    missing_main = round(missing / denominator, 4) if denominator else None
    missing_strict = round((missing + partial) / denominator, 4) if denominator else None
    return {
        "category": category,
        "eligible_records": denominator,
        "present_count": present,
        "partial_count": partial,
        "missing_count": missing,
        "not_applicable_count": 0,
        "availability_main": main,
        "availability_strict": strict,
        "availability_conservative": strict,
        "missing_main": missing_main,
        "missing_strict": missing_strict,
        "missing_conservative": missing_strict,
    }


def _controlled_sensitivity_rows() -> list[dict[str, object]]:
    return [
        _sensitivity_row("intent_evidence", 8, 2, 0),
        _sensitivity_row("requirement_evidence", 1, 1, 8),
        _sensitivity_row("test_evidence", 4, 3, 3),
        _sensitivity_row("risk_analysis", 0, 2, 8),
        _sensitivity_row("scope_evidence", 2, 6, 2),
        _sensitivity_row("trace_evidence", 0, 0, 10),
        _sensitivity_row("dependency_evidence", 0, 0, 0),
        _sensitivity_row("regression_evidence", 0, 1, 9),
        _sensitivity_row("rationale_evidence", 0, 3, 7),
        _sensitivity_row("ownership_handoff", 0, 4, 6),
    ]


def test_handoff_gap_math_uses_availability_intervals_and_tipping_points():
    rows = _controlled_sensitivity_rows()

    intervals = availability_interval_rows(rows)
    intent = next(row for row in intervals if row["category"] == "intent_evidence")
    assert intent["availability_lower"] == 0.8
    assert intent["availability_upper"] == 1.0

    gap_rows, summary = handoff_gap_rows(rows)
    assert summary["handoff_evidence_availability_interval"] == [0.0, 0.2]
    assert summary["handoff_evidence_gap_interval"] == [0.8, 1.0]
    assert summary["core_availability_interval"] == [round((0.8 + 0.4 + 0.2) / 3, 4), round((1.0 + 0.7 + 0.8) / 3, 4)]
    assert summary["minimum_robust_separation"] == round(summary["core_availability_interval"][0] - 0.2, 4)
    assert any(row["metric"] == "Handoff-Evidence Gap" for row in gap_rows)

    tipping = {row["category"]: row for row in tipping_point_rows(rows, threshold=0.5)}
    assert tipping["risk_analysis"]["flips_needed"] == 3
    assert tipping["trace_evidence"]["flips_needed"] == 5
    assert tipping["ownership_handoff"]["flips_needed"] == 1


def test_population_results_compute_wilson_and_weighted_estimates(tmp_path, monkeypatch):
    monkeypatch.setattr(population_module, "_default_population_dossier_dir", lambda: None)
    sample = []
    for index in range(4):
        sample.append(
            {
                "instance_id": f"pr_{index}",
                "repo": "owner/repo",
                "pr_number": str(index + 1),
                "pr_url": f"https://github.com/owner/repo/pull/{index + 1}",
                "source": "test",
                "author_type": "ai_authored",
                "agent_name": "codex",
                "task_type": "feature",
                "language": "Python",
                "outcome": "merged",
                "sample_split": "test",
                "notes": "test",
                "sampling_weight": "1.0",
            }
        )
    manifest = tmp_path / "sample.csv"
    write_csv_rows(manifest, sample)
    annotations = tmp_path / "annotations.csv"
    _write_completed_annotation_csv(annotations, [row["instance_id"] for row in sample])
    out = tmp_path / "results"

    summary = write_population_results(annotations, manifest, out)

    intent = summary["category_estimates"]["intent_evidence"]
    assert intent["eligible_records"] == 3
    assert intent["positive_records"] == 2
    assert intent["coverage_rate"] == round(2 / 3, 4)
    assert wilson_interval(2, 3)["upper"] == intent["coverage_ci_upper"]
    assert (out / "population_estimates.json").exists()
    assert (out / "population_evidence_estimates_table.tex").exists()
    assert (out / "paper_table_sensitivity_by_category.csv").exists()
    assert (out / "paper_table_sensitivity_by_category.tex").exists()
    assert (out / "paper_table_sensitivity_compact.csv").exists()
    assert (out / "paper_table_sensitivity_compact.tex").exists()
    assert (out / "sensitivity_summary.json").exists()
    assert (out / "sensitivity_summary.md").exists()
    assert (out / "paper_table_provenance_by_category.csv").exists()
    assert (out / "paper_table_provenance_by_category.tex").exists()
    assert (out / "paper_table_provenance_compact.csv").exists()
    assert (out / "paper_table_provenance_compact.tex").exists()
    assert (out / "paper_table_availability_intervals.csv").exists()
    assert (out / "paper_table_availability_intervals.tex").exists()
    assert (out / "paper_table_handoff_gap.csv").exists()
    assert (out / "paper_table_handoff_gap.tex").exists()
    assert (out / "paper_table_tipping_point.csv").exists()
    assert (out / "paper_table_tipping_point.tex").exists()
    assert (out / "paper_table_source_type_by_category.csv").exists()
    assert (out / "paper_table_source_type_by_category.tex").exists()
    assert (out / "provenance_status_summary.md").exists()
    assert (out / "paper_table_claims_nonclaims.csv").exists()
    assert (out / "paper_table_claims_nonclaims.md").exists()
    assert (out / "paper_table_claims_nonclaims.tex").exists()
    sensitivity = json.loads((out / "sensitivity_summary.json").read_text(encoding="utf-8"))
    assert sensitivity["main_rule"] == "present + partially_present counted positive"
    claims = (out / "paper_table_claims_nonclaims.md").read_text(encoding="utf-8")
    assert "Handoff-evidence gap within AIDev-pop" in claims
    assert "Inter-rater reliability" in claims
    compact_sensitivity = (out / "paper_table_sensitivity_compact.csv").read_text(encoding="utf-8")
    assert "Intent" in compact_sensitivity
    assert "partial-sensitive" in compact_sensitivity
    compact_provenance = (out / "paper_table_provenance_compact.csv").read_text(encoding="utf-8")
    assert "Rationale,reviewer_actionability" in compact_provenance
    handoff_gap = (out / "paper_table_handoff_gap.csv").read_text(encoding="utf-8")
    assert "Handoff-Evidence Gap" in handoff_gap
    tipping_point = (out / "paper_table_tipping_point.csv").read_text(encoding="utf-8")
    assert "flips_needed" in tipping_point


def test_population_scripts_smoke(tmp_path):
    source = tmp_path / "source.csv"
    with source.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["repository", "number", "source_agent", "title", "body", "language", "outcome", "changed_file_count"])
        writer.writeheader()
        for row in _source_rows(3):
            writer.writerow({field: row.get(field, "") for field in writer.fieldnames})
    frame = tmp_path / "frame.csv"
    sample = tmp_path / "sample.csv"

    root = Path(__file__).resolve().parents[1]
    frame_spec = importlib.util.spec_from_file_location("build_population_sampling_frame", root / "scripts" / "build_population_sampling_frame.py")
    sample_spec = importlib.util.spec_from_file_location("sample_population_prs", root / "scripts" / "sample_population_prs.py")
    frame_module = importlib.util.module_from_spec(frame_spec)
    sample_module = importlib.util.module_from_spec(sample_spec)
    assert frame_spec.loader is not None
    assert sample_spec.loader is not None
    frame_spec.loader.exec_module(frame_module)
    sample_spec.loader.exec_module(sample_module)

    assert frame_module.main(["--input", str(source), "--out", str(frame)]) == 0
    assert sample_module.main(["--frame", str(frame), "--n", "10", "--min-per-agent", "2", "--out", str(sample), "--report-out", str(tmp_path / "report")]) == 0
    assert len(read_csv_rows(sample)) == 10
    assert json.loads((tmp_path / "report" / "sampling_report.json").read_text(encoding="utf-8"))["sample_size"] == 10


def test_aidev_export_and_schema_scripts_smoke(tmp_path):
    source = tmp_path / "aidev_like.csv"
    fields = [
        "repository",
        "number",
        "html_url",
        "agent",
        "title",
        "body",
        "language",
        "state",
        "repo_stars",
        "comment_count",
        "review_count",
        "commit_count",
        "private",
    ]
    rows = [
        {
            "repository": "owner/repo",
            "number": "1",
            "html_url": "https://github.com/owner/repo/pull/1",
            "agent": "OpenAI Codex",
            "title": "Add safer parser",
            "body": "Tests: pytest. Risk: rollback.",
            "language": "Python",
            "state": "merged",
            "repo_stars": "120",
            "comment_count": "2",
            "review_count": "1",
            "commit_count": "3",
            "private": "false",
        },
        {
            "repository": "owner/small",
            "number": "2",
            "html_url": "https://github.com/owner/small/pull/2",
            "agent": "Codex",
            "title": "Small repo update",
            "body": "",
            "language": "Python",
            "state": "open",
            "repo_stars": "9",
            "comment_count": "1",
            "review_count": "0",
            "commit_count": "1",
            "private": "false",
        },
    ]
    with source.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)

    root = Path(__file__).resolve().parents[1]
    export_spec = importlib.util.spec_from_file_location("export_aidev_curated_csv", root / "scripts" / "export_aidev_curated_csv.py")
    inspect_spec = importlib.util.spec_from_file_location("inspect_aidev_schema", root / "scripts" / "inspect_aidev_schema.py")
    export_module = importlib.util.module_from_spec(export_spec)
    inspect_module = importlib.util.module_from_spec(inspect_spec)
    assert export_spec.loader is not None
    assert inspect_spec.loader is not None
    export_spec.loader.exec_module(export_module)
    inspect_spec.loader.exec_module(inspect_module)

    schema_dir = tmp_path / "schema"
    exported = tmp_path / "aidev_export.csv"
    report_dir = tmp_path / "export_report"

    assert inspect_module.main(["--input", str(source), "--out", str(schema_dir), "--sample-size", "1"]) == 0
    assert (schema_dir / "schema_summary.json").exists()
    assert export_module.main(["--input", str(source), "--out", str(exported), "--report-out", str(report_dir), "--no-joins"]) == 0

    exported_rows = read_csv_rows(exported)
    report = json.loads((report_dir / "export_report.json").read_text(encoding="utf-8"))
    assert len(exported_rows) == 1
    assert exported_rows[0]["source_agent"] == "OpenAI Codex"
    assert report["exclusion_reason_counts"]["repo_below_100_stars"] == 1


def test_dependency_audit_sheet_extracts_dependency_sensitive_rows(tmp_path):
    manifest = tmp_path / "sample.csv"
    rows = [
        {
            "instance_id": "dep_1",
            "repo": "owner/repo",
            "pr_number": "1",
            "pr_url": "https://github.com/owner/repo/pull/1",
            "title": "Update package",
            "agent_name": "codex",
            "language": "TypeScript",
            "outcome": "merged",
            "files_changed": "src/app.ts | package.json | pnpm-lock.yaml",
            "body": "Bump dependency.",
            "commit_messages": "update package",
            "comments": "",
            "reviews": "",
        },
        {
            "instance_id": "non_dep",
            "repo": "owner/repo",
            "pr_number": "2",
            "pr_url": "https://github.com/owner/repo/pull/2",
            "title": "Refactor",
            "agent_name": "codex",
            "language": "TypeScript",
            "outcome": "open",
            "files_changed": "src/app.ts | README.md",
            "body": "Refactor only.",
        },
    ]
    write_csv_rows(manifest, rows)
    root = Path(__file__).resolve().parents[1]
    spec = importlib.util.spec_from_file_location("build_dependency_audit_sheet", root / "scripts" / "build_dependency_audit_sheet.py")
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)

    out = tmp_path / "dependency_audit"
    assert module.main(["--manifest", str(manifest), "--out", str(out), "--no-workbook"]) == 0

    audit_rows = read_csv_rows(out / "dependency_audit_sheet.csv")
    summary = json.loads((out / "dependency_candidate_summary.json").read_text(encoding="utf-8"))
    assert len(audit_rows) == 1
    assert audit_rows[0]["instance_id"] == "dep_1"
    assert "package.json" in audit_rows[0]["dependency_files"]
    assert summary["dependency_sensitive_candidates"] == 1


def test_dependency_audit_results_compute_candidate_coverage(tmp_path):
    annotations = tmp_path / "dependency_audit.csv"
    fields = ["instance_id", "dependency_evidence_label", "dependency_evidence_comment"]
    with annotations.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(
            [
                {"instance_id": "a", "dependency_evidence_label": "present"},
                {"instance_id": "b", "dependency_evidence_label": "partially_present"},
                {"instance_id": "c", "dependency_evidence_label": "missing"},
                {"instance_id": "d", "dependency_evidence_label": "not_applicable"},
            ]
        )
    root = Path(__file__).resolve().parents[1]
    spec = importlib.util.spec_from_file_location("build_dependency_audit_results", root / "scripts" / "build_dependency_audit_results.py")
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)

    out = tmp_path / "dependency_results"
    assert module.main(["--annotations", str(annotations), "--out", str(out), "--sample-size", "10"]) == 0

    summary = json.loads((out / "dependency_audit_results.json").read_text(encoding="utf-8"))
    assert summary["dependency_sensitive_candidates"] == 4
    assert summary["applicable_candidates"] == 3
    assert summary["positive_candidates"] == 2
    assert summary["coverage_rate"] == round(2 / 3, 4)
    assert (out / "dependency_audit_table.tex").exists()

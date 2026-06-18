import json
import socket

from mergedossier_bench.cli import main
from mergedossier_bench.seed_builder import (
    load_seed_manifest,
    reconstruct_dossier_from_raw,
    validate_seed_manifest,
    write_seed_corpus,
)
from mergedossier_bench.validators import load_json, validate_data, validate_file


MANIFEST = "data/manifests/seed_prs.csv"
FIXTURES = "tests/fixtures/github_prs"


def test_seed_manifest_parsing():
    rows = load_seed_manifest(MANIFEST)

    assert len(rows) == 4
    assert rows[0]["instance_id"] == "fixture_ai_merged_good_evidence"
    assert rows[0]["author_type"] == "ai_authored"


def test_seed_manifest_validation():
    rows = load_seed_manifest(MANIFEST)
    assert validate_seed_manifest(rows) == []

    bad_rows = [dict(rows[0], instance_id="", agent_name="robot")]
    errors = validate_seed_manifest(bad_rows)
    assert any("missing instance_id" in error for error in errors)
    assert any("invalid agent_name" in error for error in errors)


def test_build_seed_corpus_dry_run(tmp_path):
    out = tmp_path / "seed_corpus"
    code = main(["build-seed-corpus", "--manifest", MANIFEST, "--out", str(out), "--dry-run"])

    assert code == 0
    assert not out.exists()


def test_raw_schema_validation():
    assert validate_file(f"{FIXTURES}/fixture_ai_merged_good_evidence.json", "github_pr_raw") == []


def test_raw_to_dossier_reconstruction_validates():
    raw = load_json(f"{FIXTURES}/fixture_ai_merged_good_evidence.json")
    raw["manifest_metadata"] = {"agent_name": "codex"}
    dossier = reconstruct_dossier_from_raw(raw)

    assert validate_data(dossier, "dossier") == []
    assert dossier["instance_id"] == "fixture_ai_merged_good_evidence"
    assert dossier["evidence"]["intent"]["present"] is True
    assert dossier["evidence"]["risk_analysis"]["present"] is True
    assert dossier["evidence_provenance"]["risk_analysis"][0]["status"] == "observed"


def test_build_seed_corpus_with_fixtures(tmp_path):
    out = tmp_path / "seed_corpus"
    code = main(
        [
            "build-seed-corpus",
            "--manifest",
            MANIFEST,
            "--out",
            str(out),
            "--use-fixtures",
            FIXTURES,
        ]
    )

    assert code == 0
    assert len(list((out / "raw").glob("*.json"))) == 4
    assert len(list((out / "dossiers").glob("*.json"))) == 4
    assert (out / "manifests" / "resolved_manifest.csv").exists()
    assert (out / "logs" / "build_seed_corpus_log.jsonl").exists()
    summary = json.loads((out / "summary.json").read_text(encoding="utf-8"))
    assert summary["total_manifest_rows"] == 4
    assert summary["reconstructed_dossiers"] == 4
    assert summary["missing_fixtures"] == 0


def test_directory_reconstruction_and_generated_dossiers_validate(tmp_path):
    seed_out = tmp_path / "seed_corpus"
    write_seed_corpus(MANIFEST, seed_out, fixture_dir=FIXTURES)
    reconstructed = tmp_path / "reconstructed"

    code = main(["reconstruct-dossier", "--raw", str(seed_out / "raw"), "--out", str(reconstructed)])

    assert code == 0
    dossiers = sorted(reconstructed.glob("*.json"))
    assert len(dossiers) == 4
    for dossier in dossiers:
        assert validate_file(dossier, "dossier") == []


def test_summarize_and_annotation_export_work_on_generated_seed_dossiers(tmp_path):
    seed_out = tmp_path / "seed_corpus"
    write_seed_corpus(MANIFEST, seed_out, fixture_dir=FIXTURES)
    summary_out = tmp_path / "summary"
    annotation_out = tmp_path / "annotation_tasks.json"

    summarize_code = main(["summarize", "--dossiers", str(seed_out / "dossiers"), "--out", str(summary_out)])
    export_code = main(
        ["export-annotation-tasks", "--dossiers", str(seed_out / "dossiers"), "--out", str(annotation_out)]
    )

    assert summarize_code == 0
    assert export_code == 0
    summary = json.loads((summary_out / "summary.json").read_text(encoding="utf-8"))
    tasks = json.loads(annotation_out.read_text(encoding="utf-8"))
    assert summary["valid_dossiers"] == 4
    assert len(tasks) == 4
    assert "provenance_sections" in tasks[0]["data"]


def test_seed_builder_requires_no_network(monkeypatch, tmp_path):
    def fail_network(*args, **kwargs):
        raise AssertionError("network access should not be used")

    monkeypatch.setattr(socket, "create_connection", fail_network)
    out = tmp_path / "seed_corpus"
    summary = write_seed_corpus(MANIFEST, out, fixture_dir=FIXTURES)

    assert summary["reconstructed_dossiers"] == 4

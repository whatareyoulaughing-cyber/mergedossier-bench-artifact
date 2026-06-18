import json
from pathlib import Path

from mergedossier_bench.cli import main
from mergedossier_bench.schema import EVIDENCE_TYPES


def _evidence_item(present: bool, quality: int) -> dict:
    return {
        "present": present,
        "quality": quality,
        "claim": "Evidence claim." if present else "",
        "grounding": [{"artifact_type": "test", "reference": "ref"}] if present else [],
    }


def _dossier(dossier_id: str, present: bool, quality: int) -> dict:
    return {
        "schema_version": "0.1.0",
        "dossier_id": dossier_id,
        "instance_id": f"instance-{dossier_id}",
        "repository": "owner/repo",
        "pr_url": f"https://github.com/owner/repo/pull/{dossier_id}",
        "source_agent": "Codex",
        "created_at": "2026-06-01T12:00:00Z",
        "dossier_created_at": "2026-06-02T00:00:00Z",
        "evidence": {evidence_type: _evidence_item(present, quality) for evidence_type in EVIDENCE_TYPES},
    }


def _jsonl_rows(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def test_summarize_works_on_directory(tmp_path):
    out = tmp_path / "summary-dir"
    code = main(["summarize", "--dossiers", "examples/corpus", "--out", str(out)])

    assert code == 0
    summary = json.loads((out / "summary.json").read_text(encoding="utf-8"))
    assert summary["total_dossiers"] == 4
    assert summary["valid_dossiers"] == 4
    assert summary["invalid_dossiers"] == 0
    assert {"strong", "adequate", "thin", "insufficient"} <= set(summary["readiness_band_counts"])
    assert (out / "summary.md").exists()
    assert (out / "scores.jsonl").exists()
    assert (out / "invalid_dossiers.jsonl").exists()
    assert (out / "leaderboard.csv").exists()


def test_summarize_works_on_jsonl_file(tmp_path):
    out = tmp_path / "summary-jsonl"
    code = main(["summarize", "--dossiers", "examples/corpus/toy_dossiers.jsonl", "--out", str(out)])

    assert code == 0
    summary = json.loads((out / "summary.json").read_text(encoding="utf-8"))
    scores = _jsonl_rows(out / "scores.jsonl")
    assert summary["total_dossiers"] == 4
    assert len(scores) == 4
    assert scores[0]["source"].endswith("toy_dossiers.jsonl:1")
    assert all("toy_dossiers.jsonl:" in score["source"] for score in scores)


def test_invalid_dossiers_are_reported_instead_of_crashing(tmp_path):
    corpus = tmp_path / "corpus"
    corpus.mkdir()
    (corpus / "valid.json").write_text(json.dumps(_dossier("valid", True, 2)), encoding="utf-8")
    (corpus / "invalid.json").write_text(json.dumps({"schema_version": "0.1.0"}), encoding="utf-8")
    out = tmp_path / "summary"

    code = main(["summarize", "--dossiers", str(corpus), "--out", str(out)])

    assert code == 0
    summary = json.loads((out / "summary.json").read_text(encoding="utf-8"))
    invalid_rows = _jsonl_rows(out / "invalid_dossiers.jsonl")
    assert summary["total_dossiers"] == 2
    assert summary["valid_dossiers"] == 1
    assert summary["invalid_dossiers"] == 1
    assert invalid_rows[0]["source"].endswith("invalid.json")
    assert "validation_error" in invalid_rows[0]


def test_aggregate_statistics_are_correct_on_controlled_corpus(tmp_path):
    corpus = tmp_path / "controlled.jsonl"
    corpus.write_text(
        "\n".join(
            [
                json.dumps(_dossier("complete", True, 2)),
                json.dumps(_dossier("empty", False, 0)),
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    out = tmp_path / "summary"

    code = main(["summarize", "--dossiers", str(corpus), "--out", str(out)])

    assert code == 0
    summary = json.loads((out / "summary.json").read_text(encoding="utf-8"))
    assert summary["total_dossiers"] == 2
    assert summary["valid_dossiers"] == 2
    assert summary["mean_evidence_sufficiency_score"] == 50.0
    assert summary["median_evidence_sufficiency_score"] == 50.0
    assert summary["min_score"] == 0.0
    assert summary["max_score"] == 100.0
    assert summary["readiness_band_counts"] == {"insufficient": 1, "strong": 1}
    assert summary["missing_evidence_counts"]["risk_analysis"] == 1
    assert summary["evidence_category_coverage"]["intent"]["present_count"] == 1
    assert summary["evidence_category_coverage"]["intent"]["coverage_rate"] == 0.5


def test_existing_cli_smoke_behavior_is_not_broken(tmp_path):
    out = tmp_path / "score.json"
    code = main(["score", "--dossier", "examples/toy_merge_dossier.json", "--out", str(out)])

    assert code == 0
    report = json.loads(out.read_text(encoding="utf-8"))
    assert report["dossier_id"] == "dossier-toy-owner-repo-42"
    assert report["evidence_sufficiency_score"] == 63.65

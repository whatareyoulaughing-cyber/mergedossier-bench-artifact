import json
from pathlib import Path

from mergedossier_bench.cli import main
from mergedossier_bench.provenance import audit_provenance, find_uncited_evidence, summarize_provenance
from mergedossier_bench.seed_builder import reconstruct_dossier_from_raw, write_seed_corpus
from mergedossier_bench.validators import load_json, validate_data, validate_file


MANIFEST = "data/manifests/seed_prs.csv"
FIXTURES = "tests/fixtures/github_prs"


def test_old_toy_dossier_validates_without_provenance():
    assert validate_file("examples/toy_merge_dossier.json", "dossier") == []


def test_reconstructed_dossier_has_schema_valid_provenance():
    raw = load_json(f"{FIXTURES}/fixture_ai_merged_good_evidence.json")
    dossier = reconstruct_dossier_from_raw(raw)

    assert validate_data(dossier, "dossier") == []
    provenance = dossier["evidence_provenance"]
    assert provenance["risk_analysis"][0]["status"] == "observed"
    assert provenance["test_rationale"][0]["status"] in {"observed", "inferred"}
    assert "dependency_evidence" in provenance


def test_invalid_provenance_status_source_and_confidence_fail():
    dossier = load_json("examples/toy_merge_dossier.json")
    dossier["evidence_provenance"] = {
        "intent": [
            {
                "status": "maybe",
                "source_type": "telepathy",
                "source_id": None,
                "source_url": None,
                "raw_path": None,
                "excerpt": "not valid",
                "extraction_rule": "bad_rule",
                "confidence": "certain",
                "notes": None,
            }
        ]
    }

    errors = validate_data(dossier, "dossier")
    assert any("evidence_provenance" in error for error in errors)


def test_uncited_evidence_detection_on_legacy_dossier():
    dossier = load_json("examples/toy_merge_dossier.json")

    uncited = find_uncited_evidence(dossier)

    assert uncited
    assert any(row["category"] == "intent" for row in uncited)


def test_audit_provenance_supports_directory_and_jsonl(tmp_path):
    seed_out = tmp_path / "seed_corpus"
    write_seed_corpus(MANIFEST, seed_out, fixture_dir=FIXTURES)
    audit_dir = tmp_path / "audit_dir"
    summary = audit_provenance(seed_out / "dossiers", audit_dir)

    assert summary["total_dossiers"] == 4
    assert summary["dossiers_with_provenance"] == 4
    assert (audit_dir / "provenance_summary.json").exists()
    assert (audit_dir / "uncited_evidence.jsonl").exists()
    assert (audit_dir / "missing_provenance.jsonl").exists()

    jsonl = tmp_path / "dossiers.jsonl"
    with jsonl.open("w", encoding="utf-8") as f:
        for path in sorted((seed_out / "dossiers").glob("*.json")):
            f.write(json.dumps(json.loads(path.read_text(encoding="utf-8"))) + "\n")
    audit_jsonl = tmp_path / "audit_jsonl"
    code = main(["audit-provenance", "--dossiers", str(jsonl), "--out", str(audit_jsonl)])

    assert code == 0
    assert json.loads((audit_jsonl / "provenance_summary.json").read_text(encoding="utf-8"))["total_dossiers"] == 4


def test_provenance_summary_counts_observed_and_inferred():
    raw = load_json(f"{FIXTURES}/fixture_ai_merged_good_evidence.json")
    dossier = reconstruct_dossier_from_raw(raw)

    summary = summarize_provenance([dossier])

    assert summary["dossiers_with_provenance"] == 1
    assert summary["inferred_vs_observed_counts"]["observed"] >= 1

import json

from mergedossier_bench.cli import main
from mergedossier_bench.dossier_cards import make_dossier_cards
from mergedossier_bench.perturbation import run_perturbation_suite
from mergedossier_bench.pilot_analysis import run_pilot_analysis
from mergedossier_bench.review_demands import extract_review_demands
from mergedossier_bench.seed_builder import write_seed_corpus


MANIFEST = "data/manifests/seed_prs.csv"
FIXTURES = "tests/fixtures/github_prs"


def test_perturbation_suite_expected_status_checks(tmp_path):
    out = tmp_path / "perturbation"
    summary = run_perturbation_suite(out)

    assert summary["total_checks"] == 10
    assert summary["passed"] == 10
    assert summary["failed"] == 0
    assert (out / "perturbation_results.json").exists()
    assert (out / "perturbation_results.md").exists()
    assert (out / "paper_table_perturbation_checks.csv").exists()


def test_dossier_card_generation(tmp_path):
    seed_out = tmp_path / "seed_corpus"
    write_seed_corpus(MANIFEST, seed_out, fixture_dir=FIXTURES)
    out = tmp_path / "cards"

    summary = make_dossier_cards(seed_out / "dossiers", out)

    assert summary["total_cards"] == 4
    assert (out / "index.md").exists()
    assert (out / "cards_summary.json").exists()
    assert len(list((out / "cards").glob("*.md"))) == 4


def test_pilot_analysis_writes_paper_tables(tmp_path):
    seed_out = tmp_path / "seed_corpus"
    write_seed_corpus(MANIFEST, seed_out, fixture_dir=FIXTURES)
    out = tmp_path / "pilot"

    summary = run_pilot_analysis(seed_out / "dossiers", out)

    assert summary["valid_dossiers"] == 4
    assert "not population estimates" in summary["warning"]
    for name in (
        "pilot_summary.json",
        "pilot_summary.md",
        "paper_table_evidence_coverage.csv",
        "paper_table_missing_evidence.csv",
        "paper_table_provenance_status.csv",
        "paper_table_source_types.csv",
        "paper_table_sensitivity_by_category.csv",
        "sensitivity_summary.json",
        "sensitivity_summary.md",
        "paper_table_provenance_by_category.csv",
        "paper_table_source_type_by_category.csv",
        "paper_table_claims_nonclaims.md",
        "paper_table_claims_nonclaims.tex",
        "paper_table_by_author_type.csv",
        "paper_table_by_outcome.csv",
    ):
        assert (out / name).exists()
    sensitivity = json.loads((out / "sensitivity_summary.json").read_text(encoding="utf-8"))
    assert sensitivity["construct"] == "Review-Evidence Availability"
    claims = (out / "paper_table_claims_nonclaims.md").read_text(encoding="utf-8")
    assert "Evidence availability in AIDev-pop" in claims
    assert "Inter-rater reliability" in claims


def test_review_demand_extraction_writes_exploratory_tables(tmp_path):
    out = tmp_path / "review_demands"

    summary = extract_review_demands(FIXTURES, out)

    assert summary["total_review_demand_signals"] >= 2
    assert "test_demand" in summary["category_counts"]
    assert "requirement_demand" in summary["category_counts"]
    assert "reviewer utility" in summary["interpretation"]
    assert (out / "review_demand_signals.jsonl").exists()
    assert (out / "review_demand_summary.json").exists()
    assert (out / "paper_table_review_demands.csv").exists()


def test_new_cli_smoke_commands(tmp_path):
    seed_out = tmp_path / "seed_corpus"
    write_seed_corpus(MANIFEST, seed_out, fixture_dir=FIXTURES)

    assert main(["run-perturbation-suite", "--out", str(tmp_path / "perturb_cli")]) == 0
    assert main(["audit-provenance", "--dossiers", str(seed_out / "dossiers"), "--out", str(tmp_path / "audit_cli")]) == 0
    assert main(["make-dossier-cards", "--dossiers", str(seed_out / "dossiers"), "--out", str(tmp_path / "cards_cli"), "--format", "md"]) == 0
    assert main(["pilot-analysis", "--dossiers", str(seed_out / "dossiers"), "--out", str(tmp_path / "pilot_cli")]) == 0
    assert main(["extract-review-demands", "--raw", FIXTURES, "--out", str(tmp_path / "demands_cli")]) == 0
    assert json.loads((tmp_path / "audit_cli" / "provenance_summary.json").read_text(encoding="utf-8"))["dossiers_with_provenance"] == 4
    assert json.loads((tmp_path / "demands_cli" / "review_demand_summary.json").read_text(encoding="utf-8"))[
        "total_review_demand_signals"
    ] >= 2

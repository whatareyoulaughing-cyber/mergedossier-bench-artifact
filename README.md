# MergeDossier-Bench

A provenance-aware measurement framework for the handoff-evidence gap in AI-authored pull requests.

This repository is anonymized for double-anonymous review. Contact information is available after review.

## What This Artifact Does

MergeDossier-Bench provides an offline, reproducible artifact for measuring review-evidence availability in AI-authored pull requests. It includes:

- JSON schemas for MergeDossier records.
- CLI tools for dossier validation, legacy triage scoring, corpus summaries, provenance audit, perturbation checks, dossier cards, and pilot-analysis tables.
- Safe example dossiers and tests.
- Sanitized release manifests and paper-facing derived tables.
- A completed 500-PR AIDev-pop annotation table used to regenerate the reported availability and handoff-gap tables.

The preserved framing is: MergeDossier-Bench measures the handoff-evidence gap in AI-authored pull requests. A diff is not a dossier. A dossier must cite its evidence.

## What This Artifact Does Not Claim

This artifact does not support claims about:

- patch correctness;
- mergeability;
- reviewer utility;
- all-GitHub population rates;
- AI-vs-human causal effects;
- inter-rater reliability.

## Quickstart Smoke Test

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pytest -q
python -m mergedossier_bench.cli --help
python -m mergedossier_bench.cli summarize --dossiers examples/corpus --out outputs/smoke_corpus
python -m mergedossier_bench.cli audit-provenance --dossiers examples/corpus --out outputs/smoke_provenance
python -m mergedossier_bench.cli run-perturbation-suite --out outputs/smoke_perturbation
python -m mergedossier_bench.cli pilot-analysis --dossiers examples/corpus --out outputs/smoke_pilot_analysis
```

Windows PowerShell activation:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
pytest -q
```

## Expected Outputs

- Corpus summary: `outputs/smoke_corpus/summary.json`, `scores.jsonl`, `summary.md`.
- Provenance audit: `outputs/smoke_provenance/provenance_summary.json`, `uncited_evidence.jsonl`, `missing_provenance.jsonl`.
- Perturbation checks: `outputs/smoke_perturbation/perturbation_results.json`, `paper_table_perturbation_checks.csv`.
- Pilot analysis smoke: `outputs/smoke_pilot_analysis/` paper-facing CSV/Markdown/JSON tables.

## Reproduce Paper Tables

The population tables are regenerated from the included completed audit-code table and sample manifest:

```bash
python scripts/build_population_results.py \
  --annotations outputs/population_ai_pr_500_20260616/reports/annotation_sheet_completed.csv \
  --sample-manifest data/manifests/population_ai_pr_sample_500_20260616.csv \
  --out outputs/population_results_20260616
```

Key outputs include:

- `paper_table_sensitivity_by_category.csv`
- `paper_table_availability_intervals.csv`
- `paper_table_handoff_gap.csv`
- `paper_table_tipping_point.csv`
- `paper_table_provenance_by_category.csv`
- `paper_table_source_type_by_category.csv`
- `paper_table_claims_nonclaims.md`

## Run Tests

```bash
pytest -q
```

The tests are offline and do not require a GitHub token.

## Inspect Provenance

```bash
python -m mergedossier_bench.cli audit-provenance --dossiers examples/corpus --out outputs/provenance_review
```

Inspect:

- `outputs/provenance_review/provenance_summary.md`
- `outputs/provenance_review/uncited_evidence.jsonl`
- `outputs/provenance_review/missing_provenance.jsonl`

## Regenerate Dossier Cards

```bash
python -m mergedossier_bench.cli make-dossier-cards --dossiers examples/corpus --out outputs/dossier_cards_review --format md
```

The generated cards provide compact manual-audit views without dumping raw JSON.

## Dataset And Public-Data Notes

This release contains public-data-derived manifests, safe example dossiers, annotation outputs, and derived tables. It intentionally excludes private raw data, local logs, credentials, environment dumps, and raw external downloads.

The population-frame claim is bounded to AIDev-pop public agentic PRs represented by the included sanitized frame/sample artifacts. It is not an all-GitHub rate.

## Anonymity Note

This repository is anonymized for double-anonymous review. Author names, emails, affiliations, ORCID identifiers, personal homepages, and institution-specific contact information are omitted or replaced by anonymous placeholders.

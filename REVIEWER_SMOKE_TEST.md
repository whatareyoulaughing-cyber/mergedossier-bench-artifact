# Reviewer Smoke Test

These commands are intended for an ICSE artifact reviewer using the anonymous artifact release. They require no network access after package installation and do not require credentials.

## Environment

Linux/macOS:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
```

## Core Checks

```bash
pytest -q
python -m mergedossier_bench.cli --help
python -m mergedossier_bench.cli summarize --dossiers examples/corpus --out outputs/smoke_corpus
python -m mergedossier_bench.cli audit-provenance --dossiers examples/corpus --out outputs/smoke_provenance
python -m mergedossier_bench.cli run-perturbation-suite --out outputs/smoke_perturbation
python -m mergedossier_bench.cli pilot-analysis --dossiers examples/corpus --out outputs/smoke_pilot_analysis
```

## Expected Files

```text
outputs/smoke_corpus/summary.json
outputs/smoke_corpus/scores.jsonl
outputs/smoke_provenance/provenance_summary.json
outputs/smoke_provenance/uncited_evidence.jsonl
outputs/smoke_perturbation/perturbation_results.json
outputs/smoke_perturbation/paper_table_perturbation_checks.csv
outputs/smoke_pilot_analysis/paper_table_claims_nonclaims.md
outputs/smoke_pilot_analysis/paper_table_sensitivity_by_category.csv
```

## Reproduce Population Tables

```bash
python scripts/build_population_results.py \
  --annotations outputs/population_ai_pr_500_20260616/reports/annotation_sheet_completed.csv \
  --sample-manifest data/manifests/population_ai_pr_sample_500_20260616.csv \
  --out outputs/population_results_20260616
```

This regenerates the paper-facing derived tables from the included audit-code table and sample manifest.

## Interpretation Boundary

Passing this smoke test supports artifact installability, offline reproducibility, schema/CLI operation, provenance-audit operation, perturbation checks, and table regeneration. It does not establish patch correctness, mergeability, reviewer utility, AI-vs-human causal effects, all-GitHub rates, or inter-rater reliability.

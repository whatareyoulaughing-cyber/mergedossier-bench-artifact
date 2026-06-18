# Artifact Manifest

## File Tree Summary

- `src/`: MergeDossier-Bench Python package.
- `scripts/`: data preparation, release checking, population table generation, and artifact validation helpers.
- `schemas/`: JSON schemas for PR instances and MergeDossier records.
- `examples/`: safe toy dossiers and annotation fixtures.
- `tests/`: offline unit and CLI tests.
- `docs/`: design notes, provenance notes, artifact evaluation notes, dataset card, and claim-boundary documentation.
- `data/manifests/`: safe release manifests, including the sanitized AIDev-pop frame and deterministic 500-PR sample manifest.
- `outputs/population_ai_pr_500_20260616/reports/annotation_sheet_completed.csv`: completed single-operator audit-code table used for paper table regeneration.
- `outputs/population_results_20260616/`: derived paper-facing tables and summaries.
- `outputs/dependency_sensitive_audit_20260616/results/`: dependency-sensitive audit derived results.

## Key Scripts

- `scripts/build_population_results.py`: regenerates population result tables.
- `scripts/check_anonymous_release.py`: scans the anonymous staging directory or zip for identity/path/secret leaks.
- `scripts/reproduce_artifact_smoke.py`: runs the offline artifact smoke workflow in the full development repository.
- `scripts/check_paper_readiness.py`: paper/readiness gate in the full development repository.
- `scripts/build_anonymous_release_zip.py`: legacy curated release-zip builder retained for reproducibility context.

## Key Schemas

- `schemas/merge_dossier.schema.json`
- `schemas/pr_instance.schema.json`

## Expected Generated Outputs

- Corpus summaries: `summary.json`, `summary.md`, `scores.jsonl`.
- Provenance audit: `provenance_summary.json/md`, `uncited_evidence.jsonl`, `missing_provenance.jsonl`.
- Perturbation checks: `perturbation_results.json/md`, `paper_table_perturbation_checks.csv`.
- Dossier cards: `index.md`, `cards_summary.json`, `cards/*.md`.
- Population tables: sensitivity, availability interval, handoff gap, tipping point, provenance, source-type, and claims/non-claims tables.

## Safe Data Files Included

- `data/manifests/seed_prs.csv`
- `data/manifests/population_ai_pr_frame_sanitized_20260616.csv`
- `data/manifests/population_ai_pr_sample_500_20260616.csv`
- `outputs/population_ai_pr_500_20260616/reports/annotation_sheet_completed.csv`
- `outputs/population_results_20260616/*`
- `outputs/dependency_sensitive_audit_20260616/results/*`

## Unsafe Or Private Files Excluded

- `.git/`
- `.venv/`
- `__pycache__/`
- `.pytest_cache/`
- local build logs and local-path-heavy outputs
- API keys, tokens, SSH keys, and environment dumps
- private raw data
- unsanitized AIDev raw export
- raw GitHub artifact downloads used during intermediate construction
- author names, emails, affiliations, ORCID identifiers, and personal homepages

## Release Zip SHA256

The final zip hash is written after build to:

```text
release/MergeDossier-Bench-anonymous-artifact.sha256
```

Embedding the exact zip hash inside this file before zipping would make the archive self-referential. The adjacent `.sha256` file and `release/release_build_log.md` are the authoritative hash records.

## Test Result Summary

The build log records the current validation results. Required validation commands are:

```bash
pytest -q
python scripts/check_anonymous_release.py
python -m mergedossier_bench.cli summarize --dossiers examples/corpus --out outputs/smoke_corpus
python -m mergedossier_bench.cli audit-provenance --dossiers examples/corpus --out outputs/smoke_provenance
python -m mergedossier_bench.cli run-perturbation-suite --out outputs/smoke_perturbation
python -m mergedossier_bench.cli pilot-analysis --dossiers examples/corpus --out outputs/smoke_pilot_analysis
```

## Paper Table Mapping

| Paper table/output | Regeneration command |
|---|---|
| Sensitivity by category | `python scripts/build_population_results.py --annotations outputs/population_ai_pr_500_20260616/reports/annotation_sheet_completed.csv --sample-manifest data/manifests/population_ai_pr_sample_500_20260616.csv --out outputs/population_results_20260616` |
| Availability intervals | Same as above |
| Handoff gap | Same as above |
| Tipping point | Same as above |
| Provenance by category | Same as above |
| Source type by category | Same as above |
| Claims / non-claims | Same as above, or `python -m mergedossier_bench.cli pilot-analysis --dossiers examples/corpus --out outputs/smoke_pilot_analysis` for smoke output |

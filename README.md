# MergeDossier-Bench

**Handoff-evidence gap measurement for AI-authored pull requests.**

Slogan: **A diff is not a dossier.**

Supporting slogan: **A dossier must cite its evidence.**

MergeDossier-Bench is a provenance-aware benchmark and measurement framework
for an ICSE-style paper around a simple claim:

> Coding agents should not only submit patches; they should submit evidence that helps humans understand, verify, question, and safely take responsibility for those patches.

This repo is designed for Codex or another coding agent to pick up immediately. Start with [`AGENTS.md`](AGENTS.md), then follow [`TODO.md`](TODO.md).

## Why this exists

Most coding-agent evaluation asks whether the generated patch passes tests or appears mergeable. MergeDossier-Bench moves one step earlier in the human decision pipeline:

- Not only: **Would a maintainer merge this PR?**
- But: **What review evidence did the AI-authored PR visibly provide?**

The main paper-facing construct is the **handoff-evidence gap**: AI-authored
PRs may expose surface evidence such as intent, scope, and tests while omitting
handoff-critical evidence such as risk, trace, regression boundary, rationale,
and ownership. The legacy `Evidence Sufficiency Score` remains available for
backward-compatible artifact scoring, but central empirical claims should use
category-level availability intervals and gap estimates rather than one
composite judgment.

The benchmark studies whether an AI-authored PR includes a useful *dossier*:

1. intent evidence,
2. requirement traceability,
3. test rationale,
4. regression safety,
5. risk analysis,
6. scope justification,
7. agent trace,
8. limitations and uncertainty,
9. reviewer actionability,
10. ownership handoff.

For manuscript wording and claim boundaries, see
[`docs/14_reframing_to_evidence_availability.md`](docs/14_reframing_to_evidence_availability.md)
and [`docs/15_claims_and_nonclaims.md`](docs/15_claims_and_nonclaims.md).

## Repository map

```text
MergeDossier-Bench-starter/
├── AGENTS.md                         # Codex instructions
├── TODO.md                           # Implementation task board
├── README.md                         # This file
├── pyproject.toml                    # Python package metadata
├── docs/
│   ├── 00_positioning.md             # How we differ from SWE-bench / FrontierCode / review benchmarks
│   ├── 01_paper_plan.md              # ICSE paper plan, RQs, contributions, timeline
│   ├── 02_dossier_schema.md          # Human-readable schema spec
│   ├── 03_annotation_guidelines.md   # Codebook for evidence-availability audit codes
│   ├── 04_experimental_design.md     # Mining study + human study + benchmark construction
│   ├── 05_leaderboard_design.md      # Leaderboard design and reporting protocol
│   ├── 06_related_work_seed.md       # Seed bibliography and positioning notes
│   └── 07_submission_checklist.md    # ICSE readiness checklist
├── schemas/
│   ├── merge_dossier.schema.json
│   ├── pr_instance.schema.json
│   ├── annotation.schema.json
│   └── score_report.schema.json
├── examples/
│   ├── toy_pr_instance.json
│   ├── toy_merge_dossier.json
│   └── toy_annotation.json
├── src/mergedossier_bench/
│   ├── __init__.py
│   ├── annotation_stats.py
│   ├── cli.py
│   ├── dossier_builder.py
│   ├── github_miner.py
│   ├── schema.py
│   ├── scoring.py
│   └── validators.py
├── scripts/
│   ├── bootstrap_env.sh
│   ├── generate_label_studio_config.py
│   ├── make_release_zip.sh
│   └── run_toy_pipeline.sh
└── tests/
    ├── test_cli_smoke.py
    ├── test_schemas.py
    └── test_scoring.py
```

## Quick start

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
python -m mergedossier_bench.cli validate --kind dossier --file examples/toy_merge_dossier.json
python -m mergedossier_bench.cli score --dossier examples/toy_merge_dossier.json --out /tmp/toy_score.json
python -m mergedossier_bench.cli build-dossier --instance examples/toy_pr_instance.json --out /tmp/dossier_skeleton.json
pytest -q
```

Without optional dependencies, the CLI still performs basic schema checks. With `jsonschema` installed, it performs full JSON Schema validation.

## Corpus mode

Corpus mode evaluates a batch of MergeDossiers as an evidence-centered benchmark
release artifact. It validates every dossier, scores valid dossiers with the
legacy Evidence Sufficiency Score, records invalid dossiers without stopping the
run, and writes aggregate outputs for paper tables and leaderboards.

Use a directory of `*.json` dossiers:

```bash
python -m mergedossier_bench.cli summarize --dossiers examples/corpus --out outputs/corpus_smoke
```

Use a JSONL file with one MergeDossier object per line:

```bash
python -m mergedossier_bench.cli summarize --dossiers examples/corpus/toy_dossiers.jsonl --out outputs/corpus_jsonl_smoke
```

The output directory contains:

- `scores.jsonl`: one score report per valid dossier, with source metadata.
- `invalid_dossiers.jsonl`: invalid records with source path or line number and validation error.
- `summary.json`: aggregate counts, legacy score statistics, artifact triage bands, missing evidence counts, and evidence coverage.
- `summary.md`: human-readable corpus overview with paper-ready tables.
- `leaderboard.csv`: ranked dossiers when valid score reports are available.

## Provenance-aware audit

MVP-4 adds optional evidence provenance without changing the existing Evidence
Sufficiency Score. Older dossiers still validate, while reconstructed dossiers
can now cite where each evidence category came from: PR title/body, linked
issues, changed files, commits, CI checks, reviews, comments, manifests, or
conservative heuristics.

Audit provenance for one JSON dossier, a JSONL corpus, or a directory:

```bash
python -m mergedossier_bench.cli audit-provenance \
  --dossiers data/seed_corpus/dossiers \
  --out outputs/provenance_audit
```

The output directory contains:

- `provenance_summary.json`: coverage, status, source-type, and missing-category counts.
- `provenance_summary.md`: human-readable provenance audit tables.
- `uncited_evidence.jsonl`: present evidence claims that lack observed or inferred provenance.
- `missing_provenance.jsonl`: invalid dossiers and evidence categories without provenance records.

Run deterministic perturbation checks over offline synthetic fixtures:

```bash
python -m mergedossier_bench.cli run-perturbation-suite \
  --out outputs/perturbation_suite
```

This writes `perturbation_results.json`, `perturbation_results.md`, and
`paper_table_perturbation_checks.csv`. These checks validate reconstruction
rules against controlled evidence signals; they are not external-validity
evidence.

Generate compact audit cards:

```bash
python -m mergedossier_bench.cli make-dossier-cards \
  --dossiers data/seed_corpus/dossiers \
  --out outputs/dossier_cards \
  --format md
```

This writes `index.md`, `cards_summary.json`, and one Markdown card per valid
dossier under `cards/`.

Create paper-facing Review-Evidence Availability and handoff-gap tables:

```bash
python -m mergedossier_bench.cli pilot-analysis \
  --dossiers data/seed_corpus/dossiers \
  --out outputs/pilot_analysis
```

The `pilot-analysis` outputs include availability sensitivity tables,
provenance-by-category tables, source-type-by-category tables, and
claims/non-claims tables:

- `paper_table_sensitivity_by_category.csv`
- `sensitivity_summary.json` and `sensitivity_summary.md`
- `paper_table_provenance_by_category.csv`
- `paper_table_source_type_by_category.csv`
- `paper_table_claims_nonclaims.md` and `paper_table_claims_nonclaims.tex`

The population-result builder additionally emits handoff-gap robustness tables:

- `paper_table_availability_intervals.csv` and `paper_table_availability_intervals.tex`
- `paper_table_handoff_gap.csv` and `paper_table_handoff_gap.tex`
- `paper_table_tipping_point.csv` and `paper_table_tipping_point.tex`

These tables are descriptive for the analyzed corpus only. They must not be
described as unsupported population estimates, authorship effects, patch
correctness, mergeability, inter-rater reliability, or reviewer-utility results.

Optionally extract deterministic exploratory review-comment demand signals from
raw PR artifacts:

```bash
python -m mergedossier_bench.cli extract-review-demands \
  --raw tests/fixtures/github_prs \
  --out outputs/review_demands
```

This writes `review_demand_signals.jsonl`, `review_demand_summary.json`, and
`paper_table_review_demands.csv`. These are exploratory demand signals, not
evidence of reviewer utility or causal effects.

## Population-frame expansion

The population workflow upgrades the 22-PR pilot into a stratified study over a
declared public AI/AI-assisted PR frame. The intended frame is the AIDev curated
public agentic-PR subset, not all GitHub PRs or all AI-authored PRs.

Install the analysis extras used to read parquet files:

```bash
pip install -e ".[dev,analysis,workbook]"
```

Inspect the AIDev pull-request table before conversion:

```bash
python scripts/inspect_aidev_schema.py \
  --dataset hao-li/AIDev \
  --table pull_request.parquet \
  --out outputs/aidev_schema_inspection_20260616
```

Export a MergeDossier-compatible CSV from the AIDev-pop curated parquet source:

```bash
python scripts/export_aidev_curated_csv.py \
  --dataset hao-li/AIDev \
  --table pull_request.parquet \
  --out data/external/aidev/aidev_curated_export_20260616.csv \
  --report-out outputs/aidev_export_report_20260616
```

Normalize the exported CSV into the sampling frame:

```bash
python scripts/build_population_sampling_frame.py \
  --input data/external/aidev/aidev_curated_export_20260616.csv \
  --out data/manifests/population_ai_pr_frame_20260616.csv \
  --report-out outputs/population_sampling_report_20260616/frame_summary.json
```

Sample 500 PRs with deterministic stratification:

```bash
python scripts/sample_population_prs.py \
  --frame data/manifests/population_ai_pr_frame_20260616.csv \
  --n 500 \
  --seed 20260616 \
  --out data/manifests/population_ai_pr_sample_500_20260616.csv \
  --report-out outputs/population_sampling_report_20260616
```

Run metadata-only corpus construction and reports:

```bash
python scripts/run_population_corpus_pipeline.py \
  --sample data/manifests/population_ai_pr_sample_500_20260616.csv \
  --out outputs/population_ai_pr_500_20260616 \
  --annotation-repeats 50 \
  --seed 20260616
```

For final analysis, use `--live` with `GITHUB_TOKEN` to enrich sampled PRs with
public GitHub artifacts. The pipeline writes `reports/annotation_tasks.json`,
`reports/annotation_tasks_with_repeats.json`, `reports/annotation_sheet.csv`,
and, when `openpyxl` is installed, `reports/annotation_sheet.xlsx`.

You must manually complete the 500 unique PR audit codes plus 50 delayed repeats
before building paper-facing population tables:

```bash
python scripts/build_population_results.py \
  --annotations outputs/population_ai_pr_500_20260616/reports/annotation_sheet_completed.csv \
  --sample-manifest data/manifests/population_ai_pr_sample_500_20260616.csv \
  --out outputs/population_results_20260616
```

Build a focused dependency-sensitive follow-up audit sheet from the same 500-PR
sample:

```bash
python scripts/build_dependency_audit_sheet.py \
  --manifest data/manifests/population_ai_pr_sample_500_20260616.csv \
  --out outputs/dependency_sensitive_audit_20260616
```

This sheet only covers PRs with dependency manifests or lockfiles. Do not report
dependency-evidence coverage until the `dependency_evidence_label` column is
completed.

After completing the dependency audit sheet, build the focused secondary result:

```bash
python scripts/build_dependency_audit_results.py \
  --annotations outputs/dependency_sensitive_audit_20260616/dependency_audit_sheet_annotated.xlsx \
  --out outputs/dependency_sensitive_audit_20260616/results
```

These estimates are valid only within the declared sampling frame and
single-operator protocol unless a second operator or external audit slice is
added.

## Annotation workflow

The annotation workflow prepares MergeDossiers for a single-operator
Review-Evidence Availability audit. It keeps the task focused on whether review
evidence is visible and category-coded, not whether the patch is correct or
mergeable.

Generate a Label Studio interface:

```bash
python scripts/generate_label_studio_config.py --out outputs/label_studio_config.xml
```

Export Label Studio import tasks from a dossier directory:

```bash
python -m mergedossier_bench.cli export-annotation-tasks \
  --dossiers examples/corpus \
  --out outputs/annotation_tasks.json
```

You can also export tasks from a JSONL corpus by passing
`--dossiers examples/corpus/toy_dossiers.jsonl`.

In Label Studio, create a project, paste or upload
`outputs/label_studio_config.xml` as the labeling interface, then import
`outputs/annotation_tasks.json` as tasks. If only one operator is available,
append delayed-repeat tasks for a self-consistency audit:

```bash
python -m mergedossier_bench.cli create-reliability-sample \
  --tasks outputs/annotation_tasks.json \
  --out outputs/annotation_tasks_with_repeats.json \
  --rate 0.2 \
  --min-count 5
```

Import `outputs/annotation_tasks_with_repeats.json` instead of the original task
file, then label the repeated tasks later without consulting the original
audit codes. After annotation, export the project as
JSON and run:

```bash
python -m mergedossier_bench.cli annotation-stats \
  --annotations examples/annotations/toy_label_studio_export.json \
  --out outputs/annotation_stats_smoke
```

The annotation statistics output directory contains:

- `annotation_records.jsonl`: one normalized annotation record per operator-task pair.
- `agreement_summary.json`: task counts, label distributions, agreement, kappa, and disagreement summaries.
- `agreement_summary.md`: human-readable overview, label distribution table, agreement table, and top disagreement cases.
- `disagreement_cases.jsonl`: ranked category-level disagreements for adjudication.

See `docs/08_annotation_protocol.md` for the codebook, single-operator repeat
audit, and adjudication protocol.

If Label Studio is too much overhead for a pilot, export a spreadsheet-friendly
CSV annotation sheet instead:

```bash
python -m mergedossier_bench.cli export-annotation-csv \
  --tasks outputs/annotation_tasks_with_repeats.json \
  --out outputs/annotation_sheet.csv \
  --annotator-id solo
```

For Excel labeling with dropdowns, convert the CSV into an `.xlsx` workbook:

```bash
python scripts/export_annotation_workbook.py \
  --csv outputs/annotation_sheet.csv \
  --out outputs/annotation_workbook.xlsx
```

If your Python environment does not have `openpyxl`, install the optional
workbook extra with `pip install -e ".[workbook]"`. Fill each `*_label` column
with one of `present`, `partially_present`, `missing`, or `not_applicable`, and
optionally add `*_comment` notes. Then export the `Annotation` sheet to the
completed CSV:

```bash
python scripts/export_annotation_csv_from_workbook.py \
  --workbook outputs/annotation_workbook.xlsx \
  --out outputs/annotation_sheet_completed.csv
```

Before statistics, validate the completed CSV:

```bash
python -m mergedossier_bench.cli validate-annotation-csv \
  --annotations outputs/annotation_sheet_completed.csv
```

For an unfinished template, use `--allow-incomplete` to check column structure
without requiring all audit codes. Then run the same statistics command on the
completed CSV:

```bash
python -m mergedossier_bench.cli annotation-stats \
  --annotations outputs/annotation_sheet_completed.csv \
  --out outputs/annotation_stats_from_csv
```

To create paper-ready LaTeX result snippets after validation:

```bash
python scripts/build_paper_results_from_annotations.py \
  --annotations outputs/annotation_sheet_completed.csv \
  --out outputs/annotation_paper_results
```

This writes annotation statistics, LaTeX tables, a Markdown integration summary,
and an adjudication sheet for any category-level disagreements.

For the real pilot workbook, the one-command post-annotation path is:

```bash
python scripts/run_completed_annotation_pipeline.py
```

It exports the `Annotation` sheet, validates the completed CSV, creates
statistics, writes LaTeX result snippets, and produces the adjudication sheet.

## Seed corpus builder

The seed corpus builder creates an offline-first bridge from toy dossiers to a
small PR-derived corpus. It reads a CSV manifest, loads synthetic or future raw
PR artifacts, reconstructs conservative MergeDossiers, and writes raw artifacts,
dossiers, logs, and summaries. Tests use fixtures only; no GitHub token or
network access is required.

Validate the manifest without writing corpus files:

```bash
python -m mergedossier_bench.cli build-seed-corpus \
  --manifest data/manifests/seed_prs.csv \
  --out data/seed_corpus \
  --dry-run
```

Build the fixture-backed seed corpus:

```bash
python -m mergedossier_bench.cli build-seed-corpus \
  --manifest data/manifests/seed_prs.csv \
  --out data/seed_corpus \
  --use-fixtures tests/fixtures/github_prs
```

Reconstruct dossiers again from raw artifacts:

```bash
python -m mergedossier_bench.cli reconstruct-dossier \
  --raw data/seed_corpus/raw \
  --out data/seed_corpus/dossiers
```

Summarize generated seed dossiers:

```bash
python -m mergedossier_bench.cli summarize \
  --dossiers data/seed_corpus/dossiers \
  --out outputs/seed_corpus_summary
```

Export generated seed dossiers for annotation:

```bash
python -m mergedossier_bench.cli export-annotation-tasks \
  --dossiers data/seed_corpus/dossiers \
  --out outputs/seed_annotation_tasks.json
```

The seed builder writes:

- `raw/<instance_id>.json`: raw fixture or future fetched PR artifacts.
- `dossiers/<instance_id>.json`: reconstructed MergeDossier files.
- `manifests/resolved_manifest.csv`: manifest rows used in the build.
- `logs/build_seed_corpus_log.jsonl`: per-row build status.
- `summary.json` and `summary.md`: build counts, artifact gaps, and evidence presence counts.

See `docs/09_seed_corpus_protocol.md` for inclusion criteria, authorship
recording, privacy notes, and annotation handoff.

## Artifact evaluation smoke test

The artifact is designed to support an ICSE-style artifact evaluation path. The
current target is **Artifacts Evaluated - Functional** for the offline pipeline,
with **Artifacts Available** after archival release. Do not claim reproduced or
replicated results until release metadata, external reproduction, and validation
paths are complete.

Run the reviewer-facing offline workflow:

```bash
python scripts/reproduce_artifact_smoke.py
```

The script exercises schema validation, single-dossier scoring, directory and
JSONL corpus summaries, fixture-backed seed-corpus construction, annotation-task
export, delayed-repeat sampling, CSV template validation, annotation-statistics
parsing, and `pytest -q`.
It writes all outputs under:

```text
outputs/artifact_smoke/
```

Build the anonymous-review release packet:

```bash
python scripts/build_sanitized_population_frame.py
python scripts/scan_raw_frame_release_risks.py
python scripts/build_anonymous_release_zip.py
python scripts/check_anonymous_release.py
python scripts/check_release_zip_smoke.py
python scripts/build_zenodo_deposit_packet.py
python scripts/check_public_release_preflight.py
python scripts/check_submission_blockers.py
```

See `docs/12_artifact_evaluation.md` for the artifact inventory, expected
outputs, badge target, and reviewer checklist. See `docs/13_dataset_card.md`
for the AIDev-pop handoff-evidence audit dataset card and `docs/14_release_manifest.md` for
the anonymous-review release manifest. See `docs/16_raw_frame_release_policy.md`
for the raw-frame release boundary and non-revealing risk scan. The current
submission-readiness packet is in `outputs/submission_readiness_20260617/`.
The Zenodo deposit packet under `outputs/zenodo_deposit_packet_20260617/`
prepares checksums and manual upload instructions, but it does not claim that a
DOI has already been minted.
The public-release preflight under `outputs/public_release_preflight_20260617/`
checks the deposit packet before manual publication while keeping DOI/public URL
placeholders explicit.
For portal copy/paste, use `ZENODO_COPY_FIELDS.md` and
`GITHUB_RELEASE_COPY_FIELDS.md` in the deposit packet.
The blocker dashboard under `outputs/submission_blocker_dashboard_20260617/`
summarizes which local gates pass and which external actions remain.
The acceptance-confidence gap report under
`outputs/acceptance_probability_gap_report_20260617/` summarizes the remaining
distance to an 80%-style high-confidence submission posture without estimating
a calibrated acceptance probability.
The post-P0 closeout packet under `outputs/post_p0_closeout_20260617/` provides
a parameterized dry-run-first PowerShell runner for after the external audit
return and real DOI/public URL are available.
The external-audit intake report under `outputs/external_audit_intake_20260617/`
scans candidate returned sheets and currently flags
`annotation_sheet_completed_annotation.csv` as complete-looking but not safe to
use as an independent external return without provenance confirmation.
The external-audit send-now packet under `outputs/external_audit_send_now_20260617/`
contains the copied handoff zip, Chinese/English `.eml` drafts, plain email
text, reminders, and a return checklist so the external-audit P0 can be sent
without searching across folders.
The public-release publish-now packet under
`outputs/public_release_publish_now_20260617/` collects Zenodo/GitHub copy
fields, the upload-file pointer, checksum, and a dry-run-first
`POST_PUBLICATION_UPDATE.ps1` runner for the DOI/public-URL P0 action.
The anonymous-release check verifies that the generated zip does not contain
local Windows user paths or local user identifiers in text artifacts.
The release-zip smoke check under `outputs/release_zip_smoke_20260617/`
extracts the generated anonymous-review zip and runs a stable offline test/CLI
subset from inside the extracted package. This local verification report is not
included inside the zip, avoiding checksum self-reference.
After a real DOI and public repository URL exist, update placeholders with:

```bash
python scripts/update_public_release_metadata.py --dry-run \
  --doi <artifact-doi> \
  --repo-url <public-repo-url> \
  --paper-url <paper-url-or-doi> \
  --author-name "<public-author-name>" \
  --affiliation "<public-affiliation>"

python scripts/update_public_release_metadata.py \
  --doi <artifact-doi> \
  --repo-url <public-repo-url> \
  --paper-url <paper-url-or-doi> \
  --author-name "<public-author-name>" \
  --affiliation "<public-affiliation>"
```

## Paper format check

The current paper draft targets the ICSE 2027 Research Track IEEE format:
`\documentclass[10pt,conference]{IEEEtran}`. The local guard checks the class
options, page size, page count, LaTeX log, and common spacing/font tampering
risks:

```bash
python scripts/check_icse_format.py \
  --tex paper/main.tex \
  --pdf paper/main.pdf \
  --log paper/build.log \
  --out outputs/icse_format_check_20260613.json \
  --markdown outputs/icse_format_check_20260613.md
```

This check is a desk-rejection guard, not a substitute for final empirical
readiness. The current manuscript reports completed AIDev-pop audit codes for a
500-PR sample plus 50 delayed repeats, while still excluding AI-vs-human,
reviewer-utility, and all-GitHub claims.

For figure and table polish, run the companion layout-quality audit:

```bash
python scripts/check_layout_quality.py \
  --tex paper/main.tex \
  --pdf paper/main.pdf \
  --log paper/build.log \
  --figures-dir paper/figures \
  --out-json outputs/layout_quality_20260617.json \
  --out-md outputs/layout_quality_20260617.md
```

This check covers PDF freshness relative to TeX and included figures, Type 1
PDF fonts, vector PDF figures, caption length, table captions and labels, table
font size, vertical table rules, and direct PNG/JPG figure inclusion in the main
TeX source.

For the final paper artifact, also run the PDF proofread gate:

```bash
python scripts/check_final_pdf_proofread.py \
  --pdf paper/main.pdf \
  --out outputs/final_pdf_proofread_20260617
```

It renders the pages, writes a contact sheet, extracts PDF text, and checks for
paper-identity phrases plus unresolved placeholder tokens.

To regenerate figures, rebuild `paper/main.pdf`, and run both paper layout
gates in one step:

```bash
python scripts/build_and_check_paper_layout.py \
  --out-dir outputs/paper_layout_build_check_20260617
```

## Paper readiness check

Run the broader local gate before sending the package around:

```bash
python scripts/check_paper_readiness.py
```

The default mode runs the ICSE format gate, PDF/layout quality gate,
`pytest -q`, the offline artifact smoke workflow, and annotation CSV
validation. Before final submission, require completed audit codes:

```bash
python scripts/check_paper_readiness.py --require-completed-annotations
```

### Live GitHub fetching

Live fetching is optional. Fixture replay remains the default path for tests and
does not require network access. For a real pilot, lint the manifest first:

```bash
python -m mergedossier_bench.cli lint-seed-manifest \
  --manifest data/manifests/real_pilot_template.csv
```

Then fetch a small public pilot when `GITHUB_TOKEN` is available:

```bash
python -m mergedossier_bench.cli build-seed-corpus \
  --manifest data/manifests/real_pilot_template.csv \
  --out data/seed_corpus_live \
  --live \
  --limit 5
```

The fetcher uses `GITHUB_TOKEN` by default, but never prints or logs it. Use
`--github-token-env` for another environment variable and `--api-base` for
GitHub Enterprise or tests. Existing `raw/<instance_id>.json` files are reused
unless `--force` is supplied.

Summarize and export live-generated dossiers:

```bash
python -m mergedossier_bench.cli summarize \
  --dossiers data/seed_corpus_live/dossiers \
  --out outputs/seed_corpus_live_summary

python -m mergedossier_bench.cli export-annotation-tasks \
  --dossiers data/seed_corpus_live/dossiers \
  --out outputs/seed_corpus_live_annotation_tasks.json
```

## Minimal viable paper artifact

A plausible ICSE submission package under the current framing:

- 500 AI/AI-assisted PR instances sampled from the declared AIDev-pop frame.
- A sanitized 33,596-row population-frame manifest for sampling audit without
  raw PR text.
- A raw-frame release risk scan that reports pattern counts without exposing
  matched secret-like strings or raw snippets.
- For each PR, a normalized PR instance and a provenance-aware MergeDossier evidence packet.
- A completed single-operator audit with delayed repeats, reported as self-consistency rather than inter-rater reliability.
- A prepared 50-task external audit slice and analysis script for a future
  second-operator check; no external agreement is claimed until that sheet is
  completed.
- A no-second-operator submission strategy at
  `docs/17_single_operator_submission_strategy.md`. This path treats the
  unfinished external-audit slice as a P1 limitation rather than a P0 blocker,
  provided the manuscript uses the single-operator boundary and does not claim
  inter-rater reliability.
- A sendable external-auditor handoff zip at
  `outputs/external_audit_handoff_20260617/MergeDossier-external-audit-handoff.zip`.
- An external-auditor handoff independence check at
  `outputs/external_audit_handoff_20260617/external_auditor_handoff_check.md`
  confirming the package has no primary/result paths and blank audit-code cells.
- A returned-audit checker:
  `python scripts/check_external_audit_return.py --completed <xlsx-or-csv>`,
  which exports/analyzes the returned slice and refuses incomplete sheets.
- An external-audit progress checker:
  `python scripts/check_external_audit_progress.py --audit <xlsx-or-csv>`,
  which reports completion progress and writes a sendable feedback note if
  cells still need attention.
- Public archival-release metadata templates at
  `outputs/public_release_metadata_20260617/`.
- A manual Zenodo deposit packet with SHA256 checksums and upload instructions
  at `outputs/zenodo_deposit_packet_20260617/`; DOI remains unminted until the
  archive is actually published.
- A public-release preflight report at
  `outputs/public_release_preflight_20260617/` that verifies the deposit
  packet checksum, upload manifest, metadata fields, claim-boundary notes, and
  post-publication update command before manual publication.
- Copy-paste portal field helpers:
  `outputs/zenodo_deposit_packet_20260617/ZENODO_COPY_FIELDS.md` and
  `outputs/zenodo_deposit_packet_20260617/GITHUB_RELEASE_COPY_FIELDS.md`.
- A post-publication metadata updater:
  `python scripts/update_public_release_metadata.py --doi ... --repo-url ...`,
  to replace DOI, public repository, author, and affiliation placeholders after
  real publication. Run it with `--dry-run` first to write a preview without
  modifying metadata files.
- An anonymous-release leak scan at `outputs/anonymous_release_check_20260617/`
  that checks the generated zip for local paths and user identifiers.
- A release-zip functional smoke check at
  `outputs/release_zip_smoke_20260617/` that verifies the final anonymous zip
  can be extracted and run through core offline tests and CLI commands.
- A manuscript claim-hygiene check at
  `outputs/manuscript_claim_hygiene_20260617/` that checks HEG framing anchors,
  non-claim boundaries, robustness table anchors, and high-risk overclaim
  phrases.
- A submission action packet at `outputs/submission_action_packet_20260617/`
  with `NEXT_ACTIONS_ZH.md`, the external-auditor handoff zip, and archive
  deposit metadata so the two remaining P0 external actions can be executed
  without searching across output folders. If a Windows editor displays the
  Chinese file incorrectly, use the UTF-8-BOM copy `NEXT_ACTIONS_ZH_WINDOWS.md`.
- An external-audit recruitment packet at
  `outputs/external_audit_recruitment_20260617/` with send-ready English and
  Chinese messages, an author send checklist, and an auditor boundary card.
- A local ICSE submission packet at `outputs/icse_submission_packet_20260617/`
  with `PORTAL_FIELDS.md`, `ICSE_SUBMISSION_CHECKLIST_ZH.md`, the PDF, the
  anonymous artifact zip, and checksum file for upload-time use.
- A submission-packet self-check at
  `outputs/icse_submission_packet_check_20260617/` that verifies packet file
  sizes, artifact checksum, portal fields, and checklist boundaries.
- A double-anonymous submission check at
  `outputs/double_anonymous_submission_check_20260617/` that checks the PDF and
  source for anonymous author text, front-matter identity terms,
  acknowledgments, emails, local paths, and placeholders.
- An AI assistance disclosure packet at
  `outputs/ai_assistance_disclosure_packet_20260617/` plus a disclosure check at
  `outputs/ai_assistance_disclosure_check_20260617/`, so portal AI-use wording
  is ready while preserving the boundary that AI tools were assistants, not
  operators or annotators.
- A submission blocker dashboard at
  `outputs/submission_blocker_dashboard_20260617/`, currently showing local
  readiness as passing while external audit completion and DOI/public URL remain
  external actions.
- A single-operator submission-mode dashboard can be generated with
  `python scripts/check_submission_blockers.py --single-operator-submission-mode --out outputs/submission_blocker_dashboard_20260618_single_operator`.
  In this mode, incomplete external audit completion is reported as a limitation
  and prepared follow-up material, not as current external validation.
- An acceptance-confidence gap report at
  `outputs/acceptance_probability_gap_report_20260617/`, currently showing
  `local_ready_external_blocked` with two P0 external actions and no local
  failures.
- A P0 execution dashboard at `outputs/p0_execution_dashboard_20260617/`, with
  `OPEN_P0_ACTIONS.ps1` for opening the external-audit send-now packet and the
  public-release publish-now packet from one place.
- A consolidated 80% push packet at `outputs/80_percent_push_packet_20260617/`,
  with `START_HERE_80_PERCENT_ZH_WINDOWS.md` and
  `MergeDossier-80-percent-push-packet.zip` collecting the external-audit email,
  handoff attachment, public-release checklist, upload pointer, and artifact
  archive for the remaining P0 actions.
- A post-P0 closeout packet at `outputs/post_p0_closeout_20260617/`, with
  `POST_P0_FINALIZE.ps1` and a Chinese checklist for safely processing a
  completed external audit return plus real DOI/public URL.
- An external-audit intake report at `outputs/external_audit_intake_20260617/`,
  which found one complete-looking candidate but zero ready external-return
  candidates because the best match resembles a primary/full annotation sheet.
- An external-audit send-now packet at `outputs/external_audit_send_now_20260617/`,
  with `SEND_NOW_EMAIL_ZH.eml`, `SEND_NOW_EMAIL_EN.eml`,
  `SEND_NOW_EMAIL_ZH_WINDOWS.md`, reminders, and a copied
  `MergeDossier-external-audit-handoff.zip`.
- A public-release publish-now packet at
  `outputs/public_release_publish_now_20260617/`, with
  `PUBLISH_NOW_CHECKLIST_ZH_WINDOWS.md`, `ZENODO_COPY_FIELDS.md`,
  `GITHUB_RELEASE_COPY_FIELDS.md`, `UPLOAD_FILE_POINTER.txt`, and
  `POST_PUBLICATION_UPDATE.ps1`.
- Category-level availability intervals, handoff-evidence gap tables, robust separation, and tipping-point analysis.
- Explicit claims/non-claims tables blocking correctness, mergeability, reviewer-utility, AI-vs-human, and all-GitHub claims.
- A legacy Evidence Sufficiency Score retained for artifact compatibility, not as the central empirical construct.

## Core title candidates

Primary title:

> **MergeDossier-Bench: Measuring the Handoff-Evidence Gap in AI-Authored Pull Requests**

Backup title:

> **A Diff Is Not a Dossier: Measuring the Handoff-Evidence Gap in AI-Authored Pull Requests**

Canonical citation sentence:

> MergeDossier-Bench measures the handoff-evidence gap in AI-authored pull requests by reporting provenance-backed availability intervals for surface and handoff-critical evidence.

## License

The anonymous-review snapshot is released under the MIT License in [`LICENSE`](LICENSE). Replace anonymous-review metadata with public author and repository metadata before archival release.

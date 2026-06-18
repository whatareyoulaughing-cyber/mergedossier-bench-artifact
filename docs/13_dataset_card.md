# Dataset Card

## Dataset Name

MergeDossier-Bench AIDev-pop handoff-evidence audit corpus.

## Status

This dataset card describes the current research artifact state on 2026-06-17.
The current paper-facing corpus is a **provisional anonymous-review artifact**
for a 500-PR AIDev-pop population-frame handoff-evidence audit. It is suitable
for artifact review, reproducibility checks, and bounded AIDev-pop descriptive
estimates. It is not a dataset for AI-versus-human causal claims, all-GitHub
rates, patch correctness, mergeability, reviewer utility, or inter-rater
reliability.

## Purpose

The corpus supports provenance-aware measurement of review-evidence
availability and the handoff-evidence gap in AI-authored and AI-assisted pull
requests. The unit of analysis is a pull request plus a MergeDossier: a
structured evidence packet describing intent, requirement traceability, tests,
regression safety, risk, scope, agent trace, limitations, reviewer
actionability, and ownership handoff.

The dataset is not designed to determine whether a patch is correct, whether a
pull request should be merged, or whether an automated code-review agent can
find defects.

## Current Composition

Current AIDev-pop audit corpus:

- 33,596 eligible public agentic PR rows in the declared AIDev-pop frame.
- 500 PRs in the deterministic stratified sample, drawn with seed `20260616`.
- 50 delayed-repeat audit records.
- 550 complete annotation rows.
- Handoff Evidence Availability: [0.0%, 10.16%].
- Handoff-Evidence Gap: [89.84%, 100.0%].
- Minimum robust separation between strict core evidence and lenient handoff
  evidence: 36.77 percentage points.

The earlier 22-PR mixed-source public snapshot is retained only as preliminary
pipeline and rubric validation. It is not the current empirical dataset.

## Files

Provisional pilot:

- `data/manifests/real_pilot_full_provisional_verified_manifest_20260613.csv`
- `data/real_pilot_mixed_source_raw_20260613/`
- `outputs/real_pilot_mixed_source_summary_20260613/summary.json`
- `outputs/real_pilot_mixed_source_summary_20260613/scores.jsonl`
- `outputs/real_pilot_mixed_source_group_summary_20260613.csv`
- `outputs/real_pilot_mixed_source_annotation_tasks_with_repeats_20260613.json`
- `outputs/real_pilot_mixed_source_annotation_sheet_completed_20260613.csv`
- `outputs/real_pilot_mixed_source_annotation_paper_results_20260613/`
- `outputs/submission_readiness_20260614/human_match_verification_summary.md`

AIDev-pop population-frame audit:

- `data/manifests/population_ai_pr_frame_sanitized_20260616.csv`
- `data/manifests/population_ai_pr_sample_500_20260616.csv`
- `outputs/aidev_export_report_20260616/`
- `outputs/population_sampling_report_20260616/`
- `outputs/population_ai_pr_500_20260616/reports/annotation_sheet_completed.csv`
- `outputs/population_results_20260616/population_estimates.json`
- `outputs/population_results_20260616/paper_table_availability_intervals.csv`
- `outputs/population_results_20260616/paper_table_handoff_gap.csv`
- `outputs/population_results_20260616/paper_table_tipping_point.csv`
- `outputs/dependency_sensitive_audit_20260616/results/dependency_audit_results.json`
- `outputs/external_audit_slice_20260617/`
- `outputs/raw_frame_release_risk_20260617/`

The anonymous-review artifact includes a sanitized population-frame manifest
with the 33,596 frame rows, sampling metadata, eligibility fields, strata,
weights, and sample-membership flags. It excludes PR titles, bodies, changed
file lists, commit messages, comments, reviews, and notes. The full normalized
population frame CSV is retained locally. It should be archived only after a
separate raw-text privacy and secret screening pass because public PR text can
contain token-like or private-key-like strings copied from upstream
repositories. The non-revealing scanner is documented in
`docs/16_raw_frame_release_policy.md` and writes counts, pattern names, and safe
row identifiers without matched raw text.

Toy and fixture data:

- `examples/corpus/`
- `examples/annotations/toy_label_studio_export.json`
- `tests/fixtures/github_prs/`
- `data/manifests/seed_prs.csv`

## Collection Method

The software pipeline supports three collection modes:

1. Synthetic and toy fixtures for schema and scoring validation.
2. Fixture-backed seed-corpus construction from local raw PR fixtures.
3. Optional live GitHub fetching from public pull-request endpoints when
   `GITHUB_TOKEN` is available.

The current provisional public pilot combines live-fetched AI-side artifacts
with conservatively reconstructed human-match artifacts from public GitHub PR
pages when unauthenticated API rate limits prevented complete extraction.

## Labels

The AIDev-pop audit pass is complete as a single-operator delayed-repeat
study. It should be read as audit-code evidence and self-consistency evidence,
not as inter-rater reliability.

Completed annotation artifact:

- 500 primary audit records.
- 50 delayed-repeat audit records.
- 550 complete annotation rows.
- Single-operator self-consistency audit with no category-level
  self-disagreements.
- Availability intervals, handoff-evidence gap, robust separation, and
  tipping-point tables generated from the completed audit CSV.

The intended label values are:

- `present`
- `partially_present`
- `missing`
- `not_applicable`

The audit-code target is review-evidence availability and handoff evidence, not
patch correctness or mergeability.

## Known Limitations

- The audit is limited to the declared AIDev-pop frame.
- Authorship can be ambiguous; the protocol allows AI-assisted, mixed, unknown,
  and human-authored metadata rather than forcing unsupported categories.
- Public GitHub artifacts may be rate-limited, deleted, private, or incomplete.
- The current audit uses one operator and delayed repeats; it does not establish
  inter-rater reliability.
- The current numbers should not be used as evidence that AI-authored PRs differ
  from human PRs.

## Ethical and Privacy Considerations

The corpus uses public pull-request artifacts. It should not be used to rank or
profile individual developers. Before public release, remove secrets, private
emails, access tokens, and security-sensitive exploit payloads while preserving
enough public metadata for reproducibility.

## Recommended Uses

- Validate the MergeDossier schema and scoring pipeline.
- Exercise corpus summaries and leaderboard outputs.
- Prepare and test Label Studio annotation workflows.
- Study AIDev-pop review-evidence availability and the handoff-evidence gap
  under the documented audit-code protocol.

## Non-Recommended Uses

- Ranking developers or maintainers.
- Claiming patch correctness.
- Claiming mergeability.
- Training a model to infer private author intent.
- Making AI-versus-human empirical claims.

## Maintenance

The final release should add:

- dataset version,
- archival DOI,
- final license and copyright metadata,
- public repository URL after anonymous review.
- raw-text release decision for the full frame, if the venue artifact policy
  requires more than the sanitized sampling-frame manifest. The default policy
  is to release the sanitized frame and keep raw text local unless a separate
  scrubbed or restricted archive is prepared.
- Zenodo or institutional archive deposit using the prepared packet under
  `outputs/zenodo_deposit_packet_20260617/`; the packet contains checksums and
  instructions but does not mint or claim a DOI.
- optional second annotator or external audit slice before any
  inter-coder-reliability claim.
  A deterministic 50-task external audit packet already exists at
  `outputs/external_audit_slice_20260617/`, including CSV and XLSX workbook
  formats, but no independent audit result is claimed until it is completed.

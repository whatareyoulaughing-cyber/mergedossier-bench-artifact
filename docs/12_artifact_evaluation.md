# Artifact Evaluation Plan

## Target

ICSE 2027 Artifact Evaluation follows ACM Artifact Review and Badging v1.1.
For the current project state, the appropriate target is:

- **Artifacts Available** after archival release on Zenodo or an equivalent
  persistent repository.
- **Artifacts Evaluated - Functional** now, because the offline pipeline is
  documented, complete enough to exercise, and covered by tests.
- **Artifacts Evaluated - Reusable** after the public DOI archive, repository
  metadata, and external reuse check are complete.

The current package should not claim Results Validated, Reproduced, or
Replicated. The AIDev-pop audit is bounded to one declared population frame and
one operator; delayed-repeat self-consistency and provenance auditability do not
replace independent replication.

## Artifact Inventory

Core software:

- `src/mergedossier_bench/`: CLI, schema validation, scoring, corpus summary,
  seed-corpus construction, GitHub fetching, annotation export, and annotation
  statistics.
- `schemas/`: JSON schemas for PR instances, MergeDossiers, annotations, and
  score reports.
- `scripts/reproduce_artifact_smoke.py`: reviewer-facing offline smoke workflow.
- `scripts/generate_label_studio_config.py`: Label Studio interface generator.
- `scripts/export_annotation_workbook.py`: Excel workbook generator for
  spreadsheet annotation.
- `scripts/export_annotation_csv_from_workbook.py`: exports the workbook
  `Annotation` sheet back to CSV for validation and statistics.
- `scripts/build_paper_results_from_annotations.py`: converts completed
  annotations into LaTeX result tables, pilot statistical treatment files, and
  a Markdown integration summary.
- `scripts/check_external_audit_return.py`: validates a returned external-audit
  workbook or CSV, exports the workbook if needed, and reruns the conservative
  external-audit analysis.
- `scripts/check_external_audit_progress.py`: reports completion progress for
  an in-progress or returned external-audit workbook/CSV and writes a sendable
  feedback note for missing or invalid audit-code cells.
- `scripts/build_adjudication_sheet.py`: creates an adjudication CSV and
  Markdown summary from category-level disagreement cases.
- `scripts/run_completed_annotation_pipeline.py`: one-command post-annotation
  path from filled workbook to completed CSV, validation, statistics, LaTeX
  result snippets, and adjudication files.
- `scripts/build_submission_readiness_packet.py`: summarizes provisional
  human-match verification and release-readiness status for paper submission.
- `scripts/build_population_results.py`: builds population-frame estimates,
  availability intervals, handoff-evidence gap tables, and tipping-point tables.
- `scripts/build_sanitized_population_frame.py`: emits the text-free
  33,596-row population-frame manifest used in the anonymous-review artifact.
- `scripts/scan_raw_frame_release_risks.py`: scans the full raw population
  frame for token-like and private-key-like patterns without writing matched
  strings or snippets to the report.
- `scripts/check_final_pdf_proofread.py`: renders the final PDF, builds a
  contact sheet, extracts PDF text, and checks paper-identity phrases plus
  unresolved placeholder tokens.
- `scripts/build_zenodo_deposit_packet.py`: prepares a manual archive-deposit
  packet with upload manifest, SHA256 checksums, and metadata templates without
  claiming a DOI.
- `scripts/check_public_release_preflight.py`: verifies the manual
  archive-deposit packet checksum, upload manifest, metadata fields,
  claim-boundary notes, and post-publication update command before public
  release.
- `scripts/update_public_release_metadata.py`: post-publication helper for
  replacing DOI, public repository URL, author, affiliation, and release-date
  placeholders after real archival publication.
- `scripts/check_submission_blockers.py`: builds an evidence-backed dashboard
  separating local pass/ready gates from external audit and DOI/publication
  actions.
- `scripts/build_submission_action_packet.py`: collects the remaining external
  action materials into a user-facing execution packet.
- `scripts/build_external_auditor_handoff_zip.py`: creates a sendable
  external-auditor handoff zip that excludes the primary completed annotation
  CSV and paper result tables.
- `scripts/check_external_auditor_handoff.py`: verifies the external-auditor
  handoff zip contains only handoff files, no primary/result paths, and blank
  audit-code cells before it is sent.
- `scripts/build_external_audit_recruitment_packet.py`: writes send-ready
  English/Chinese recruitment messages and boundary cards for the external
  audit slice.
- `scripts/build_icse_submission_packet.py`: collects the PDF, anonymous
  artifact zip, checksum, portal fields, and submission checklist into a local
  submission packet.
- `scripts/check_icse_submission_packet.py`: validates the local submission
  packet files, manifest sizes, artifact checksum, portal fields, and claim
  boundary checklist.
- `scripts/check_double_anonymous_submission.py`: checks the PDF/source for
  double-anonymous hygiene, including anonymous author text, front-matter
  identity terms, acknowledgments, emails, local paths, and placeholders.
- `scripts/build_ai_assistance_disclosure_packet.py`: prepares portal-ready AI
  assistance disclosure text from the paper memory draft.
- `scripts/check_ai_assistance_disclosure.py`: verifies AI disclosure wording,
  boundaries, and placement warnings.
- `scripts/check_manuscript_claim_hygiene.py`: checks paper-facing framing
  anchors, non-claim boundaries, and high-risk overclaim phrases before
  submission.
- `scripts/build_anonymous_release_zip.py`: creates the anonymous-review
  release packet and refuses to package files that match common secret patterns.
- `scripts/check_anonymous_release.py`: scans the generated anonymous-review
  zip text files and PDF metadata for local path or local-user leaks after
  packaging-time redaction.
- `scripts/check_release_zip_smoke.py`: extracts the generated
  anonymous-review zip into a temporary directory and runs a bounded offline
  smoke check from inside the extracted package.

Data and examples:

- `examples/`: toy PR, toy dossier, toy annotation, toy corpus, and toy Label
  Studio export.
- `tests/fixtures/github_prs/`: offline GitHub PR fixtures.
- `data/manifests/seed_prs.csv`: fixture-backed seed corpus manifest.
- `data/manifests/real_pilot_full_provisional_verified_manifest_20260613.csv`:
  provisional 22-PR pilot manifest.
- `data/manifests/population_ai_pr_sample_500_20260616.csv`: deterministic
  500-PR AIDev-pop sample manifest.
- `data/manifests/population_ai_pr_frame_sanitized_20260616.csv`: text-free
  33,596-row AIDev-pop frame manifest for sampling audit.

Paper-facing outputs:

- `outputs/real_pilot_mixed_source_summary_20260613/`: provisional pilot corpus
  summary.
- `outputs/real_pilot_mixed_source_annotation_tasks_with_repeats_20260613.json`:
  22 primary tasks plus 5 delayed repeats for the one-annotator pilot.
- `outputs/real_pilot_mixed_source_annotation_sheet_20260613.csv`:
  spreadsheet-friendly version of the same annotation packet.
- `outputs/real_pilot_mixed_source_annotation_workbook_20260613.xlsx`:
  Excel version with dropdown labels and an instruction sheet for one-annotator
  labeling.
- `outputs/real_pilot_mixed_source_annotation_sheet_completed_20260613.csv`:
  completed single-annotator annotation sheet.
- `outputs/real_pilot_mixed_source_annotation_paper_results_20260613/`:
  annotation statistics, self-consistency table, adjudication files, and pilot
  statistical treatment.
- `outputs/submission_readiness_20260614/`: provisional human-match
  verification summary and release-readiness checklist.
- `outputs/population_results_20260616/`: population-frame coverage estimates,
  availability intervals, handoff-evidence gap tables, tipping-point table,
  provenance/source tables, and claims/non-claims tables.
- `outputs/dependency_sensitive_audit_20260616/results/`: focused
  dependency-sensitive candidate-subset audit.
- `outputs/raw_frame_release_risk_20260617/`: non-revealing raw-frame risk
  scan summary used to document why the full raw-text frame is not shipped by
  default.
- `outputs/final_pdf_proofread_20260617/`: final PDF proofread report,
  extracted text, rendered pages, and contact sheet.
- `outputs/submission_blocker_dashboard_20260617/`: current local/external
  blocker dashboard for submission confidence.
- `outputs/acceptance_probability_gap_report_20260617/`: local
  acceptance-confidence gap report summarizing the remaining P0 external
  actions without estimating a calibrated acceptance probability.
- `outputs/post_p0_closeout_20260617/`: parameterized closeout runner and
  checklist for the moment when the external audit return and real DOI/public
  URL are available.
- `outputs/external_audit_intake_20260617/`: candidate-file intake scan that
  distinguishes ready external-return candidates from complete-looking but
  independence-unverified files.
- `outputs/external_audit_send_now_20260617/`: send-now external-audit email,
  `.eml` drafts, attachment copy, follow-up reminders, and return checklist.
- `outputs/public_release_publish_now_20260617/`: Zenodo/GitHub copy fields,
  upload-file pointer, checksum, and dry-run-first post-publication update
  runner for DOI/public URL publication.
- `outputs/p0_execution_dashboard_20260617/`: one-page P0 execution dashboard
  and `OPEN_P0_ACTIONS.ps1` helper for opening the two remaining external-action
  packets.
- `outputs/80_percent_push_packet_20260617/`: consolidated author-side packet
  containing the external-audit send-now files and public-release publish-now
  files for executing the remaining P0 actions.
- `outputs/manuscript_claim_hygiene_20260617/`: manuscript framing and
  claim-boundary hygiene check.
- `outputs/submission_action_packet_20260617/`: Chinese next-action packet for
  the external audit return and DOI/public-URL publication steps.
- `outputs/icse_submission_packet_20260617/`: local ICSE submission packet with
  files for upload, portal fields, and a final checklist.
- `outputs/icse_submission_packet_check_20260617/`: self-check report for the
  local ICSE submission packet.
- `outputs/double_anonymous_submission_check_20260617/`: double-anonymous PDF
  and source hygiene check.
- `outputs/ai_assistance_disclosure_packet_20260617/`: portal-ready AI
  assistance disclosure packet.
- `outputs/ai_assistance_disclosure_check_20260617/`: AI disclosure wording and
  placement check.
- `outputs/anonymous_release_check_20260617/`: generated zip anonymity scan.
- `docs/13_dataset_card.md`: AIDev-pop handoff-evidence audit dataset card.
- `docs/14_release_manifest.md`: anonymous-review release manifest.
- `docs/16_raw_frame_release_policy.md`: raw-frame release boundary and
  scanner procedure.
- `outputs/release/MergeDossier-Bench-anonymous-review.zip`: generated
  anonymous-review release packet.

## One-Command Offline Check

From a fresh checkout after installing the package:

```bash
pip install -e ".[dev]"
python scripts/reproduce_artifact_smoke.py
python scripts/check_manuscript_claim_hygiene.py
python scripts/build_submission_action_packet.py
python scripts/build_icse_submission_packet.py
python scripts/check_icse_submission_packet.py
python scripts/check_double_anonymous_submission.py
python scripts/build_ai_assistance_disclosure_packet.py
python scripts/check_ai_assistance_disclosure.py
python scripts/build_anonymous_release_zip.py
python scripts/check_release_zip_smoke.py
```

The script writes:

```text
outputs/artifact_smoke/
  toy_score.json
  corpus_dir/summary.json
  corpus_jsonl/summary.json
  seed_corpus/
  seed_summary/summary.json
  seed_annotation_tasks.json
  seed_annotation_tasks_with_repeats.json
  seed_annotation_sheet.csv
  seed_annotation_sheet_validation.json
  annotation_stats/agreement_summary.json
  artifact_smoke_log.json
```

It also runs `pytest -q`. The current test suite has 145 passing tests.

The release-zip smoke checker writes:

```text
outputs/release_zip_smoke_20260617/
  release_zip_smoke.json
  release_zip_smoke.md
```

This output is a local verification artifact and is intentionally not packaged
inside the anonymous-review zip, avoiding a checksum self-reference.

## Optional Live Fetch

Live GitHub fetching is not required for the artifact smoke check. If a reviewer
wants to exercise it, set `GITHUB_TOKEN` and run a small manifest with
`--live --limit 5`. The token is read from the environment and is not printed or
stored by the tool.

## Expected Limitations

- The AIDev-pop audit is single-operator and does not support inter-rater
  reliability claims.
- The estimates apply only to the declared AIDev-pop frame.
- The full normalized frame CSV is not included in the anonymous-review zip
  because public PR text can contain token-like or private-key-like strings
  copied from upstream repositories. The sanitized 33,596-row frame is included
  for sampling audit; any raw-text archive requires a separate scrubbed or
  restricted release decision.
- Some public GitHub artifacts may be missing because of rate limits, deleted
  data, or unauthenticated endpoint access.
- Label Studio itself is an external UI dependency; the repository provides task
  export and export parsing, but it does not vendor Label Studio.

## Reviewer Checklist

1. Install with `pip install -e ".[dev]"`.
2. Run `python scripts/reproduce_artifact_smoke.py`.
3. Confirm `pytest -q` passes inside the smoke log.
4. Inspect `outputs/artifact_smoke/corpus_dir/summary.json`.
5. Inspect `outputs/artifact_smoke/annotation_stats/agreement_summary.md`.
6. Inspect `outputs/population_results_20260616/paper_table_handoff_gap.csv`.
7. Inspect `docs/13_dataset_card.md` and confirm the dataset scope and limits.
8. Inspect `docs/14_release_manifest.md` and confirm expected release contents.
9. Inspect `docs/16_raw_frame_release_policy.md` and
   `outputs/raw_frame_release_risk_20260617/raw_frame_release_risk_summary.md`.
10. Inspect `outputs/final_pdf_proofread_20260617/final_pdf_proofread.md` and
   the generated contact sheet.
11. Inspect `outputs/manuscript_claim_hygiene_20260617/manuscript_claim_hygiene.md`.
12. Inspect `outputs/submission_action_packet_20260617/NEXT_ACTIONS_ZH.md`.
13. Inspect `outputs/icse_submission_packet_20260617/PORTAL_FIELDS.md` and
   `outputs/icse_submission_packet_20260617/ICSE_SUBMISSION_CHECKLIST_ZH.md`.
14. Inspect `outputs/icse_submission_packet_check_20260617/icse_submission_packet_check.md`.
15. Inspect `outputs/double_anonymous_submission_check_20260617/double_anonymous_submission_check.md`.
16. Inspect `outputs/ai_assistance_disclosure_packet_20260617/PORTAL_AI_DISCLOSURE.md`
   and `outputs/ai_assistance_disclosure_check_20260617/ai_assistance_disclosure_check.md`.
17. Inspect `outputs/release/MergeDossier-Bench-anonymous-review.zip` and its
   embedded `RELEASE_MANIFEST.json`.
18. Run `python scripts/check_release_zip_smoke.py` and inspect
   `outputs/release_zip_smoke_20260617/release_zip_smoke.md`.
19. Inspect `.paper/ai_assistance_disclosure.md`.
20. Confirm no secrets or tokens are present in manifests, logs, or raw fixtures.

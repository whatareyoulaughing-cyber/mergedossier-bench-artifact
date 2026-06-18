# Release Manifest

## Release Target

MergeDossier-Bench v0.1.0, anonymous-review artifact snapshot.

The current release target is a functional artifact for reviewer inspection.
The final public release should be archived with a DOI after anonymous review
and after final metadata, license, and repository URLs are added.

Current paper framing: **MergeDossier-Bench: Measuring the Handoff-Evidence Gap
in AI-Authored Pull Requests**. The release should support the AIDev-pop
population-frame audit, availability-interval tables, handoff-evidence gap
tables, provenance audit outputs, and offline smoke workflow.

## Required Files For Review Snapshot

Software:

- `pyproject.toml`
- `src/mergedossier_bench/`
- `schemas/`
- `scripts/reproduce_artifact_smoke.py`
- `scripts/generate_label_studio_config.py`
- `scripts/build_population_results.py`
- `scripts/check_icse_format.py`
- `scripts/check_final_pdf_proofread.py`
- `scripts/check_paper_readiness.py`
- `scripts/build_zenodo_deposit_packet.py`
- `scripts/update_public_release_metadata.py`
- `scripts/build_submission_action_packet.py`
- `scripts/build_icse_submission_packet.py`
- `scripts/check_icse_submission_packet.py`
- `scripts/check_double_anonymous_submission.py`
- `scripts/build_ai_assistance_disclosure_packet.py`
- `scripts/check_ai_assistance_disclosure.py`
- `scripts/check_manuscript_claim_hygiene.py`
- `scripts/check_submission_blockers.py`
- `scripts/check_anonymous_release.py`
- `scripts/check_release_zip_smoke.py`
- `scripts/check_external_audit_return.py`
- `tests/`

Documentation:

- `README.md`
- `AGENTS.md`
- `docs/00_positioning.md`
- `docs/02_dossier_schema.md`
- `docs/03_annotation_guidelines.md`
- `docs/08_annotation_protocol.md`
- `docs/12_artifact_evaluation.md`
- `docs/13_dataset_card.md`
- `docs/14_reframing_to_evidence_availability.md`
- `docs/15_claims_and_nonclaims.md`
- `docs/16_raw_frame_release_policy.md`
- `.paper/ai_assistance_disclosure.md`
- `CITATION.cff`
- `LICENSE`

Data:

- `examples/`
- `tests/fixtures/github_prs/`
- `data/manifests/seed_prs.csv`
- `data/manifests/real_pilot_full_provisional_verified_manifest_20260613.csv`
- `data/manifests/population_ai_pr_frame_sanitized_20260616.csv`
- `data/manifests/population_ai_pr_sample_500_20260616.csv`
- `data/real_pilot_mixed_source_raw_20260613/`

Paper-facing outputs:

- `outputs/real_pilot_mixed_source_summary_20260613/`
- `outputs/real_pilot_mixed_source_group_summary_20260613.csv`
- `outputs/real_pilot_mixed_source_annotation_tasks_with_repeats_20260613.json`
- `outputs/real_pilot_mixed_source_annotation_sheet_completed_20260613.csv`
- `outputs/real_pilot_mixed_source_annotation_paper_results_20260613/`
- `outputs/submission_readiness_20260614/`
- `outputs/aidev_export_report_20260616/`
- `outputs/population_sampling_report_20260616/`
- `outputs/population_ai_pr_500_20260616/reports/annotation_sheet_completed.csv`
- `outputs/population_results_20260616/`
- `outputs/dependency_sensitive_audit_20260616/results/`
- `outputs/external_audit_slice_20260617/`
- `outputs/final_pdf_proofread_20260617/`
- `outputs/raw_frame_release_risk_20260617/`
- `outputs/manuscript_claim_hygiene_20260617/`
- `outputs/submission_blocker_dashboard_20260617/`
- `outputs/acceptance_probability_gap_report_20260617/`
- `outputs/post_p0_closeout_20260617/`
- `outputs/external_audit_intake_20260617/`
- `outputs/external_audit_send_now_20260617/`
- `outputs/public_release_publish_now_20260617/`
- `outputs/icse_format_check_20260617_handoff_gap.md`
- `outputs/layout_quality_20260617.md`
- `outputs/visual_check_layout_quality_20260617/visual_layout_review.md`
- `outputs/visual_check_layout_quality_20260617/contact.png`
- `outputs/paper_readiness_check_20260617_handoff_gap/`
- `outputs/paper_layout_build_check_20260617/`

Required handoff-gap tables under `outputs/population_results_20260616/`:

- `paper_table_availability_intervals.csv` and `.tex`
- `paper_table_handoff_gap.csv` and `.tex`
- `paper_table_tipping_point.csv` and `.tex`
- `paper_table_claims_nonclaims.md` and `.tex`

External-audit slice packet:

- `outputs/external_audit_slice_20260617/external_audit_tasks.json`
- `outputs/external_audit_slice_20260617/external_audit_sheet.csv`
- `outputs/external_audit_slice_20260617/README_external_audit.md`
- `outputs/external_audit_slice_20260617/external_audit_manifest.json`

This packet is ready for an independent operator, but it is not used for a
current inter-rater reliability claim unless completed and analyzed.

The local submission action packet at
`outputs/submission_action_packet_20260617/` is generated for the author, not
packaged inside the anonymous-review release. Keeping it outside the release
zip avoids a checksum self-reference because the packet records the current
archive checksum for manual deposit.
The local ICSE submission packet at `outputs/icse_submission_packet_20260617/`
is also excluded from the anonymous-review release because it contains a copied
artifact zip for upload convenience.
The local release-zip smoke report at `outputs/release_zip_smoke_20260617/` is
also excluded. It is generated after the zip exists by extracting that zip and
running commands from the extracted tree, so packaging it would introduce a
self-reference.
The local acceptance-confidence gap report at
`outputs/acceptance_probability_gap_report_20260617/` is also excluded. It
summarizes the current release checksum and remaining external actions, so it
is a project-management output rather than part of the anonymous-review
artifact.
The post-P0 closeout packet at `outputs/post_p0_closeout_20260617/` is also
excluded because it is an author-side runner for after the external audit and
real DOI/public URL exist.
The external-audit intake report at `outputs/external_audit_intake_20260617/`
is also excluded because it scans local candidate files and can mention local
Downloads paths; it is an author-side guard against misusing a non-external
annotation file.
The external-audit send-now packet at `outputs/external_audit_send_now_20260617/`
is also excluded because it is author-side correspondence and contains a copied
handoff attachment plus `.eml` drafts for convenience.
The public-release publish-now packet at
`outputs/public_release_publish_now_20260617/` is also excluded because it is an
author-side publication helper and references local upload paths.
The P0 execution dashboard at `outputs/p0_execution_dashboard_20260617/` is
also excluded because it is an author-side helper that points to the
external-audit send-now packet and the public-release publish-now packet.
The consolidated 80% push packet at `outputs/80_percent_push_packet_20260617/`
is also excluded because it bundles author-side correspondence and publication
execution files, including a copied upload archive, for manual P0 execution.

The full normalized population frame CSV is not included in the anonymous
review zip because it contains public PR text that can trigger token and private
key patterns copied from upstream repositories. The review packet includes the
export report, deterministic sample manifest, sampling report, build scripts,
derived tables, sanitized 33,596-row population frame, and non-revealing
raw-frame risk scan. Any full raw-text archive should be prepared separately
after automated scanning and manual review.

## Exclude From Public Release

- local virtual environments,
- pytest caches,
- generated LaTeX auxiliaries,
- private raw data,
- `.env` files,
- tokens or credentials,
- one-off exploratory outputs not referenced by the paper or artifact docs.

## Verification Commands

Run:

```bash
python scripts/reproduce_artifact_smoke.py
pytest -q
python scripts/build_and_check_paper_layout.py --out-dir outputs/paper_layout_build_check_20260617
python scripts/check_layout_quality.py --tex paper/main.tex --pdf paper/main.pdf --log paper/build.log --figures-dir paper/figures
python scripts/check_final_pdf_proofread.py --pdf paper/main.pdf --out outputs/final_pdf_proofread_20260617
python scripts/check_manuscript_claim_hygiene.py
python scripts/build_submission_action_packet.py
python scripts/build_icse_submission_packet.py
python scripts/check_icse_submission_packet.py
python scripts/check_double_anonymous_submission.py
python scripts/build_ai_assistance_disclosure_packet.py
python scripts/check_ai_assistance_disclosure.py
python scripts/scan_raw_frame_release_risks.py
python scripts/build_anonymous_release_zip.py
python scripts/check_anonymous_release.py
python scripts/check_release_zip_smoke.py
python scripts/build_zenodo_deposit_packet.py
python scripts/check_public_release_preflight.py
python scripts/check_submission_blockers.py
```

After a real DOI and public repository URL exist, run:

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

Expected:

- smoke workflow exits with code 0,
- `outputs/artifact_smoke/artifact_smoke_log.json` exists,
- `pytest -q` reports 151 passing tests in the current snapshot,
- `scripts/build_and_check_paper_layout.py` exits with code 0 and rebuilds
  `paper/main.pdf` before running format and layout gates,
- `scripts/check_layout_quality.py` exits with code 0, reports 0 warnings,
  and confirms the PDF is fresh relative to TeX and included figures,
- `scripts/check_final_pdf_proofread.py` exits with code 0 and reports 0
  failures while writing the contact sheet,
- `scripts/check_manuscript_claim_hygiene.py` exits with code 0 and reports no
  missing framing anchors, missing non-claim boundaries, or overclaim findings,
- `scripts/build_submission_action_packet.py` writes
  `outputs/submission_action_packet_20260617/NEXT_ACTIONS_ZH.md` and copies the
  external-auditor handoff files plus archive-deposit metadata,
- `scripts/build_icse_submission_packet.py` writes
  `outputs/icse_submission_packet_20260617/PORTAL_FIELDS.md`, a checklist, and
  a local copy of the PDF/artifact files for upload,
- `scripts/check_icse_submission_packet.py` exits with code 0 and verifies
  submission packet files, manifest sizes, checksum, portal fields, and claim
  boundary checklist,
- `scripts/check_double_anonymous_submission.py` exits with code 0 and reports
  no PDF/source identity leaks under the local double-anonymous hygiene rules,
- `scripts/build_ai_assistance_disclosure_packet.py` writes
  `outputs/ai_assistance_disclosure_packet_20260617/PORTAL_AI_DISCLOSURE.md`,
- `scripts/check_ai_assistance_disclosure.py` exits with code 0 and verifies
  AI disclosure responsibility, non-operator, and non-claim boundaries,
- `scripts/scan_raw_frame_release_risks.py` writes JSON/Markdown reports
  without matched secret text,
- `scripts/build_zenodo_deposit_packet.py` writes upload instructions, a
  manifest, and SHA256 checksums without claiming a DOI,
- `scripts/check_public_release_preflight.py` exits with code 0 and reports
  `ready_for_manual_publication`, with expected warnings for unresolved
  DOI/public-URL placeholders before real publication,
- `scripts/update_public_release_metadata.py` is available for post-publication
  placeholder replacement after a real DOI exists,
- `scripts/check_submission_blockers.py` reports P0 external blockers and local
  pass/ready gates,
- `scripts/check_anonymous_release.py` reports 0 local path/user leaks in
  generated text artifacts and PDF metadata inside the anonymous-review zip,
- `scripts/check_release_zip_smoke.py` extracts the generated zip into a
  temporary directory, runs a stable test subset plus corpus/provenance CLI
  commands from inside the extracted package, and writes
  `outputs/release_zip_smoke_20260617/release_zip_smoke.md`,
- `outputs/visual_check_layout_quality_20260617/visual_layout_review.md`
  records the final full-page contact-sheet visual review,
- `python scripts/check_paper_readiness.py --out outputs/paper_readiness_check_20260617_handoff_gap`
  exits with code 0.
- `outputs/release/MergeDossier-Bench-anonymous-review.zip` exists and contains
  `RELEASE_MANIFEST.json`.

## Metadata To Replace Before Public Archival

- `CITATION.cff`: replace anonymous author and placeholder URLs.
- `LICENSE`: replace anonymous-review copyright holder if required by the
  archival venue.
- `pyproject.toml`: replace anonymous author metadata if the public repository
  should expose authorship.
- `README.md`: add public repository URL and archival DOI.
- `docs/13_dataset_card.md`: add final dataset version, DOI, and final
  release status.
- `outputs/public_release_metadata_20260617/`: replace placeholders in the
  Zenodo metadata template and GitHub release notes.

## Badge Boundary

Current snapshot:

- Functional artifact: supported by smoke workflow and tests.
- Available artifact: pending archival DOI.
- Reusable artifact: pending final DOI, public repository metadata, license
  cleanup, and external reuse check.
- Results Validated: not claimed.

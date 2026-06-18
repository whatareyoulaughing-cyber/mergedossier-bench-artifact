# Submission Blocker Dashboard

Overall status: **submission_ready_local**

Mode: Single-operator submission mode is active: an incomplete external audit is treated as a P1 limitation, not a P0 blocker, because the manuscript must avoid inter-rater-reliability claims and rely on delayed-repeat self-consistency, provenance records, perturbation checks, and reproducible scripts.

| Blocker | Severity | Status | Evidence | Action |
|---|---:|---:|---|---|
| External audit slice | P1 | ready | outputs/external_audit_analysis_20260617/external_audit_summary.json status=incomplete; blank_label_cells=500. | Submit with the single-operator boundary: delayed-repeat self-consistency, provenance/perturbation checks, and no inter-rater-reliability claim. |
| Anonymous artifact release | P0 | pass | release/UPLOAD_RESULT.md records verified anonymous GitHub release: https://github.com/whatareyoulaughing-cyber/mergedossier-bench-artifact/releases/tag/v0.1-anonymous. | Use the anonymous release URL in the submission portal; defer DOI archival until double-anonymous constraints are lifted. |
| DOI archival boundary | P2 | ready | release/UPLOAD_RESULT.md records DOI deferral during double-anonymous review. | Do not claim DOI archival in the submission; mint DOI after review constraints are lifted or if the venue explicitly permits anonymous DOI. |
| Local paper readiness | P1 | pass | outputs/paper_readiness_check_20260617_handoff_gap/paper_readiness_check.json status=pass; gates=8. | Keep rerunning before final submission. |
| Manuscript claim hygiene | P1 | pass | outputs/manuscript_claim_hygiene_20260617/manuscript_claim_hygiene.json status=pass; findings=0. | Keep rerunning after paper edits. |
| Post-upload ICSE submission packet | P1 | pass | outputs/icse_submission_packet_post_upload_20260618/packet_status.json records artifact URL and remaining action: submit with single-operator boundary; treat external audit as future replication material. | Use outputs/icse_submission_packet_post_upload_20260618/PORTAL_FIELDS_FINAL_POST_UPLOAD.md and send the external-audit handoff packet. |
| External auditor handoff independence | P1 | pass | outputs/external_audit_handoff_20260617/external_auditor_handoff_check.json status=pass; failures=0. | Send the checked handoff zip to the external auditor. |
| ICSE submission packet self-check | P1 | pass | outputs/icse_submission_packet_check_20260617/icse_submission_packet_check.json status=pass; failures=0; warnings=0. | Keep rerunning after rebuilding the ICSE submission packet. |
| Double-anonymous submission check | P1 | pass | outputs/double_anonymous_submission_check_20260617/double_anonymous_submission_check.json status=pass; failures=0; warnings=0. | Keep rerunning after paper/PDF edits. |
| AI assistance disclosure | P1 | pass | outputs/ai_assistance_disclosure_check_20260617/ai_assistance_disclosure_check.json status=pass; failures=0; warnings=1. | Use outputs/ai_assistance_disclosure_packet_20260617/PORTAL_AI_DISCLOSURE.md if the submission portal asks for AI usage. |
| Release zip functional smoke | P1 | pass | outputs/release_zip_smoke_20260617/release_zip_smoke.json status=pass; commands=3. | Keep rerunning after rebuilding the anonymous release zip. |
| Public release preflight | P1 | pass | outputs/public_release_preflight_20260617/public_release_preflight.json status=ready_for_manual_publication; warnings=2. | Use the preflight report while manually publishing the DOI/public repository. |
| Anonymous release leak scan | P1 | pass | outputs/anonymous_release_check_20260617/anonymous_release_check.json status=pass; findings=0. | Keep rerunning after rebuilding the release zip. |
| Public metadata placeholders | P1 | open | Placeholders remain in: outputs/public_release_metadata_20260617/zenodo_metadata_template.json, CITATION.cff, README.md | After DOI/public repository creation, run scripts/update_public_release_metadata.py. |
| Raw-frame release policy | P2 | ready | outputs/raw_frame_release_risk_20260617/raw_frame_release_risk_summary.json reports 25 affected raw-frame rows; sanitized release remains default. | Keep raw frame excluded unless a separate scrubbed/restricted archive is prepared. |

## Interpretation

P0 open items are external actions required before claiming very high submission confidence. Local pass/ready items reduce reviewer risk but do not prove external audit completion. In single-operator submission mode, the external-audit packet remains prepared follow-up material rather than current evidence. For double-anonymous review, a verified anonymous artifact URL can satisfy review access while DOI archival remains a post-review boundary unless the venue explicitly permits anonymous DOI minting.

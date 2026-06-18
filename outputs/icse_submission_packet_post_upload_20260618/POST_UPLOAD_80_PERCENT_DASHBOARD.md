# Post-Upload 80% Dashboard

Generated: 2026-06-18

## Current Readiness

Heuristic readiness is now **78-80%**, not a calibrated acceptance probability.

The anonymous artifact release is now a verified strength:

- anonymous repository: https://github.com/whatareyoulaughing-cyber/mergedossier-bench-artifact
- anonymous release: https://github.com/whatareyoulaughing-cyber/mergedossier-bench-artifact/releases/tag/v0.1-anonymous
- release zip SHA256: recorded in the GitHub release asset `MergeDossier-Bench-anonymous-artifact.sha256`
- anonymous scan: pass, 0 findings
- downloaded release zip anonymous scan: pass, 0 findings
- local tests after the single-operator route change: 151 passed
- reviewer smoke commands: pass
- single-operator dashboard: `submission_ready_local`, `P0 open=0`, `fail=0`

## Gap To 80%

The remaining gap is no longer a hard external-audit blocker. Because two independent operators are not available before submission, the active route is a bounded single-operator submission.

The paper should foreground:

1. 500 AIDev-pop PRs with 50 delayed repeats.
2. Single-operator delayed-repeat self-consistency.
3. Provenance-backed inspectability.
4. Perturbation checks and sensitivity/HEG robustness tables.
5. External-audit packet as future independent-replication material only.

## Submission Boundary

Submit with the current artifact URL and the single-operator limitation text in `SUBMIT_NOW_WITHOUT_EXTERNAL_AUDIT_LIMITATION.md` and `outputs/no_second_operator_alternative_20260618/SUBMISSION_COPY_FIELDS_SINGLE_OPERATOR_ZH.md`.

This keeps the paper honest: single-operator audit, delayed-repeat self-consistency, provenance-backed instrument auditability, and bounded AIDev-pop estimates. Do not write that the external audit is complete.

## Do Not Spend More Time On

- DOI minting during double-anonymous review, unless the venue explicitly permits anonymous DOI.
- More artifact packaging, unless a reviewer-facing defect is found.
- New AI-vs-human comparisons.
- Reviewer utility claims.
- Mergeability or correctness claims.
- Inter-rater reliability or completed external agreement.

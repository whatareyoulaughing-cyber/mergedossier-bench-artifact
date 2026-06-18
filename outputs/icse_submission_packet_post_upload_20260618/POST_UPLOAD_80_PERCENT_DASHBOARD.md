# Post-Upload 80% Dashboard

Generated: 2026-06-18

## Current Readiness

Heuristic readiness is still **75-78%**, not a calibrated acceptance probability.

The anonymous artifact release is now a verified strength:

- anonymous repository: https://github.com/whatareyoulaughing-cyber/mergedossier-bench-artifact
- anonymous release: https://github.com/whatareyoulaughing-cyber/mergedossier-bench-artifact/releases/tag/v0.1-anonymous
- release zip SHA256: `32622b929dc9ba98d6b35031542d363499a6a9bd2206c99cb72a0db9d9a424d7`
- anonymous scan: pass, 0 findings
- fresh clone tests: 145 passed
- reviewer smoke commands: pass

## Gap To 80%

The remaining gap is not more figure polish. It is the external audit slice.

To plausibly reach the 80% target, complete this sequence:

1. Send `outputs/external_audit_handoff_20260617/MergeDossier-external-audit-handoff.zip` to an external operator.
2. Receive the completed `external_audit_sheet.xlsx`.
3. Run `check_external_audit_progress.py` and `check_external_audit_return.py`.
4. If complete, add a bounded external-audit sentence. Do not claim inter-rater reliability.

## If The Audit Cannot Return In Time

Submit with the current artifact URL and the conservative limitation text in `SUBMIT_NOW_WITHOUT_EXTERNAL_AUDIT_LIMITATION.md`.

This keeps the paper honest: single-operator audit, delayed-repeat self-consistency, provenance-backed instrument auditability, and bounded AIDev-pop estimates.

## Do Not Spend More Time On

- DOI minting during double-anonymous review, unless the venue explicitly permits anonymous DOI.
- More artifact packaging, unless a reviewer-facing defect is found.
- New AI-vs-human comparisons.
- Reviewer utility claims.
- Mergeability or correctness claims.


# External Audit Quickstart

Thank you for helping with a 50-task external audit slice for MergeDossier-Bench.

## What To Do

1. Open `external_audit_sheet.xlsx`.
2. Use the `Annotation` sheet.
3. Fill every column ending in `_label` using only the dropdown values:
   `present`, `partially_present`, `missing`, or `not_applicable`.
4. Add short comments where the evidence is ambiguous or difficult to judge.
5. Do not inspect the primary completed audit sheet or paper results while coding.
6. Save the completed workbook and send it back.

## Coding Boundary

Code visible review-evidence availability only. Do not judge whether the patch is correct,
whether it should be merged, whether reviewers would prefer it, or whether AI-authored PRs
are better or worse than human-authored PRs.

## Return Format

Preferred: return the completed `external_audit_sheet.xlsx`.
Optional: also export the `Annotation` sheet as CSV.

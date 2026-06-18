# External Audit Return Gate

Generated: 2026-06-18

## Current State

The 50-task external audit slice is still incomplete in the current repository state.

Current evidence:

- selected tasks: 50
- required audit-code cells: 500
- valid external audit-code cells: 0
- blank audit-code cells: 500

Therefore the manuscript may claim single-operator audit and delayed-repeat self-consistency, but it must not claim external agreement, inter-rater reliability, or independently validated labels.

## Required Return Check

After receiving the completed workbook or CSV:

```powershell
python scripts/check_external_audit_progress.py --audit <completed_external_audit_sheet.xlsx-or-csv> --out outputs/external_audit_progress_20260618
python scripts/check_external_audit_return.py --completed <completed_external_audit_sheet.xlsx-or-csv> --out outputs/external_audit_analysis_20260618
```

Completion evidence must be in:

- `outputs/external_audit_analysis_20260618/external_audit_return_status.json`
- `outputs/external_audit_analysis_20260618/external_audit_summary.json`
- `outputs/external_audit_analysis_20260618/external_audit_summary.md`

## Allowed Wording If Complete

Use only bounded wording:

> We also completed a 50-task external audit slice as an instrument-audit check. This audit supports inspectability of the coding protocol but does not establish inter-rater reliability.

## Required Wording If Not Complete

Use:

> External audit materials are prepared, but the current results rely on a single-operator audit with delayed-repeat self-consistency. We therefore do not claim inter-rater reliability.


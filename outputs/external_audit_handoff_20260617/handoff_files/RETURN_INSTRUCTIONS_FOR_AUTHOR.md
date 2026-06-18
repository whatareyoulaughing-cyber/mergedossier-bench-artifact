# Return Instructions For Author

After receiving the completed external-audit workbook:

Preferred one-command check:

```bash
python scripts/check_external_audit_progress.py \
  --audit <completed_external_audit_sheet.xlsx> \
  --out outputs/external_audit_progress_20260617

python scripts/check_external_audit_return.py \
  --completed <completed_external_audit_sheet.xlsx> \
  --out outputs/external_audit_analysis_20260617
```

The progress helper writes a completion report and a sendable feedback note
if cells still need attention. The return helper accepts either `.xlsx`
or `.csv`, exports the workbook if needed, runs the external-audit
analysis, and writes `external_audit_return_status.md`.

Manual fallback:

1. Export the `Annotation` sheet to CSV:

```bash
python scripts/export_annotation_csv_from_workbook.py \
  --workbook <completed_external_audit_sheet.xlsx> \
  --out outputs/external_audit_analysis_20260617/completed_external_audit_sheet.csv
```

2. Analyze the completed slice:

```bash
python scripts/analyze_external_audit_slice.py \
  --primary outputs/population_ai_pr_500_20260616/reports/annotation_sheet_completed.csv \
  --external outputs/external_audit_analysis_20260617/completed_external_audit_sheet.csv \
  --manifest outputs/external_audit_slice_20260617/external_audit_manifest.json \
  --out outputs/external_audit_analysis_20260617
```

Only cite the external-audit result if `external_audit_summary.json` reports
`status: complete`.

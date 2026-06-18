# Parallel External Audit Packets

These packets split the existing 50-task external audit slice into smaller independent packets.
They do not change the study design or create an inter-rater-reliability claim.

## Send

- `outputs/external_audit_parallel_packets_20260618/MergeDossier-external-audit-part_01.zip`: 25 rows
- `outputs/external_audit_parallel_packets_20260618/MergeDossier-external-audit-part_02.zip`: 25 rows

Ask each operator to return only their completed workbook or CSV.

## Merge Returns

After all parts return, merge them:

```powershell
python scripts/build_external_audit_parallel_packets.py merge --partials <completed_part_01.csv-or-xlsx> <completed_part_02.csv-or-xlsx> --out outputs/external_audit_parallel_packets_20260618/merged_external_audit_sheet.csv
```

Then run the existing return gate:

```powershell
python scripts/check_external_audit_return.py --completed outputs/external_audit_parallel_packets_20260618/merged_external_audit_sheet.csv --out outputs/external_audit_analysis_20260618
```

Only a complete merged return may support a bounded external-audit statement.

# Send These Two Packets Now

Generated: 2026-06-18

To reduce turnaround time, send the two packets below to two different external operators.
Each packet has 25 rows. This does not change the paper claim boundary: the merged return
is an external audit slice only, not inter-rater reliability.

## Attachments

1. `outputs/external_audit_parallel_packets_20260618/MergeDossier-external-audit-part_01.zip`
2. `outputs/external_audit_parallel_packets_20260618/MergeDossier-external-audit-part_02.zip`

## Short Email Text

Subject: 25-task external audit slice for an ICSE artifact paper

Hi <name>,

Could you help independently code a 25-task external audit packet for my ICSE artifact paper?
Please open the attached zip, fill every `_label` cell in `external_audit_sheet.xlsx`, and
return the completed workbook.

Use only these audit codes: `present`, `partially_present`, `missing`, or `not_applicable`.
Please do not judge code correctness, mergeability, reviewer utility, or AI-vs-human differences.
Also, please do not look at my primary annotation CSV or paper results.

Estimated time: about 30-45 minutes.

Thank you!

## After Both Returns

Merge:

```powershell
python scripts/build_external_audit_parallel_packets.py merge --partials <completed_part_01.xlsx> <completed_part_02.xlsx> --out outputs/external_audit_parallel_packets_20260618/merged_external_audit_sheet.csv
```

Run the return gate:

```powershell
python scripts/check_external_audit_return.py --completed outputs/external_audit_parallel_packets_20260618/merged_external_audit_sheet.csv --out outputs/external_audit_analysis_20260618
```


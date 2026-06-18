# Release Zip Smoke Check

Status: **pass**

Archive: `outputs/release/MergeDossier-Bench-anonymous-review.zip`
Package root: `MergeDossier-Bench-anonymous-20260617`

## Commands

| Name | Return code |
|---|---:|
| pytest_subset | 0 |
| corpus_summary | 0 |
| provenance_audit | 0 |

## Expected Outputs

| Output | Present |
|---|---:|
| `outputs/release_zip_smoke/corpus/summary.json` | True |
| `outputs/release_zip_smoke/corpus/scores.jsonl` | True |
| `outputs/release_zip_smoke/provenance/provenance_summary.json` | True |
| `outputs/release_zip_smoke/provenance/uncited_evidence.jsonl` | True |

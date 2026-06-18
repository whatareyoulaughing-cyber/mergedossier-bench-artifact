# Evidence Provenance

MergeDossier-Bench treats review-evidence availability as a cited measurement
problem. The original slogan still holds: **A diff is not a dossier.** MVP-4
adds a second operational rule: **A dossier must cite its evidence.**

## Schema

`schemas/merge_dossier.schema.json` accepts an optional top-level
`evidence_provenance` object. This keeps legacy dossiers valid while allowing
new reconstructed dossiers to attach provenance records to each evidence
category.

Canonical internal evidence keys remain:

- `intent`
- `requirement_traceability`
- `test_rationale`
- `regression_safety`
- `risk_analysis`
- `scope_justification`
- `change_summary`
- `agent_trace`
- `limitations`
- `reviewer_actionability`
- `ownership_handoff`

Each provenance record contains:

- `status`: `observed`, `inferred`, `missing`, or `not_applicable`
- `source_type`: PR title/body, linked issue, changed file, commit, CI check,
  review, comment, manifest, heuristic, or unknown
- `source_id`, `source_url`, `raw_path`, and `excerpt` when available
- `extraction_rule`
- `confidence`: `high`, `medium`, or `low`
- optional `notes`

## Interpretation

`observed` means the visible artifact explicitly says the evidence. `inferred`
means the reconstruction rule found metadata that supports a cautious evidence
claim, such as changed test files or passing CI. `missing` means the audit looked
for a signal and did not find it. `not_applicable` means the category was checked
but the available artifact made the category irrelevant for that instance.

The existing `evidence_sufficiency_score` is unchanged. Provenance is an audit
layer, not a replacement score.

## CLI

```bash
python -m mergedossier_bench.cli audit-provenance \
  --dossiers data/seed_corpus/dossiers \
  --out outputs/provenance_audit
```

Required outputs:

- `provenance_summary.json`
- `provenance_summary.md`
- `uncited_evidence.jsonl`
- `missing_provenance.jsonl`

The audit should be used to find uncited evidence claims, missing provenance
categories, provenance source distributions, and evidence categories that are
often inferred rather than observed.

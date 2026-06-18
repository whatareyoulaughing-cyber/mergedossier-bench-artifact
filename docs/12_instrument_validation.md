# Instrument Validation

MVP-4 adds a small deterministic perturbation suite for the reconstruction and
provenance instrument. The goal is to check whether controlled evidence signals
move the expected category and provenance status. It is not a claim that the
instrument captures all evidence in real public PRs.

## Perturbation Checks

The suite covers:

- explicit risk versus removed risk
- changed test file only versus `Tests: pytest`
- passing CI as inferred regression evidence
- rollout, monitoring, and owner as ownership evidence
- command logs and agent trace language
- dependency manifest changes
- explicit rationale
- vague body only

Run:

```bash
python -m mergedossier_bench.cli run-perturbation-suite \
  --out outputs/perturbation_suite
```

Outputs:

- `perturbation_results.json`
- `perturbation_results.md`
- `paper_table_perturbation_checks.csv`

Each row reports the fixture, the expected category, the expected provenance
status, the observed status, and pass/fail. The suite asserts provenance status
as well as category detection.

## Boundary

Passing perturbation checks means deterministic extraction rules behave as
specified on synthetic oracle fixtures. It does not prove patch correctness,
mergeability, authorship-group effects, reviewer utility, or population-level
evidence rates.


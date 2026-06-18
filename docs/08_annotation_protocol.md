# Annotation Protocol

## Goal

MergeDossier-Bench audits review-evidence availability in AI-authored pull requests.
Operators code whether the dossier makes evidence visible, category-specific,
and provenance-backed. The audit task does not ask whether the patch is correct,
whether an agent is good at code review, or whether a PR should be merged.

Slogan: **A diff is not a dossier.**

## Evidence Categories

- `intent_evidence`: the dossier explains what the PR is trying to do.
- `requirement_evidence`: the dossier maps the change to issue text, acceptance criteria, or user-visible behavior.
- `test_evidence`: the dossier explains what tests were added, run, or intentionally omitted.
- `risk_analysis`: the dossier identifies possible failure modes or risky touched areas.
- `scope_evidence`: the dossier explains why the change is appropriately scoped.
- `trace_evidence`: the dossier exposes useful agent process evidence, such as files read or commands run.
- `dependency_evidence`: the dossier discusses dependency, API, version, migration, or compatibility evidence when relevant.
- `regression_evidence`: the dossier gives evidence that existing behavior is protected.
- `rationale_evidence`: the dossier explains why the chosen approach supports responsible review.
- `ownership_handoff`: the dossier states follow-up work, rollback, monitoring, or responsibility transferred to humans.

## Label Meanings

- `present`: specific, grounded evidence is available and useful for review.
- `partially_present`: some evidence is available, but it is thin, generic, incomplete, or weakly grounded.
- `missing`: the category is relevant but the dossier does not provide useful evidence.
- `not_applicable`: the category does not apply to this PR after considering the task context.

## Examples

### Present

A test section names the behavior under test, the exact command run, and the gap
between targeted tests and full regression tests. This supports a human check
without asking the reviewer to reconstruct the evidence from scratch.

### Partially Present

The dossier says "tests pass" but does not name the tests, map them to the
changed behavior, or state what remains untested.

### Missing

The PR changes authentication or data migration code, but the dossier has no
risk analysis, rollback note, or ownership handoff.

### Not Applicable

A documentation-only PR may not need dependency evidence if it does not touch
runtime dependencies, public APIs, or deployment behavior.

## Handling Uncertainty

Use `partially_present` when evidence exists but its availability is thin or incomplete.
Use the comment field to note what made the decision uncertain. Do not infer
evidence from unstated intentions. If a reviewer would need to inspect the diff,
issue, or CI logs to reconstruct the claim, the dossier evidence is partial or
missing.

## Avoid Judging Code Quality Directly

Annotators should not label whether the patch is correct, elegant, performant,
or mergeable. A bad patch can still provide clear evidence, and a good patch can
arrive with weak evidence. The annotation target is the evidence interface
between coding agents and maintainers.

## Focus On Review-Evidence Availability

Ask:

- Does the dossier state what evidence exists?
- Is that evidence specific to this PR?
- Is it grounded in visible artifacts such as issue text, tests, CI, changed files, or agent trace?
- Does it help a human reviewer know what to verify?
- Does it state uncertainty, limits, and ownership clearly?

Avoid:

- rewarding boilerplate,
- treating merge outcome as ground truth,
- treating passing tests as complete evidence,
- penalizing a dossier for not solving the underlying coding task.

## Single-Operator Audit Process

When only one operator is available, use a delayed self-consistency audit.
Export the annotation tasks, then create a reliability sample that appends a
random subset of repeated tasks. Annotate the repeats later, without looking at
the original audit codes. The repeated tasks share a `reliability_group_id`, so
`annotation-stats` can report percent agreement as self-consistency.

This is a reliability check, not a substitute for inter-rater agreement. In the
paper, describe it as delayed repeat self-consistency. Do not call it Cohen's
kappa, inter-rater reliability, or ground-truth agreement unless a second
operator independently codes the same tasks.

Recommended settings:

- repeat at least 20% of tasks,
- repeat at least 5 tasks for small pilots,
- wait at least 48 hours before labeling repeats when possible,
- adjudicate all present-vs-missing self-disagreements,
- keep original and repeat audit codes as raw evidence,
- keep adjudicated audit codes in a separate file or column,
- report the number of repeated tasks and the random seed used to create them.

This design does not replace inter-rater reliability. It is an instrument-audit
guard against drift and inconsistent audit-code use by the same operator.

## Adjudication Process

1. Label all primary tasks.
2. Code delayed repeat tasks without consulting original audit codes.
3. Compute per-category self-consistency and disagreement severity.
4. Prioritize adjudication for present-vs-missing disagreements and recurring category disagreements.
5. Re-open only the dossier evidence visible during annotation; do not inspect new PR evidence during adjudication.
6. Record an adjudication note that explains whether the final label follows the original, the repeat, or a clarified codebook rule.
7. Discuss only the evidence visible to operators if a second reviewer becomes available later.
8. Preserve raw audit codes, comments, repeat audit codes, and adjudicated audit codes as separate artifacts.

## Minimal Release Artifacts For A One-Annotator Pilot

Before using the audit codes in a paper table, release or archive:

- the imported Label Studio task JSON, including repeated tasks,
- the Label Studio export JSON or completed CSV annotation sheet,
- `agreement_summary.json` and `agreement_summary.md`,
- `annotation_records.jsonl`,
- `disagreement_cases.jsonl`,
- adjudication notes for severe self-disagreements,
- the frozen version of this protocol used during labeling.

## Spreadsheet Annotation Option

For small pilots, the tasks can be labeled in a spreadsheet instead of Label
Studio:

```bash
python -m mergedossier_bench.cli export-annotation-csv \
  --tasks outputs/real_pilot_mixed_source_annotation_tasks_with_repeats_20260613.json \
  --out outputs/real_pilot_mixed_source_annotation_sheet_20260613.csv \
  --annotator-id solo
```

For Excel, use the workbook with dropdowns:

```bash
python scripts/export_annotation_workbook.py \
  --csv outputs/real_pilot_mixed_source_annotation_sheet_20260613.csv \
  --out outputs/real_pilot_mixed_source_annotation_workbook_20260613.xlsx
```

Fill each `*_label` cell with exactly one of:

- `present`
- `partially_present`
- `missing`
- `not_applicable`

After labeling, export the `Annotation` sheet as
`outputs/real_pilot_mixed_source_annotation_sheet_completed_20260613.csv`:

```bash
python scripts/export_annotation_csv_from_workbook.py \
  --workbook outputs/real_pilot_mixed_source_annotation_workbook_20260613.xlsx \
  --out outputs/real_pilot_mixed_source_annotation_sheet_completed_20260613.csv
```

Validate the completed CSV before using it in paper tables:

```bash
python -m mergedossier_bench.cli validate-annotation-csv \
  --annotations outputs/real_pilot_mixed_source_annotation_sheet_completed_20260613.csv
```

For an unfinished template, add `--allow-incomplete` to check columns and label
vocabulary without requiring every label cell. Then compute statistics directly
from the completed CSV:

```bash
python -m mergedossier_bench.cli annotation-stats \
  --annotations outputs/real_pilot_mixed_source_annotation_sheet_completed_20260613.csv \
  --out outputs/real_pilot_mixed_source_annotation_stats_20260613
```

Generate paper-ready result snippets:

```bash
python scripts/build_paper_results_from_annotations.py \
  --annotations outputs/real_pilot_mixed_source_annotation_sheet_completed_20260613.csv \
  --out outputs/real_pilot_mixed_source_annotation_paper_results_20260613
```

This command also writes `adjudication_sheet.csv` and `adjudication_sheet.md`
for self-disagreements that need a final note.

For the real pilot workbook, the same export, validation, statistics, result
snippet, and adjudication steps can be run with one command:

```bash
python scripts/run_completed_annotation_pipeline.py
```

The same delayed-repeat rule applies: complete the primary rows first, wait if
possible, then complete rows where `is_reliability_repeat` is true without
looking back at the original audit codes.

## Recommended Training Procedure

1. Read `docs/02_dossier_schema.md` and this protocol.
2. Jointly annotate 5 practice dossiers.
3. Compare audit codes category by category and revise ambiguous examples.
4. Independently annotate a 20-task pilot batch with at least 5 delayed repeats.
5. Review self-consistency statistics and update the codebook before the full study.
6. Freeze the protocol before annotating the release corpus.

## Current Limitations

The MVP statistics include percent agreement for repeated tasks and pairwise
Cohen's kappa when exactly two operators are available. For a one-operator audit,
report self-consistency rather than inter-rater reliability. Krippendorff's
alpha is left as a future extension for larger multi-operator designs without
adding heavy dependencies to the starter kit.

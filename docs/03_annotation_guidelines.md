# Annotation Guidelines

## Goal

Operators audit whether an AI-authored PR makes review-relevant evidence visible, category-coded, and provenance-backed.

Operators are **not** asked to determine whether the patch is correct, mergeable, or useful to reviewers. They assign evidence-availability audit codes.

## Unit of annotation

One item = one PR + one MergeDossier.

Annotators may see:

- PR title and body,
- linked issue summary,
- diff summary,
- changed file list,
- CI/test summary,
- review comments,
- dossier evidence fields,
- optional agent trace snippets.

## Main audit codes

### Evidence availability by category

For each evidence type, assign 0, 1, or 2:

- **0 Missing:** not provided, irrelevant, contradicted by available facts, or pure boilerplate.
- **1 Partial:** visible but incomplete, generic, weakly grounded, or missing important context.
- **2 Present:** specific, grounded, and review-relevant.

### Legacy artifact triage

- **0 Insufficient:** A reviewer would need to reconstruct most evidence manually.
- **1 Thin:** Some useful evidence, but important gaps remain.
- **2 Adequate:** Enough evidence for a normal review, with manageable gaps.
- **3 Strong:** The dossier substantially improves review efficiency and accountability.

This triage value is retained for artifact browsing only; it is not the main empirical construct.

### Blocking concern tags

Annotators may select any:

- missing intent,
- missing requirement traceability,
- weak tests,
- no regression evidence,
- scope too broad,
- no risk analysis,
- no agent trace,
- generic boilerplate,
- misleading evidence,
- suspicious generated tests,
- unexplained architectural change,
- security-sensitive change,
- performance-sensitive change,
- human ownership unclear.

## Annotation examples

### Example: test rationale

PR says:

> Added tests and all tests pass.

Rating: **1**. It provides some test evidence but no rationale.

PR says:

> Added `test_empty_cache_returns_404` to cover the linked issue where empty cache entries previously returned 500. Existing integration tests cover non-empty cache entries. Ran `pytest tests/cache/test_lookup.py` and full CI passed.

Rating: **2**. Specific, grounded, and useful.

### Example: scope justification

PR touches 18 files but does not explain why.

Rating: **0** or **1** depending on whether the changed-file list makes the scope obvious.

PR says:

> The fix is limited to the parser and the two API adapters. I did not change the serializer because the linked issue concerns input normalization only.

Rating: **2**.

## Disagreement resolution

1. In the current audit, one operator codes each dossier.
2. A delayed repeat subset is labeled later to measure self-consistency.
3. Resolve present-vs-missing self-disagreements by re-reading only visible evidence.
4. If a second operator becomes available, compute inter-rater agreement by category.
5. Keep raw audit codes, repeat audit codes, and adjudicated audit codes.

## Redaction policy

Before annotation release:

- remove secrets and tokens,
- remove private emails,
- remove security exploit payloads if they could cause harm,
- preserve public GitHub URLs when allowed,
- preserve enough metadata for reproducibility.

# MergeDossier Schema

A **MergeDossier** is a structured evidence packet attached to an AI-authored pull request.

It is not a replacement for review. It is the reviewer's map, lantern, and tripwire kit.

## Top-level entities

### PR instance

The raw normalized pull request:

- repository,
- PR number and URL,
- author and source agent,
- base/head commits,
- linked issue,
- changed files,
- commits,
- tests and CI,
- reviews and comments,
- merge/reject outcome,
- optional agent trace.

### MergeDossier

The evidence packet:

- dossier metadata,
- PR metadata,
- evidence categories,
- optional extracted snippets,
- limitations,
- scoring metadata.

### Annotation

Human labels:

- evidence sufficiency ratings,
- missing evidence types,
- blocking concerns,
- perceived merge acceptability,
- reviewer confidence,
- notes.

## Evidence categories

### 1. Intent evidence

Does the PR explain what it is trying to accomplish?

Examples:

- clear problem statement,
- linked issue summary,
- change goal,
- non-goals.

### 2. Requirement traceability

Does the PR map changes back to requirements, issue text, acceptance criteria, or user-visible behavior?

Examples:

- checklist mapping requirements to changed files,
- issue-to-test links,
- explicit acceptance criteria.

### 3. Test rationale

Does the PR explain why the added or modified tests are sufficient?

Examples:

- what behavior each test covers,
- why existing tests are enough,
- known gaps.

### 4. Regression safety

Does the PR provide evidence that it avoids breaking existing behavior?

Examples:

- CI results,
- targeted regression tests,
- backward-compatibility reasoning,
- dependency/API compatibility notes.

### 5. Risk analysis

Does the PR identify potential failure modes or risky touched areas?

Examples:

- concurrency risks,
- security-sensitive paths,
- data migration hazards,
- performance risks.

### 6. Scope justification

Does the PR explain why the changed files and lines are appropriately scoped?

Examples:

- why only these files changed,
- why broad refactoring is avoided,
- alternative paths not taken.

### 7. Change summary

Does the PR provide a reviewer-friendly summary of the changes?

Examples:

- bullet summary,
- affected components,
- before/after behavior.

### 8. Agent trace

Does the PR expose useful agent process evidence?

Examples:

- files read,
- commands run,
- tests attempted,
- failed approaches,
- final verification steps.

### 9. Limitations and uncertainty

Does the PR state what is not verified or where the agent is uncertain?

Examples:

- untested environments,
- assumptions,
- caveats,
- manual review focus areas.

### 10. Reviewer actionability

Does the dossier help reviewers focus their attention?

Examples:

- suggested review checklist,
- high-risk files,
- "please verify X" notes,
- explanation of changed APIs.

### 11. Ownership handoff

Does the PR make clear what responsibility humans inherit after merging?

Examples:

- follow-up tasks,
- monitoring needs,
- migration notes,
- rollback plan.

## Scoring scale for each category

Use a 0 to 2 quality scale:

- **0 = absent or misleading**
- **1 = present but thin, generic, or incomplete**
- **2 = specific, useful, and grounded in the PR**

Presence alone is not enough. Generic statements like "all tests pass" usually deserve 1, not 2, unless linked to relevant commands and test purpose.

## Files

Machine-readable schemas live in `schemas/`:

- `merge_dossier.schema.json`
- `pr_instance.schema.json`
- `annotation.schema.json`
- `score_report.schema.json`

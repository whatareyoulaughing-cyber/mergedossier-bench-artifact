# Experimental Design

> **Superseded current-paper notice (2026-06-17):** This file records early
> expansion ideas. The current ICSE draft does not claim reviewer utility,
> human acceptability modeling, AI-vs-human causal effects, mergeability, or
> all-GitHub rates. The active empirical claim is the handoff-evidence gap in
> the 500-PR AIDev-pop frame, computed from single-operator audit codes with
> delayed-repeat self-consistency and provenance-backed outputs.

## Phase A: Mining and sampling

### Data sources

Potential sources:

- AIDev-style normalized CSVs,
- GitHub REST/GraphQL API,
- public PR pages,
- CI logs where public,
- agent traces where voluntarily released.

### Sampling strategy

Stratify by:

- source agent,
- language,
- repository size/stars,
- PR size,
- task type,
- merge outcome,
- CI status,
- review activity.

Avoid only sampling successful PRs. Evidence sufficiency matters for rejected and abandoned PRs too.

### Task type buckets

- bug fix,
- feature,
- documentation,
- refactoring,
- test-only,
- dependency/update,
- formatting/mechanical,
- security-related,
- performance-related,
- unknown.

## Phase B: Dossier construction

For each PR, construct a dossier from available artifacts:

- PR body,
- linked issues,
- commits,
- changed file summaries,
- tests,
- CI logs,
- review comments,
- agent trace if available.

Two versions are useful:

1. **Observed dossier:** evidence actually provided by the PR.
2. **Generated dossier:** evidence a tool reconstructs from available artifacts.

This lets the paper separate two questions:

- What evidence do current agents provide by default?
- Can we generate better dossiers to support review?

## Phase C: Annotation

Annotate evidence categories and overall sufficiency.

Recommended MVP:

- 300 to 500 PRs,
- one annotator per PR in the pilot, with delayed repeat tasks for self-consistency,
- adjudication for a 20% subset or high-disagreement cases.

Recommended ambitious version:

- 1,000+ PRs,
- at least three source agents,
- at least three languages,
- post-merge maintenance signals.

## Phase D: Future-only modeling

### Outcome variables

- evidence sufficiency score,
- human acceptability label,
- review confidence,
- merge/reject outcome,
- review rounds,
- time-to-decision,
- post-merge churn.

### Baseline features

- patch size,
- changed files,
- CI status,
- tests added,
- PR body length,
- source agent,
- repository size,
- author history,
- task type.

### Dossier features

- evidence category scores,
- missing evidence count,
- risk evidence present,
- test rationale quality,
- scope justification quality,
- agent trace present,
- limitations present.

### Analysis

- descriptive distributions,
- regression models,
- ablation by evidence category,
- mixed-effects models by repository if sample size supports it,
- optional calibration analysis for the legacy triage score, if a later study
  collects the independent outcome data needed for that question.

## Phase E: Controlled human study

### Conditions

- **Diff-only:** reviewer sees only normal PR artifacts.
- **Diff + CI/tests:** reviewer sees test/CI summary.
- **Diff + generated dossier:** reviewer sees automatically generated dossier.
- **Diff + curated dossier:** reviewer sees human-curated dossier.

### Measures

- time-to-decision,
- confidence,
- risk detection,
- incorrect acceptance,
- false rejection,
- perceived review burden,
- perceived accountability.

### Hypotheses

- H1: Dossiers increase reviewer confidence without increasing incorrect acceptance.
- H2: Dossiers improve detection of scope/risk/test gaps.
- H3: Some evidence types are more valuable than others, especially test rationale, risk analysis, and scope justification.

## Phase F: Leaderboard

Leaderboard should not rank agents by patch correctness alone.

Rank by:

- Evidence Sufficiency Score,
- evidence completeness,
- human usefulness,
- calibration between claimed evidence and actual PR artifacts,
- optional mergeability/correctness if available.

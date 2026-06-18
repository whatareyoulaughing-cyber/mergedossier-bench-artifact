# Leaderboard Design

## Principle

MergeDossier-Bench should not reward verbose hallucinated explanations. It should reward grounded, useful, reviewer-relevant evidence.

## Required report fields

Each submission should report:

- agent name and version,
- model name and version,
- harness/scaffold,
- tool access,
- repository context allowed,
- whether agent trace is available,
- whether test execution was allowed,
- number of attempts/retries,
- evidence generation method,
- human post-processing allowed or not.

## Scores

### Evidence Sufficiency Score

Weighted 0 to 100 score from evidence categories.

### Groundedness flag

Evidence is grounded if it cites or points to a PR artifact:

- file path,
- line range,
- test command,
- CI run,
- issue reference,
- commit hash,
- review comment,
- trace step.

Ungrounded claims should be penalized.

### Reviewer usefulness

Optional human study rating.

### Calibration

Compare agent claims against available artifacts. For example, if the dossier claims "full test suite passed" but no such CI run exists, penalize.

## Suggested table

| Agent | Harness | ESS | Intent | Tests | Risk | Scope | Trace | Groundedness | Reviewer usefulness |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|

## Anti-gaming rules

- Penalize boilerplate.
- Penalize long dossiers with no grounding.
- Penalize false claims more than missing claims.
- Report token budget and attempts.
- Report whether the agent had access to hidden tests or reviewer comments.
- Freeze benchmark instances for leaderboard submissions.

## Public website slogan

> **Can your coding agent bring evidence, not just a diff?**

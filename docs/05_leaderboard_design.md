# Leaderboard Design

> **Superseded current-paper notice (2026-06-18):** This file is an early
> leaderboard design sketch. The current ICSE manuscript does **not** evaluate
> agents on reviewer usefulness, patch correctness, mergeability, or
> AI-vs-human effects. The active paper claim is the handoff-evidence gap in a
> deterministic 500-PR AIDev-pop sample, using review-evidence availability,
> provenance-backed outputs, sensitivity analysis, and a single-operator audit
> with delayed repeats. Treat the leaderboard ideas below as future design
> notes, not as submitted empirical claims.

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

### Future reviewer-usefulness study

Optional future human-study rating. This is outside the current ICSE
submission and must not be described as a completed result.

### Calibration

Compare agent claims against available artifacts. For example, if the dossier claims "full test suite passed" but no such CI run exists, penalize.

## Suggested table

| Agent | Harness | ESS | Intent | Tests | Risk | Scope | Trace | Groundedness | Future usefulness study |
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

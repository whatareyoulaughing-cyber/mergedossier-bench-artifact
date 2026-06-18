# Final Portal Fields After Anonymous Artifact Upload

Generated: 2026-06-18

## Title

MergeDossier-Bench: Measuring the Handoff-Evidence Gap in AI-Authored Pull Requests

## Abstract

Coding agents increasingly submit pull requests, but maintainers need more than a patch before they can take responsibility for a change. MergeDossier-Bench is a provenance-aware benchmark and measurement framework for auditing review-evidence availability in AI-authored pull requests. It measures whether public PR artifacts expose intent, requirements, tests, regression behavior, risk, scope, traceability, rationale, and ownership evidence. The contribution is a bounded measurement framework and population-frame evidence study, not a correctness or mergeability benchmark. The artifact provides a MergeDossier schema, provenance-aware commands, corpus summaries, audit-code exports, perturbation checks, and paper-facing tables. Using the AIDev-pop curated public agentic-PR frame, we normalize 33,596 eligible pull requests, draw a deterministic stratified sample of 500 PRs, and collect 50 delayed-repeat records from one operator. Within this declared frame, audit codes reveal a handoff-evidence gap: surface evidence such as intent, scope, and tests is commonly visible, but handoff-critical evidence is largely absent. Treating partial evidence as threshold uncertainty yields handoff evidence availability in [0.0%, 10.16%] and a handoff-evidence gap in [89.84%, 100.0%]. Even under strict coding for surface evidence and lenient coding for handoff evidence, the minimum separation is 36.77 percentage points. The delayed repeats produced no category-level disagreements; we report this only as single-operator self-consistency. The results estimate evidence availability within AIDev-pop; they do not claim AI-vs-human effects, reviewer utility, or all-GitHub population rates.

Abstract word count: 219

## Keywords

AI-assisted software engineering; pull requests; empirical software engineering; benchmark design; review-evidence availability

## Artifact URL

https://github.com/whatareyoulaughing-cyber/mergedossier-bench-artifact/releases/tag/v0.1-anonymous

## Artifact Note

The anonymous artifact package is available for review at https://github.com/whatareyoulaughing-cyber/mergedossier-bench-artifact/releases/tag/v0.1-anonymous. It includes source, safe examples, derived tables, smoke-test instructions, an anonymization scan report, a `.sha256` checksum asset, and single-operator submission-boundary notes for the no-second-operator case. DOI archival is planned after double-anonymous constraints are lifted.

## Boundary Note

This submission reports a single-operator AIDev-pop audit with 50 delayed repeats, provenance-backed inspectability, perturbation checks, and sensitivity analyses. It does not claim patch correctness, mergeability, reviewer utility, AI-vs-human causal effects, all-GitHub rates, completed external agreement, inter-rater reliability, or DOI archival during double-anonymous review.

## Verification Snapshot

- `pytest -q`: 151 passed
- ICSE format: pass, 0 fail, 0 warn
- Paper readiness: pass
- Double-anonymous check: pass
- Anonymous release zip scan: pass, 0 findings
- Downloaded release zip scan: pass, 0 findings
- Anonymous repo main commit: 97e8a9d

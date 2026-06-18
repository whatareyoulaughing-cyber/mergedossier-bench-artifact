# Final Portal Fields After Anonymous Artifact Upload

Generated: 2026-06-18

## Title

MergeDossier-Bench: Measuring the Handoff-Evidence Gap in AI-Authored Pull Requests

## Abstract

Coding agents increasingly submit pull requests, but maintainers need more than a patch before they can take responsibility for a change. They need evidence about intent, requirements, tests, regression behavior, risk, scope, traceability, rationale, and ownership. MergeDossier-Bench is a provenance-aware benchmark and measurement framework for auditing review-evidence availability in AI-authored pull requests. The contribution is a measurement framework and a bounded population-frame evidence study, not a correctness or mergeability benchmark. The artifact defines a MergeDossier schema, category-level availability tables, a legacy triage score, corpus-level summaries, a Label Studio audit workflow, an offline seed-corpus builder, an optional live GitHub fetcher, and provenance-aware audit commands. Using the AIDev-pop curated public agentic-PR frame, we normalize 33,596 eligible pull requests, draw a deterministic stratified sample of 500 PRs, and collect 50 delayed-repeat records from one operator. Within this declared frame, audit codes reveal a handoff-evidence gap: surface evidence such as intent, scope, and tests is commonly visible, but handoff-critical evidence is largely absent. Treating partial evidence as threshold uncertainty yields handoff evidence availability in [0.0%, 10.16%] and a handoff-evidence gap in [89.84%, 100.0%]. Even under strict coding for surface evidence and lenient coding for handoff evidence, the minimum separation is 36.77 percentage points. The delayed repeats produced no category-level disagreements, which we report only as single-operator self-consistency. The results estimate evidence availability within AIDev-pop; they do not claim AI-vs-human effects, reviewer utility, or all-GitHub population rates.

Abstract word count: 260

## Keywords

AI-assisted software engineering; pull requests; empirical software engineering; benchmark design; review-evidence availability

## Artifact URL

https://github.com/whatareyoulaughing-cyber/mergedossier-bench-artifact/releases/tag/v0.1-anonymous

## Artifact Note

The anonymous artifact package is available for review at https://github.com/whatareyoulaughing-cyber/mergedossier-bench-artifact/releases/tag/v0.1-anonymous. It includes source, safe examples, derived tables, smoke-test instructions, and an anonymization scan report. DOI archival is planned after double-anonymous constraints are lifted.

## Boundary Note

This submission does not claim patch correctness, mergeability, reviewer utility, AI-vs-human causal effects, all-GitHub rates, inter-rater reliability, or DOI archival during double-anonymous review.


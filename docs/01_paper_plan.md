# Paper Plan

> **Superseded current-paper notice (2026-06-17):** This file is an early
> planning artifact. The current manuscript is framed as
> **MergeDossier-Bench: Measuring the Handoff-Evidence Gap in AI-Authored Pull
> Requests**. Current empirical claims are limited to provenance-certified
> review-evidence availability intervals and the handoff-evidence gap in the
> 500-PR AIDev-pop frame. Do not use the older RQs below to claim reviewer
> utility, human acceptability modeling, AI-vs-human effects, mergeability, or
> all-GitHub rates. The current claim boundary is in
> `paper/main.tex`, `docs/14_reframing_to_evidence_availability.md`, and
> `docs/15_claims_and_nonclaims.md`.

## Current working title

**MergeDossier-Bench: Measuring the Handoff-Evidence Gap in AI-Authored Pull Requests**

Backup title:

**A Diff Is Not a Dossier: Evidence-Centered Evaluation of AI-Authored Pull Requests**

## Current thesis

Coding agents are increasingly able to open pull requests, but a pull request is
not merely a diff. Before humans can take responsibility for a change, they
need visible evidence about intent, requirements, tests, risks, scope, trace,
rationale, and downstream ownership. MergeDossier-Bench provides a
provenance-aware measurement framework for review-evidence availability and
measures the handoff-evidence gap in a deterministic 500-PR AIDev-pop sample.

## Current abstract skeleton

MergeDossier-Bench is a provenance-aware benchmark and measurement framework
for review-evidence availability in AI-authored pull requests. The current
paper uses the AIDev-pop curated public agentic-PR frame, normalizes 33,596
eligible PRs, draws a deterministic stratified sample of 500 PRs, and audits
50 delayed repeats with one operator. The paper reports category-level
availability intervals, provenance-backed inspectability, sensitivity analyses,
and a quantified handoff-evidence gap. It does not claim patch correctness,
mergeability, reviewer utility, AI-vs-human causal effects, all-GitHub rates,
or inter-rater reliability.

## Current research questions

### RQ1: How can review evidence be represented as provenance-certified availability intervals?

Output: a MergeDossier representation, evidence-family crosswalk, provenance
statuses, availability intervals, and handoff-gap quantities.

### RQ2: What handoff-evidence gap appears in AIDev-pop?

Output: category-level evidence availability and handoff-evidence-gap estimates
for the deterministic 500-PR AIDev-pop sample, bounded to that declared frame.

### Future-only extension: Do richer MergeDossiers improve reviewer decisions?

Controlled study:

- Condition A: diff only.
- Condition B: diff + tests/CI.
- Condition C: diff + generated MergeDossier.
- Condition D: diff + full curated MergeDossier.

This reviewer-utility study is not part of the current submission.

Measure:

- reviewer confidence,
- time-to-decision,
- risk detection,
- incorrect acceptance rate,
- false rejection rate,
- perceived accountability.

## Contributions

1. **Concept:** Define MergeDossier as an evidence packet for AI-authored pull requests.
2. **Schema:** Formalize evidence categories and metadata for reproducible evaluation.
3. **Benchmark:** Release MergeDossier-Bench, a set of AI-authored PR instances with evidence packets and human evidence-sufficiency annotations.
4. **Metric:** Propose Evidence Sufficiency Score and evidence-type ablations.
5. **Empirical findings:** Characterize evidence gaps in current AI-authored PRs.
6. **Human study:** Test whether dossiers improve reviewer decision quality.
7. **Tooling:** Release validation, scoring, and leaderboard scripts.

## Paper narrative

1. Coding agents are moving from code suggestions to PR authorship.
2. A PR is a socio-technical decision artifact, not just a patch.
3. Existing evaluation stops too early or asks a different question.
4. Humans need evidence before accepting responsibility for merge.
5. We define a dossier schema and benchmark.
6. We show current AI-authored PRs often lack specific evidence types.
7. We show evidence sufficiency adds signal beyond pass/fail tests.
8. We show richer dossiers help humans make better decisions.
9. We argue future coding agents should submit evidence packets by default.

## Expected figures

1. **Figure 1:** Patch-only workflow vs dossier-supported workflow.
2. **Figure 2:** MergeDossier schema overview.
3. **Figure 3:** Evidence sufficiency heatmap by evidence type and agent.
4. **Figure 4:** Predictive value of dossier evidence beyond traditional PR signals.
5. **Figure 5:** Human study results: diff-only vs diff+tests vs diff+dossier.

## Killer sentences

- **A diff is not a dossier.**
- **Passing tests may show that a patch works; a dossier shows why humans should trust it.**
- **MergeDossier-Bench evaluates the evidence interface between coding agents and maintainers.**
- **The next unit of evaluation for coding agents is not only the patch, but the evidence that travels with it.**

## Minimal viable submission

- 300 to 500 AI-authored PRs.
- Single-annotator pilot labels with delayed repeat tasks for self-consistency; add a second annotator if resources become available.
- Evidence taxonomy with agreement statistics.
- Evidence Sufficiency Score.
- Baselines using PR metadata and CI/test signals.
- One controlled study with 24 to 40 experienced developers.

## Ambitious version

- 1,000+ PRs.
- Multiple coding agents.
- Multiple languages.
- Longitudinal post-merge maintenance signals.
- Public leaderboard.
- Dossier generator evaluated across Codex, Claude Code, Devin, Copilot, Cursor, Aider.

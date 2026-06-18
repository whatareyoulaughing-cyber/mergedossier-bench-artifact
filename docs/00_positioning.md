# Positioning: Why MergeDossier-Bench Exists

## One-line positioning

**MergeDossier-Bench evaluates whether AI-authored pull requests bring enough evidence for humans to responsibly review, question, trust, and merge them.**

## What we are not

MergeDossier-Bench is not:

- another SWE-bench-style patch correctness benchmark,
- another code-review-agent benchmark,
- another review-effort prediction paper,
- another mergeability benchmark,
- another generic AI-code quality study.

## What we are

We study the **evidence interface** between a coding agent and a human maintainer.

When an agent opens a PR, the human maintainer does not only need a diff. They need to know:

- What problem was the agent trying to solve?
- Which requirements does the patch satisfy?
- Why are the tests sufficient?
- What risks did the agent consider?
- Why is the patch scope appropriate?
- What uncertainty remains?
- What should the reviewer focus on?

This evidence is the **MergeDossier**.

## Nearby work and our wedge

### SWE-bench / SWE-bench Verified

SWE-bench standardizes repository-level issue-fixing evaluation. SWE-bench Verified is a human-filtered subset of 500 instances. These benchmarks ask whether agents can produce patches that solve tasks under an evaluation harness.

Our wedge: **patch correctness is necessary but not sufficient for human oversight.**

### FrontierCode

FrontierCode explicitly pushes beyond unit tests and evaluates mergeability across dimensions such as behavioral correctness, regression safety, mechanical cleanliness, test correctness, scope, and code quality.

Our wedge: **FrontierCode asks whether code is mergeable; MergeDossier-Bench asks whether the PR provides the evidence a human needs to decide.**

### AIDev

AIDev provides a large-scale dataset of agent-authored pull requests from real GitHub repositories.

Our wedge: **AIDev is a map of the terrain; MergeDossier-Bench defines an evidence standard and benchmark on top of real PR workflows.**

### Code-review-agent benchmarks

CR-Bench, c-CRAB, SWE-PRBench, CodeFuse-CR-Bench and similar work evaluate whether AI review agents find PR issues or resolve review tasks.

Our wedge: **we evaluate PR evidence quality, not AI reviewer skill.**

### Review-effort / attention-tax work

Recent work predicts review effort or studies review dynamics for AI-generated PRs.

Our wedge: **we ask what evidence could reduce ambiguity and support human accountability, not merely how many comments or minutes a PR consumes.**

## Brand rule

Use the project name as one token:

> MergeDossier-Bench

Avoid spelling it as "Merge Dossier Bench" in headings, filenames, paper title, or repository names. The fused form is more searchable and avoids unrelated "merge dossier" document-management noise.

## Citation slots we want to own

Future papers should cite us when they write sentences like:

- "AI-authored PRs need evidence beyond a diff and passing tests."
- "Human-centered evaluation of coding agents should include evidence sufficiency."
- "Coding agents should expose intent, requirements, tests, risks, scope, and uncertainty to reviewers."
- "A PR may be mergeable in principle but still poorly supported as a human decision artifact."

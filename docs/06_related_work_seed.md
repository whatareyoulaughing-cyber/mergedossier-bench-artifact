# Related Work Seed

This file is a seed map, not a finished related-work section. Re-check all papers before submission.

## Pull-request review and maintainer understanding

### Expectations, Outcomes, and Challenges of Modern Code Review

Bacchelli and Bird study tool-based code review at Microsoft and report that
modern review supports more than defect detection, including knowledge transfer,
team awareness, alternative solutions, and change understanding.

- ICSE 2013 page: https://2013.icse-conferences.org/content/expectations-outcomes-and-challenges-modern-code-review.html

Positioning: supports the claim that reviewers need understanding and context,
not only defect signals.

### An Exploratory Study of the Pull-Based Software Development Model

Gousios, Pinzger, and van Deursen study pull-based development and factors
affecting merge decisions and processing time.

- ACM DOI: https://doi.org/10.1145/2568225.2568260
- DBLP: https://dblp.org/rec/conf/icse/GousiosPD14

Positioning: connects MergeDossier-Bench to pull-request research rather than
only AI-agent benchmarks.

### Work Practices and Challenges in Pull-Based Development

Gousios, Zaidman, Storey, and van Deursen study the integrator perspective,
including the work of managing and accepting contributions.

- DOI: https://doi.org/10.1109/ICSE.2015.55
- TU Delft record: https://research.tudelft.nl/en/publications/work-practices-and-challenges-in-pull-based-development-the-integ/

Positioning: motivates the maintainer/integrator responsibility side of the
MergeDossier construct.

### Modern Code Review: A Case Study at Google

Sadowski, Söderberg, Church, Sipko, and Bacchelli study code review practices at
Google using interviews, survey responses, and review logs.

- Google Research page: https://research.google/pubs/modern-code-review-a-case-study-at-google/
- ACM DOI: https://doi.org/10.1145/3183519.3183525

Positioning: supports the idea that modern review is tool-mediated,
lightweight, frequent, and tied to shared understanding and codebase norms.

## Patch correctness benchmarks

### SWE-bench / SWE-bench Verified

SWE-bench evaluates language models and agents on real GitHub issue-resolution tasks. SWE-bench Verified is a human-filtered subset of 500 instances.

- Website: https://www.swebench.com/

Positioning: essential baseline, but patch correctness/test passing does not cover evidence sufficiency.

## Mergeability / production-readiness benchmarks

### FrontierCode

FrontierCode evaluates whether coding-agent outputs are mergeable, using dimensions such as behavioral correctness, regression safety, mechanical cleanliness, test correctness, scope, and code quality.

- Official blog: https://cognition.ai/blog/frontier-code

Positioning: FrontierCode asks whether the code should be merged. MergeDossier-Bench asks whether the PR provides enough evidence for humans to make that judgment.

## Real-world AI-authored PR datasets

### AIDev

AIDev aggregates large-scale agent-authored PRs from OpenAI Codex, Devin, GitHub Copilot, Cursor, and Claude Code.

- arXiv: https://arxiv.org/abs/2602.09185
- Hugging Face: https://huggingface.co/datasets/hao-li/AIDev

Positioning: likely data source. MergeDossier-Bench adds evidence schema, labels, and evaluation protocol.

## AI code-review-agent benchmarks

### c-CRAB / Code Review Agent Benchmark

Evaluates automated code review agents on real-world pull requests.

- arXiv: https://arxiv.org/abs/2603.23448

### CR-Bench

Evaluates AI code review agents with a focus on real-world utility.

- arXiv: https://arxiv.org/abs/2603.11078

Positioning: these evaluate reviewers, not the evidence contained in AI-authored PRs.

## Review effort / attention tax

### Early-stage prediction of review effort in AI-generated PRs

Studies AI-generated PR review effort and predicts high-review-effort PRs using early static cues.

- arXiv: https://arxiv.org/abs/2601.00753

Positioning: studies effort and attention. MergeDossier-Bench studies evidence sufficiency and decision support.

## Pull-request governance for AI-authored changes

Relevant public threads and product discussions show increasing concern that AI-authored PRs may require different controls or stronger human oversight.

- GitLab issue about requiring additional approvals for AI-authored merge requests: https://gitlab.com/gitlab-org/gitlab/-/issues/578758
- GitHub community discussion about separating AI PR contribution and merge permissions: https://github.com/orgs/community/discussions/182732

Positioning: supports the paper's motivation that PR evidence and human accountability are becoming operational issues.

## Coding-agent repository instructions

AGENTS.md and Codex-style project instructions indicate that coding agents increasingly operate with repository-local workflow guidance.

- OpenAI Codex AGENTS.md docs: https://developers.openai.com/codex/guides/agents-md
- AGENTS.md format: https://agents.md/

Positioning: MergeDossier can be integrated into repository instructions as a required PR artifact.

# Population Study Protocol

This protocol upgrades the 22-PR pilot into a population-frame study without
turning the paper into an AI-vs-human causal comparison.

## Population Frame

The target population is the AIDev curated public agentic-PR frame: public
AI/AI-assisted pull requests with enough metadata to identify the repository,
pull-request number, and AI/AI-assisted authorship signal. Claims must be
written as estimates within this declared frame, not as statements about all
GitHub pull requests or all AI-authored pull requests.

Rows are excluded when the PR is private, deleted, unavailable, lacks a
repository/PR number, lacks usable AI/AI-assisted authorship evidence, or lacks
enough public artifacts for conservative dossier reconstruction.

The executable data path starts from the original `hao-li/AIDev`
`pull_request.parquet` AIDev-pop table, which the dataset card describes as the
filtered more-than-100-stars subset. `scripts/inspect_aidev_schema.py` records
the observed schema, and `scripts/export_aidev_curated_csv.py` writes the
compact CSV consumed by the sampling-frame builder.

## Sampling

Use a deterministic stratified sample:

- target sample size: 500 unique PRs;
- seed: `20260616`;
- primary allocation: agent/tool;
- secondary strata within agent/tool: language/ecosystem, outcome, and PR-size
  tercile;
- minimum per available agent/tool: 50 when feasible;
- sampling without replacement.

The sampler writes both a manifest and a sampling report containing frame size,
eligible size, excluded counts, stratum counts, selected IDs, seed, and fill
rules. The manifest keeps sampling weights for population-frame estimates.

## Dossier Construction

Use metadata-only reconstruction for dry runs and tests. For the final 500-PR
corpus, enrich sampled PRs through the existing GitHub REST fetcher when AIDev
metadata does not include enough visible PR artifacts. Preserve raw artifacts,
endpoint errors, resolved manifests, reconstructed dossiers, corpus summaries,
provenance audit outputs, dossier cards, and pilot-analysis tables.

## Annotation

The main analysis uses human labels, not automated reconstruction scores.

The planned annotation workload is:

- 500 unique PRs;
- 50 delayed repeats;
- 550 total annotation records;
- one annotator, unless a second annotator or external audit slice becomes
  available.

Report delayed-repeat self-consistency only. Do not call it inter-rater
reliability.

## Analysis

Report evidence-family coverage and missing rates with Wilson 95% intervals and
sampling weights. Include descriptive breakdowns by agent/tool, language,
outcome, and PR-size tercile when the stratum size is adequate.

Allowed current claim shape:

> Within the AIDev curated public agentic-PR frame, sampled AI/AI-assisted PRs
> show [estimated evidence gap] under the MergeDossier evidence-family rubric.

Disallowed current claim shapes:

- AI-authored PRs are worse than human PRs.
- MergeDossier improves reviewer decisions.
- The results estimate all AI PRs on GitHub.
- The single-annotator labels establish inter-rater reliability.

# Real Pilot Corpus Plan

## Pilot Target

The first real pilot corpus should include 20 to 50 public pull requests. It is
for pipeline validation, rubric refinement, and annotator training, not final
empirical claims.

Target composition:

- at least 10 AI-authored or AI-assisted PRs,
- at least 10 human-authored matched PRs,
- both merged and closed-unmerged outcomes where possible,
- at least 3 languages or ecosystems if possible,
- small, medium, and large PRs.

## Record For Each PR

- why the PR was selected,
- evidence of AI authorship or AI assistance, if any,
- ambiguity notes,
- whether it is suitable for human annotation,
- whether it contains enough public artifacts,
- task type, language, outcome, and sample split,
- whether a matched human PR is available.

## AI-Authored And AI-Assisted PRs

Accept AI authorship only when observable evidence exists, such as bot account
metadata, PR text, labels, linked agent logs, or maintainer comments. Record the
evidence in the manifest notes. Use `mixed` for substantial human co-authorship.

## Human-Authored Matched PRs

Match human PRs by repository or ecosystem when possible. Prefer similar task
type, language, approximate file count, and PR size. The matched human PR is not
a correctness baseline; it is a comparison point for evidence practices.

## Suitability For Annotation

A PR is suitable when annotators can see enough public artifacts to judge
evidence sufficiency: PR title/body, changed files, linked issues or issue
references, checks/statuses, and relevant comments when available.

## Single-Annotator Feasibility

If only one annotator is available, the pilot remains useful for pipeline
validation and rubric refinement. Use delayed repeat annotation for at least 20%
of tasks, with a minimum of 5 repeated tasks. Report self-consistency separately
from any future inter-rater agreement. Do not claim that the pilot establishes
human consensus.

## Do Not Overclaim

- Unknown `author_type` is allowed.
- Mixed authorship is allowed.
- AI-assisted is not the same as fully AI-authored.
- The pilot corpus is for pipeline validation and rubric refinement, not final claims.
- Merge outcome is not ground truth for correctness.
- Passing CI is metadata evidence, not proof of full regression safety.

## Pilot Procedure

1. Draft a manifest with 20 to 50 candidate public PRs.
2. Run `lint-seed-manifest` and fix errors.
3. Fetch a small `--limit 5` batch first.
4. Inspect raw artifacts, reconstructed dossiers, and endpoint errors.
5. Revise manifest notes for ambiguous authorship.
6. Build the full pilot corpus.
7. Run `summarize` and export annotation tasks.
8. Create delayed repeat tasks with `create-reliability-sample`.
9. Annotate a small subset and revise the protocol before the full pilot.

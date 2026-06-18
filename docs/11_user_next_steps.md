# User Next Steps For The ICSE Pilot

> **Superseded current-paper notice (2026-06-18):** This checklist described an
> earlier 20--50 PR pilot path. The current submission route uses the completed
> AIDev-pop 500-PR deterministic stratified sample, 50 delayed repeats, and a
> single-operator audit. The 22-PR public snapshot is retained only as
> preliminary pipeline/rubric validation. Do not use the older pilot checklist
> below to describe the submitted empirical scope.

This file is the working checklist for turning the current infrastructure
prototype into a real pilot study. It assumes a single annotator. Do not report
inter-rater reliability unless a second annotator is added later.

## Current State

- The corpus pipeline, GitHub fetcher, reconstruction, summarization, Label
  Studio export, and delayed-repeat reliability sample are implemented.
- This historical checklist no longer describes the submitted empirical scope;
  use `paper/main.tex`, `docs/14_reframing_to_evidence_availability.md`, and
  `docs/17_single_operator_submission_strategy.md` for the current paper route.
- The current public PR candidate list has 18 candidates. They are candidates,
  not verified AI-authored examples.
- The live probe has only 3 PRs. Its scores are useful for smoke testing, not
  for empirical claims.

## What You Need To Do First

1. Open `data/manifests/real_pilot_curation_sheet_20260613.csv`.
2. For each PR, open the `pr_url` in a browser.
3. Decide whether the PR should be included in the pilot.
4. Record observable authorship evidence. Do not infer AI authorship from vague
   wording, repository names, or product mentions alone.
5. Mark whether public artifacts are sufficient for annotation.

Use these values consistently:

- `include_decision`: `include`, `exclude`, or `maybe`
- `verified_author_type`: `ai_authored`, `mixed`, `human_authored`, or `unknown`
- `verified_agent_name`: `claude_code`, `codex`, `copilot`, `cursor`, `other`, or
  `unknown`
- `public_artifacts_sufficient`: `yes`, `no`, or `unclear`
- `annotation_suitable`: `yes`, `no`, or `unclear`

## Inclusion Rules

Include a PR only when it has enough public evidence for a maintainer-oriented
evidence sufficiency judgment. Useful artifacts include the PR title/body,
changed files, linked issues, checks/statuses, comments, and visible agent or
author notes.

For AI or AI-assisted PRs, record the exact public evidence. Examples include a
bot account, explicit PR text, commit metadata, labels, linked logs, or
maintainer comments. If the evidence is weak, use `mixed` or `unknown` and say
why in `notes`.

For human matched PRs, choose similar task type, language, rough size, and
repository/ecosystem where possible. The matched human PR is not a correctness
baseline. It is a comparison point for evidence practices.

## What Not To Do

- Do not judge whether the code is correct.
- Do not judge whether the PR should be merged.
- Do not treat merge outcome as ground truth.
- Do not treat passing CI as complete evidence.
- Do not overclaim AI authorship.
- Do not turn the project into a code-review-agent benchmark.
- Do not turn the project into a mergeability benchmark.

Core framing: evidence-centered evaluation of AI-authored pull requests.

Slogan: **A diff is not a dossier.**

## Minimum Pilot Target

The preferred pilot target is 20 to 50 public PRs:

- at least 10 AI-authored or AI-assisted PRs,
- at least 10 matched human PRs,
- mixed languages or ecosystems if possible,
- varied outcomes and PR sizes if possible.

Since the current candidate list has 18 PRs, the next practical milestone is:

1. verify the 18 existing candidates,
2. exclude weak or unsuitable candidates,
3. add at least 2 more strong public PRs,
4. ideally reach 20 usable PRs before writing empirical results.

## Commands After The Curation Sheet Is Filled

Create the selected manifest manually as:

```bash
data/manifests/real_pilot_selected.csv
```

It should keep the same columns as `data/manifests/real_pilot_candidates_20260613.csv`.
Then run:

```bash
python -m mergedossier_bench.cli lint-seed-manifest --manifest data/manifests/real_pilot_selected.csv
python -m mergedossier_bench.cli build-seed-corpus --manifest data/manifests/real_pilot_selected.csv --out data/real_pilot_raw --live --continue-on-error
python -m mergedossier_bench.cli reconstruct-dossier --raw data/real_pilot_raw --out data/real_pilot_dossiers
python -m mergedossier_bench.cli summarize --dossiers data/real_pilot_dossiers --out outputs/real_pilot_summary
python -m mergedossier_bench.cli export-annotation-tasks --dossiers data/real_pilot_dossiers --out outputs/real_pilot_annotation_tasks.json
python -m mergedossier_bench.cli create-reliability-sample --tasks outputs/real_pilot_annotation_tasks.json --out outputs/real_pilot_annotation_tasks_with_repeats.json --rate 0.2 --min-count 5
```

If GitHub rate limits block the live fetch, set a token first:

```bash
set GITHUB_TOKEN=YOUR_TOKEN
python -m mergedossier_bench.cli build-seed-corpus --manifest data/manifests/real_pilot_selected.csv --out data/real_pilot_raw --live --github-token-env GITHUB_TOKEN --continue-on-error
```

## Annotation Procedure

1. Import the Label Studio XML config generated by:

```bash
python scripts/generate_label_studio_config.py --out outputs/label_studio_config.xml
```

2. Import `outputs/real_pilot_annotation_tasks_with_repeats.json` into Label
   Studio.
3. Label all primary tasks first.
4. Label repeat tasks later, ideally after 48 hours, without checking the
   original labels.
5. Export Label Studio JSON after annotation.
6. Run:

```bash
python -m mergedossier_bench.cli annotation-stats --export outputs/label_studio_export.json --out outputs/real_pilot_annotation_stats.json
```

## What To Send Back To Codex

After curation and annotation, send or point Codex to:

- `data/manifests/real_pilot_selected.csv`
- `outputs/real_pilot_summary/summary.json`
- `outputs/real_pilot_summary/summary.md`
- `outputs/real_pilot_annotation_stats.json`
- the Label Studio export JSON

Then Codex can update the results tables, figures, threats to validity, artifact
package, and `paper/main.pdf`.

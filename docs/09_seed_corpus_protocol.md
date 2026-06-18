# Seed Corpus Protocol

## Goal

The seed corpus bridges toy examples and a future real-world MergeDossier-Bench
release. It records public or synthetic pull-request artifacts, reconstructs
conservative MergeDossiers, and prepares dossiers for corpus summaries and
human annotation. The seed corpus is evidence-centered: it evaluates what
evidence travels with a PR, not whether the patch is correct or mergeable.

Slogan: **A diff is not a dossier.**

## Inclusion Criteria

- Pull requests with enough public metadata to reconstruct at least a PR title,
  body or summary, changed files, and basic review or CI context.
- AI-authored, human-authored, mixed, and unknown-authorship PRs when authorship
  can be recorded transparently.
- PRs spanning bug fixes, features, refactors, tests, documentation, and
  dependency changes.
- Matched human-authored PRs that are comparable by task type, language, size,
  and repository context when possible.

## Exclusion Criteria

- Private repositories or private PR content without explicit permission.
- PRs containing secrets, credentials, private emails, exploit payloads, or
  sensitive user data that cannot be safely redacted.
- PRs whose authorship cannot be recorded honestly even as `unknown`.
- PRs where essential artifacts are unavailable and reconstruction would require
  guessing.

## AI-Authored PR Identification

Record observable signals rather than assumptions:

- bot account or agent account name,
- PR text stating the agent or tool used,
- repository labels or metadata identifying agent authorship,
- linked agent logs or generated traces,
- maintainer comments identifying an AI-authored PR.

Use `mixed` when humans substantially rewrote or co-authored the PR. Use
`unknown` when the evidence is ambiguous.

## Human-Authored Matched PR Protocol

For matched human PRs, choose PRs from the same or similar repositories when
possible. Match on language, task type, approximate changed-file count, and
outcome. Do not treat a human-authored PR as a correctness baseline; it is a
comparison point for evidence practices.

## Public Data, Privacy, And Ethics

Prefer public GitHub data and store only the artifacts needed for evidence
analysis. Redact secrets, private identifiers, and sensitive payloads before
release. Preserve enough metadata to make reconstruction reproducible, including
fetch mode, timestamp, manifest row, and unavailable-artifact errors.

## Unavailable PRs

If a PR is deleted, private, rate-limited, or otherwise unavailable, record the
row in the build log with a clear error. Do not replace it with guessed content.
The offline MVP uses fixtures only; future live fetching should preserve the
same explicit error records.

## Ambiguous Authorship

Use controlled manifest values:

- `ai_authored`
- `human_authored`
- `mixed`
- `unknown`

When in doubt, prefer `unknown` and explain the ambiguity in the manifest notes.

## Observed Evidence vs Inferred Evidence

Observed evidence comes directly from PR text, linked issue text, changed files,
CI/check metadata, review comments, issue comments, commits, or explicit agent
traces. Inferred evidence can be derived from metadata such as changed-file
counts or touched directories, but reconstruction notes must mark it as inferred.

Do not hallucinate missing evidence. If a category is unsupported, set
`present=false` and write a useful notes message.

## Using Seed Corpus Outputs For Annotation

The seed builder writes raw artifacts and reconstructed dossiers:

```text
data/seed_corpus/
  raw/
  dossiers/
  manifests/resolved_manifest.csv
  logs/build_seed_corpus_log.jsonl
  summary.json
  summary.md
```

Run corpus summary on `data/seed_corpus/dossiers`, then export annotation tasks
from the same directory. Human annotators should judge evidence sufficiency in
the reconstructed dossier, while remembering that reconstruction is conservative
and artifact-bound.

## Live Fetching Protocol

Live fetching is optional and should be used only for public PRs selected for a
pilot or release corpus. Run `lint-seed-manifest` before fetching. Start with a
small `--limit` batch and inspect `logs/build_seed_corpus_log.jsonl`,
`summary.json`, and a sample of reconstructed dossiers before scaling up.

## Token Handling

Use `GITHUB_TOKEN` or another environment variable passed through
`--github-token-env`. Never write the token to manifests, logs, raw artifacts, or
notes. The CLI should report endpoint failures without including request
headers.

## API Rate Limits

The live fetcher records endpoint-level failures and GitHub rate-limit metadata
when the API returns it. Use `--sleep-seconds` for polite throttling. If rate
limits interrupt a run, keep the partial raw artifacts, then rerun after reset;
cached `raw/<instance_id>.json` files are reused unless `--force` is supplied.

## Caching And Reproducibility

Each live raw artifact records `fetched_at`, `fetch_mode`, the manifest row, raw
endpoint payloads, and endpoint errors. Preserve raw artifacts with the resolved
manifest so reconstructed dossiers can be regenerated without repeating the
network fetch.

## Resolved Manifest Records

`manifests/resolved_manifest.csv` should record the manifest rows used for the
run. Keep the same `instance_id` across raw artifacts, reconstructed dossiers,
annotation tasks, and paper tables.

## Failed Or Partial Fetches

If one endpoint fails, record the failure under `errors` and reconstruct only
from available artifacts. If the main PR endpoint is unavailable, the row should
remain in the build log as a failure. Do not fill missing endpoint content from
memory or assumptions.

## Curating A 20-50 PR Pilot Corpus

For the first real pilot, target 20 to 50 public PRs. Include at least 10
AI-authored or AI-assisted PRs and at least 10 human-authored matched PRs when
available. Balance task type, language, PR size, and outcome. Prefer PRs with
enough public artifacts for annotation.

## Avoid Overclaiming AI Authorship

AI-assisted is not the same as fully AI-authored. Record observable evidence:
bot account, PR text, labels, logs, or maintainer comments. Use `mixed` when
humans substantially co-authored or rewrote the change. Use `unknown` when the
evidence is unclear.

## Ambiguous Agent Involvement

When agent involvement is ambiguous, set `author_type=unknown` or `mixed`, set
`agent_name=unknown` when needed, and explain the ambiguity in `notes`. These
rows can still be useful for pipeline validation, but they should not support
claims about specific agents.

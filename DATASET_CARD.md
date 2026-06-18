# Dataset Card

## Dataset Name

MergeDossier-Bench anonymous artifact release data.

## Source Frame

The population study is bounded to AIDev-pop public agentic pull requests represented by the included sanitized frame and deterministic sample manifest. The frame contains 33,596 eligible PRs. The study sample contains 500 sampled PRs and 50 delayed repeats for single-operator self-consistency checks.

## Included Data

- Sanitized AIDev-pop frame manifest.
- Deterministic 500-PR sample manifest.
- Completed evidence-availability audit-code table.
- Derived population-result tables.
- Dependency-sensitive audit derived results.
- Toy examples and schema fixtures.

## Excluded Data

- Private repository data.
- Credentials, API tokens, environment dumps, and local logs.
- Unsanitized raw AIDev export.
- Raw GitHub artifact downloads.
- Author names, emails, affiliations, ORCID identifiers, personal homepages, and institution-specific metadata.

## Public-Data Policy

The included manifests and derived tables are based on public PR metadata and manually coded review-evidence availability. The release avoids bundling private raw artifacts and local machine metadata.

## Anonymization / Redaction Policy

The release staging directory is scanned for local paths, Windows user paths, cloud-sync paths, emails, token patterns, SSH private keys, hidden leak-prone directories, and selected notebook metadata risks. Contact information is omitted or replaced with anonymous placeholders for double-anonymous review.

## Known Limits

- The population-frame estimate is bounded to AIDev-pop public agentic PRs, not all GitHub PRs.
- The audit is a single-operator audit with delayed-repeat self-consistency, not inter-rater reliability.
- The artifact measures review-evidence availability and handoff-evidence gap, not patch correctness or mergeability.
- Reviewer utility remains out of scope.
- AI-vs-human causal effects are not claimed.

## Recommended Citation

During double-anonymous review, use the anonymous citation metadata in `CITATION.cff`. Full citation and contact details should be added after review.


# Raw Frame Release Policy

## Default Release Boundary

The anonymous-review and default public artifact release uses the sanitized
AIDev-pop population-frame manifest:

- `data/manifests/population_ai_pr_frame_sanitized_20260616.csv`
- `outputs/population_sampling_report_20260616/sanitized_frame_report.json`

The sanitized frame preserves sampling-frame audit fields, strata, weights,
eligibility metadata, and the 500-sample membership flag. It removes raw PR
titles, bodies, changed-file lists, commit messages, comments, reviews, and
notes.

## Why The Full Raw Frame Is Not Shipped By Default

The full normalized population frame is derived from public pull-request
artifacts, but public text can still contain token-like strings, private-key
headers, internal URLs, emails, security payloads, or sensitive snippets copied
from upstream repositories. Public availability does not make such text safe to
redistribute in a benchmark archive.

The paper's current claims do not require redistributing the full raw-text
frame. The sampling report, sanitized frame, deterministic sample manifest,
scripts, completed audit sheet, and generated result tables are sufficient to
audit the declared AIDev-pop sampling frame and reproduce the reported
handoff-evidence gap tables.

## Risk Scan

Run the non-revealing scanner before any raw-frame release decision:

```bash
python scripts/scan_raw_frame_release_risks.py
```

Default outputs:

- `outputs/raw_frame_release_risk_20260617/raw_frame_release_risk_summary.json`
- `outputs/raw_frame_release_risk_20260617/raw_frame_release_risk_summary.md`

The scanner reports pattern names, affected columns, row counts, and safe PR
identifiers only. It intentionally omits matched strings and surrounding
snippets.

## Release Decision

Default policy:

1. Include the sanitized population frame in the anonymous-review artifact.
2. Exclude the full raw-text frame from the anonymous-review and default public
   release.
3. If a venue or artifact reviewer requests raw text, prepare a separate
   restricted or scrubbed archive after running automated scans and manual
   review.
4. Do not claim that the raw frame is publicly archived until a DOI or access
   path actually exists.

This policy supports artifact auditability while avoiding unnecessary
redistribution of sensitive text. It does not change the empirical scope: all
population-rate wording remains limited to the declared AIDev-pop frame, not
all GitHub pull requests.

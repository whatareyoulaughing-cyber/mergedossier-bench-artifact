# Claims and Non-Claims

This table should appear in paper-facing reports and can be used directly in
the manuscript or artifact appendix. It keeps MergeDossier-Bench centered on
the handoff-evidence gap within a declared population frame while blocking
common overclaims.

| Claim | Non-claim |
|---|---|
| Handoff-evidence gap in AIDev-pop | All-GitHub rates |
| Provenance-backed visibility | Patch correctness |
| Category-level missing evidence | Mergeability |
| Single-operator self-consistency | Inter-rater reliability |
| Dependency candidate audit | Full-sample dependency prevalence |
| Instrument auditability | Reviewer utility |
| Descriptive population-frame estimates | AI-vs-human causal effects |

## Recommended Use

Use the claims as the outer boundary of the paper. For example, the manuscript
may report the handoff-evidence gap within a declared AIDev-pop sampling frame,
but should not generalize to all GitHub pull requests.

Use provenance-backed visibility to say that a dossier cites where a piece of
evidence came from. Do not use provenance to claim the patch is correct or
mergeable.

Use delayed-repeat self-consistency only as a single-operator repeatability
audit. Do not describe it as inter-rater reliability.

Use review-demand extraction, if reported, as exploratory context about comment
language. Do not describe it as evidence that MergeDossier-Bench improves
reviewer decisions.

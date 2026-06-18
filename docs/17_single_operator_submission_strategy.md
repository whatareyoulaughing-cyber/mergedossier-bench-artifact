# Single-Operator Submission Strategy

This note records the submission strategy when no second operator is available before the ICSE deadline.

## Decision

Submit with a bounded single-operator audit rather than treating the unfinished external-audit slice as a hard blocker.

The manuscript may report:

- a deterministic 500-PR stratified AIDev-pop sample;
- 50 delayed-repeat tasks;
- delayed-repeat self-consistency under the same protocol;
- category-level review-evidence availability estimates;
- handoff-evidence gap robustness tables;
- provenance-status and source-type tables;
- perturbation fixtures and offline reproducibility checks;
- a prepared external-audit packet as future replication material.

The manuscript must not report:

- inter-rater reliability;
- Cohen's kappa or Krippendorff's alpha as current results;
- completed external agreement;
- reviewer utility;
- patch correctness;
- mergeability;
- AI-vs-human causal effects;
- all-GitHub population rates.

## Recommended Wording

Use:

> The AIDev-pop audit was conducted by one operator with 50 delayed repeats.
> We therefore report delayed-repeat self-consistency, provenance-backed
> inspectability, perturbation checks, and sensitivity analyses rather than
> inter-rater reliability. A deterministic 50-task external-audit packet is
> included for future independent replication, but no external agreement is
> claimed in the submitted results.

Avoid:

> We validate the coding scheme with an external audit.

Avoid:

> The labels have inter-rater reliability.

Avoid:

> The review-evidence availability codes are objectively correct.

## Why This Is Defensible

The paper's central claim is not that subjective coding agreement has been established.
The central claim is that MergeDossier-Bench provides a provenance-aware measurement framework and that, within AIDev-pop, public PR artifacts exhibit a large handoff-evidence gap.

This claim is supported by:

- explicit claim/non-claim boundaries;
- public sample construction and deterministic scripts;
- availability intervals rather than single threshold-only labels;
- tipping-point analysis showing that many handoff-critical codes would have to flip to erase the gap;
- provenance records that make evidence sources inspectable;
- perturbation fixtures that test instrument behavior on controlled inputs;
- delayed repeats that test same-operator stability.

These checks support instrument auditability and repeatability under the stated protocol.
They do not support subjective agreement claims.

## Submission Gate

For the no-second-operator path, build the dashboard with:

```powershell
python scripts/check_submission_blockers.py --single-operator-submission-mode --out outputs/submission_blocker_dashboard_20260618_single_operator
```

The expected result is:

- `p0_open_count = 0` if all other gates pass;
- the external-audit slice is listed as a P1 limitation;
- the interpretation explicitly states that external audit completion is follow-up material, not current evidence.

If an independent operator becomes available later, rerun the original strict gate without `--single-operator-submission-mode` and report the external-audit result only if the return checker passes.

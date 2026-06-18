# Reframing to the Handoff-Evidence Gap

This note reframes MergeDossier-Bench from an evidence-sufficiency judgment paper
toward handoff-evidence gap measurement. Review-evidence availability remains
the measurement substrate, but the main empirical result is now the gap between
surface evidence and handoff-critical evidence. The brand remains
MergeDossier-Bench, and the slogans remain:

- A diff is not a dossier.
- A dossier must cite its evidence.

## Recommended Title

MergeDossier-Bench: Measuring the Handoff-Evidence Gap in AI-Authored Pull
Requests

## Revised Abstract

We introduce MergeDossier-Bench, a provenance-aware benchmark and measurement
framework for review-evidence availability in AI-authored pull requests. Rather
than treating patch correctness, mergeability, or reviewer utility as ground
truth, MergeDossier-Bench asks whether a pull request visibly provides the
evidence a maintainer would need to understand the change, inspect its basis,
and audit the handoff. The framework represents evidence categories in a
structured MergeDossier, validates dossiers against a public schema, records
evidence provenance, and reports availability intervals that treat partial
evidence as threshold uncertainty. In an AIDev-pop population-frame study, the
main empirical object is the handoff-evidence gap: surface evidence such as
intent, scope, and tests is commonly visible, while risk, trace, regression
boundary, rationale, and ownership evidence remain mostly unavailable. The
availability interval for handoff evidence is [0.0\%, 10.16\%], yielding a
handoff-evidence gap of [89.84\%, 100.0\%]. The artifact also emits explicit
claims/non-claims tables to keep the interpretation bounded.

## Revised RQs

- RQ1: How can review evidence in AI-authored pull requests be represented as
  provenance-certified availability intervals rather than correctness or
  mergeability judgments?
- RQ2: What handoff-evidence gap is observed in a stratified 500-PR sample from
  AIDev-pop, and is the gap robust to strict and lenient coding rules?

## Terminology Mapping

| Previous wording | Preferred paper-facing wording |
|---|---|
| Evidence Sufficiency | Review-Evidence Availability |
| evidence sufficiency judgment | evidence availability measurement |
| sufficiency labels | evidence-availability codes |
| annotation labels | audit codes |
| annotation pass | single-operator audit |
| pilot result | evidence availability profile |
| Evidence Sufficiency Score | legacy artifact metric |
| evidence availability profile | handoff-evidence gap |
| point availability estimate | availability interval |

The legacy Evidence Sufficiency Score may remain in CLI outputs and backward
compatible score reports. The paper's central empirical claims should use
category-level availability rather than a single sufficiency judgment.

## Single-Operator Audit Language

Use:

> Because the current study uses one trained operator, delayed-repeat results
> assess within-operator repeatability rather than inter-rater reliability.
> Schema validation, provenance audit, perturbation fixtures, and sensitivity
> analysis support instrument auditability; they do not establish subjective
> agreement between independent annotators.

Avoid:

- inter-rater reliability was established
- labels were validated
- reviewer agreement
- gold-standard subjective labels

## Reviewer Utility Is Out Of Scope

MergeDossier-Bench can measure whether review evidence is visible and cited. It
does not show that dossiers improve maintainer decisions, reduce review time, or
increase merge quality. Those questions require a separate reviewer-utility
study with maintainers, tasks, outcomes, and controls.

Use:

> Reviewer utility is an important downstream question, but it is not the
> estimand of this paper. The current contribution is a provenance-aware
> measurement framework and handoff-evidence gap estimate.

Avoid:

- dossiers improve review quality
- maintainers make better decisions with MergeDossiers
- evidence availability implies correctness

# Provenance Status Summary

Provenance rows summarize inspectable evidence sources and reconstruction status; they do not establish patch correctness, mergeability, reviewer utility, or inter-rater reliability.

- Dossier source: outputs\population_ai_pr_500_20260616\dossiers
- Valid dossiers: 500
- Invalid dossiers: 0

## Status By Category

| category | observed | inferred | missing | not_applicable |
| --- | --- | --- | --- | --- |
| intent | 500 | 0 | 0 | 0 |
| requirement_traceability | 0 | 144 | 356 | 0 |
| test_rationale | 387 | 22 | 91 | 0 |
| regression_safety | 14 | 0 | 486 | 0 |
| risk_analysis | 105 | 0 | 395 | 0 |
| scope_justification | 15 | 478 | 7 | 0 |
| change_summary | 500 | 0 | 0 | 0 |
| agent_trace | 0 | 0 | 500 | 0 |
| limitations | 31 | 0 | 469 | 0 |
| reviewer_actionability | 46 | 0 | 454 | 0 |
| ownership_handoff | 89 | 0 | 411 | 0 |
| dependency_evidence | 0 | 70 | 0 | 430 |
| rationale_evidence | 61 | 0 | 439 | 0 |

## Source Types By Category

| category | source_type | count |
| --- | --- | --- |
| intent | pr_title | 500 |
| requirement_traceability | pr_body | 144 |
| requirement_traceability | heuristic | 356 |
| test_rationale | pr_body | 387 |
| test_rationale | changed_file | 22 |
| test_rationale | heuristic | 91 |
| regression_safety | pr_body | 14 |
| regression_safety | heuristic | 486 |
| risk_analysis | pr_body | 105 |
| risk_analysis | heuristic | 395 |
| scope_justification | pr_body | 15 |
| scope_justification | changed_file | 478 |
| scope_justification | heuristic | 7 |
| change_summary | changed_file | 493 |
| change_summary | commit | 7 |
| agent_trace | heuristic | 500 |
| limitations | pr_body | 31 |
| limitations | heuristic | 469 |
| reviewer_actionability | pr_body | 46 |
| reviewer_actionability | heuristic | 454 |
| ownership_handoff | pr_body | 89 |
| ownership_handoff | heuristic | 411 |
| dependency_evidence | changed_file | 70 |
| dependency_evidence | heuristic | 430 |
| rationale_evidence | pr_body | 61 |
| rationale_evidence | heuristic | 439 |

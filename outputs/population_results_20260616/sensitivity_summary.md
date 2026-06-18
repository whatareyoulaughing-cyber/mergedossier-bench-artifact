# Review-Evidence Availability Sensitivity

The handoff-critical evidence gap remains under stricter treatment of partial evidence.

- Main rule: present + partially_present counted positive
- Strict rule: only present counted positive
- Conservative rule: partially_present counted missing
- Robustly high categories: intent_evidence
- Robustly low categories: requirement_evidence, risk_analysis, trace_evidence, regression_evidence, rationale_evidence, ownership_handoff
- Partial-sensitive categories: test_evidence, scope_evidence

| category | main | strict | conservative | conservative missing |
| --- | --- | --- | --- | --- |
| intent_evidence | 100.0\% | 98.4\% | 98.4\% | 1.6\% |
| requirement_evidence | 28.8\% | 0.0\% | 0.0\% | 100.0\% |
| test_evidence | 81.8\% | 39.4\% | 39.4\% | 60.6\% |
| risk_analysis | 21.0\% | 0.0\% | 0.0\% | 100.0\% |
| scope_evidence | 98.6\% | 3.0\% | 3.0\% | 97.0\% |
| trace_evidence | 0.0\% | 0.0\% | 0.0\% | 100.0\% |
| dependency_evidence | -- | -- | -- | -- |
| regression_evidence | 2.8\% | 0.0\% | 0.0\% | 100.0\% |
| rationale_evidence | 9.2\% | 0.0\% | 0.0\% | 100.0\% |
| ownership_handoff | 17.8\% | 0.0\% | 0.0\% | 100.0\% |

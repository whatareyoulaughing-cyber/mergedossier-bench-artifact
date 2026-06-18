# AIDev-pop 500-PR 标注结果摘要

数据来源：AIDev-pop curated public agentic-PR frame。

标注规模：

- 500 primary PR annotation records
- 50 delayed-repeat records
- 550 total records
- 1 annotator

## 主要 population-frame estimates

| Evidence family | Coverage | Wilson 95% CI | Missing |
| --- | ---: | ---: | ---: |
| intent_evidence | 100.0% | 99.24%-100.0% | 0.0% |
| requirement_evidence | 28.8% | 25.0%-32.92% | 71.2% |
| test_evidence | 81.8% | 78.18%-84.94% | 18.2% |
| risk_analysis | 21.0% | 17.66%-24.78% | 79.0% |
| scope_evidence | 98.6% | 97.14%-99.32% | 1.4% |
| trace_evidence | 0.0% | 0.0%-0.76% | 100.0% |
| regression_evidence | 2.8% | 1.68%-4.64% | 97.2% |
| rationale_evidence | 9.2% | 6.97%-12.05% | 90.8% |
| ownership_handoff | 17.8% | 14.7%-21.39% | 82.2% |

`dependency_evidence` 被标为 not_applicable，因此不进入 coverage denominator。

## Delayed-repeat self-consistency

50 个 delayed repeats 中没有 category-level disagreement。这个结果只能写作
single-annotator delayed-repeat self-consistency，不能写作 inter-rater reliability。

## 可写进论文的保守结论

Within the AIDev-pop curated public agentic-PR frame, visible PR evidence is
highly concentrated in intent, scope, and test evidence, while trace,
regression, rationale, ownership handoff, and risk evidence remain frequently
missing under the MergeDossier evidence-family rubric.

## 不能 claim

- all AI-authored PRs on GitHub
- AI-vs-human causal effect
- reviewer utility improvement
- inter-rater reliability

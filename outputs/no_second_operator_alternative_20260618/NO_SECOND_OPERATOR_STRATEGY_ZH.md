# 无第二人标注时的替代提交方案

## 结论

可以不再把 two-person external audit 当成投稿前硬阻塞。
替代方案是把论文定位为：

> provenance-aware measurement framework + AIDev-pop 500-PR single-operator audit with delayed-repeat self-consistency and instrument-audit checks.

这条路线的关键是诚实收窄：

- 报告 handoff-evidence gap；
- 报告 review-evidence availability；
- 报告 50 delayed repeats 的 same-operator self-consistency；
- 报告 provenance、sensitivity、perturbation、tipping-point robustness；
- 不报告 inter-rater reliability；
- 不报告 external agreement。

## 可以写

> The AIDev-pop audit was conducted by one operator with 50 delayed repeats.
> We report delayed-repeat self-consistency, provenance-backed inspectability,
> perturbation checks, and sensitivity analyses rather than inter-rater
> reliability. A deterministic 50-task external-audit packet is included for
> future independent replication, but no external agreement is claimed in the
> submitted results.

## 不能写

- external audit completed
- inter-rater reliability established
- agreement / kappa / alpha as current evidence
- validated labels
- reviewer utility
- patch correctness
- mergeability
- AI PRs are worse than human PRs
- all-GitHub AI-authored PR rates

## Reviewer Attack 回应

| Attack | 回应 |
|---|---|
| Why no second annotator? | The current contribution is a measurement framework and bounded population-frame audit. We therefore report single-operator delayed-repeat self-consistency and avoid inter-rater reliability claims. |
| Are the labels subjective? | The paper uses audit codes, provenance snippets, perturbation fixtures, and sensitivity intervals to make decisions inspectable. This supports instrument auditability, not subjective agreement. |
| Can one operator support population results? | It supports category-level evidence-availability estimates under one documented audit protocol within AIDev-pop. It does not support psychometric reliability or reviewer-utility claims. |
| Why include an external-audit packet? | It is replication/future-validation material, not current evidence. |

## 新 gate

运行：

```powershell
python scripts/check_submission_blockers.py --single-operator-submission-mode --out outputs/submission_blocker_dashboard_20260618_single_operator
```

如果其他 gate 都通过，预期结果：

- `status = submission_ready_local`
- `p0_open_count = 0`
- external audit slice 变成 `P1 ready` limitation

## 当前最推荐动作

1. 用 single-operator mode 更新 dashboard。
2. 确认 paper/main.tex 里仍然没有 inter-rater reliability claim。
3. 如果 dashboard 和 tests 通过，就按 conservative wording 投稿。
4. external audit packet 保留在 artifact 中，作为 future independent replication material。

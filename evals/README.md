# Evaluation cases

五个代表案例，用作 M1 规则验证器的固定输入。每个文件都是自包含 JSON：

| 字段 | 含义 |
| --- | --- |
| `kind` | `validation` 由 `backend/tests/test_eval_cases.py` 直接跑；`flow` 由 API 测试覆盖，文件内注明具体测试 |
| `input` | 传给 `app.rules.evaluate` 的输入，`today` 固定以便结果可复现 |
| `expected.feasible` | 是否放行 |
| `expected.total_minor` | 整数美分总额 |
| `expected.violation_codes` | 期望出现的违规码集合（不校验顺序） |
| `expected.missing_fields` | 信息缺失字段 |

## 案例清单

| 文件 | 场景 | 结论 |
| --- | --- | --- |
| `case-01-missing-details.json` | 未给预算与交期 | 不放行，报告缺失字段 |
| `case-02-budget-gap.json` | 三页 700 美元 vs 500 美元预算 | 不放行，`budget_exceeded` |
| `case-03-unsupported-feature.json` | 要求站内点单 | 不放行，`capability_unavailable` |
| `case-04-deadline-conflict.json` | 六天上线且素材未齐 | 不放行，`deadline_conflict` |
| `case-05-change-request.json` | 报价起草后需求变更 | 新修订号作废旧草稿；过期修订号写入返回 409 |

## 运行

```bash
cd backend
uv run pytest tests/test_eval_cases.py -q
```

规则改动时先改案例再改实现；案例期望值不得为了迁就实现而放宽。

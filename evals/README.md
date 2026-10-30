# Evaluation

两个东西放在这里：固定案例集，以及把它们跑成报告的脚本。

## 案例集 `cases.json`

20 个案例，19 个 `validation`（由 pytest 与评测脚本直接跑规则层），1 个 `flow`（由 API 测试覆盖，文件内 `covered_by` 指明位置）。

| 字段 | 含义 |
| --- | --- |
| `kind` | `validation` 走 `app.rules.evaluate`；`flow` 走接口测试 |
| `brief` | 给模型看的客户原话，评测脚本用它构造提示词 |
| `input` | 规则层输入，`today` 固定以便复现 |
| `expected` | 期望的放行结论、美分总额、违规码集合、缺失字段 |

案例覆盖：信息缺失、预算不足、能力不可提供、交期冲突、加项超预算、未知加项、零页数、正好卡预算、正好卡交期、多问题叠加、需求变更。

```bash
cd backend
uv run pytest tests/test_eval_cases.py -q
```

## 评测脚本 `run_eval.py`

对比两条链路，同一批案例、同一份规则、同一个模型：

| 链路 | 做法 | 观察点 |
| --- | --- | --- |
| `baseline` | 单次提示，让模型直接给出「页数 + 加项 + 总价 + 是否可行」 | 价格与规则是否一致、是否把不可行方案说成可行 |
| `pipeline` | 模型只出五个事实，服务端生成候选并定价 | 是否给出可交付选项、无解是否明说 |

```bash
cd backend
uv run python ../evals/run_eval.py --runs 3 --workers 4
```

产物写入 `evals/reports/<时间戳>.json` 与同名 `.md`，包含逐案例结论、平均/P95 耗时、token 用量。

规则改动时先改案例期望值，再改实现；不得为了让脚本通过而放宽断言。

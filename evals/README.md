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

## 评测脚本 `run_eval.py` 与指标 `metrics.py`

对比两条链路，同一批案例、同一份规则、同一个模型：

| 链路 | 做法 | 观察点 |
| --- | --- | --- |
| `baseline` | 单次提示，让模型直接给出「页数 + 加项 + 总价 + 是否可行」 | 价格与规则是否一致、是否把不可行方案说成可行 |
| `pipeline` | 模型只出五个事实，服务端生成候选并定价 | 原需求是否满足、缩减后是否可行、无解是否明说 |

指标口径（`metrics.py`，纯函数，可单测）：

- 所有比例的分母是**调用次数**（含未解析与传输失败）；只有显式标注 `of_parsed` 的才用解析样本。
- 管线的「不安全放行」由运行期**重新调用 `evaluate` 复算**得到，不是硬编码 0。
- 每条失败记录 `failure_class`（`transport` / `content`）与原始输出前 200 字，便于按原文归类。

```bash
cd backend
uv run python ../evals/run_eval.py --runs 1 --workers 1 --timeout 90 --pause 1 --tag facts-v7
```

常用参数：`--runs`（每例重复次数）、`--limit`（只跑前 N 例）、`--workers`（默认 1，并发会让网关超时）、
`--timeout`、`--pause`（调用间隔秒）、`--arm`（`both` / `baseline` / `pipeline`）、`--tag`（报告后缀）。

产物写入 `evals/reports/<时间戳>[-<tag>].json` 与同名 `.md`，含逐案例结论、平均/P95 耗时、token 用量。

规则改动时先改案例期望值，再改实现；不得为了让脚本通过而放宽断言。评测口径与结论见
`../.agents/notes/implemented/testing/2026-10-30-comparative-evaluation.md`。

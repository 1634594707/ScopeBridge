# Agent Note: 后端采用模块化单体的领域分包，并把定价与可行性收敛成零 IO 纯函数层

Status: implemented

## Problem

项目要在两周内交付一条可被评委真实操作的成交主线，同时要能说清「AI 提议、程序裁决、人确认」的边界。如果价格计算散落在路由、模型和未来接入的模型调用里，任何人都无法证明金额没有被模型或前端改写；如果按微服务拆分，单人维护成本会吃掉实现时间。

## Decision

后端是单进程下按领域分包的模块化单体：`accounts`、`service_rules`、`requirements`、`proposals`、`quotes`，每包自带 models / schemas / service / router，跨包只调用对方 service，不跨包读表。`app/rules/` 独立成零 IO 纯函数层（`price_scope` / `evaluate`），输入是规则投影与范围输入，输出 `ValidationResult`，不认识数据库、网络和时钟（`today` 由调用方传入）。状态迁移同样收敛成纯函数 `quotes/states.transition`，非法迁移直接抛 409。数据访问使用 SQLAlchemy 2 同步会话 + psycopg3，迁移用 Alembic；金额一律整数美分。

## Alternatives considered

- **微服务拆分（requirements / proposals / quotes / payments 各自部署）**：最强的理由是模块边界物理隔离，未来支付链路故障不会拖垮报价。否掉的原因是本项目只有一名开发者和一条演示主线，跨服务鉴权、事务和本地编排的成本会直接挤掉功能实现时间；而且模块化单体在本阶段同样能靠「不跨包读表」保住边界，等真有独立扩缩容需求再拆。
- **仓储模式（Repository + Unit of Work）**：最强的理由是把领域逻辑与持久化解耦，可以用内存仓储做快速单测。否掉的原因是本项目的领域逻辑已经被抽成纯函数，测试真正的价值集中在规则与状态机上，这两处不需要数据库替身；再包一层仓储只会增加记录与领域对象互相映射的样板代码。
- **异步 SQLAlchemy / asyncpg**：最强的理由是 FastAPI 下并发吞吐更好，适合 I/O 密集。否掉的原因是 M4 引入支付后最关键的不变量是「先提交本地记录、再发外部请求」，同步会话让这条顺序在代码结构上一目了然，而演示规模下的并发量不构成瓶颈。
- **引入状态机库**：最强的理由是状态与迁移集中声明、可视化。否掉的原因是只有 4 个状态和 4 条合法迁移，自写守卫 + 单测覆盖更可控，也不会引入库自带的隐式容错。

## Consequences

- 收益：金额与可行性只有一个计算入口，M3 接模型时模型输出必须过同一个验证器；纯函数层可以脱离数据库跑全量案例，测试 3 秒内完成。
- 收益：模块边界靠目录与 import 方向维持，新增 `payments` 包有明确位置。
- 代价：同步会话在高并发下吞吐有限，属已知取舍；模块边界目前靠约定与 code review，没有引入自动依赖检查。
- 代价：报价版本的不可变性只在应用层保证，数据库没有触发器阻止更新；演示阶段接受，M4 前若无余量则维持现状并在文档中标注。

## Testing

`backend/tests/test_pricing.py`、`test_feasibility.py`、`test_state_machine.py` 覆盖纯函数层；`test_api_quote_flow.py` 覆盖读库与状态迁移；`evals/cases/*.json` 是固定案例集，`test_eval_cases.py` 逐条回放。

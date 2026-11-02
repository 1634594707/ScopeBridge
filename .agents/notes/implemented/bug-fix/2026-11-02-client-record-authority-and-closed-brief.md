# Agent Note: 客户记录是规则输入的唯一来源，已支付 brief 是终态

Status: implemented

## Problem

2026-11-02 的只读审查发现三条相互关联的数据边界缺口：

1. 卖家回复只发送 `body + expected_revision`，但 `append_message` 从“最后一条消息”继承
   `budget_minor/deadline/assets_ready`。卖家消息这三个字段为 `null`，客户下一次只改文字时，
   原本的预算、日期和素材状态会被静默清空，`evaluate` 随即返回 `missing_fields`，报价无法继续。
2. 卖家建方案时可以提交 `budget_minor/deadline`，且 `assets_ready` 默认 `true`；报价时预算和
   日期虽然从最新客户消息重算，素材状态仍取 `proposal.assets_ready`。客户说“素材未就绪”时，
   方案仍可能显示“可交付”。
3. 支付成功后 `requirements.status` 变为 `CLOSED`，但新增消息、建方案、出报价都没有检查它；
   已支付 brief 仍可再报价、再支付。修订只把 `DRAFT/REVIEWED` 置为 `SUPERSEDED`，已确认报价
   仍可支付；`start_payment` 也不检查 `source_revision` 与 `expires_at`。

另一个审计问题是删除：`delete_for_seller` 只检查是否存在 `OrderSnapshot`。处于
`RECONCILING`、或已带 PayPal order/capture id 的 attempt 会被级联删除，最需要保留的证据反而
最先消失。

## Decision

**客户记录权威，卖家只能记录显式素材假设。**

- `append_message` 按字段从“最近一条非空值”继承；卖家消息不能清空客户事实。`CLOSED` brief 拒绝
  任何新消息。
- `ProposalCreate` 不再接收 `budget_minor/deadline`；预算和日期一律来自 `latest_client_message`。
  `assets_ready` 为空时取客户记录，非空时作为卖家显式假设写入 `proposals.assets_ready`。报价
  `create_quote` 仍用 `proposal.assets_ready` 重新跑 `evaluate`，因此假设会被重新校验并显示在
  客户方案卡上。
- `requirements.status == CLOSED` 是终态：新增消息、建方案、选方案、出报价、启动支付都返回
  `409 brief_closed`（`start_payment` 另外检查 `source_revision` 与 `expires_at`）。
- `brief_is_closed` 同时检查 `OrderSnapshot`，因此历史上“快照已存在但 status 仍是 OPEN”的
  数据也不会绕过终态；迁移 `e2f4a6b8c0d1` 把已有快照的 requirement 回填为 `CLOSED`。
- 修订后 `supersede_open` 同时处理 `DRAFT`、`REVIEWED`、`CONFIRMED`；`CONFIRMED → SUPERSEDED`
  已加入状态表。
- 删除前同时检查 `OrderSnapshot`、非终态 attempt、以及任何带 `paypal_order_id` 或
  `paypal_capture_id` 的 attempt；任一命中返回 `409 payment_completed` 或
  `409 payment_in_progress`。卖家列表的 `deletable` 使用同一判据。

## Alternatives considered

1. **继续允许卖家在方案里改预算/日期，只在报价时重算**。最强理由：卖家可以快速做“预算假设”。
   否决：这会让客户看到的“可交付”建立在另一个人的数字上；预算和日期是客户约束，不是卖家的
   定价参数。
2. **素材状态只取客户记录，完全不允许假设**。最强理由：规则层只有一个输入，审计最简单。
   否决：演示需要“素材未就绪但先看交付日期”的对照；保留一个显式、可展示、报价前重新校验的
   假设比偷偷覆盖更安全。
3. **已支付 brief 允许继续加消息，只禁止新报价**。最强理由：客户可以补充交付说明。
   否决：这与“paid snapshot 是收据、已支付记录只读”冲突；补充说明应进入新 brief 或外部沟通。
4. **删除时只保留 `OrderSnapshot` 判据**。最强理由：实现最小，已支付记录有快照即可。
   否决：`RECONCILING` 正是最需要证据的状态；删除 attempt 会让 PayPal 侧的真实扣款无法对账。

## Consequences

- **收益**：客户约束不会因为一条卖家回复而丢失；方案里的素材假设可见且会被报价重新校验；
  已支付 brief 不会再产生第二份报价/支付；删除不会销毁未知支付证据。
- **代价与已知上限**：`CONFIRMED` 现在可以被修订置为 `SUPERSEDED`，客户需要重新确认；这是
  有意的产品行为，README 和落地页文案已同步。`assets_ready` 字段同时承担“假设”语义，未来若
  需要多假设类型，应新增独立字段而不是复用。
- 删除保护依赖 attempt 的 `status/paypal_order_id/paypal_capture_id`；如果未来加入新的外部
  引用字段，必须同步扩展 `undeletable_requirement_ids`。

## Verification

- `backend/tests/test_api_quote_flow.py`：卖家消息后客户只改文字，预算/日期/素材仍保留；
  方案默认取客户素材记录，显式假设写入 `assets_ready=true`。
- `backend/tests/test_api_payment.py`：`CLOSED` brief 拒绝消息/方案/报价；修订使 `CONFIRMED`
  变 `SUPERSEDED`；过期报价不能启动支付；有 in-flight attempt 的 brief 删除返回
  `409 payment_in_progress`。
- 2026-11-02: `uv run pytest -q` → `109 passed, 2 warnings`；迁移
  `e2f4a6b8c0d1` 的 `upgrade` 已在本地 demo 数据库执行，已有一条快照的 requirement 从 `OPEN`
  修复为 `CLOSED`（`alembic current` 见最终回报）。

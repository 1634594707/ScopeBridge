# Agent Note: 支付先锁定报价再调用 PayPal，未知结果只做核验

Status: implemented

## Problem

PayPal Orders v2 的「创建 → 买家批准 → 捕获」是三个独立步骤，捕获请求可能超时、响应可能在扣款后被丢弃，浏览器返回成功也可能是用户伪造的 URL。若把「浏览器回来」或「HTTP 200」当成已付款，会出现两类错误：收了钱但本地没有订单，或本地显示已付但实际没扣款。另外同一报价被重复点击、重复捕获，会形成两笔真实扣款。

## Decision

**先锁定，再调用，最后核验。** 开始支付时把报价从 `CONFIRMED` 推进到 `PAYMENT_LOCKED`，把 `PaymentAttempt` 以 `CREATING` 落库并提交，然后才调用 PayPal。任何外部调用都发生在事务提交之后。

**金额只来自服务端。** 创建订单时用已确认报价的 `total_minor` 与 `currency`；客户端请求体里没有金额字段。捕获后用 `capture.amount.value` 与 `currency_code` 逐字比对该报价，不一致进入 `RECONCILING`，绝不写订单快照。

**结果不明一律 `RECONCILING`。** 传输错误、5xx、`ORDER_ALREADY_CAPTURED` 都不判失败，改为向 PayPal 查询原订单：`COMPLETED` 则补写快照，`APPROVED` 则用同一 `PayPal-Request-Id` 重新捕获，`VOIDED`/`EXPIRED` 才判 `FAILED` 并解锁报价。

**幂等有数据库兜底。** `idempotency_key`、`paypal_order_id`、`paypal_capture_id` 各自唯一；同一报价同时最多一个活动尝试，由部分唯一索引 `uq_payment_attempts_active_quote` 保证；`OrderSnapshot.quote_version_id` 唯一，快照与 `PAID` 在同一事务提交。同键不同报价返回 `409 idempotency_conflict`。

**买家取消不是退款信号。** `cancel_url` 只回到状态页，不解锁；只有服务端核验出「确定没有成功捕获」才把报价退回 `CONFIRMED`。

## Alternatives considered

1. **直接信任浏览器返回的 `?paypal=return` 参数**。最强理由：实现最省事，用户体验连贯，PayPal 确实会把买家送回该地址。放弃原因：return URL 是客户端可伪造的，服务端没有金额与状态校验，也无法处理「扣款成功但响应丢失」。
2. **由客户端提交金额，服务端照单创建订单**。最强理由：前端可以展示任意加项与折扣。放弃原因：违反「金额只由规则层产生」，且一次篡改就能改变收款额。
3. **把 `PayPal-Request-Id` 当作永久去重机制**。最强理由：PayPal 官方支持重放同一请求返回同一结果，理论上不需要本地唯一键。放弃原因：请求标识的保存窗口依接口而异，不能当作长期唯一性保证；本地唯一约束才是最终防线。
4. **捕获超时后自动重试捕获**。最强理由：多数超时是网络抖动，重试能提升成功率。放弃原因：捕获有真实副作用，盲目重试可能造成第二笔扣款；先查询再决定，是本设计唯一的路径。
5. **客户端取消即解锁报价**。最强理由：用户不想付了应当立即恢复可编辑。放弃原因：取消只是交互事件，不能证明没有扣款；解锁会让同一版本在未知状态下被再次支付。

## Consequences

- 收益：已付款状态只可能由「服务端查询到的 COMPLETED 捕获 + 金额匹配」产生；重复点击、重复捕获、响应丢失都有确定行为；每个成功支付都有不可变快照。
- 代价：报价可能长时间停留在 `PAYMENT_LOCKED`，需要卖家在控制台点「Verify with PayPal」或买家在支付状态页刷新；没有无人值守的对账任务。
- 已知限制：沙箱买家批准必须人工完成；`PAYPAL_MERCHANT_ID` 未配置时只校验金额与币种，不校验收款方；没有退款、部分捕获与多笔分期。
- 若日后接入生产环境，需要先补：webhook 校验、对账定时任务、退款状态机，并另立笔记与本页互链。

## Verification

- `backend/tests/test_api_payment.py`：锁定与审批链接、重复键复用、捕获写快照并只写一次、金额不符留 `RECONCILING`、响应丢失后核验补写、拒付解锁并允许重试、跨报价键冲突、未确认报价不可支付、客户令牌越权 404。
- 真实沙箱（2026-10-30）：创建订单 `52192821KS579122X` 返回 approve 链接；未批准直接捕获返回 `not_approved` 且报价保持 `PAYMENT_LOCKED`；卖家核验接口返回 `AWAITING_APPROVAL`。

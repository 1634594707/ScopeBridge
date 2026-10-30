# Agent Note: 创建订单结果未知时，报价不会永久卡死

Status: implemented

## Problem

支付创建遇到网络异常时，`PaymentAttempt` 进入 `RECONCILING`，但 PayPal 从未返回 order id。此前的 `reconcile()` 遇到 `not attempt.paypal_order_id` 直接 `return attempt`：接口返回 200、状态不变、报价永远停在 `PAYMENT_LOCKED`，既不能付款也不能重新报价。这是评审里 P0 的问题，属于「异常走不完」。

## Decision

**先重试创建，再允许人工结案；两者都要留痕。**

- `POST /api/payments/{id}/retry-create`（卖家、CSRF）：用与首次创建完全相同的 `PayPal-Request-Id` 再调一次 `create_order`。PayPal 按请求号去重，所以要么拿回原来那笔订单，要么把从未发生的订单真正创建出来。最多 2 次（`retry_count` 落库），超过返回 `409 retry_limit`。
- `POST /api/payments/{id}/close`（卖家、CSRF）：请求体必须带 `note`（≥10 字符，去空白后校验）与 `confirmed_no_order: true`，服务端才会把尝试置为 `ABANDONED`、记录 `resolved_by / resolved_at / resolution_note`，并把报价从 `PAYMENT_LOCKED` 退回 `CONFIRMED`。
- `reconcile()` 在无 order id 时改为返回 `409 no_order_id`，附带 `retry_count`，不再假装成功。
- 只有 `RECONCILING` / `FAILED` 且没有 capture id 的尝试可以结案；已 `PAID` 或已有 capture 的一律拒绝。

## Alternatives considered

1. **直接解锁报价，让客户重新发起**。最强理由：最简单，用户立刻能继续。放弃原因：如果 PayPal 其实建了单、买家随后批准，就会出现一笔未记录的支付；解锁等于把未知当成了未付款。
2. **不设次数上限，无限重试创建**。最强理由：多数超时是瞬时网络问题，重试成功率高，人工介入最少。放弃原因：持续失败意味着网关或凭据有问题，无限重试只会放大延迟与日志噪音，且掩盖系统性故障。
3. **提供「标记为已付款」的人工出口**。最强理由：演示时可以手动把流程走完。放弃原因：没有 PayPal 侧证据就写 `PAID`，会污染订单快照与评测口径；结案只能往「未支付」方向走。
4. **保留原状态并只改前端提示**。最强理由：零后端风险。放弃原因：状态机没有出口，问题只是从「用户看不懂」变成「用户知道卡住了」。

## Consequences

- 收益：创建阶段的所有失败路径都有明确出口；重试与结案都有数据库痕迹，可被评测与审计复核；报价不会无声卡死。
- 代价：重试依赖 PayPal 的请求号去重窗口；窗口失效时可能产生第二笔订单，此时新的 order id 会写入同一尝试（旧订单从未暴露 approve 链接，风险限于沙箱）。
- 已知限制：结案是人工判断，服务端无法独立证明「PayPal 侧没有订单」；因此强制填写依据并在 UI 标明「解锁不会退款，因为没扣款」。
- 若日后接入生产，应补 webhook 对账，把这类结案降级为兜底手段。

## Verification

- `backend/tests/test_api_payment.py`：无 order id 时核验返回 `409 no_order_id`；重试创建恢复到 `AWAITING_APPROVAL`（`retry_count=1`）；重试两次后 `409 retry_limit`；结案缺确认或说明被 `422` 拒绝；结案后尝试为 `ABANDONED` 且报价回到 `CONFIRMED`；已有 order id 时重试被 `409 order_already_exists` 拒绝。
- 迁移 `b9318d6cb37a`：`retry_count` 带 `server_default '0'`，新增 `resolved_by / resolved_at / resolution_note`，外键 `fk_payment_attempts_resolved_by_users`（可回滚）。
- 安全复核（STRIDE，`senior-security`）：新端点均要求卖家会话 + CSRF，且通过 `requirement.seller_id` 校验归属（越权返回 404）；结案需显式确认与书面依据，并写入 `resolved_by / resolved_at / resolution_note`（Repudiation）；重试次数上限 2（DoS）；响应只返回 PayPal order/capture id，不含 token。密钥扫描 19 条命中全部是 `pnpm-lock.yaml` 与 `skills-lock.json` 中的完整性哈希被 Twilio 规则误报，源码与 `.env` 无命中。

# Agent Note: 补齐估算器与待处理支付接口，并在支付完成时关闭简报

Status: implemented

## Problem

价目页的 `ScopeEstimator` 和控制台的 `AttentionPanel` 已按接口契约定好，但后端没有
`POST /api/service-rules/estimate` 和 `GET /api/payments/attention`，两个界面只能经
`EndpointNotice` 显示 "not available on this server yet"。同时后端只写
`requirement.status = OPEN`，客户简报页的 `Closed` 筛选永远为空。

## Decision

### 范围估算器

- 公开接口，不要求会话：`POST /api/service-rules/estimate`。
- 请求只有 `{pages: 1..20, addon_codes: string[]}`；`extra="forbid"`，任何金额字段都会
  得到 `422 validation_error`，报价请求体没有携带金额的通道。
- 定价只走规则层：`get_active_rules` → `to_rule_set` → `evaluate`。预算和交期不传，
  `evaluate` 把它们记进 `missing_fields` 而不是 violations，因此响应只包含范围违规。
- 响应是 `{rule_version, currency, total_minor, items[], violations[]}`；未知 add-on
  不产生条目，只产生一条 `unknown_addon` violation，金额仍按可识别部分计算。

### 待处理支付

- 卖家接口：`GET /api/payments/attention`，`require_seller`。
- 一条 join 查询（`payment_attempts ⋈ requirements ⋈ quote_versions`），按
  `updated_at` 倒序，避免按简报逐条请求的 N+1。
- 每行是 `PaymentOut` 的全部字段，再加 `client_name`、`client_business`、
  `quote_number`。
- 只列 `RECONCILING` / `FAILED`，并且所属报价尚未 `PAID`。报价已支付后，旧失败尝试
  既不能被 `close`（返回 409 `already_paid`）也不能解锁，留在列表里无法处理；它的
  记录仍在简报的支付历史里。

### 简报关闭

- 订单快照写入的同一事务里把 `requirement.status` 置为 `CLOSED`（`payments.service._finalize`）。
  `Closed` 的产品含义是“已收款完成”，所以只有成功捕获会触发。
- 手工关闭支付尝试（`ABANDONED`）不关闭简报：报价回到 `CONFIRMED`，客户可以重试，
  简报仍是 `OPEN`。

## Alternatives considered

- **估算器在前端按公开价目表加总。** 最强理由：不等后端，首个版本立即可用。否决：
  金额只能出自 `app/rules/`，前端加总等于第二套定价实现，规则一变两边就会分叉。详见
  [前端落地页与控制台工具](2026-10-31-frontend-landing-and-desk-tools.md)。
- **关注列表由前端逐简报调 `GET /requirements/{id}/payments` 再过滤。** 最强理由：现有
  接口就够，零后端工作。否决：N 条简报需要 N+1 个请求，任一条失败都会少行却看起来完整。
  同样见上一笔记。
- **新增卖家手动关闭简报的接口和按钮。** 最强理由：没有支付的死单也能归档，`Closed`
  不必等于已付款。否决：当前没有任何前端入口，增加的就是无调用方的 API 表面；先把
  “完成”定义为收到钱，等真实出现“未付款结案”需求再补。
- **关注列表严格只按状态过滤。** 最强理由：与请求文字完全一致，实现最短。否决：测试已
  证明会产生无法处理的旧 `FAILED` 行（报价 `PAID` 后 `close` 返回 409），因此追加
  “所属报价未 `PAID`”。
- **把预算/交期也传给 `evaluate` 以复用可行性判断。** 否决：估算器本来就没有这两个
  输入，估算回答的是“这个范围多少钱”，不是“这份简报能不能做”。

## Consequences

- 收益：两个界面在真实会话下可用；所有金额仍只由规则层产生；关注列表一次查询且只给
  可处理项；支付完成后 `Closed` 筛选有真实数据。
- 代价与边界：估算器不判断预算和交期；手工关闭支付不等同于关闭简报；`FAILED` 但报价
  已支付的旧尝试不再出现在关注列表，只能到简报支付历史里查看。
- 未增加：手动关闭简报的接口或 UI。

## Verification

- 2026-10-31 于 `backend/`：`uv run pytest -q` → `95 passed`。
- 2026-10-31 于 `backend/`：`uv run ruff check .` → `All checks passed!`。
- 新增测试：估算器 5 条（含新规则版本、未知 add-on、金额/页数校验、公开访问），
  关注列表 2 条（状态进出与权限、卖家隔离），支付完成关闭简报 1 条。
- 2026-10-31 浏览器验证（`vite preview` + 真实会话；API 跑在 `scopebridge_test`，
  只有 PayPal 传输用本地假实现）：
  - 公开价目页：2 页 + copywriting → 三条 `rule_ref`、合计 `$750.00`，无“不可用”提示。
  - 卖家控制台：create 超时后列表出现 `RECONCILING`（`create_unknown` / `VERIFYING`）；
    重试 create 后移出；capture 被拒后以 `FAILED`（`capture_INSTRUMENT_DECLINED`）
    回到列表；点击行跳转到对应简报；手工关闭后列表清空。
  - 客户简报页：完成支付后该简报为 `CLOSED`，Open 1 / Closed 1，`Closed` 筛选
    只显示该简报。
  - 截图：`C:\Users\Administrator\.qoder-cn\tmp\sb-browser-verify\` 下 4 张
    （估算器、RECONCILING、FAILED、Closed 筛选）。
  - 演示库未被写入（只用了 `scopebridge_test`，验证后已清空）；临时服务已停止。

# Agent Note: 已付简报不再显示删除入口

Status: implemented

## Problem

控制台每一行都渲染垃圾桶图标，包括已经有订单快照的简报。快照是回执，`delete_for_seller`
会返回 `409 payment_completed`，于是用户点一个必然失败的按钮才知道不能删。历史已付简报
还可能停留在 `OPEN`（本次关闭逻辑上线前支付的），只看 `status` 判断并不可靠。

## Decision

- 删除判据保持唯一：订单快照存在即不可删，与 `delete_for_seller` 的检查同源。
- 卖家列表 `GET /api/requirements` 改用 `SellerRequirementSummary`，多一个 `deletable`
  字段；`receipt_requirement_ids` 用一次 `IN` 查询批量取回有快照的简报，不做 N+1。
- 前端 `ConsolePage` 只在 `brief.deletable !== false` 时渲染 `DeleteControl`；客户端列表
  仍返回普通的 `RequirementSummary`，不暴露该字段。
- 不删除、不回填任何简报；历史已付简报的状态保持原样。

## Alternatives considered

- **按 `status === "CLOSED"` 在前端隐藏。** 最强理由：不用改后端契约。否决：历史已付
  简报仍是 `OPEN`，会漏掉；而且 `CLOSED` 是结果状态，不是“有没有回执”本身。
- **保留按钮，点击后禁用或给出提示。** 最强理由：仍能看到删除能力。否决：必然失败的
  入口本身就是噪音，用户已明确要求不再显示。
- **前端逐条请求订单接口再判断。** 否决：N+1，且任一请求失败都会让列表少信息。

## Consequences

- 收益：已付简报的删除入口消失；判据与后端删除规则同源；卖家列表只多一次批量查询。
- 代价：卖家列表响应多一个字段；未付款但已关闭的简报仍可删除（符合当前删除规则）。
- 未改：删除接口本身、客户端列表、历史数据。

## Verification

- 2026-10-31 于 `backend/`：`uv run pytest -q` → `96 passed`；`uv run ruff check .` →
  `All checks passed!`。
- 新增测试 `test_seller_list_marks_paid_briefs_as_not_deletable`：同一份简报支付前
  `deletable: true`，支付后 `deletable: false`；客户端列表不含该字段。
- 运行实例（演示库，未经修改）实测 `GET /api/requirements` 返回
  `[true, true, false]`，第三行是改动前已付的简报。
- 浏览器截图：`C:\Users\Administrator\.qoder-cn\tmp\sb-browser-verify\live-console-after.png`，
  第三行已付回执的垃圾桶图标消失，前两行仍在。

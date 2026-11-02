# Agent Note: 演示脚本与验收口径只写当前代码真能走通的路径

Status: implemented

## Problem

审查发现演示材料与实际代码不一致：

- `DEMO_SCRIPT.md` Path B 写“Retry create 成功后按 Close”。retry 成功后状态是
  `AWAITING_APPROVAL`，前端/后端的 Close 只接受 `RECONCILING/FAILED`，该步骤无法执行。
- README 写“停 API、按 Confirm again、再按 Verify”。API 停着时请求到不了服务端；若在
  `CAPTURING` 已提交后被杀，UI 只有 `RECONCILING` 才显示 Verify，且 `VERIFYING` 不是后端状态。
- README/DEVELOPMENT 把 M5 标为 done，同时注明真实用户试用未做；`FORMAL_PROPOSAL.md` §13
  要求 Playwright，但仓库没有 Playwright/E2E。

## Decision

**演示路径按当前状态机重写；验收口径按实际完成度标注。**

- Path B 改用可复现的 `PAYPAL_TIMEOUT_SECONDS=0.05` 诱导 create 超时：attempt 进入
  `RECONCILING`/`create_unknown`；恢复超时并重启 API 后按 **Retry create**，同一
  `PayPal-Request-Id` 返回订单；随后买家批准、capture、`PAID`/`CLOSED`。Close 是独立可选路径，
  不在同一次 take 里演示。
- README 恢复段改用同一机制，不再写“停 API 后 Verify”；`RECONCILING` 明确标注 UI 显示为
  **Verifying**。
- `M5` 状态改为 “code complete; real user trial not run”；`M6` 保持 pending；
  `FORMAL_PROPOSAL.md` §13 改为 “Playwright is not implemented; browser flow is manual”，并加
  2026-11-02 实现状态说明。没有编造试用记录或日期。
- README 的“故障注入”截图说明改为“本地 fake adapter”，并说明提交构建没有 fault switch。

## Alternatives considered

1. **给代码加一个 demo 专用故障注入开关**。最强理由：脚本最顺，能精确复现 `create_unknown`。
   否决：生产代码里多一条可伪造支付失败的分支，违反单一主路径；用 `PAYPAL_TIMEOUT_SECONDS`
   已经能真实触发超时，不需要假开关。
2. **保留原 Path B，只在文字上说明“先不要 Close”**。最强理由：改动最小。否决：脚本仍要求
   一个 UI 不允许的动作，录制者会在现场卡住；必须删掉错误步骤。
3. **补一个完整 Playwright 套件**。最强理由：最接近正式提案的验收。否决：当前环境没有可运行
   的浏览器依赖，补了也不能验证；先用 API 测试 + 手工脚本，并把未实现写清楚，避免“声称已验证”。
4. **把 M5 直接写成 done，靠“用户试用”另行补**。最强理由：里程碑好看。否决：这是伪造验收
   状态；README/DEVELOPMENT 明确写“未做”，P0-1 只做口径纠正。

## Consequences

- **收益**：演示路径与代码状态一致，录制时不会遇到“按 Close 没按钮”；评审看到的 M5/M6 状态
  是真实的。
- **代价与已知上限**：Path B 需要重启 API 并等待超时配置生效；Path C 是独立 take。M6、真实
  用户试用、Playwright 仍未完成，不能用本 note 代替它们。

## Verification

- `docs/DEMO_SCRIPT.md` Path B 与 README 恢复段已按上述状态重写；`FORMAL_PROPOSAL.md` §13 已
  改为实际范围。
- 阶段二功能清单会继续把“真实用户试用、M6 视频/复现、E2E”列为未完成项。

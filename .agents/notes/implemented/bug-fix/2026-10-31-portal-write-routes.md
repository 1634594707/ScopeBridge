# Agent Note: 客户门户写接口漏了 /requirements

Status: implemented

## Problem

客户门户的 `selectProposal`、`confirmQuote`、`startPayment` 三个前端路径写成了
`/api/portal/{requirement}/...`，而服务端路由是
`/api/portal/requirements/{requirement}/...`。点击“Choose this scope”“Confirm this version”
或“Continue to PayPal”会命中不存在的前端路径，返回 404 `Not Found`，状态机不会前进。

服务端测试直接调用正确路由并通过，所以这个前端契约缺口一直没暴露；录制演示视频时
“Continue to PayPal”出现 `Not Found`，才定位到三处路径。

## Decision

- 三个路径都补上 `/requirements`，与服务端保持一字不差。
- 服务端路由不变；不加旧路径别名（单路径原则，避免两套契约长期漂移）。
- 无前端测试脚手架，回归用 `tsc`/生产构建检查字符串，并在真实浏览器里逐个点击验证。

## Alternatives considered

- **服务端新增 `/api/portal/{id}/...` 别名**：最强理由是不改前端。否决：两套路径会各自
  演化，旧客户端会永久依赖错误契约，违反“一个目标一条主路径”。
- **只修 `startPayment`**：录制只暴露了它。否决：另外两个按钮有同样的漏段，只修一个会
  留下两个坏入口。
- **先引入前端测试框架**：成本大于本次修复；先用构建产物和浏览器点击回归，等真正需要
  UI 测试时再引入。

## Consequences

- 收益：客户门户的选方案、确认报价、开始支付三个按钮恢复；前端与服务端路径一致。
- 代价：无；服务端契约、权限与状态机未变。
- 未改：服务端路由、支付状态机和数据库。

## Verification

- `pnpm exec tsc -b && pnpm exec vite build` 通过。
- 构建产物中三个路径均为 `/portal/requirements/...`。
- 浏览器重录：三个按钮都到达正确接口，`Continue to PayPal` 创建支付并进入 PayPal，
  不再出现 `Not Found`。

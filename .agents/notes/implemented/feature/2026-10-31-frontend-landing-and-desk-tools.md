# Agent Note: 介绍页扩成完整产品页,控制台加检索工具,两个依赖后端的新界面先上前端

Status: implemented

## Problem

原介绍页只有首屏、三段问题、三步流程和一组 FAQ,讲不清报价状态机、规则定价和 PayPal
核验这三条项目主线;公开页没有页脚和移动端菜单。控制台和客户简报列表只能整表浏览,
简报一多就找不到人。用户要求只改 `frontend/`,可以先做前端功能,后端之后补。

## Decision

**介绍页按产品主线拆成分节组件,控制台加纯前端的检索工具,依赖新接口的界面在接口缺失时显式报缺。**

- 介绍页:`pages/landing/` 下分为 Hero(首屏 + 设计事实条)、Walkthrough(问题 + 五步可点选流程)、
  Lifecycle(报价与支付状态机,含 Verifying / Failed / 手工关闭 / Superseded 分支)、
  Pricing(四方职责 + 实时价目)、Payments(核验流程 + 对账面板样例)、Trust(保证、双角色、
  对比表、FAQ 折叠、收尾 CTA)。`LandingPage` 自己处理 `#section` 滚动,路由不会做这件事。
- 介绍页上的样例金额全部标注 Specimen;实时价目只渲染 `GET /api/service-rules` 的返回值,
  失败时显示 `Price list unavailable` 和错误码,不用占位数字顶替。
- 外壳:匿名访客得到 `PublicTopBar`(分节锚点、登录、Start a brief、移动端菜单)和
  `SiteFooter`;登录角色保留侧栏,加 `ctrl/⌘ K` 跳转面板(`CommandPalette`),只读取该角色
  已有的简报列表接口。
- 检索:`lib/briefFilters.ts` 的筛选状态(搜索、状态、素材、排序)存在 URL 查询参数里,
  控制台和客户简报页共用 `BriefToolbar`;统计卡与截止日徽标只按日期和状态计数,
  永远不对金额求和。CSV 导出的是可见行的服务端原值。
- 依赖后端接口的两个界面:`POST /api/service-rules/estimate`(请求体只有 `pages` 与
  `addon_codes`,没有金额)驱动价目页的 `ScopeEstimator`;`GET /api/payments/attention`
  驱动控制台的 `AttentionPanel`。两者经 `EndpointNotice` 区分"接口不存在"(404/405)
  和真实错误,都不回退成示例数据。后端随后在
  [补齐估算器与待处理支付接口](2026-10-31-estimator-attention-and-brief-closure.md)
  中实现,前端契约未变。

## Alternatives considered

- **估算器在浏览器里按价目表自己加总。** 最强理由:不用等后端,价目表本就公开,首个版本
  马上可用。否决:金额只能出自 `app/rules/`,前端加总等于第二个定价实现,规则一改两边
  就会悄悄分叉,违反"金额唯一来源"。
- **待支付关注列表在前端拼出来:对每条简报调 `GET /requirements/{id}/payments` 再过滤。**
  最强理由:现有接口就够,零后端工作。否决:简报数为 N 时要 N+1 个请求,而且只要有一个
  失败,列表就会少行却看起来完整,这正是被禁止的静默降级。
- **把筛选状态放进组件 state。** 最强理由:实现更短。否决:刷新即丢,也无法把筛好的视图
  发给别人;URL 参数代价很小。

## Consequences

- 收益:介绍页从约 370 行单文件变成 6 个分节,讲清了状态机、定价职责和支付核验;简报多时
  能按名字、状态、素材、截止日快速定位;两个新界面在后端补齐接口后无需再改前端。
- 代价:介绍页的样例数据是硬编码的演示价目,价目规则变化后需要手动同步文案。
- `CLOSED` 筛选现在有真实数据:后端在订单快照写入的同一事务里把简报置为 `CLOSED`,
  见[补齐估算器与待处理支付接口](2026-10-31-estimator-attention-and-brief-closure.md)。

## Verification

- `cd frontend && pnpm exec tsc -b` 通过;`pnpm exec vite build` 通过(2145 modules)。
- 浏览器(`vite preview`,后端未启动):介绍页 8 个分节锚点存在,FAQ 锚点跳转后距视口顶
  约 80px;移动端 375×812 菜单展开、点锚点后自动收起;实时价目显示
  `Price list unavailable · code · network_error`;未知路径渲染 404 页。
- 未验证:控制台、简报页、估算器和关注列表在真实会话下的表现。当时后端未改动;接口随后在
  [补齐估算器与待处理支付接口](2026-10-31-estimator-attention-and-brief-closure.md)
  中补齐并通过后端测试;浏览器端已于 2026-10-31 联调通过(见该笔记 Verification)。

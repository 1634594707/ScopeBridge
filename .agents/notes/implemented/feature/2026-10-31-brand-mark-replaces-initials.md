# Agent Note: 品牌标记改成图形标记，替掉 "SB" 字母缩写

Status: implemented

## Problem

侧栏、顶栏和浏览器标签页一直用松绿方块里的 "SB" 两个字母当标记。这个缩写读起来别扭，也不带任何产品语义：它既没说出「范围被框定」，也没说出「成交线被锁定」。字母标记在非英文语境下还要额外解释，而 ScopeBridge 真正想强调的恰恰是那三件事——规则定价、人工复核、客户确认同一版本。

## Decision

**用图形标记替掉字母缩写，并且交付矢量几何而不是生成位图。**

- 图形语义：四个制图角标＝被框定的工作范围（scope）；一条横贯的成交线＝定价后的那条协议线；线尾一个实心方块＝被锁定、被确认的唯一版本。
- 资产与位置：
  - `frontend/public/favicon.svg`——松绿圆角方块（rx=5）＋纸白反白标记，给浏览器标签页。
  - `frontend/public/logo-mark.svg`——松绿标记、透明底，给 README 等文档直接引用。
  - `frontend/src/components/BrandMark.tsx`——React 组件。`BrandMark` 用 `currentColor` 跟随文字色，`BrandTile` 是松绿方块版本，供 `AppShell` 的侧栏与顶栏使用；落地页首屏的眉标行也换成了 `BrandMark`。
- 几何：一份 48 单位坐标系的路径（角标笔画 5，成交线笔画 3，方块 8×8），统一用 `translate(16 16) scale(0.56) translate(-24 -24)` 缩进 32 单位画布。三处资产共用同一份坐标与缩放，favicon 与界面标记的比例不会漂移。
- 配色沿用既有 token：松绿 `#0F4C45` 与纸白 `#FAFAF8`，`tailwind.config.js` 不需要新增颜色。
- 概念图来源：先用用户提供的 OpenAI 兼容图像端点（`https://new.orbitix.site`，模型 `gpt-image-2.5-flare` 与 `gpt-image-2.5-sunburst`）生成 7 张候选位图取概念（桥拱、拱心石、制图角标、文档加弧线、门洞拱等），再手写成矢量几何交付。端点密钥只经环境变量传入，生成脚本放在系统临时目录，不入库。

## Alternatives considered

1. **直接用生成的一张位图当 logo**。最强理由：省事，视觉上「就是 AI 出的图」。放弃原因：PNG 在 16–32px 会糊，描边粗细不统一，也没法跟随主题色；favicon 场景下位图会被浏览器缩放糊掉。
2. **桥拱 + 拱心石（名字里 Bridge 的直译）**。最强理由：语义最贴产品——拱心石正好对应「唯一被确认的版本撑起整个协议」。放弃原因：大尺寸下读起来像隧道/门洞，拱心石方块像烟囱；缩到 18px 只剩「一个 n 加一个点」，识别度明显弱于角标方案。
3. **保留字母缩写，只换字体和排版**。最强理由：零改动、零风险，favicon 与界面自动一致。放弃原因：用户已明确否定这个缩写，而且字母承载不了「框定范围 / 锁定版本」这条主线。
4. **只改 favicon，界面里继续用 SB**。最强理由：改动面最小。放弃原因：标签页与界面里是两套标记，比不改更像半成品。

## Consequences

- 收益：标记在 16px 仍可辨；favicon、界面方块、独立资产三处比例一致；标记语义与产品主线（规则定价 → 人工复核 → 客户确认）一一对应。
- 代价：新增两个静态资源和一个组件；README 仓库地图补了一行说明品牌资产的位置。
- 已知限制：几何在三个文件里各写一份（`favicon.svg`、`logo-mark.svg`、`BrandMark.tsx`），以后改形状必须三处同步，否则比例会漂移。真要单一来源，需要把 SVG 以 `?raw` 方式引入构建产物，本次没做。
- 候选位图没有入库：仓库体量只有 3.9 MB，7 张 PNG 约 7 MB，不值当；生成配方记在本篇里，需要时可复现。

## Verification

- `cd frontend && pnpm exec tsc -b` 与 `pnpm exec vite build` 均通过；构建产物里有 `favicon.svg` 与 `logo-mark.svg`。
- 用无头 Chrome 加载仓库里真实的两个 SVG 文件，在 128 / 32 / 16 / 18px 下渲染核对比例与可读性。
- 静态服务 `frontend/dist` 后截图真实落地页页头，确认顶栏方块标记与眉标行小标记渲染正确。
- `cd backend && uv run pytest -q` 与 `uv run ruff check .` 通过（本次改动不触后端，仍按仓库规则全量跑）。
- 笔记校验：`npx tsx .agents/skills/write-notes-like-deepseek/scripts/verify-agent-note-tree.ts` 与 `verify-agent-note-format.ts` 通过。

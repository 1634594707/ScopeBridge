# Agent Note: M6 复现环境、Path B 数据与提交材料骨架

Status: implemented

## Problem

2026-11-02 的 M6 工作有三个互相牵制的风险：

1. 需要一条“从零到测试全绿”的复现路径，但不能碰 demo 数据卷里那条真实 sandbox 记录
   （order `5UL759133K5843017` / capture `5AR676939L8640110` / 50000）。
2. `DEMO_SCRIPT.md` 的 Path B 需要第二条已确认报价，而现有 seed 只创建一条 demo brief。
3. 提交材料需要 Devpost 字段和必交项清单，但不能编造真实试用、团队信息或视频结果。

## Decision

**用隔离 stack 验证，用隔离数据库准备 Path B，用草稿标记用户自有内容。**

- `scripts/docker-compose.verify.yml` 使用独立 service、端口 55434、数据库
  `scopebridge_verify`；`scripts/verify.ps1` / `verify.sh` 以 compose project
  `scopebridge-verify` 启动，卷名因此是项目级 `scopebridge-verify_scopebridge-verify-pgdata`，
  与 demo 卷分离。脚本只 `up -d`，从不 `down -v`。
- 验证脚本的数据库、账号、模型/PayPal 占位符全部通过进程环境变量覆盖，不写 `.env`；每一步用
  真实退出码判断，失败立即退出，最后打印每步耗时。就绪判断用容器内 `pg_isready`，不是固定 sleep。
- `scripts/prepare-demo-pathb.ps1` 在**同一个 PostgreSQL 服务器的另一个数据库**
  `scopebridge_pathb` 上执行 alembic 和 `python -m app.seed --pathb`；不读写 demo 数据库
  `scopebridge` 的业务行。Path B 录制时用进程级 `DATABASE_URL` 指向该库，不改 `.env`。
- `app.seed --pathb` 创建干净 brief → 一个方案 → 报价 → review → 客户 confirm，重复运行如果
  已存在同客户 brief 就直接打印并退出。
- `docs/DEMO_SCRIPT.md` 扩为逐秒动作、中文旁白/英文字幕、预热页、账号切换、
  `PAYPAL_TIMEOUT_SECONDS` 失败注入与重启顺序；`docs/SUBMISSION_DRAFT.md` 提供中英文 Devpost
  草稿，并把真实试用、团队信息、视频 URL、公开仓库/About 许可证标成 **[USER]**。
- Playwright 仍未实现；材料继续写“手工脚本”。

## 提交合规与资源审计

- `docs/SUBMISSION_COMPLIANCE.md` 按赛方 rubric（PayPal central、AI meaningful、substantive
  progress、text description、functional demo、tools、public repo、video）逐条给出
  满足/部分/未满足/无法本地核实、证据、缺口和 owner。三处用户自有项固定为视频、公开仓库
  About、Devpost 表单；当前工作区未 commit/push 也单列为用户项。
- Functional demo 选择 A（评委按仓库自跑）。无模型/PayPal 凭据时能到 UI、brief、手工定价、
  报价、review、confirm；model 与 payment 分别返回 503 `model_not_configured` /
  `paypal_not_configured`，不会静默降级。B（hosted demo）未部署，部署最小步骤写在合规文档。
- AI 承重被标为 partial/risk：`create_quote` 不要求 `ai_extractions`，手工路径可完全绕过模型。
  建议的最小改动是“当前 revision 必须有事实抽取 + 澄清问题”门禁和“AI 变更摘要”；只写方案，
  未改代码。
- 视频改为单条 2:25 剪切：保留 happy path + 35 秒 recovery，砍掉 landing 动效、完整换座、
  模型等待、长报价滚动和 Path C close；用字幕解释被砍部分。没有录制结果声明。
- 资源审计：应用端使用系统字体（`frontend/tailwind.config.js#L33-L44`）；`lucide-react` ISC，
  React/React Query MIT；没有外部字体/图片/音频 URL。`docs/architecture.html` 内嵌 JetBrains
  Mono WOFF2，并在同文件 `#L36-L129` 保留 SIL OFL 1.1 文本。`docs/thumbnail.png` 的来源没有
  文档记录，标为需用户确认；`recordings/` 是 git-ignored 本地文件，不作为提交视频。
- 跨平台：`scripts/verify.ps1` 实跑；`scripts/verify.sh` 未端到端执行，但在 `bash:5` 容器中
  `bash -n` 通过；`.github/workflows/verify.yml` 已添加但本轮未运行。

## Alternatives considered

1. **复用 demo compose project，只加 `-p` 参数**。最强理由：文件最少。否决：
   `docker-compose.yml` 固定了 `container_name: scopebridge-db`，会与正在运行的 demo 容器冲突；
   独立 compose 文件才能保证不碰 demo。
2. **在 demo 数据库里新建第二条 brief**。最强理由：录制时不用切换 `DATABASE_URL`。否决：用户明确
   要求隔离库，且任何误操作都可能污染真实快照所在的库；独立 `scopebridge_pathb` 更安全。
3. **让验证脚本 `down -v` 清场**。最强理由：真正的从零开始，避免残留。否决：会删除卷，且无法
   保证未来不会误删 demo 卷；脚本只保证项目级隔离，不删除数据。
4. **在提交草稿里先写“已试用/已录制”占位**。最强理由：表单看起来完整。否决：这是编造；草稿把
   用户自有项明确标出，不替用户填。
5. **选 hosted demo B 作为唯一功能演示**。最强理由：评委无需本地环境，点开就能用。否决：需要
   公网 HTTPS、数据库、sandbox/模型凭据、公开注册治理和持续成本；本轮不允许部署，且 A 已能覆盖
   手工报价/确认路径，B 只作为可选后续。
6. **强制模型抽取后才能报价，彻底消除 AI 绕过**。最强理由：最符合“AI meaningful”。否决：会破坏
   无模型凭据时的手工路径，且当前产品承诺 manual path 可用；先提议“澄清门禁 + 人工澄清记录”，
   而不是直接砍掉 fallback。
7. **把 Path A 和 Path B 各录一条视频提交**。最强理由：每条都完整。否决：赛方要求单条 <3 分钟；
   2:40 + 1:30 会超时；改为单条 2:25 剪切，用字幕解释被砍的 Close 路径。

## Consequences

- **收益**：A 脚本最新一次从启动数据库（复用 stack）到 `vite build` 共 30.4 秒（含
  `uv sync`/`pnpm install`），109 个测试通过；Path B 数据在 `scopebridge_pathb` 中为 `OPEN`
  brief + `CONFIRMED` v1 quote；demo 快照保持 `5UL759133K5843017` /
  `5AR676939L8640110` / 50000 不变。
- **代价与已知上限**：验证 stack 留在 55434 端口，需要手动 `stop`；Path B 录制需要切换 API 的
  `DATABASE_URL` 并重启；真实试用、视频、Playwright 仍由用户完成。`seed --pathb` 只幂等检查
  “同客户是否已有 brief”，如果上一次中途失败留下半成品，需要人工清理 pathb 库。AI 承重风险没有
  在本轮修复；视频、公开仓库/About、Devpost 表单和真实试用仍是用户项。

## Verification

- `scripts/verify.ps1` 实跑：加上 `uv sync` / `pnpm install` 后，同一隔离 stack 最新一次
  30.4s；更早的 cold run（尚未加依赖步骤）40.8s；两次都是 `109 passed`。每步耗时见
  `docs/M6_RUNBOOK.md`。
- `scripts/prepare-demo-pathb.ps1` 实跑：`scopebridge_pathb` 中 requirement
  `ee60127e-e1b8-4a89-a796-62e47cdabc89`（`OPEN`）、quote v1 `CONFIRMED`、total 50000；再次运行
  打印已存在，不重复创建。
- demo 库只读查询仍为 requirement `CLOSED`、quote `PAID`、attempt `COMPLETED`、snapshot
  `5UL759133K5843017` / `5AR676939L8640110` / 50000。

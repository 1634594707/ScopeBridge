# 工作区 Agent 规则（ScopeBridge）

ScopeBridge 是受约束的服务成交助手：模型可以提议，但价格只由规则层产生，方案只由程序裁决，付款只由客户端确认。以下规则服务于这个目标，所有会话必须遵守。

## 一、决策笔记（Agent Notes）

重要改动必须留笔记，笔记放在 `.agents/notes/`，遵循 `write-notes-like-deepseek` skill 的规范（状态即目录：proposed / implemented / rejected / archived；六类：feature、bug-fix、simplification、architecture、process、testing）。

1. **动手前判断是否非平凡改动**：改了行为、架构、跨文件契约、流程与工具链、测试策略、落盘/网络/配置格式，任一命中即必须写笔记；纯机械改动（格式化、重命名、样式）严禁立笔记。
2. **写新笔记前先检索同主题旧笔记**：已有归属的改动就地更新那篇，不新开；被完全吸收的旧提案当场归档或删除。
3. **被放弃的方案必须写，且先写它最强的理由**，再解释为什么不用。
4. **提交前跑笔记校验**：

   ```bash
   npx tsx .agents/skills/write-notes-like-deepseek/scripts/verify-agent-note-tree.ts
   npx tsx .agents/skills/write-notes-like-deepseek/scripts/verify-agent-note-format.ts
   ```

## 二、技术决策查证（SDFrame）

涉及架构选型、设计模式、测试策略、部署方式等技术决策时，先查 SDFrame（<https://sdframe.caldis.me/>，免认证静态 API）再下结论：

- 索引：`https://sdframe.caldis.me/api/frameworks.index.json`
- 详情：`https://sdframe.caldis.me/api/frameworks/{slug}.json`（取详情前先用索引校验 slug）
- 依据候选框架的「适用/不适用场景」和 Do's/Don'ts 判断，不凭印象

## 三、工程铁律（本项目具体化）

- **单路径，无 fallback**：一个目标只保留一条主路径，禁止为「失败时看起来正常」而写静默降级；失败要 Fail-Fast 并向上抛出明确原因。
- **金额只有一个来源**：`app/rules/` 是唯一能定价的地方。模型输出无论包含什么数字，都不得进入报价；客户端请求体不得携带金额。
- **响应体不得泄漏**：错误响应只含 `{code, message, details?}`，不得出现 token、session、UID、IP、文件路径与异常原文。
- **外部结果不明一律进 RECONCILING**：不得把「未确认」当成成功或失败；只有服务端核验过的状态才能解锁报价或写快照。
- **凭据只在 `.env`**：沙箱与模型凭据不得入库，`.env.example` 只留占位符。

## 四、验证与汇报

- 提交前跑：`uv run pytest -q`、`uv run ruff check .`、`pnpm exec tsc -b`、`pnpm exec vite build`。
- 完成报告必须区分**已验证**（附上实际命令与结果）、**未验证**与**阻塞项**，不得把计划中的能力说成已实现。
- 引用评测数字时必须带报告文件路径与运行时间，不得外推为通用「模型准确率」。

## 五、技能与文档

- `.agents/skills/` 下的技能为辅助工具，不能覆盖用户授权边界与上条铁律。
- 技能名称出现在文档里不代表当前宿主已加载；缺少技能或检查工具必须报告，不能宣称执行成功。
- 项目文档索引见 `docs/README.md`。

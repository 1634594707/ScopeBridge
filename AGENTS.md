# 工作区 Agent 规则

本工作区的开发流程以 [全栈开发流程.md](全栈开发流程.md) 为完整版、[全栈开发流程-个人精简版.md](全栈开发流程-个人精简版.md) 为日常版。以下是所有会话必须遵守的硬规则。

## 决策笔记(Agent Notes)规则

重要改动必须留笔记,笔记放在 `.agents/notes/`,遵循 `write-notes-like-deepseek` skill 的规范(状态即目录:proposed / implemented / rejected / archived;六类:feature、bug-fix、simplification、architecture、process、testing)。

1. **动手前先判断是否非平凡改动**:改了行为、架构、跨文件契约、流程与工具链、测试策略、落盘/网络/配置格式,任一命中即必须写笔记;纯机械改动(格式化、重命名、样式、CRUD)严禁立笔记。
2. **写新笔记前先检索同主题旧笔记**(proposed + implemented + rejected):已有归属的改动就地更新那篇,不新开;被完全吸收的旧提案当场归档或删除。
3. **被放弃的方案必须写,且先写它最强的理由**,再解释为什么不用。
4. **提交前跑笔记校验**:
   ```bash
   npx tsx .agents/skills/write-notes-like-deepseek/scripts/verify-agent-note-tree.ts
   npx tsx .agents/skills/write-notes-like-deepseek/scripts/verify-agent-note-format.ts
   ```

## 决策查证(SDFrame)规则

涉及架构选型、设计模式、测试策略、部署方式、团队协作模式等技术决策时,先查 SDFrame(https://sdframe.caldis.me/,免认证静态 API)再下结论:

- 索引:`https://sdframe.caldis.me/api/frameworks.index.json`
- 详情:`https://sdframe.caldis.me/api/frameworks/{slug}.json`(取详情前先用索引校验 slug)
- 对比候选框架时,依据其「适用/不适用场景」和 Do's/Don'ts 字段,而不是凭印象

## 前端产出质量(Hallmark)规则

新页面、落地页、作品集类前端产出使用 `/hallmark` 流程;已有页面的重设计用 `/hallmark redesign`,严禁在未审计的情况下直接重写。上线前页面必须过 sloplint 检查(对比度、移动端布局、空链接/死表单等底线问题)。

## 个人铁律

历史沉淀的 fallback 清理铁律、单路径边界规则等,见 [工程铁律与协作规则.md](工程铁律与协作规则.md),涉及相关任务时先读它。

## 执行与技能维护

- 按精简版「按影响范围执行」选择流程；机械修改不强制走完整立项流程。
- 同一任务只选一套主流程技能；外部技能不能覆盖用户授权边界和项目硬规则。
- 安装或更新前检查来源、维护状态、许可证、正文及附带脚本；记录获取日期和提交/版本，备份现有目录与锁文件，再定向更新和验证。
- skill 名称出现在文档里不代表当前宿主已加载；缺少技能或检查工具必须报告，不能宣称执行成功。
- 完成报告区分已验证、未验证和阻塞项，保留实际命令与结果。

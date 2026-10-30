# 文档索引

给评委与开发者的英文入口是根 [`README.md`](../README.md)。本目录存放中文设计文档、图表、演示脚本与截图。

## 现役文档

| 文件 | 内容 | 状态 |
| --- | --- | --- |
| [`FORMAL_PROPOSAL.md`](FORMAL_PROPOSAL.md) | 正式方案 v3.0：定位、用户、流程、技术选型、接口、状态机、里程碑、评测、参赛交付清单 | 现役（目标与验收标准） |
| [`DEVELOPMENT.md`](DEVELOPMENT.md) | 开发记录：里程碑状态、目录、数据模型、实际 API、状态与恢复、模型契约、评测、与计划的偏差 | 现役（随实现更新） |
| [`DEMO_SCRIPT.md`](DEMO_SCRIPT.md) | 演示脚本：成功路径 ≤2:40、异常恢复路径 ≤1:30、英文字幕与录制注意事项 | 现役 |
| [`architecture.html`](architecture.html) / [`architecture.json`](architecture.json) | 技术架构图（可交互 HTML + 源数据） | 现役 |
| [`workflow.html`](workflow.html) / [`workflow.json`](workflow.json) | 业务流程图 | 现役 |
| [`screenshots/`](screenshots/) | 界面与真实沙箱支付截图，编号 01–18 | 现役 |
| [`archive/`](archive/) | 已失效的历史文档 | 归档 |

## 归档文档

| 文件 | 说明 |
| --- | --- |
| `archive/PROJECT_PLAN-v2.md` | 项目规划 v2.0，已被 FORMAL_PROPOSAL v3.0 取代，仅作开工基线保留 |

图表渲染校验的中间产物（浏览器快照、validation/receipt JSON）与提案审阅截图不入库，仅保留最终图表与源数据。

## 阅读顺序

1. 想快速了解产品与跑起来：根 `README.md`
2. 想看设计与验收：`FORMAL_PROPOSAL.md`
3. 想接手开发：`DEVELOPMENT.md`
4. 想录制演示：`DEMO_SCRIPT.md`
5. 想看决策理由：`.agents/notes/implemented/`（架构、测试、缺陷修复三类笔记）

# Agent Note: 模型只出事实，候选范围与价格由服务端生成

Status: implemented

## Problem

M3 需要让模型参与需求理解，但产品底线是「模型不得决定金额、不得直接生成可付款方案」。当前模型通过 OpenAI 兼容网关 `api.uselunora.com` 调用 `deepseek-v4.1-flash`。实测该网关对 `response_format`（`json_object` 与 `json_schema` strict）不生效：它接受参数但模型仍会输出散文或自带 schema 的 JSON。

若把「提取 + 候选方案 + 依据」压成一次嵌套 JSON 调用，模型的输出形状由它自己决定，程序只能整体接受或整体拒绝，拒绝率过高（实测连续 5 次全部不符合约定 schema）。同时，候选范围的组合（几页、是否加外链、砍掉哪些能力）本质上是定价规则问题，不是语言问题。

## Decision

模型只负责**事实抽取**，端口契约固定为五个键：`pages`、`budget_usd`、`deadline_days`、`assets_ready`、`features`。`extra="forbid"`，任何多余键、类型越界、散文、代码围栏一律整体拒绝（`422 model_output_invalid`），不做猜测性修补。

候选范围由 `app/ai/candidates.py` 的纯函数生成：先按「照原样」报价，不可行且能收窄时再给一个「单页 + 外部点单链接 + 仅保留工作室具备的能力」的选项，至多两个。价格与违规项一律由 `app/rules.evaluate` 计算；模型返回的 `budget_usd` 只作为「模型读到的数字」展示，永不进入报价。

`app/ai/client.complete_json` 是唯一的适配器（ports-and-adapters）：单次请求、无自动重试、超时 60 s，失败以 `502 model_unavailable` 暴露给卖家，由人决定手工定价或重试。每次调用（成功、拒绝、传输错误）都写入 `ai_extractions`，保留模型名、提示词版本、输入消息 ID、原始输出、解析结果、错误码与耗时，作为评测证据。

提示词固定为 `facts-v6`，并遵守两条实测结论：system 提示必须简短、命令式（人格化开场会让 flash 转成散文）；user 消息只放纯文本简报，不塞 JSON 批量数据（塞 JSON 会让模型去「重排这个 JSON」而不是抽取事实）。纯文本简报 + 五键 schema 实测 5/5 通过，2.1–3.2 s。

## Alternatives considered

1. **一次调用返回嵌套结构（需求字段 + 候选方案 + 依据 ID）**。最强理由：少一次映射，模型还能自带取舍理由，产品叙事更「AI 原生」。放弃原因：实测该网关下 0/5 符合约定 schema，且候选组合本质是规则问题；把规则判断交给语言模型会让「为什么是这个价」无法机械验证。
2. **依赖 `json_schema` strict 强制形状**。最强理由：由服务端约束解码，理论上最可靠。放弃原因：网关接受参数但不执行，模型仍输出自带 schema；记录在案后不再重复尝试。
3. **接受任意 JSON 再按启发式映射键名**。最强理由：能显著提高「看起来成功」的比例。放弃原因：键名映射属于静默纠错，会把模型的臆造当作事实，违反单路径与 Fail-Fast 铁律。
4. **对失败自动重试一次**。最强理由：抽取是只读操作，重试符合幂等前提，可把成功率翻倍。放弃原因：重试会掩盖模型不稳定性（评测报告需要真实失败率），并让单次点击延迟与成本翻倍；改为把失败明确暴露给卖家，由其决定重试或手工定价。

## Consequences

- 收益：金额不可能被模型影响；候选组合可单测；模型换版本时只需保证五键契约不变；每次调用可追溯到提示词版本与原始输出。
- 代价：模型不再贡献「方案叙事」，候选的 `rationale` 是服务端固定文案；`features` 由模型用自由字符串表达（实测出现过 `online_ordering`），需要与能力码不完全一致时才由 `unsupported_requests` 暴露差距。
- 已知限制：该网关下模型仍有小概率返回散文，接口会返回 `422`，前端明确提示「未定价，请手工处理」，不提供兜底解析。
- 若日后更换为真正执行 `json_schema` 的供应商，可重新评估把候选生成交回模型；届时应先补一条新笔记并互链本页。

## Verification

- `backend/tests/test_ai_extraction.py`：服务端两个候选的构造、金额来自规则、散文/多余键/越界页数被拒、证据行落库、最新草稿为空时返回 `{"extraction": null}`。
- 真实网关手测：`facts-v6` 连续 5 次五键通过；UI 中一次完整调用 2.2 s，产出「As briefed $700 / cannot deliver」与「One-page launch, narrowed to fit $500 / deliverable」。

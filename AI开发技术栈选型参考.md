# AI 开发技术栈选型参考

> 一张选型卡,服务《全栈开发流程》阶段 A2(方案选型与决策查证)。语言选型不在 SDFrame 的 317 个设计框架里,这张卡按同样的纪律补位:**先分层、再看证据、按场景拍板,被放弃的方案写下最强理由**。

## 0. 什么时候翻这张卡

命中任意一条:

- 要做一个 MCP server / AI agent CLI / 推理网关 / 模型工具链
- 要给现有系统加 AI 能力,纠结后端用什么语言重写或新建
- 看到社区"Rust 重写一切"的风向,心动但不确定该不该跟
- 新项目定性问:"这种东西该用什么写?"

不适用:纯 CRUD 业务后端、普通 Web 应用——那按团队现有栈走,别为技术新鲜感换语言。

## 1. 核心洞察:先分层,再选语言

"AI 开发用什么语言"是个伪问题——AI 系统是分层的,每一层的主流语言不同。**Go 和 Rust 的主场在基础设施与工具链层,不是应用编排层**:

| 层 | 干什么 | 主流语言(2026 现状) | 为什么 |
|---|---|---|---|
| 模型/训练引擎 | 算子、CUDA 内核、训练框架 | C++ / CUDA / Python 绑定 | 极致性能 + 硬件生态锁死 |
| 推理服务 | 模型 serving、批调度 | **Python** 主导(vLLM、SGLang),性能内核 C++ | 研究生态在 Python |
| 基础设施/工具链 | 容器、CLI、代理、网关、向量库、代码工具 | **Go + Rust** 主场 | 静态二进制、并发、延迟可控 |
| Agent/应用编排 | agent loop、工作流、RAG 应用 | **TS / Python** 主导,Go 快速追上 | 生态与迭代速度 |
| 客户端 | 桌面/Web/移动 | 各端原生 | — |

**结论先行:选 Go/Rust 的正确姿势,是把它们放在基础设施层;硬拿它们写应用编排层,是在逆着生态游泳。**

## 2. 四个候选画像

### Go —— 工程化基础设施default

- **最强理由**:单静态二进制分发、goroutine 并发模型天然适合网络代理/网关、编译快部署简单、从 Java 上手最快(工程化心智最接近,你有 Spring 全景图背景,一两周可写生产代码)
- **AI 生态**:MCP go-sdk 官方 Tier 1(Google 参与);agent 框架 Eino(ByteDance 生产验证,2026 公认最成熟)+ Genkit Go + Google ADK Go + tRPC-Agent-Go;Ollama、Docker、Docker Model Runner 全是 Go
- **天花板**:无 GC 之外的手动内存控制;推理内核做不了(得 FFI 到 C++);运行时体积比 Rust 大

### Rust —— 性能与正确性天花板

- **最强理由**:无 GC 的尾延迟控制、内存安全、单二进制、对 C/C++ 推理引擎(llama.cpp)FFI 一流;AI 编码工具链在集体 Rust 化——OpenAI Codex CLI 就是 Rust(codex-rs),2026 年有报道称 Copilot 运行时也完成 Rust 移植
- **AI 生态**:MCP rust-sdk 官方 Tier 1;Qdrant、LanceDB、Turso、Meilisearch(向量/检索);candle、mistral.rs(推理);HF tokenizers、safetensors(Rust 写的,Python 只是绑定);uv、ruff、turbopack、swc、oxc(JS/Python 工具链的 Rust 底座)
- **天花板**:学习曲线陡(借用检查 1-3 个月才顺手),开发速度慢 2-3 倍,招聘池小——个人项目可学,团队项目慎入

### TypeScript —— 应用编排层default

- **最强理由**:AI 应用层生态最厚(Vercel AI SDK、LangChain.js),前端后端一种语言;Claude Code(TS on Bun)、Gemini CLI 都是 TS,证明性能不是应用层瓶颈;Bun 编译单二进制后分发问题已解决
- **天花板**:数值计算不行,重 CPU 任务只能调外部服务

### Python —— 推理与数据层default

- **最强理由**:推理服务(vLLM/SGLang)和数据处理的事实标准,模型 API 客户端永远第一时间支持
- **天花板**:打包分发是老大难,性能靠 C++/Rust 内核补(uv/ruff 的存在本身说明 Python 工具链正在被 Rust 接管底座)

## 3. 真实世界锚点(选型时引用,不凭印象)

| 产物 | 语言 | 说明 |
|---|---|---|
| OpenAI Codex CLI | Rust | codex-rs,AI agent CLI 的 Rust 旗舰 |
| Claude Code | TS (Bun) | 应用编排层 TS 够用的证明;2026 有 Rust 移植报道 |
| GitHub Copilot 运行时 | Rust | 2026 年报道完成移植 |
| Block Goose | Rust | 开源 AI agent 桌面端 |
| Ollama | Go | 内嵌 llama.cpp(C++)引擎,Go 做壳 |
| Docker / Kubernetes / Podman | Go | 容器基础设施全是 Go |
| Qdrant / LanceDB / Turso | Rust | 向量库/边缘数据库 |
| vLLM / SGLang / litellm | Python | 推理服务与网关事实标准 |
| llama.cpp | C++ | 端侧推理引擎,被 Go/Rust 壳集成 |
| HF tokenizers / safetensors | Rust | Python 生态的性能底座 |
| uv / ruff / turbopack / swc / oxc | Rust | JS/Python 工具链的 Rust 化浪潮 |
| Eino(CloudWeGo) | Go | ByteDance 生产验证的 agent 框架 |
| MCP 官方 SDK | 10 语言 | Go、Rust 均为 Tier 1;Python 最流行 |

**模式总结:Rust 赢在"重写性能敏感的工具链",Go 赢在"云原生基础设施的持续统治",Python 守住推理与数据,TS 守住应用编排。四者不是替代关系,是分层协作。**

## 4. 按场景速查

| 你要做的东西 | 首选 | 备选 | 理由 |
|---|---|---|---|
| MCP server(工具/资源服务) | TS 或 Python(生态最熟) | Go、Rust(都 Tier 1,看团队) | 协议层四种都一等公民,跟团队栈走 |
| AI agent CLI(本地工具) | **Go**(个人)/**Rust**(追求极致) | TS (Bun) | 单二进制 + 本地性能;Go 上手快 |
| 推理网关/代理(转发、限流、路由) | **Go** | Rust | 网络代理是 goroutine 主场(litellm 是 Python 例外,因为要贴推理层) |
| 向量检索/数据库 | 直接用现成的 | — | Qdrant(Rust)、pgvector,别自己造 |
| 端侧推理集成 | 调 llama.cpp / Ollama API | Rust FFI | 别用应用层语言造推理轮子 |
| 企业 Java 后端加 AI | **Java 直连模型 API**,或 Go 写独立 AI 网关 | Python 推理服务 + Java 调用 | 不要为了 AI 重写整个 Spring 系统 |
| 数据管道/清洗 | Python | Rust(polars) | 生态;Rust 只在瓶颈处介入 |
| 给 JS/Python 生态做性能底座 | **Rust** | — | uv/ruff/swc 已验证这条路 |

## 5. 决策问题链(五问定语言)

1. **这东西在 AI 系统的哪一层?** 应用编排 → TS/Python/Go;基础设施/工具链 → Go/Rust;推理/数据 → Python
2. **性能敏感在哪?** 平均吞吐(Go 够)还是尾延迟/内存(Rust 上)
3. **谁维护?** 个人想借 AI 快速出活 → Go;愿意付 1-3 个月学习税 → Rust;团队 → 看现有技能池
4. **要不要贴着 C/C++ 推理引擎?** 要 → Rust FFI 一流;走 API/子进程 → 无所谓
5. **分发形态?** 单二进制 CLI → Go/Rust/Bun;服务端部署 → 都行,看运维栈

## 6. 常见反模式

- **为了"新"把 Spring 业务系统重写成 Go/Rust**——AI 能力加一层网关/服务就行,重写是最高风险选项
- **拿 Rust 写 RAG 应用编排**——生态在 TS/Python,你在逆流;Rust 该去写你要调的那个向量库
- **拿 Go 手写推理引擎**——去 FFI/调 llama.cpp,别造轮子
- **用"大厂在用"当唯一论据**——大厂重写 Codex 是因为它们有无限工程资源;你的约束不同,问题链第 3 问优先
- **一个系统四种语言**——分层允许混布,但每个新语言都要付维护税;两个以内为佳

## 7. 与工作流的衔接

- 本卡是**阶段 A2** 的领域补充卡:走完 A2 的候选对比后,用第 5 节问题链收口
- 选型结论按纪律落 `.agents/notes/`:**备选方案必填,先写被放弃方案的最强理由**(比如选 Go,就先写"Rust 的尾延迟优势"这条最强理由,再写为什么对你不成立)
- SDFrame 相关查证:分层选型可查 `modular-monolith`、`ports-and-adapters`;服务边界查 `microservices-decomposition`;性能权衡查对应质量关注点
- 重型语言决策(影响多个模块)用 `research` 把调查发现沉淀成仓库文档,再用 `handoff` 带进实施会话

## 8. 参考来源

- MCP 官方 SDK 页:https://modelcontextprotocol.io/docs/2026-07-28/sdk (go-sdk、rust-sdk 均 Tier 1)
- Go agent 框架对比(2026-09):Eino / Genkit Go / ADK Go / tRPC-Agent-Go / LangChainGo — https://xavidop.me/genkit/2026-09-21-top-go-genai-frameworks-2026 、https://encore.dev/articles/best-go-framework-for-building-ai-agents 、https://www.cloudwego.io/docs/eino/overview
- AI 工具 Rust 化报道(2026-10):https://levelup.gitconnected.com/copilot-claude-code-and-codex-now-run-on-rust-ai-ported-two-of-them-in-weeks-f3f6fc5451f5
- 查证日期:2026-10-30。语言生态变化快,超过 6 个月未更新请重新查证再引用。

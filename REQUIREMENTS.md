# PayPal AI Hackathon｜参赛要求（中立版）

版本：v0.1｜整理日期：2026-10-30｜来源：官方规则页与活动页实测抓取
用途：只记录**比赛本身**的要求与事实，不含任何产品方向、技术选型或实现建议。

> 产品方向、目标用户、核心链路请由作者自行决定后另写文档。本文件不预设。

---

## 1. 赛事基本信息

| 项 | 值 |
| --- | --- |
| 赛事 | PayPal AI Hackathon |
| 平台 | Devpost |
| 活动页 | https://paypalaihackathon.devpost.com/ |
| 官方规则 | https://paypalaihackathon.devpost.com/rules |
| 报名状态（2026-10-30 复核） | `open`，官方标注剩余 14 天 |
| **提交截止** | **2026-11-13 04:00（北京时间）** = 2026-11-12 20:00 UTC |
| 评审期 | 2026-12-01 ~ 2026-12-15（太平洋时间） |
| 奖池 | $67,500 |
| 报名费 | 无 |

时间倒排参考：距截止约 13.5 天；若按每天 4 小时人工投入，总计约 46 小时。建议在**截止前 48 小时（2026-11-11 04:00）**冻结功能，之后只修 bug、补材料。

---

## 2. 参赛资格（已逐条核实，附原文）

| 项 | 结论 | 规则原文摘录 |
| --- | --- | --- |
| 个人可参赛 | 可以 | "Join individually or as a team, and start something new or meaningfully advance an existing project." |
| 地区限制 | 排除名单不含中国大陆 | "…including, but not limited to, Brazil, Quebec, Russia, Crimea, Cuba, Iran, and North Korea and any other country which is comprehensively sanctioned by the U.S. Treasury's Office of Foreign Assets Control" |
| 年龄 | 需达**居住地**法定成年年龄 | "Individuals who are at least the age of majority where they reside as of the time of entry" |
| 是否要求到场 | 活动页标注 Online；规则未要求到场 | 活动页 location = Online |
| 费用 | 无需购买或付款 | "NO PURCHASE OR PAYMENT NECESSARY TO ENTER OR WIN." |

> 地区一项是基于排除名单的推断，不是主办方逐国确认。若本人同时持有受制裁地区居留或国籍，需重新核对。

---

## 3. 提交的硬性要求

| 项 | 要求 | 原文要点 |
| --- | --- | --- |
| 平台集成 | 必须集成 **PayPal 开发者平台（免费沙箱环境）**，并搭配 AI 工具/模型/平台 | "…integrates the PayPal developer platform (using the free sandbox environment) along with an AI tool, model, or platform of their choice" |
| 项目来源 | 新建项目，或赛期内对已有项目**实质推进** | "…must make meaningful progress on the project during the course of the hackathon" |
| 代码仓库 | 公开仓库，GitHub / Bitbucket / GitLab 任一 | "Provide a URL to your public code repository for judging and testing on GitHub, Bitbucket, or Gitlab." |
| 许可证 | **LICENSE 文件必须在仓库 About 区顶部可见** | "Must be public and open source, with a license file visible at the top of the repo (in the About section)." |
| 可运行演示 | 评委必须能**真正运行或交互**；不要求公网部署 | "judges must be able to actually run or interact with a working build"；可通过"清晰完整的安装与运行说明让评委自行构建运行"满足 |
| 演示视频 | **少于 3 分钟**，超时部分评委无义务观看 | "should be less than three (3) minutes. Judges are not required to watch beyond three minutes" |
| 原创性 | 须为本人原创；使用开源依赖需遵守其许可证并形成增强 | "…must be your original work product… complies with applicable open source licenses" |

---

## 4. 评审标准（四条，**等权**）

| # | 标准 | 官方描述要点 |
| --- | --- | --- |
| 1 | **技术实现** | 是否充分、熟练使用 PayPal 开发者平台与 AI 工具；是否真实工作量、可运行、非平凡；是否形成**完整连贯的产品体验**而非技术验证 |
| 2 | **潜在影响** | 是否针对真实人群解决真实问题，且**演示出来的东西确实解决了它** |
| 3 | **创新性** | 概念是否新颖，是否区别于现有方案 |
| 4 | **演示** | 视频是否端到端展示可用；是否讲清"解决什么问题、给谁用、为什么重要"；是否易懂 |

平票规则：按上表顺序逐条比较得分。

---

## 5. 技术事实（2026-10-30 本机实测）

沙箱接口与调用顺序已验证可用，可作为方案设计的既定前提：

| 步骤 | 接口 | 实测结果 |
| --- | --- | --- |
| 取访问令牌 | `POST /v1/oauth2/token`（client_credentials） | 200 |
| 创建订单 | `POST /v2/checkout/orders`（intent=CAPTURE） | 201，返回 approve 链接 |
| 捕获付款 | `POST /v2/checkout/orders/{id}/capture` | 201，`state=COMPLETED` |
| 查询订单 | `GET /v2/checkout/orders/{id}` | 200 |

- 沙箱基址：`https://api-m.sandbox.paypal.com`
- 实测凭据：order `1CM93622D0961861W` → capture `6A196125P4397030M`，10.00 USD
- 凭据获取：https://developer.paypal.com → Apps & Credentials → **Sandbox** → 创建应用
- 沙箱买家账号：同站 **Sandbox Accounts** 列表里类型为 Personal 的账号（邮箱 + 系统生成密码）
- 公开测试卡（官方文档公开数据）：如 `4032033480253520`，有效期取任意未来月/年，CVV 任意三位

---

## 6. 安全底线（提交前必须满足）

1. **Client ID / Secret 不得进入仓库**：仓库是公开的，凭据必须走环境变量或本地 `.env`（已 gitignore）。
2. **只用沙箱**：真实收款/生产环境属于需要明确授权的动作，不在比赛必需范围内。
3. **不采集真实卡号**：演示数据必须脱敏。
4. 提交材料里不得出现无依据的声明（性能、用户量、AI 使用范围）。

---

## 7. 待作者决定（本文件不预填）

- [ ] 产品方向与目标用户
- [ ] 核心链路（用户从进入到看到结果的那一条主线）
- [ ] 演示形态：评委本地运行 / 公网可访问 demo（后者属于公开部署，需授权）
- [ ] 视频语言：中文 + 英文字幕 / 纯英文
- [ ] 许可证类型

---

## 8. 提交材料对照表

| 材料 | 对应哪条要求 |
| --- | --- |
| 公开仓库 + `LICENSE`（About 顶部可见） | 第 3 节 |
| `README.md`：安装与运行说明 | "评委能真正运行"（可用说明满足） |
| 演示视频（≤3 分钟，公开链接） | 第 3 节 |
| 项目简介与截图 | Devpost 提交表单字段 |
| AI 与第三方内容说明 | 原创性与披露要求 |
| 沙箱运行说明 / 测试账号指引 | 便于评委复现支付流程 |

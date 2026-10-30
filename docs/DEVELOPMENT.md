# ScopeBridge 开发清单与接口约定

v2.0 · 与 PROJECT_PLAN.md 配套 · 以下为计划接口，不是现有 API

## 目录与环境

建议目录为 frontend/src、backend/app、backend/tests、evals、docs。backend/app 下按 requirements、proposals、quotes、payments 划分业务文件，不提前拆分服务。开始开发时选择兼容的稳定依赖并提交锁文件，不使用未核验的 latest 版本号。

环境模板包括 DATABASE_URL、MODEL_API_KEY、MODEL_NAME、PAYPAL_CLIENT_ID、PAYPAL_CLIENT_SECRET、PAYPAL_BASE_URL、APP_BASE_URL、SESSION_SECRET。沙箱基址固定在服务端允许列表中。依赖启动指令在脚手架完成后写入根 README，本文不提供尚不存在的启动命令。

## 最小数据契约

| 实体 | 核心字段与约束 |
|---|---|
| ServiceRuleVersion | 不可变规则 JSON、币种、价格、服务能力、工期条件 |
| Requirement 与 Message | 归属、原始消息、预算、日期、素材条件、修订号 |
| Proposal | 需求修订号、规则版本、包含项、排除项、取舍、校验结果 |
| QuoteVersion 与 QuoteItem | 版本、金额、消息及规则引用、审核与确认时间、状态 |
| PaymentAttempt | 报价 ID、操作请求标识、PayPal order ID、capture ID、状态 |
| OrderSnapshot | 已支付报价快照、支付关联、创建时间；每笔成功支付唯一 |

模型输出为 requirement_fields、missing_questions、candidate_scopes、source_message_ids。价格字段即使存在也不作为业务金额。验证器返回 feasible、violations、computed_items、total_minor、currency。未知规则、虚构来源、负数数量、非法币种或缺少条件均拒绝放行。

## API 草案

| 方法与路径 | 作用与权限 |
|---|---|
| POST /api/session | 服务者登录；限制尝试次数 |
| GET /api/service-rules | 读取可报价规则 |
| POST /api/requirements | 建立客户需求和受限访问权限 |
| POST /api/requirements/{id}/messages | 添加原文，携带 expected_revision |
| POST /api/requirements/{id}/proposals | 生成并验证最多两方案 |
| POST /api/requirements/{id}/quotes | 从可行方案生成报价草稿 |
| POST /api/quotes/{id}/review | 仅服务者，审核当前版本 |
| POST /api/quotes/{id}/confirm | 客户确认已审核且未过期版本 |
| POST /api/quotes/{id}/payment-attempts | 锁定确认版本，创建或返回已有支付 |
| POST /api/payments/{id}/capture | 校验归属及报价状态后执行捕获 |
| POST /api/payments/{id}/reconcile | 查询原支付并更新本地状态 |
| GET /api/orders/{id} | 读取授权范围内订单和快照 |

支付写操作携带 Idempotency-Key；同键不同请求体返回冲突。后端将业务键持久化映射到 PayPal 请求标识，创建与捕获分别保存。并发修改使用 expected_revision，冲突返回 409。未认证返回 401，无资源权限返回 403，输入不合法返回 422。外部结果未知返回可恢复的处理中状态，前端不得当作已支付。Cookie 会话写操作增加 CSRF 防护。

## 状态与恢复

报价：DRAFT → REVIEWED → CONFIRMED → PAYMENT_LOCKED → PAID。审核修改产生新草稿；开始支付前的变更使旧版本 SUPERSEDED。PAYMENT_LOCKED 只有在服务端核实没有成功支付且旧操作不能继续执行后才解锁；无法判断时保留锁定供核验。

支付：CREATING → AWAITING_APPROVAL → CAPTURING → COMPLETED。任何外部操作结果不明进入 RECONCILING；查询已完成则写订单，明确待批准则恢复批准流程，明确失败才进入 FAILED。客户端 cancel 记录为交互事件，不直接解除支付锁。

同一报价最多一个活动支付尝试，PayPal order ID 与 capture ID 分别唯一；COMPLETED 和订单快照在同一事务保存。数据库异常发生在外部扣款之后时，下次核验能补写本地记录。已完成状态不可被较旧查询结果覆盖。

## 开发顺序与完成定义

- [ ] M0：完成五个样例、服务规则、仓库结构、环境模板和健康检查。验收：前后端连通数据库，密钥未被 Git 跟踪。
- [ ] M1：实现纯函数价格与可行性验证器。验收：三页为 70000 美分，50000 预算不放行，单页外链与站内点单明确区分。
- [ ] M2：实现手动草稿、审核、确认、归属权限和版本冲突。验收：未经审核、越权或旧版本无法确认。
- [ ] M3：接模型提取、候选方案和依据映射。验收：无效输出不进入付款，每项引用可追溯；无解可人工处理。
- [ ] M4：实现真实沙箱创建、捕获与恢复。验收：重复请求、客户端取消、捕获响应丢失、数据库补写分别覆盖。
- [ ] M5：完成对比、差异、订单页面，跑 20 案例评测并开展用户试用。
- [ ] M6：干净环境复现、视频、许可证与提交材料。验收：所有对外指标均能对应测试记录。

每个里程碑完成后记录变更、已验证事项及未完成项；失败先修复再进入下一阶段。当前里程碑均未完成。

# Agent Note: 卖家会话与客户令牌走两条互不复用的身份路径，并按 STRIDE 固化边界

Status: implemented

## Problem

一个页面同时服务两类人：服务者要管理全部需求，客户只应看到自己被授权的那一份。若用同一个中间件「兼容」两种身份，权限判断里必然出现隐式分支，任何一处遗漏都会变成越权读取报价或替别人确认。

## Decision

两条路径物理分离，不共用中间件：

- **服务者**：`POST /api/session` 口令登录（Argon2id 校验），服务端 `seller_sessions` 存令牌的 SHA-256 摘要与 CSRF 令牌，浏览器只拿 HttpOnly + SameSite=Lax Cookie；所有写操作经 `require_csrf` 校验 `X-CSRF-Token`。登录失败按邮箱 15 分钟内 5 次限流，超限返回 429。
- **客户**：`POST /api/requirements` 时生成 32 字节随机令牌，库中只存 SHA-256 摘要，且与单一 requirement 绑定；客户端通过 `X-Customer-Token` 请求头携带，令牌不出现在任何 API 路径里。
- **统一错误体** `{code, message, details?}`，不返回异常原文、SQL、路径或令牌片段；数据库不可用统一 503；越权一律 403，不存在一律 404，不泄露资源是否存在。
- **响应头**：`X-Content-Type-Options: nosniff`、`X-Frame-Options: DENY`、`Referrer-Policy: no-referrer`、`Cache-Control: no-store`。

STRIDE 落地对照：

| 类别 | 场景 | 现状 |
| --- | --- | --- |
| Spoofing | 口令撞库 | Argon2id + 失败限流 5/15min + 恒定时间比较；无 MFA（演示接受） |
| Tampering | 前端改金额 | 金额只由服务端 `price_scope` 计算，客户端只提交范围；报价版本创建后不可改，改版新建 `quote_number` |
| Tampering | 并发覆盖 | `expected_revision` CAS，冲突 409 |
| Repudiation | 事后否认 | 消息带作者与修订号，报价带 `reviewed_by/reviewed_at/confirmed_at`；无独立审计表（演示接受） |
| Information disclosure | 客户令牌泄露 | 只存摘要、绑定单一需求、`Referrer-Policy: no-referrer`；令牌仍会短暂出现在 URL 中，前端读入后存 sessionStorage 并改用请求头 |
| Denial of service | 公开入口刷单 | 登录有限流；`POST /api/requirements` 未限流（本地演示接受，公网部署前必须加） |
| Elevation of privilege | 跨卖家读取 | `load_for_seller` 校验 `seller_id`，跨账号返回 403；客户接口一律先解析令牌再校验资源归属 |

## Alternatives considered

- **统一会话 + 角色字段**：最强的理由是一次登录覆盖两类用户，前端只需一个 auth 状态。否掉的原因是客户不该有账号，令牌泄露的爆炸半径必须被限制在单条需求；共用中间件会让「客户能否调用 /api/quotes/{id}/review」变成一条需要读代码才能确认的分支。
- **JWT 承载身份**：最强的理由是免查询、易横向扩展。否掉的原因是无法即时吊销、需要处理算法混淆与密钥轮换；单进程演示用服务端会话表更简单，登出即失效。
- **客户令牌改为 URL 查询参数**：最强的理由是分享链接直观。否掉的原因是令牌会进入访问日志、Referer 与浏览器历史；改为路径一次读取后转请求头，路径本身在页面跳转后不再出现在后续 API 调用中。

## Consequences

- 收益：任何人都能从路由依赖一眼看出该接口属于哪类身份；越权测试（另一个卖家、伪造令牌）都是显式用例。
- 收益：令牌与口令在库中都没有明文，泄露数据库不等于泄露会话。
- 代价：客户每次请求都要带请求头，前端需要一处 `customerToken` 存取封装；直接粘贴 `/r/{token}` 之外的深链接需要重新进入。
- 代价：公开入口没有限流，若做公网 demo 必须先补；这一点已在 README 的已知限制里写明。

## Testing

`backend/tests/test_api_auth.py` 覆盖错误口令、限流、会话往返、缺少 CSRF、未知客户令牌、跨卖家读取；`test_api_quote_flow.py` 覆盖未审核不可确认、重复确认 409、旧修订写入 409。

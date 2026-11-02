# Agent Note: 错误 envelope 必须覆盖未捕获异常，revision 必须条件更新

Status: implemented

## Problem

2026-11-02 审查发现两条基础契约没有真正成立：

1. 错误响应声称永远是 `{code, message, details?}`，但 `/api/health` 数据库失败返回
   `{"status":"degraded","database":"unavailable"}`；未处理的 `RuntimeError` / `PayPalError`
   走 Starlette 默认 500，前端 `ApiError` 无法解析。
2. `append_message` 是“读 revision → 比较 → 自增 → commit”的检查后执行，没有行锁或条件更新。
   两个并发请求都能读到同一个 revision，最终由 `uq_messages_requirement_revision` 让一个失败；
   `IntegrityError` 被 `SQLAlchemyError` handler 统一转成 `503 database_unavailable`，而不是
   承诺的 `409`。

## Decision

**所有失败都走同一个 envelope；并发 token 用数据库条件更新。**

- `register_error_handlers` 增加 `IntegrityError → 409 {code:"conflict"}`、通用
  `Exception → 500 {code:"internal_error", message:"The request could not be completed."}`。
  通用 handler 只记录异常类型到服务端日志，不把异常原文、路径或 SQL 放进响应。
- `/api/health` 数据库失败改为抛 `ApiError(503, "database_unavailable", ...)`，响应同样是
  `{code, message}`；`_seller_id` 的缺失账号也改为 `503 seller_missing`。
- `append_message` 改为
  `UPDATE requirements SET revision = revision + 1 WHERE id = ? AND revision = ?`，检查
  `rowcount`；失败时回滚并返回 `409 revision_conflict`（带 `expected_revision` 与
  `current_revision`）。消息插入仍与 revision 自增在同一事务；`IntegrityError` 也映射为
  `409 revision_conflict`，不再落到数据库不可用。
- `start_payment` 的报价锁定、capture/close 的状态写入同样使用条件更新；`IntegrityError`
  （例如并发创建 attempt 的唯一索引冲突）由服务层或全局 handler 映射为 `409`。

## Alternatives considered

1. **在 `SQLAlchemyError` handler 里按异常字符串判断是否冲突**。最强理由：不用改服务层。
   否决：依赖异常文本/驱动细节，正是项目明令禁止的“猜测标识符”；`IntegrityError` 是更准确的
   类型边界。
2. **继续在 Python 里比较 revision，靠唯一约束兜底**。最强理由：改动最小，顺序请求可用。
   否决：并发时唯一约束会先触发，返回 503，客户看到“数据库不可用”；承诺的 409 不成立。
3. **给 `ExpectedRevision` 加内存锁**。最强理由：实现简单，单进程有效。否决：多 worker 或
   多进程下失效；数据库条件更新才是跨进程事实。
4. **让通用异常 handler 返回 `str(exc)` 便于排障**。最强理由：调试直观。否决：违反错误体
   不泄露路径/异常原文的铁律；排障信息留在服务端日志。

## Consequences

- **收益**：前端只需解析一种错误体；真正的 revision 冲突在并发下也是 409；健康检查和
  未捕获异常不再破坏契约。
- **代价与已知上限**：通用 500 的 `message` 是固定的，客户端不能从响应判断具体异常；排障
  必须看服务端日志。`IntegrityError` 统一映射为 `409 conflict`，服务层对已知冲突仍返回更具体的
  code。`quote_number` 的并发分配仍可能由唯一约束返回 `409 conflict`，调用方需重试。

## Verification

- `backend/tests/test_api_errors.py`：health 数据库失败返回 503 `{code,message}`；未捕获异常
  返回 500 `internal_error`，响应不含异常原文/路径。
- `backend/tests/test_api_quote_flow.py`：顺序 stale revision 仍返回 409；并发保证由条件
  `UPDATE ... WHERE revision = ?` 的 rowcount 提供。
- 2026-11-02: `uv run pytest -q` → `109 passed, 2 warnings`；`uv run ruff check .` 通过。

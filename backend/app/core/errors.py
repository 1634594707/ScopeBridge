"""Uniform error envelope.

Every failure leaves the API as `{"code", "message", "details"}`. Exception
messages, SQL text, file paths and tokens never reach the client.
"""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError
from starlette.exceptions import HTTPException as StarletteHTTPException


class ApiError(Exception):
    def __init__(
        self,
        status_code: int,
        code: str,
        message: str,
        details: Any | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message
        self.details = details


def unauthorized(message: str = "Sign in required") -> ApiError:
    return ApiError(401, "unauthorized", message)


def forbidden(message: str = "You do not have access to this resource") -> ApiError:
    return ApiError(403, "forbidden", message)


def not_found(message: str = "Resource not found") -> ApiError:
    return ApiError(404, "not_found", message)


def conflict(code: str, message: str, details: Any | None = None) -> ApiError:
    return ApiError(409, code, message, details)


def unprocessable(code: str, message: str, details: Any | None = None) -> ApiError:
    return ApiError(422, code, message, details)


def _envelope(status: int, code: str, message: str, details: Any | None) -> JSONResponse:
    payload: dict[str, Any] = {"code": code, "message": message}
    if details is not None:
        payload["details"] = details
    return JSONResponse(status_code=status, content=payload)


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(ApiError)
    async def _api_error(_: Request, exc: ApiError) -> JSONResponse:
        return _envelope(exc.status_code, exc.code, exc.message, exc.details)

    @app.exception_handler(RequestValidationError)
    async def _validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
        details = [
            {
                "field": ".".join(str(part) for part in error["loc"][1:]),
                "message": error["msg"],
            }
            for error in exc.errors()
        ]
        return _envelope(422, "validation_error", "Request body is not valid", details)

    @app.exception_handler(StarletteHTTPException)
    async def _http_error(_: Request, exc: StarletteHTTPException) -> JSONResponse:
        code = {401: "unauthorized", 403: "forbidden", 404: "not_found"}.get(
            exc.status_code, "http_error"
        )
        return _envelope(exc.status_code, code, str(exc.detail), None)

    @app.exception_handler(SQLAlchemyError)
    async def _db_error(_: Request, __: SQLAlchemyError) -> JSONResponse:
        return _envelope(
            503,
            "database_unavailable",
            "The database is not reachable. Check DATABASE_URL and that PostgreSQL is running.",
            None,
        )

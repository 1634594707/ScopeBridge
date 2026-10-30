"""FastAPI application assembly."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import Any

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.api.router import api_router
from app.core.config import get_settings
from app.core.db import SessionLocal, get_db
from app.core.errors import register_error_handlers

logger = logging.getLogger("scopebridge")

settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI):
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    try:
        with SessionLocal() as db:
            db.execute(text("SELECT 1"))
        logger.info("database connection ok")
    except SQLAlchemyError:
        logger.error(
            "database is not reachable; run `uv run alembic upgrade head` and check DATABASE_URL"
        )
    yield


def create_app() -> FastAPI:
    app = FastAPI(
        title="ScopeBridge API",
        version="0.1.0",
        description="Guided service scoping, rule-checked quotes, human-confirmed agreements.",
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.app_origin],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["Content-Type", "X-CSRF-Token", "X-Customer-Token"],
    )
    register_error_handlers(app)
    app.include_router(api_router)

    @app.middleware("http")
    async def security_headers(request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Cache-Control"] = "no-store"
        return response

    @app.get("/api/health", tags=["health"])
    def health(db: Session = Depends(get_db)) -> Any:
        try:
            db.execute(text("SELECT 1"))
        except SQLAlchemyError:
            return JSONResponse(
                status_code=503,
                content={"status": "degraded", "database": "unavailable"},
            )
        return {"status": "ok", "database": "ok"}

    return app


app = create_app()

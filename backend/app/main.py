"""FastAPI application assembly."""

from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.api.router import api_router
from app.core.config import get_settings
from app.core.db import SessionLocal, get_db
from app.core.errors import ApiError, not_found, register_error_handlers
from app.payments.service import recover_stale_attempts

logger = logging.getLogger("scopebridge")

settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI):
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    try:
        with SessionLocal() as db:
            db.execute(text("SELECT 1"))
            recovered = recover_stale_attempts(db)
        logger.info("database connection ok")
        if recovered:
            logger.info("parked %s stale payment attempt(s) for verification", recovered)
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
        allow_headers=["Content-Type", "X-CSRF-Token", "Idempotency-Key"],
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
        except SQLAlchemyError as exc:
            raise ApiError(
                503,
                "database_unavailable",
                "The database is not reachable.",
            ) from exc
        return {"status": "ok", "database": "ok"}

    serve_frontend(app, Path(os.environ.get("FRONTEND_DIST", default_dist())))
    return app


def default_dist() -> Path:
    return Path(__file__).resolve().parent.parent / "static"


def serve_frontend(app: FastAPI, dist: Path) -> None:
    """Serve the built SPA from the same origin as the API.

    The frontend calls `/api...` and leans on the session cookie, so shipping both
    from one origin keeps CORS and cookie rules out of the deployment. When the
    directory is absent (local dev with `vite`, or the test suite) nothing is
    mounted and the API behaves exactly as before.
    """
    index = dist / "index.html"
    if not index.is_file():
        return
    root = dist.resolve()
    assets = dist / "assets"
    if assets.is_dir():
        app.mount("/assets", StaticFiles(directory=assets), name="assets")

    @app.get("/{path:path}", include_in_schema=False)
    def spa(path: str) -> FileResponse:
        if path.startswith("api/"):
            raise not_found("No such endpoint")
        candidate = (dist / path).resolve()
        if path and root in candidate.parents and candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(index)


app = create_app()

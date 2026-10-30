"""Aggregate API router."""

from __future__ import annotations

from fastapi import APIRouter

from app.accounts.router import router as accounts_router
from app.ai.router import router as ai_router
from app.proposals.router import router as proposals_router
from app.quotes.router import router as quotes_router
from app.requirements.router import router as requirements_router
from app.service_rules.router import router as service_rules_router

api_router = APIRouter(prefix="/api")
api_router.include_router(accounts_router)
api_router.include_router(service_rules_router)
api_router.include_router(requirements_router)
api_router.include_router(proposals_router)
api_router.include_router(ai_router)
api_router.include_router(quotes_router)

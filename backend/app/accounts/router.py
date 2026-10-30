"""Seller session endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from app.accounts import service
from app.accounts.schemas import SellerProfile, SessionResponse, SignInRequest
from app.api.deps import (
    CSRF_COOKIE,
    SESSION_COOKIE,
    SellerAuth,
    require_csrf,
    require_seller,
)
from app.core.config import get_settings
from app.core.db import get_db

router = APIRouter(tags=["session"])
settings = get_settings()


def _set_session_cookies(response: Response, token: str, csrf_token: str) -> None:
    max_age = int(service.SESSION_TTL.total_seconds())
    response.set_cookie(
        SESSION_COOKIE,
        token,
        max_age=max_age,
        httponly=True,
        samesite="lax",
        secure=settings.cookie_secure,
        path="/",
    )
    response.set_cookie(
        CSRF_COOKIE,
        csrf_token,
        max_age=max_age,
        httponly=False,
        samesite="lax",
        secure=settings.cookie_secure,
        path="/",
    )


@router.post("/session", response_model=SessionResponse)
def sign_in(
    payload: SignInRequest,
    response: Response,
    db: Session = Depends(get_db),
) -> SessionResponse:
    user, token, session = service.sign_in(db, payload.email, payload.password)
    _set_session_cookies(response, token, session.csrf_token)
    return SessionResponse(
        seller=SellerProfile(id=user.id, email=user.email, display_name=user.display_name),
        csrf_token=session.csrf_token,
    )


@router.get("/session", response_model=SessionResponse)
def read_session(auth: SellerAuth = Depends(require_seller)) -> SessionResponse:
    return SessionResponse(
        seller=SellerProfile(
            id=auth.user.id,
            email=auth.user.email,
            display_name=auth.user.display_name,
        ),
        csrf_token=auth.session.csrf_token,
    )


@router.delete("/session", status_code=204)
def sign_out(
    response: Response,
    auth: SellerAuth = Depends(require_csrf),
    db: Session = Depends(get_db),
) -> Response:
    service.revoke_session(db, auth.session.id)
    response.delete_cookie(SESSION_COOKIE, path="/")
    response.delete_cookie(CSRF_COOKIE, path="/")
    response.status_code = 204
    return response

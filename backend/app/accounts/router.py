"""Account and session endpoints: one seller operator, registered clients."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from app.accounts import service
from app.accounts.models import ROLE_CLIENT, ROLE_SELLER
from app.accounts.schemas import (
    RegisterClientRequest,
    SessionAccount,
    SessionResponse,
    SignInRequest,
)
from app.api.deps import (
    CSRF_COOKIE,
    SESSION_COOKIE,
    UserAuth,
    require_user,
    require_user_csrf,
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


def _session_response(user, session) -> SessionResponse:
    return SessionResponse(
        account=SessionAccount(
            id=user.id,
            email=user.email,
            display_name=user.display_name,
            role=user.role,
        ),
        csrf_token=session.csrf_token,
    )


@router.post("/session", response_model=SessionResponse)
def seller_sign_in(
    payload: SignInRequest,
    response: Response,
    db: Session = Depends(get_db),
) -> SessionResponse:
    user, token, session = service.sign_in(db, payload.email, payload.password, ROLE_SELLER)
    _set_session_cookies(response, token, session.csrf_token)
    return _session_response(user, session)


@router.post("/clients", response_model=SessionResponse, status_code=201)
def register_client(
    payload: RegisterClientRequest,
    response: Response,
    db: Session = Depends(get_db),
) -> SessionResponse:
    user, token, session = service.register_client(
        db, payload.email, payload.password, payload.display_name
    )
    _set_session_cookies(response, token, session.csrf_token)
    return _session_response(user, session)


@router.post("/client-session", response_model=SessionResponse)
def client_sign_in(
    payload: SignInRequest,
    response: Response,
    db: Session = Depends(get_db),
) -> SessionResponse:
    user, token, session = service.sign_in(db, payload.email, payload.password, ROLE_CLIENT)
    _set_session_cookies(response, token, session.csrf_token)
    return _session_response(user, session)


@router.get("/session", response_model=SessionResponse)
def read_session(auth: UserAuth = Depends(require_user)) -> SessionResponse:
    return _session_response(auth.user, auth.session)


@router.delete("/session", status_code=204)
def sign_out(
    response: Response,
    auth: UserAuth = Depends(require_user_csrf),
    db: Session = Depends(get_db),
) -> Response:
    service.revoke_session(db, auth.session.id)
    response.delete_cookie(SESSION_COOKIE, path="/")
    response.delete_cookie(CSRF_COOKIE, path="/")
    response.status_code = 204
    return response

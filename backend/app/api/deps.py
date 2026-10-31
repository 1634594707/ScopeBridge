"""One session path for both roles: a cookie-bound session row plus CSRF for
unsafe methods. The `role` column on the user decides what a request may touch;
client resources are additionally guarded by ownership checks. Portal tokens
are gone — a signed-in client is the identity, not a link."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from fastapi import Depends, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.accounts.models import ROLE_CLIENT, ROLE_SELLER, User, UserSession
from app.core.db import get_db
from app.core.errors import forbidden, unauthorized
from app.core.security import constant_time_equals, sha256_hex

SESSION_COOKIE = "sb_session"
CSRF_COOKIE = "sb_csrf"
CSRF_HEADER = "X-CSRF-Token"

UNSAFE_METHODS = frozenset({"POST", "PUT", "PATCH", "DELETE"})


@dataclass(frozen=True)
class UserAuth:
    user: User
    session: UserSession


def _load_auth(request: Request, db: Session) -> UserAuth:
    token = request.cookies.get(SESSION_COOKIE)
    if not token:
        raise unauthorized("Sign in to continue")

    session = db.scalar(
        select(UserSession).where(UserSession.token_hash == sha256_hex(token))
    )
    if session is None:
        raise unauthorized("Session is no longer valid")
    if session.expires_at <= datetime.now(UTC):
        db.delete(session)
        db.commit()
        raise unauthorized("Session has expired")

    user = db.get(User, session.user_id)
    if user is None:
        raise unauthorized("Session is no longer valid")
    return UserAuth(user=user, session=session)


def require_user(request: Request, db: Session = Depends(get_db)) -> UserAuth:
    """Any signed-in account, either role."""
    return _load_auth(request, db)


def require_seller(request: Request, db: Session = Depends(get_db)) -> UserAuth:
    auth = _load_auth(request, db)
    if auth.user.role != ROLE_SELLER:
        raise forbidden("This area is for the studio account")
    return auth


def require_client(request: Request, db: Session = Depends(get_db)) -> UserAuth:
    auth = _load_auth(request, db)
    if auth.user.role != ROLE_CLIENT:
        raise forbidden("This area is for the client account")
    return auth


def _with_csrf(request: Request, auth: UserAuth) -> UserAuth:
    if request.method in UNSAFE_METHODS:
        header = request.headers.get(CSRF_HEADER, "")
        if not header or not constant_time_equals(header, auth.session.csrf_token):
            raise forbidden("CSRF token is missing or invalid")
    return auth


def require_csrf(request: Request, auth: UserAuth = Depends(require_seller)) -> UserAuth:
    """Seller writes: seller session plus CSRF."""
    return _with_csrf(request, auth)


def require_user_csrf(request: Request, auth: UserAuth = Depends(require_user)) -> UserAuth:
    """Role-agnostic writes (sign-out)."""
    return _with_csrf(request, auth)


def require_client_csrf(request: Request, auth: UserAuth = Depends(require_client)) -> UserAuth:
    """Client writes: client session plus CSRF."""
    return _with_csrf(request, auth)

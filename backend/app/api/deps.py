"""Two separate identity paths, deliberately not unified.

Seller: server-side session row reached through an HttpOnly cookie, plus a CSRF
token for unsafe methods. Client: an opaque portal token bound to exactly one
requirement, sent as a request header. Keeping them apart means no request can
ever be authorised by the wrong rule.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from fastapi import Depends, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.accounts.models import SellerSession, User
from app.core.db import get_db
from app.core.errors import forbidden, unauthorized
from app.core.security import constant_time_equals, sha256_hex
from app.requirements.models import Requirement

SESSION_COOKIE = "sb_session"
CSRF_COOKIE = "sb_csrf"
CSRF_HEADER = "X-CSRF-Token"
CUSTOMER_HEADER = "X-Customer-Token"

UNSAFE_METHODS = frozenset({"POST", "PUT", "PATCH", "DELETE"})


@dataclass(frozen=True)
class SellerAuth:
    user: User
    session: SellerSession


def require_seller(request: Request, db: Session = Depends(get_db)) -> SellerAuth:
    token = request.cookies.get(SESSION_COOKIE)
    if not token:
        raise unauthorized("Sign in to use the seller console")

    session = db.scalar(
        select(SellerSession).where(SellerSession.token_hash == sha256_hex(token))
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

    return SellerAuth(user=user, session=session)


def require_csrf(request: Request, auth: SellerAuth = Depends(require_seller)) -> SellerAuth:
    if request.method in UNSAFE_METHODS:
        header = request.headers.get(CSRF_HEADER, "")
        if not header or not constant_time_equals(header, auth.session.csrf_token):
            raise forbidden("CSRF token is missing or invalid")
    return auth


def require_customer(request: Request, db: Session = Depends(get_db)) -> Requirement:
    token = request.headers.get(CUSTOMER_HEADER)
    if not token:
        raise unauthorized("This page needs its client link")

    requirement = db.scalar(
        select(Requirement).where(Requirement.portal_token_hash == sha256_hex(token))
    )
    if requirement is None:
        raise unauthorized("This client link is no longer valid")
    return requirement

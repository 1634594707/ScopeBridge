"""Sign-in, session issuing and throttling boundary."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.accounts.models import LoginAttempt, SellerSession, User
from app.core.errors import ApiError, unauthorized
from app.core.security import (
    hash_password,
    new_opaque_token,
    sha256_hex,
    verify_password,
)

SESSION_TTL = timedelta(hours=12)
FAILURE_WINDOW = timedelta(minutes=15)
MAX_FAILURES = 5


def ensure_seller(db: Session, email: str, password: str, display_name: str) -> User:
    """Seed the single operator account. Idempotent by email."""
    existing = db.scalar(select(User).where(User.email == email.lower()))
    if existing is not None:
        return existing
    user = User(
        email=email.lower(),
        display_name=display_name,
        password_hash=hash_password(password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _recent_failures(db: Session, email: str) -> int:
    since = datetime.now(UTC) - FAILURE_WINDOW
    return int(
        db.scalar(
            select(func.count(LoginAttempt.id)).where(
                LoginAttempt.email == email,
                LoginAttempt.succeeded.is_(False),
                LoginAttempt.created_at >= since,
            )
        )
        or 0
    )


def sign_in(db: Session, email: str, password: str) -> tuple[User, str, SellerSession]:
    """Return (user, plaintext session token, session row).

    The plaintext token is the only moment the secret exists; the database keeps
    its SHA-256 digest.
    """
    normalized = email.lower().strip()
    if _recent_failures(db, normalized) >= MAX_FAILURES:
        raise ApiError(
            429,
            "too_many_attempts",
            "Too many failed sign-in attempts. Try again in 15 minutes.",
        )

    user = db.scalar(select(User).where(User.email == normalized))
    if user is None or not verify_password(user.password_hash, password):
        db.add(LoginAttempt(email=normalized, succeeded=False))
        db.commit()
        raise unauthorized("Email or password is incorrect")

    db.add(LoginAttempt(email=normalized, succeeded=True))
    token = new_opaque_token()
    session = SellerSession(
        user_id=user.id,
        token_hash=sha256_hex(token),
        csrf_token=new_opaque_token(),
        expires_at=datetime.now(UTC) + SESSION_TTL,
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return user, token, session


def revoke_session(db: Session, session_id: UUID) -> None:
    session = db.get(SellerSession, session_id)
    if session is not None:
        db.delete(session)
        db.commit()

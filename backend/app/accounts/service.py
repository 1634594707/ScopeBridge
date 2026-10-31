"""Account registration, sign-in, session issuing and throttling."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.accounts.models import (
    ROLE_CLIENT,
    ROLE_SELLER,
    LoginAttempt,
    User,
    UserSession,
)
from app.core.errors import ApiError, conflict, unauthorized
from app.core.security import (
    hash_password,
    new_opaque_token,
    sha256_hex,
    verify_password,
)

SESSION_TTL = timedelta(hours=12)
FAILURE_WINDOW = timedelta(minutes=15)
MAX_FAILURES = 5


def _find_user(db: Session, email: str) -> User | None:
    return db.scalar(select(User).where(User.email == email.lower()))


def ensure_seller(db: Session, email: str, password: str, display_name: str) -> User:
    """Seed the single operator account. Idempotent by email."""
    existing = _find_user(db, email)
    if existing is not None:
        if existing.role != ROLE_SELLER:
            existing.role = ROLE_SELLER
            db.commit()
            db.refresh(existing)
        return existing
    user = User(
        email=email.lower(),
        display_name=display_name,
        password_hash=hash_password(password),
        role=ROLE_SELLER,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def ensure_client(db: Session, email: str, password: str, display_name: str) -> User:
    """Seed a demo client account. Idempotent by email."""
    existing = _find_user(db, email)
    if existing is not None:
        if existing.role != ROLE_CLIENT:
            existing.role = ROLE_CLIENT
            db.commit()
            db.refresh(existing)
        return existing
    user = User(
        email=email.lower(),
        display_name=display_name,
        password_hash=hash_password(password),
        role=ROLE_CLIENT,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def register_client(
    db: Session, email: str, password: str, display_name: str
) -> tuple[User, str, UserSession]:
    """Create a client account and open its first session."""
    normalized = email.lower().strip()
    if _find_user(db, normalized) is not None:
        raise conflict(
            "email_already_registered",
            "That email already has an account. Sign in instead.",
        )
    user = User(
        email=normalized,
        display_name=display_name.strip(),
        password_hash=hash_password(password),
        role=ROLE_CLIENT,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return _issue_session(db, user)


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


def sign_in(
    db: Session, email: str, password: str, role: str
) -> tuple[User, str, UserSession]:
    """Return (user, plaintext session token, session row) for the given role.

    The plaintext token is the only moment the secret exists; the database keeps
    its SHA-256 digest. A wrong role is answered like a wrong password so the
    endpoint never confirms which side an email belongs to.
    """
    normalized = email.lower().strip()
    if _recent_failures(db, normalized) >= MAX_FAILURES:
        raise ApiError(
            429,
            "too_many_attempts",
            "Too many failed sign-in attempts. Try again in 15 minutes.",
        )

    user = _find_user(db, normalized)
    if user is None or not verify_password(user.password_hash, password) or user.role != role:
        db.add(LoginAttempt(email=normalized, succeeded=False))
        db.commit()
        raise unauthorized("Email or password is incorrect")

    db.add(LoginAttempt(email=normalized, succeeded=True))
    return _issue_session(db, user)


def _issue_session(db: Session, user: User) -> tuple[User, str, UserSession]:
    token = new_opaque_token()
    session = UserSession(
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
    session = db.get(UserSession, session_id)
    if session is not None:
        db.delete(session)
        db.commit()

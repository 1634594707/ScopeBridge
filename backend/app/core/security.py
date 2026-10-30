"""Password hashing, opaque tokens and digests."""

from __future__ import annotations

import hashlib
import hmac
import os
import secrets

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

# Argon2 defaults to 64 MiB per hash. Tests set a lower cost so constrained CI
# machines do not fail on memory allocation; production keeps the default.
_MEMORY_COST = int(os.environ.get("ARGON2_MEMORY_COST", "65536"))
_hasher = PasswordHasher(memory_cost=_MEMORY_COST, parallelism=1)


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password_hash: str, password: str) -> bool:
    try:
        return _hasher.verify(password_hash, password)
    except VerifyMismatchError:
        return False


def new_opaque_token() -> str:
    """URL-safe token handed to a browser or a client, never stored in plain text."""
    return secrets.token_urlsafe(32)


def sha256_hex(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def constant_time_equals(left: str, right: str) -> bool:
    return hmac.compare_digest(left.encode("utf-8"), right.encode("utf-8"))

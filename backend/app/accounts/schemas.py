"""Wire schemas for the account and session endpoints."""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, Field


class SignInRequest(BaseModel):
    email: str = Field(min_length=3, max_length=255)
    password: str = Field(min_length=8, max_length=200)


class RegisterClientRequest(BaseModel):
    email: str = Field(min_length=3, max_length=255)
    password: str = Field(min_length=8, max_length=200)
    display_name: str = Field(min_length=1, max_length=120)


class SessionAccount(BaseModel):
    id: UUID
    email: str
    display_name: str
    role: str


class SessionResponse(BaseModel):
    account: SessionAccount
    csrf_token: str

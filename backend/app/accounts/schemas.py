"""Wire schemas for the seller session endpoints."""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, Field


class SignInRequest(BaseModel):
    email: str = Field(min_length=3, max_length=255)
    password: str = Field(min_length=8, max_length=200)


class SellerProfile(BaseModel):
    id: UUID
    email: str
    display_name: str


class SessionResponse(BaseModel):
    seller: SellerProfile
    csrf_token: str

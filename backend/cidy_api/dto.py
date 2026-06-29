from __future__ import annotations

import uuid
from typing import Literal

from pydantic import BaseModel, EmailStr


class MagicLinkRequest(BaseModel):
    email: EmailStr


class MagicLinkResponse(BaseModel):
    sent: bool
    dev_link: str | None = None


class VerifyRequest(BaseModel):
    token: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    id: uuid.UUID
    email: str


class CollaboratorAdd(BaseModel):
    email: EmailStr
    role: Literal["editor", "reviewer"]


class CollaboratorOut(BaseModel):
    user_id: uuid.UUID
    email: str
    role: str

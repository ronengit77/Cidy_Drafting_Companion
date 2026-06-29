from __future__ import annotations

import uuid
from datetime import datetime
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


class ArtifactCreate(BaseModel):
    schema_id: str
    title: str = ""
    content: dict = {}


class ArtifactUpdate(BaseModel):
    expected_version_no: int
    title: str
    content: dict


class ArtifactSummary(BaseModel):
    id: uuid.UUID
    schema_id: str
    schema_version: str
    title: str
    version_no: int
    status: str
    updated_at: datetime


class ArtifactDetail(ArtifactSummary):
    owner_id: uuid.UUID
    content: dict
    created_at: datetime


class VersionSummary(BaseModel):
    version_no: int
    title: str
    created_at: datetime


class IssueOut(BaseModel):
    path: str
    severity: str
    message: str


class ValidationReportOut(BaseModel):
    is_valid: bool
    required_total: int
    required_filled: int
    missing: list[str]
    issues: list[IssueOut]

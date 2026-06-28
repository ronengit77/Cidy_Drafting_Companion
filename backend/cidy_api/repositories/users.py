from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from cidy_api.models_db import User


def _normalize(email: str) -> str:
    return email.strip().lower()


def get_or_create_by_email(session: Session, email: str) -> User:
    normalized = _normalize(email)
    existing = session.execute(select(User).where(User.email == normalized)).scalar_one_or_none()
    if existing is not None:
        return existing
    user = User(email=normalized)
    session.add(user)
    session.flush()
    return user


def touch_last_login(session: Session, user: User) -> None:
    user.last_login_at = datetime.now(timezone.utc)
    session.flush()

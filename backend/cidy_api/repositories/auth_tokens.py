from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from cidy_api.models_db import AuthToken


def create_token(
    session: Session, user_id: uuid.UUID, token_hash: str, expires_at: datetime
) -> AuthToken:
    token = AuthToken(user_id=user_id, token_hash=token_hash, expires_at=expires_at)
    session.add(token)
    session.flush()
    return token


def consume_token(session: Session, token_hash: str) -> AuthToken | None:
    token = session.execute(
        select(AuthToken).where(AuthToken.token_hash == token_hash)
    ).scalar_one_or_none()
    if token is None or token.consumed_at is not None:
        return None
    if token.expires_at <= datetime.now(timezone.utc):
        return None
    token.consumed_at = datetime.now(timezone.utc)
    session.flush()
    return token

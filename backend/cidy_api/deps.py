from __future__ import annotations

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from cidy_api.auth import AuthError, decode_jwt
from cidy_api.db import get_session
from cidy_api.models_db import User

_UNAUTH = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="not authenticated",
    headers={"WWW-Authenticate": "Bearer"},
)


def get_current_user(
    authorization: str | None = Header(default=None),
    session: Session = Depends(get_session),
) -> User:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise _UNAUTH
    raw_jwt = authorization.split(" ", 1)[1]
    try:
        user_id = decode_jwt(raw_jwt)
    except AuthError:
        raise _UNAUTH
    user = session.get(User, user_id)
    if user is None:
        raise _UNAUTH
    return user

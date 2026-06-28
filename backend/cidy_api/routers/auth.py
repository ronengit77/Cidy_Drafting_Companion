from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from cidy_api import auth, email_sink
from cidy_api.config import get_settings
from cidy_api.db import get_session
from cidy_api.dto import MagicLinkRequest, MagicLinkResponse, TokenResponse, VerifyRequest
from cidy_api.models_db import User
from cidy_api.repositories import auth_tokens, users

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/magic-link", response_model=MagicLinkResponse)
def request_magic_link(payload: MagicLinkRequest, session: Session = Depends(get_session)) -> MagicLinkResponse:
    settings = get_settings()
    user = users.get_or_create_by_email(session, payload.email)
    raw, token_hash = auth.generate_magic_token()
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=settings.magic_link_expire_minutes)
    auth_tokens.create_token(session, user.id, token_hash, expires_at)
    link = f"{settings.app_base_url}/auth/verify?token={raw}"
    email_sink.send_magic_link(user.email, link)
    session.commit()
    return MagicLinkResponse(sent=True, dev_link=link if settings.dev_mode else None)


@router.post("/verify", response_model=TokenResponse)
def verify(payload: VerifyRequest, session: Session = Depends(get_session)) -> TokenResponse:
    token = auth_tokens.consume_token(session, auth.hash_token(payload.token))
    if token is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid or expired token")
    user = session.get(User, token.user_id)
    users.touch_last_login(session, user)
    access = auth.create_jwt(user.id)
    session.commit()
    return TokenResponse(access_token=access)

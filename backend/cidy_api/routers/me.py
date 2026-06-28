from __future__ import annotations

from fastapi import APIRouter, Depends

from cidy_api.deps import get_current_user
from cidy_api.dto import UserResponse
from cidy_api.models_db import User

router = APIRouter(tags=["me"])


@router.get("/me", response_model=UserResponse)
def me(current_user: User = Depends(get_current_user)) -> User:
    return current_user

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from cidy_api import authz
from cidy_api.db import get_session
from cidy_api.deps import get_current_user
from cidy_api.dto import CollaboratorAdd, CollaboratorOut
from cidy_api.models_db import User
from cidy_api.repositories import collaborators, users

router = APIRouter(prefix="/artifacts/{artifact_id}/collaborators", tags=["collaborators"])


@router.post("", response_model=CollaboratorOut)
def add(
    artifact_id: uuid.UUID,
    payload: CollaboratorAdd,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> CollaboratorOut:
    authz.require_artifact(session, current_user, artifact_id, "own")
    target = users.get_or_create_by_email(session, payload.email)
    row = collaborators.add_collaborator(session, artifact_id, target.id, payload.role)
    session.commit()
    return CollaboratorOut(user_id=target.id, email=target.email, role=row.role)


@router.get("", response_model=list[CollaboratorOut])
def list_(
    artifact_id: uuid.UUID,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> list[CollaboratorOut]:
    authz.require_artifact(session, current_user, artifact_id, "read")
    out: list[CollaboratorOut] = []
    for row in collaborators.list_collaborators(session, artifact_id):
        user = session.get(User, row.user_id)
        out.append(CollaboratorOut(user_id=row.user_id, email=user.email, role=row.role))
    return out


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove(
    artifact_id: uuid.UUID,
    user_id: uuid.UUID,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> Response:
    authz.require_artifact(session, current_user, artifact_id, "own")
    removed = collaborators.remove_collaborator(session, artifact_id, user_id)
    if not removed:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="collaborator not found")
    session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)

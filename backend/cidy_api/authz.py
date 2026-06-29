from __future__ import annotations

import uuid

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from cidy_api.models_db import Artifact, ArtifactCollaborator, User

_READ = {"owner", "editor", "reviewer"}
_EDIT = {"owner", "editor"}
_OWN = {"owner"}
_NEEDS = {"read": _READ, "edit": _EDIT, "own": _OWN}


def access_level(session: Session, user: User, artifact: Artifact) -> str | None:
    if artifact.owner_id == user.id:
        return "owner"
    row = session.execute(
        select(ArtifactCollaborator.role).where(
            ArtifactCollaborator.artifact_id == artifact.id,
            ArtifactCollaborator.user_id == user.id,
        )
    ).scalar_one_or_none()
    return row


def require_artifact(
    session: Session, user: User, artifact_id: uuid.UUID, need: str
) -> Artifact:
    artifact = session.get(Artifact, artifact_id)
    if artifact is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="artifact not found")
    level = access_level(session, user, artifact)
    if level not in _NEEDS[need]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="forbidden")
    return artifact

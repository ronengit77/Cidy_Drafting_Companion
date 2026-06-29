from __future__ import annotations

import uuid

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from cidy_api.models_db import ArtifactCollaborator


def add_collaborator(
    session: Session, artifact_id: uuid.UUID, user_id: uuid.UUID, role: str
) -> ArtifactCollaborator:
    existing = session.execute(
        select(ArtifactCollaborator).where(
            ArtifactCollaborator.artifact_id == artifact_id,
            ArtifactCollaborator.user_id == user_id,
        )
    ).scalar_one_or_none()
    if existing is not None:
        existing.role = role
        session.flush()
        return existing
    row = ArtifactCollaborator(artifact_id=artifact_id, user_id=user_id, role=role)
    session.add(row)
    session.flush()
    return row


def remove_collaborator(session: Session, artifact_id: uuid.UUID, user_id: uuid.UUID) -> bool:
    result = session.execute(
        delete(ArtifactCollaborator).where(
            ArtifactCollaborator.artifact_id == artifact_id,
            ArtifactCollaborator.user_id == user_id,
        )
    )
    session.flush()
    return result.rowcount > 0


def list_collaborators(session: Session, artifact_id: uuid.UUID) -> list[ArtifactCollaborator]:
    return list(
        session.execute(
            select(ArtifactCollaborator).where(ArtifactCollaborator.artifact_id == artifact_id)
        ).scalars().all()
    )

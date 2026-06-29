from __future__ import annotations

import uuid

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from cidy_api.models_db import Artifact, ArtifactCollaborator


def create_artifact(
    session: Session,
    *,
    owner_id: uuid.UUID,
    schema_id: str,
    schema_version: str,
    title: str,
    content: dict,
) -> Artifact:
    artifact = Artifact(
        owner_id=owner_id,
        schema_id=schema_id,
        schema_version=schema_version,
        title=title,
        content=content,
    )
    session.add(artifact)
    session.flush()
    return artifact


def get_artifact(session: Session, artifact_id: uuid.UUID) -> Artifact | None:
    return session.get(Artifact, artifact_id)


def list_for_user(session: Session, user_id: uuid.UUID) -> list[Artifact]:
    collab_ids = select(ArtifactCollaborator.artifact_id).where(
        ArtifactCollaborator.user_id == user_id
    )
    stmt = (
        select(Artifact)
        .where(or_(Artifact.owner_id == user_id, Artifact.id.in_(collab_ids)))
        .order_by(Artifact.updated_at.desc())
    )
    return list(session.execute(stmt).scalars().all())

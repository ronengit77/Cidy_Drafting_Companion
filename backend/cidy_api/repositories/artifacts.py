from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from cidy_api.models_db import Artifact, ArtifactCollaborator, ArtifactVersion


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


class ConflictError(Exception):
    """Raised when an update's expected version_no does not match current."""


class VersionNotFound(Exception):
    """Raised when restoring a version_no that has no snapshot."""


def _snapshot(session: Session, artifact: Artifact, author_id: uuid.UUID) -> None:
    session.add(
        ArtifactVersion(
            artifact_id=artifact.id,
            version_no=artifact.version_no,
            title=artifact.title,
            content=artifact.content,
            author_id=author_id,
        )
    )


def update_artifact(
    session: Session,
    artifact: Artifact,
    *,
    expected_version_no: int,
    title: str,
    content: dict,
    author_id: uuid.UUID,
) -> Artifact:
    if artifact.version_no != expected_version_no:
        raise ConflictError(
            f"expected version {expected_version_no}, current is {artifact.version_no}"
        )
    _snapshot(session, artifact, author_id)
    artifact.title = title
    artifact.content = content
    artifact.version_no += 1
    artifact.updated_at = datetime.now(timezone.utc)
    session.flush()
    return artifact


def list_versions(session: Session, artifact_id: uuid.UUID) -> list[ArtifactVersion]:
    stmt = (
        select(ArtifactVersion)
        .where(ArtifactVersion.artifact_id == artifact_id)
        .order_by(ArtifactVersion.version_no.desc())
    )
    return list(session.execute(stmt).scalars().all())


def restore_version(
    session: Session, artifact: Artifact, target_version_no: int, *, author_id: uuid.UUID
) -> Artifact:
    stmt = select(ArtifactVersion).where(
        ArtifactVersion.artifact_id == artifact.id,
        ArtifactVersion.version_no == target_version_no,
    )
    target = session.execute(stmt).scalar_one_or_none()
    if target is None:
        raise VersionNotFound(f"no version {target_version_no}")
    _snapshot(session, artifact, author_id)
    artifact.title = target.title
    artifact.content = target.content
    artifact.version_no += 1
    artifact.updated_at = datetime.now(timezone.utc)
    session.flush()
    return artifact

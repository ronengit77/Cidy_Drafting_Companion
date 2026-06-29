from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from cidy_api import authz, schema_registry
from cidy_api.db import get_session
from cidy_api.deps import get_current_user
from cidy_api.dto import (
    ArtifactCreate,
    ArtifactDetail,
    ArtifactSummary,
    ArtifactUpdate,
    VersionSummary,
)
from cidy_api.models_db import Artifact, User
from cidy_api.repositories import artifacts as artifacts_repo

router = APIRouter(prefix="/artifacts", tags=["artifacts"])


def _detail(a: Artifact) -> ArtifactDetail:
    return ArtifactDetail(
        id=a.id, schema_id=a.schema_id, schema_version=a.schema_version, title=a.title,
        version_no=a.version_no, status=a.status, updated_at=a.updated_at,
        owner_id=a.owner_id, content=a.content, created_at=a.created_at,
    )


@router.post("", response_model=ArtifactDetail, status_code=status.HTTP_201_CREATED)
def create(
    payload: ArtifactCreate,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> ArtifactDetail:
    schema = schema_registry.get_schema(payload.schema_id)
    if schema is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="unknown schema_id")
    artifact = artifacts_repo.create_artifact(
        session, owner_id=current_user.id, schema_id=schema.schema_id,
        schema_version=schema.version, title=payload.title, content=payload.content,
    )
    session.commit()
    return _detail(artifact)


@router.get("", response_model=list[ArtifactSummary])
def list_(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> list[ArtifactSummary]:
    rows = artifacts_repo.list_for_user(session, current_user.id)
    return [
        ArtifactSummary(
            id=a.id, schema_id=a.schema_id, schema_version=a.schema_version, title=a.title,
            version_no=a.version_no, status=a.status, updated_at=a.updated_at,
        )
        for a in rows
    ]


@router.get("/{artifact_id}", response_model=ArtifactDetail)
def get(
    artifact_id: uuid.UUID,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> ArtifactDetail:
    artifact = authz.require_artifact(session, current_user, artifact_id, "read")
    return _detail(artifact)


@router.put("/{artifact_id}", response_model=ArtifactDetail)
def update(
    artifact_id: uuid.UUID,
    payload: ArtifactUpdate,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> ArtifactDetail:
    artifact = authz.require_artifact(session, current_user, artifact_id, "edit")
    try:
        artifacts_repo.update_artifact(
            session, artifact, expected_version_no=payload.expected_version_no,
            title=payload.title, content=payload.content, author_id=current_user.id,
        )
    except artifacts_repo.ConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    session.commit()
    return _detail(artifact)


@router.get("/{artifact_id}/versions", response_model=list[VersionSummary])
def versions(
    artifact_id: uuid.UUID,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> list[VersionSummary]:
    authz.require_artifact(session, current_user, artifact_id, "read")
    return [
        VersionSummary(version_no=v.version_no, title=v.title, created_at=v.created_at)
        for v in artifacts_repo.list_versions(session, artifact_id)
    ]


@router.post("/{artifact_id}/versions/{version_no}/restore", response_model=ArtifactDetail)
def restore(
    artifact_id: uuid.UUID,
    version_no: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> ArtifactDetail:
    artifact = authz.require_artifact(session, current_user, artifact_id, "edit")
    try:
        artifacts_repo.restore_version(session, artifact, version_no, author_id=current_user.id)
    except artifacts_repo.VersionNotFound as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    session.commit()
    return _detail(artifact)

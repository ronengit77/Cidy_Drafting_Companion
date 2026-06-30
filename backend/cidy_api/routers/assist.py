from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from cidy_api import authz, schema_registry
from cidy_api.db import get_session
from cidy_api.deps import get_current_user
from cidy_api.dto import CoherenceResponse, ShapeFieldRequest, ShapeFieldResponse
from cidy_api.llm import assist
from cidy_api.llm.base import LLMError, LLMProvider
from cidy_api.llm.deps import get_llm_provider
from cidy_api.models_db import User

router = APIRouter(prefix="/artifacts", tags=["assist"])

_NO_LLM = HTTPException(
    status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="LLM not configured"
)
_LLM_DOWN = HTTPException(
    status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="LLM temporarily unavailable"
)


@router.post("/{artifact_id}/assist/shape", response_model=ShapeFieldResponse)
def shape(
    artifact_id: uuid.UUID,
    payload: ShapeFieldRequest,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
    provider: LLMProvider | None = Depends(get_llm_provider),
) -> ShapeFieldResponse:
    if provider is None:
        raise _NO_LLM
    artifact = authz.require_artifact(session, current_user, artifact_id, "edit")
    schema = schema_registry.get_schema(artifact.schema_id)
    if schema is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="artifact references an unknown schema",
        )
    section = next((s for s in schema.sections if s.id == payload.section_id), None)
    if section is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="unknown section_id")
    field = next((f for f in section.fields if f.id == payload.field_id), None)
    if field is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="unknown field_id")
    try:
        shaped = assist.shape_field(
            provider,
            fund=schema.fund,
            artifact_type=schema.artifact_type,
            section_title=section.title,
            field_label=field.label,
            field_guidance=field.guidance,
            raw_input=payload.raw_input,
        )
    except LLMError as exc:
        raise _LLM_DOWN from exc
    return ShapeFieldResponse(shaped_text=shaped)


@router.post("/{artifact_id}/assist/coherence", response_model=CoherenceResponse)
def coherence(
    artifact_id: uuid.UUID,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
    provider: LLMProvider | None = Depends(get_llm_provider),
) -> CoherenceResponse:
    if provider is None:
        raise _NO_LLM
    artifact = authz.require_artifact(session, current_user, artifact_id, "read")
    schema = schema_registry.get_schema(artifact.schema_id)
    if schema is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="artifact references an unknown schema",
        )
    try:
        assessment = assist.coherence_check(provider, schema=schema, values=artifact.content)
    except LLMError as exc:
        raise _LLM_DOWN from exc
    return CoherenceResponse(assessment=assessment)

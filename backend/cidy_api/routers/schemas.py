from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from cidy_api import schema_registry

router = APIRouter(prefix="/schemas", tags=["schemas"])


@router.get("", response_model=list[schema_registry.SchemaInfo])
def list_schemas() -> list[schema_registry.SchemaInfo]:
    return schema_registry.list_schemas()


@router.get("/{schema_id}")
def get_schema(schema_id: str) -> dict:
    schema = schema_registry.get_schema(schema_id)
    if schema is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="unknown schema")
    return schema.model_dump()

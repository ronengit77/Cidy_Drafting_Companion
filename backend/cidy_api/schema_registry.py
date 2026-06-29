from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import BaseModel

from cidy.reference.sdg import SDGFramework, load_sdg_framework_file
from cidy.schema.loader import load_schema_file
from cidy.schema.models import TemplateSchema

_REPO_ROOT = Path(__file__).resolve().parents[2]
_SCHEMAS_DIR = _REPO_ROOT / "schemas"
_SDG_PATH = _REPO_ROOT / "data" / "sdg_framework.json"


class SchemaInfo(BaseModel):
    schema_id: str
    version: str
    fund: str
    artifact_type: str
    title: str


@lru_cache
def _load_all() -> dict[str, TemplateSchema]:
    schemas: dict[str, TemplateSchema] = {}
    for path in sorted(_SCHEMAS_DIR.glob("*.json")):
        schema = load_schema_file(path)
        schemas[schema.schema_id] = schema
    return schemas


def list_schemas() -> list[SchemaInfo]:
    return [
        SchemaInfo(
            schema_id=s.schema_id,
            version=s.version,
            fund=s.fund,
            artifact_type=s.artifact_type,
            title=s.title,
        )
        for s in _load_all().values()
    ]


def get_schema(schema_id: str) -> TemplateSchema | None:
    return _load_all().get(schema_id)


@lru_cache
def get_sdg_framework() -> SDGFramework:
    return load_sdg_framework_file(_SDG_PATH)

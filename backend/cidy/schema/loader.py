from __future__ import annotations

import json
from pathlib import Path

from pydantic import ValidationError

from cidy.schema.models import TemplateSchema


class SchemaError(Exception):
    """Raised when a Template Schema cannot be loaded or validated."""


def load_schema(data: dict) -> TemplateSchema:
    try:
        return TemplateSchema.model_validate(data)
    except ValidationError as exc:
        raise SchemaError(str(exc)) from exc


def load_schema_json(text: str) -> TemplateSchema:
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise SchemaError(f"invalid JSON: {exc}") from exc
    return load_schema(data)


def load_schema_file(path: str | Path) -> TemplateSchema:
    return load_schema_json(Path(path).read_text(encoding="utf-8"))

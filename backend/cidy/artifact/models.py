from __future__ import annotations

from pydantic import BaseModel, Field


class Artifact(BaseModel):
    schema_id: str
    schema_version: str
    title: str = ""
    values: dict[str, object] = Field(default_factory=dict)
    version_no: int = 0

    def to_json(self) -> str:
        return self.model_dump_json()

    @classmethod
    def from_json(cls, text: str) -> "Artifact":
        return cls.model_validate_json(text)

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict


class FieldType(str, Enum):
    TEXT = "text"
    RICH_TEXT = "rich_text"
    NUMBER = "number"
    CURRENCY = "currency"
    BOOLEAN = "boolean"
    SINGLE_SELECT = "single_select"
    MULTI_SELECT = "multi_select"
    CHECKBOX_GROUP = "checkbox_group"
    DATE = "date"
    QUARTER_YEAR = "quarter_year"
    SDG_TARGET_LIST = "sdg_target_list"
    GA_RESOLUTION_LIST = "ga_resolution_list"
    REPEATING_GROUP = "repeating_group"
    BUDGET_TABLE = "budget_table"
    RATING_SCALE = "rating_scale"


class Constraints(BaseModel):
    model_config = ConfigDict(extra="forbid")

    required: bool = False
    max_chars: int | None = None
    max_words: int | None = None
    max_pages: float | None = None
    max_items: int | None = None
    order: str | None = None
    options: list[str] | None = None
    min_value: float | None = None


class Field(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    label: str
    type: FieldType
    guidance: str = ""
    constraints: Constraints = Constraints()
    fields: list["Field"] | None = None


class Section(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    title: str
    guidance: str = ""
    repeating: bool = False
    fields: list[Field]


class TemplateSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_id: str
    version: str
    fund: str
    artifact_type: str
    title: str
    sections: list[Section]

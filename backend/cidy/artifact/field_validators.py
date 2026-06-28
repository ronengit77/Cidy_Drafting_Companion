from __future__ import annotations

import numbers

from pydantic import BaseModel

from cidy.schema.models import Field, FieldType


class Issue(BaseModel):
    path: str
    severity: str
    message: str


def _error(path: str, message: str) -> Issue:
    return Issue(path=path, severity="error", message=message)


def validate_field_value(field: Field, value: object, path: str) -> list[Issue]:
    if value is None:
        return []

    c = field.constraints
    issues: list[Issue] = []
    t = field.type

    if t in (FieldType.TEXT, FieldType.RICH_TEXT):
        text = str(value)
        if c.max_chars is not None and len(text) > c.max_chars:
            issues.append(_error(path, f"exceeds max {c.max_chars} characters"))
        if c.max_words is not None and len(text.split()) > c.max_words:
            issues.append(_error(path, f"exceeds max {c.max_words} words"))

    elif t in (FieldType.NUMBER, FieldType.CURRENCY):
        if isinstance(value, bool) or not isinstance(value, numbers.Number):
            issues.append(_error(path, "must be a number"))
        elif c.min_value is not None and value < c.min_value:
            issues.append(_error(path, f"must be >= {c.min_value}"))

    elif t in (FieldType.BOOLEAN,):
        if not isinstance(value, bool):
            issues.append(_error(path, "must be a boolean"))

    elif t in (FieldType.SINGLE_SELECT,):
        if c.options is not None and value not in c.options:
            issues.append(_error(path, f"must be one of {c.options}"))

    elif t in (FieldType.MULTI_SELECT, FieldType.CHECKBOX_GROUP):
        if c.options is not None:
            if not isinstance(value, list):
                issues.append(_error(path, "must be a list"))
            else:
                bad = [v for v in value if v not in c.options]
                if bad:
                    issues.append(_error(path, f"{bad} not in {c.options}"))

    return issues

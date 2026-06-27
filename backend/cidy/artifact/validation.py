from __future__ import annotations

from pydantic import BaseModel

from cidy.artifact.field_validators import Issue, validate_field_value
from cidy.artifact.models import Artifact
from cidy.artifact.sdg_validator import validate_sdg_target_list
from cidy.reference.sdg import SDGFramework
from cidy.schema.models import Field, FieldType, Section, TemplateSchema


class ValidationReport(BaseModel):
    issues: list[Issue] = []
    required_total: int = 0
    required_filled: int = 0
    missing: list[str] = []

    @property
    def is_valid(self) -> bool:
        return not any(i.severity == "error" for i in self.issues)


def _is_empty(value: object) -> bool:
    return value is None or value == "" or value == [] or value == {}


def _validate_field(
    field: Field,
    value: object,
    path: str,
    framework: SDGFramework,
    report: ValidationReport,
) -> None:
    if field.constraints.required:
        report.required_total += 1
        if _is_empty(value):
            report.missing.append(path)
            report.issues.append(Issue(path=path, severity="error", message="required field is empty"))
            return
        report.required_filled += 1
    elif _is_empty(value):
        return

    if field.type is FieldType.SDG_TARGET_LIST:
        report.issues.extend(validate_sdg_target_list(value, field.constraints, framework, path))
    elif field.type is FieldType.REPEATING_GROUP:
        for i, item in enumerate(value or []):
            for sub in field.fields or []:
                _validate_field(sub, (item or {}).get(sub.id), f"{path}[{i}].{sub.id}", framework, report)
    else:
        report.issues.extend(validate_field_value(field, value, path))


def _validate_section(
    section: Section, section_values: object, framework: SDGFramework, report: ValidationReport
) -> None:
    if section.repeating:
        items = section_values if isinstance(section_values, list) else []
        for i, item in enumerate(items):
            for field in section.fields:
                _validate_field(
                    field, (item or {}).get(field.id), f"{section.id}[{i}].{field.id}", framework, report
                )
    else:
        values = section_values if isinstance(section_values, dict) else {}
        for field in section.fields:
            _validate_field(field, values.get(field.id), f"{section.id}.{field.id}", framework, report)


def validate_artifact(
    schema: TemplateSchema, artifact: Artifact, framework: SDGFramework
) -> ValidationReport:
    report = ValidationReport()
    for section in schema.sections:
        _validate_section(section, artifact.values.get(section.id), framework, report)
    return report

from __future__ import annotations

from cidy.schema.models import TemplateSchema
from cidy_api.llm.base import LLMProvider


def shape_field(
    provider: LLMProvider,
    *,
    fund: str,
    artifact_type: str,
    section_title: str,
    field_label: str,
    field_guidance: str,
    raw_input: str,
) -> str:
    system = (
        f"You are an expert UN programme officer drafting a {fund} {artifact_type}. "
        f"Rewrite the user's draft for the field '{field_label}' in section '{section_title}' "
        f"into clear, concise, formal language appropriate for this document. "
        f"Follow this guidance: {field_guidance or 'N/A'}. "
        f"Return only the rewritten text, with no preamble or commentary."
    )
    return provider.complete(system, raw_input).strip()


def render_artifact_summary(schema: TemplateSchema, values: dict) -> str:
    lines: list[str] = []
    for section in schema.sections:
        section_values = values.get(section.id)
        if section.repeating and isinstance(section_values, list):
            for i, item in enumerate(section_values, start=1):
                for field in section.fields:
                    value = (item or {}).get(field.id)
                    if value:
                        lines.append(f"{section.title} [{i}] / {field.label}: {value}")
        elif isinstance(section_values, dict):
            for field in section.fields:
                value = section_values.get(field.id)
                if value:
                    lines.append(f"{section.title} / {field.label}: {value}")
    return "\n".join(lines)


def coherence_check(provider: LLMProvider, *, schema: TemplateSchema, values: dict) -> str:
    summary = render_artifact_summary(schema, values)
    system = (
        f"You are reviewing a {schema.fund} {schema.artifact_type} for coherence and clarity. "
        f"Identify inconsistencies, unclear statements, vague claims, and gaps across sections. "
        f"Reference the section and field names. Be concise and specific. "
        f"If the draft reads well, say so briefly."
    )
    user = f"Here is the current draft:\n\n{summary or '(empty draft)'}"
    return provider.complete(system, user, max_tokens=800).strip()

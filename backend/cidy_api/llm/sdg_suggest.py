from __future__ import annotations

import json
from dataclasses import dataclass

from cidy.reference.sdg import SDGFramework
from cidy_api.llm.base import LLMProvider


@dataclass
class SDGSuggestion:
    target: str
    title: str
    rationale: str


def _extract_json(text: str) -> dict:
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = stripped.strip("`")
        if stripped.lower().startswith("json"):
            stripped = stripped[4:]
    start = stripped.find("{")
    end = stripped.rfind("}")
    if start == -1 or end == -1 or end < start:
        return {}
    try:
        parsed = json.loads(stripped[start : end + 1])
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def suggest_sdg_targets(
    provider: LLMProvider,
    framework: SDGFramework,
    *,
    fund: str,
    artifact_type: str,
    context: str,
    max_suggestions: int = 8,
) -> list[SDGSuggestion]:
    goals_list = "\n".join(
        f"Goal {g.goal} ({g.title}): " + ", ".join(t.target for t in g.targets)
        for g in framework.goals
    )
    system = (
        f"You are aligning a {fund} {artifact_type} with the UN Sustainable Development Goals. "
        f"From the project's content, identify the most relevant SDG TARGETS (e.g. '8.5'). "
        f"Choose ONLY from the official target codes provided. Suggest at most {max_suggestions}. "
        f'Respond with ONLY a JSON object of the form '
        f'{{"suggestions": [{{"target": "<code>", "rationale": "<one short sentence>"}}]}}.'
    )
    user = (
        f"Official SDG targets by goal:\n{goals_list}\n\n"
        f"Project content:\n{context or '(empty draft)'}"
    )
    raw = provider.complete(system, user, max_tokens=700)
    data = _extract_json(raw)

    suggestions: list[SDGSuggestion] = []
    seen: set[str] = set()
    for item in data.get("suggestions", []):
        if not isinstance(item, dict):
            continue
        code = str(item.get("target", "")).strip()
        if not code or code in seen or not framework.has_target(code):
            continue
        seen.add(code)
        target = framework.get_target(code)
        suggestions.append(
            SDGSuggestion(
                target=code,
                title=target.text if target else "",
                rationale=str(item.get("rationale", "")).strip(),
            )
        )
        if len(suggestions) >= max_suggestions:
            break
    return suggestions

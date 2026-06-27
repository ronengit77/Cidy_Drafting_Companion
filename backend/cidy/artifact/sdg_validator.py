from __future__ import annotations

from cidy.artifact.field_validators import Issue
from cidy.reference.sdg import SDGFramework
from cidy.schema.models import Constraints


def _sort_key(code: str) -> tuple[int, int, int, str]:
    goal, _, target = code.partition(".")
    try:
        g = int(goal)
    except ValueError:
        return (10**9, 1, 0, code)  # unparseable codes sort last, deterministically
    if target.isdigit():
        return (g, 0, int(target), "")
    return (g, 1, 0, target)


def validate_sdg_target_list(
    value: object, constraints: Constraints, framework: SDGFramework, path: str
) -> list[Issue]:
    if value is None or value == []:
        return []

    issues: list[Issue] = []
    if not isinstance(value, list):
        return [Issue(path=path, severity="error", message="must be a list of SDG targets")]

    unknown = [c for c in value if not framework.has_target(c)]
    if unknown:
        issues.append(Issue(path=path, severity="error", message=f"unknown SDG targets: {unknown}"))

    if constraints.max_items is not None and len(value) > constraints.max_items:
        issues.append(
            Issue(path=path, severity="error", message=f"list at most {constraints.max_items} targets")
        )

    if constraints.order == "ascending":
        valid = [c for c in value if framework.has_target(c)]
        if valid != sorted(valid, key=_sort_key):
            issues.append(
                Issue(path=path, severity="error", message="SDG targets must be in ascending order")
            )

    return issues

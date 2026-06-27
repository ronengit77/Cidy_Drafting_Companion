from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel


class SDGTarget(BaseModel):
    target: str
    text: str


class SDGGoal(BaseModel):
    goal: int
    title: str
    targets: list[SDGTarget]


class SDGFramework(BaseModel):
    goals: list[SDGGoal]

    def _index(self) -> dict[str, SDGTarget]:
        return {t.target: t for g in self.goals for t in g.targets}

    def has_target(self, code: str) -> bool:
        return code in self._index()

    def get_target(self, code: str) -> SDGTarget | None:
        return self._index().get(code)

    def all_target_codes(self) -> set[str]:
        return set(self._index())


def load_sdg_framework(data: dict) -> SDGFramework:
    return SDGFramework.model_validate(data)


def load_sdg_framework_file(path: str | Path) -> SDGFramework:
    return load_sdg_framework(json.loads(Path(path).read_text(encoding="utf-8")))

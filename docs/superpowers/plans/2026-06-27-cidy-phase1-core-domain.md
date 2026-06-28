# CIdy Phase 1 — Core Domain Library Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a dependency-free Python library that models CIdy's canonical artifact, loads/validates versioned Template Schemas and SDG reference data, and validates artifact content against a schema — the foundation every later phase (API, conversation engine, export) builds on.

**Architecture:** Pydantic v2 models define Template Schemas (versioned form-definitions) and the canonical artifact (nested `values` mirroring the schema's sections). A validation engine walks a schema against an artifact's values and returns a structured report (errors/warnings + completeness). SDG reference data is loaded from a bundled JSON file. The real DA Concept Note and RPTC Activity Proposal templates are authored as schema JSON data files. No network, no AWS, no LLM in this phase.

**Tech Stack:** Python 3.12, Pydantic v2, pytest.

## Global Constraints

- Python version floor: **3.12**.
- Models use **Pydantic v2** API (`model_validate`, `model_dump`, `field_validator`, `ConfigDict`). No Pydantic v1 calls.
- No network access, no AWS SDK, no LLM calls in this phase.
- Canonical artifact `values` are **nested** (mirror the schema's section/field structure), not dotted-key flat. This supersedes the illustrative dotted-key example in `documentation/technical-requirements.md` §4.1 — note that discrepancy when Phase 2 reads this model.
- All work lives under `backend/`. Schema and reference data files live under `schemas/` and `data/` at repo root.
- Test framework: **pytest**. Every task is TDD: failing test first, then minimal implementation.
- Commit after every task with a `feat:`/`test:`/`chore:` prefixed message.

---

### Task 1: Project scaffolding

**Files:**
- Create: `backend/pyproject.toml`
- Create: `backend/cidy/__init__.py`
- Create: `backend/tests/__init__.py`
- Create: `backend/tests/test_smoke.py`

**Interfaces:**
- Consumes: nothing.
- Produces: an installable `cidy` package and a working `pytest` setup that later tasks extend.

- [ ] **Step 1: Write the failing test**

`backend/tests/test_smoke.py`:
```python
import cidy


def test_package_importable():
    assert cidy.__version__ == "0.1.0"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_smoke.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'cidy'` (or `AttributeError` on `__version__`).

- [ ] **Step 3: Create the package files**

`backend/pyproject.toml`:
```toml
[project]
name = "cidy"
version = "0.1.0"
description = "CIdy Drafting Companion core domain library"
requires-python = ">=3.12"
dependencies = ["pydantic>=2.6,<3"]

[project.optional-dependencies]
dev = ["pytest>=8.0"]

[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"

[tool.setuptools.packages.find]
where = ["."]
include = ["cidy*"]

[tool.pytest.ini_options]
testpaths = ["tests"]
```

`backend/cidy/__init__.py`:
```python
__version__ = "0.1.0"
```

`backend/tests/__init__.py`:
```python
```

- [ ] **Step 4: Install dev dependencies and run the test**

Run: `cd backend && pip install -e ".[dev]" && python -m pytest tests/test_smoke.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/pyproject.toml backend/cidy/__init__.py backend/tests/__init__.py backend/tests/test_smoke.py
git commit -m "chore: scaffold cidy core domain package"
```

---

### Task 2: Template Schema models

**Files:**
- Create: `backend/cidy/schema/__init__.py`
- Create: `backend/cidy/schema/models.py`
- Create: `backend/tests/schema/__init__.py`
- Create: `backend/tests/schema/test_models.py`

**Interfaces:**
- Consumes: nothing.
- Produces:
  - `FieldType` (str Enum): `TEXT`, `RICH_TEXT`, `NUMBER`, `CURRENCY`, `BOOLEAN`, `SINGLE_SELECT`, `MULTI_SELECT`, `CHECKBOX_GROUP`, `DATE`, `QUARTER_YEAR`, `SDG_TARGET_LIST`, `GA_RESOLUTION_LIST`, `REPEATING_GROUP`, `BUDGET_TABLE`, `RATING_SCALE`.
  - `Constraints(BaseModel)`: `required: bool = False`, `max_chars: int | None = None`, `max_words: int | None = None`, `max_pages: float | None = None`, `max_items: int | None = None`, `order: str | None = None` (`"ascending"`/`None`), `options: list[str] | None = None`, `min_value: float | None = None`.
  - `Field(BaseModel)`: `id: str`, `label: str`, `type: FieldType`, `guidance: str = ""`, `constraints: Constraints = Constraints()`, `fields: list[Field] | None = None` (nested fields for a `REPEATING_GROUP` field).
  - `Section(BaseModel)`: `id: str`, `title: str`, `guidance: str = ""`, `repeating: bool = False`, `fields: list[Field]`.
  - `TemplateSchema(BaseModel)`: `schema_id: str`, `version: str`, `fund: str`, `artifact_type: str`, `title: str`, `sections: list[Section]`.

- [ ] **Step 1: Write the failing test**

`backend/tests/schema/test_models.py`:
```python
import pytest
from pydantic import ValidationError

from cidy.schema.models import (
    Constraints,
    Field,
    FieldType,
    Section,
    TemplateSchema,
)


def test_build_minimal_schema():
    schema = TemplateSchema(
        schema_id="demo",
        version="1",
        fund="DA",
        artifact_type="concept_note",
        title="Demo",
        sections=[
            Section(
                id="background",
                title="Background",
                fields=[
                    Field(
                        id="objective",
                        label="Objective",
                        type=FieldType.RICH_TEXT,
                        constraints=Constraints(required=True, max_words=200),
                    )
                ],
            )
        ],
    )
    assert schema.sections[0].fields[0].type is FieldType.RICH_TEXT
    assert schema.sections[0].fields[0].constraints.required is True


def test_repeating_group_field_has_nested_fields():
    field = Field(
        id="outputs",
        label="Outputs",
        type=FieldType.REPEATING_GROUP,
        fields=[Field(id="output", label="Output", type=FieldType.RICH_TEXT)],
    )
    assert field.fields[0].id == "output"


def test_unknown_field_type_rejected():
    with pytest.raises(ValidationError):
        Field(id="x", label="X", type="not_a_type")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/schema/test_models.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'cidy.schema'`.

- [ ] **Step 3: Write the models**

`backend/cidy/schema/__init__.py`:
```python
```

`backend/tests/schema/__init__.py`:
```python
```

`backend/cidy/schema/models.py`:
```python
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/schema/test_models.py -v`
Expected: PASS (3 tests).

- [ ] **Step 5: Commit**

```bash
git add backend/cidy/schema backend/tests/schema
git commit -m "feat: add Template Schema pydantic models"
```

---

### Task 3: Schema loader

**Files:**
- Create: `backend/cidy/schema/loader.py`
- Create: `backend/tests/schema/test_loader.py`

**Interfaces:**
- Consumes: `TemplateSchema` (Task 2).
- Produces:
  - `load_schema(data: dict) -> TemplateSchema`
  - `load_schema_json(text: str) -> TemplateSchema`
  - `load_schema_file(path: str | Path) -> TemplateSchema`
  - `SchemaError(Exception)` raised on invalid input.

- [ ] **Step 1: Write the failing test**

`backend/tests/schema/test_loader.py`:
```python
import json

import pytest

from cidy.schema.loader import SchemaError, load_schema, load_schema_file, load_schema_json

VALID = {
    "schema_id": "demo",
    "version": "1",
    "fund": "DA",
    "artifact_type": "concept_note",
    "title": "Demo",
    "sections": [
        {"id": "s1", "title": "S1", "fields": [{"id": "f1", "label": "F1", "type": "text"}]}
    ],
}


def test_load_schema_from_dict():
    schema = load_schema(VALID)
    assert schema.schema_id == "demo"
    assert schema.version == "1"


def test_load_schema_json_round_trip():
    schema = load_schema_json(json.dumps(VALID))
    assert schema.sections[0].fields[0].id == "f1"


def test_load_schema_file(tmp_path):
    p = tmp_path / "schema.json"
    p.write_text(json.dumps(VALID), encoding="utf-8")
    schema = load_schema_file(p)
    assert schema.fund == "DA"


def test_invalid_schema_raises_schema_error():
    with pytest.raises(SchemaError):
        load_schema({"schema_id": "bad"})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/schema/test_loader.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'cidy.schema.loader'`.

- [ ] **Step 3: Write the loader**

`backend/cidy/schema/loader.py`:
```python
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/schema/test_loader.py -v`
Expected: PASS (4 tests).

- [ ] **Step 5: Commit**

```bash
git add backend/cidy/schema/loader.py backend/tests/schema/test_loader.py
git commit -m "feat: add Template Schema loader"
```

---

### Task 4: SDG reference data model and loader

**Files:**
- Create: `backend/cidy/reference/__init__.py`
- Create: `backend/cidy/reference/sdg.py`
- Create: `backend/tests/reference/__init__.py`
- Create: `backend/tests/reference/test_sdg.py`

**Interfaces:**
- Consumes: nothing.
- Produces:
  - `SDGTarget(BaseModel)`: `target: str` (e.g. `"8.5"`), `text: str`.
  - `SDGGoal(BaseModel)`: `goal: int`, `title: str`, `targets: list[SDGTarget]`.
  - `SDGFramework(BaseModel)`: `goals: list[SDGGoal]`; methods `has_target(code: str) -> bool`, `get_target(code: str) -> SDGTarget | None`, `all_target_codes() -> set[str]`.
  - `load_sdg_framework(data: dict) -> SDGFramework`
  - `load_sdg_framework_file(path) -> SDGFramework`

- [ ] **Step 1: Write the failing test**

`backend/tests/reference/test_sdg.py`:
```python
from cidy.reference.sdg import SDGFramework, load_sdg_framework

DATA = {
    "goals": [
        {
            "goal": 8,
            "title": "Decent Work and Economic Growth",
            "targets": [
                {"target": "8.5", "text": "Full and productive employment..."},
                {"target": "8.6", "text": "Reduce youth not in employment..."},
            ],
        }
    ]
}


def test_load_and_lookup():
    fw = load_sdg_framework(DATA)
    assert isinstance(fw, SDGFramework)
    assert fw.has_target("8.5") is True
    assert fw.get_target("8.6").text.startswith("Reduce youth")


def test_unknown_target():
    fw = load_sdg_framework(DATA)
    assert fw.has_target("99.9") is False
    assert fw.get_target("99.9") is None


def test_all_target_codes():
    fw = load_sdg_framework(DATA)
    assert fw.all_target_codes() == {"8.5", "8.6"}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/reference/test_sdg.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'cidy.reference'`.

- [ ] **Step 3: Write the model and loader**

`backend/cidy/reference/__init__.py`:
```python
```

`backend/tests/reference/__init__.py`:
```python
```

`backend/cidy/reference/sdg.py`:
```python
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/reference/test_sdg.py -v`
Expected: PASS (3 tests).

- [ ] **Step 5: Commit**

```bash
git add backend/cidy/reference backend/tests/reference
git commit -m "feat: add SDG reference framework model and loader"
```

---

### Task 5: Canonical artifact model

**Files:**
- Create: `backend/cidy/artifact/__init__.py`
- Create: `backend/cidy/artifact/models.py`
- Create: `backend/tests/artifact/__init__.py`
- Create: `backend/tests/artifact/test_models.py`

**Interfaces:**
- Consumes: nothing.
- Produces:
  - `Artifact(BaseModel)`: `schema_id: str`, `schema_version: str`, `title: str = ""`, `values: dict[str, object] = {}`, `version_no: int = 0`.
    - `values` is nested: for a normal section, `values[section_id]` is `dict[field_id, value]`; for a repeating section, `values[section_id]` is `list[dict[field_id, value]]`.
  - `to_json(self) -> str` and classmethod `from_json(cls, text: str) -> Artifact` for round-tripping.

- [ ] **Step 1: Write the failing test**

`backend/tests/artifact/test_models.py`:
```python
from cidy.artifact.models import Artifact


def test_construct_and_round_trip():
    art = Artifact(
        schema_id="demo",
        schema_version="1",
        title="My draft",
        values={
            "background": {"objective": "Improve X"},
            "outcomes": [{"outcome": "OC1"}, {"outcome": "OC2"}],
        },
        version_no=3,
    )
    text = art.to_json()
    restored = Artifact.from_json(text)
    assert restored == art
    assert restored.values["outcomes"][1]["outcome"] == "OC2"


def test_defaults():
    art = Artifact(schema_id="demo", schema_version="1")
    assert art.values == {}
    assert art.version_no == 0
    assert art.title == ""
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/artifact/test_models.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'cidy.artifact'`.

- [ ] **Step 3: Write the model**

`backend/cidy/artifact/__init__.py`:
```python
```

`backend/tests/artifact/__init__.py`:
```python
```

`backend/cidy/artifact/models.py`:
```python
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/artifact/test_models.py -v`
Expected: PASS (2 tests).

- [ ] **Step 5: Commit**

```bash
git add backend/cidy/artifact backend/tests/artifact
git commit -m "feat: add canonical artifact model"
```

---

### Task 6: Field-level value validators

**Files:**
- Create: `backend/cidy/artifact/field_validators.py`
- Create: `backend/tests/artifact/test_field_validators.py`

**Interfaces:**
- Consumes: `Field`, `FieldType`, `Constraints` (Task 2).
- Produces:
  - `Issue(BaseModel)`: `path: str`, `severity: str` (`"error"`/`"warning"`), `message: str`.
  - `validate_field_value(field: Field, value: object, path: str) -> list[Issue]` — validates a single scalar field's value against its type and constraints. Returns `[]` when valid. Does NOT handle `REPEATING_GROUP`, `SDG_TARGET_LIST`, or required-ness (those are handled by Tasks 7–8). A `None`/absent value yields no field-level issue here.

- [ ] **Step 1: Write the failing test**

`backend/tests/artifact/test_field_validators.py`:
```python
from cidy.artifact.field_validators import Issue, validate_field_value
from cidy.schema.models import Constraints, Field, FieldType


def _field(type_, **constraints):
    return Field(id="f", label="F", type=type_, constraints=Constraints(**constraints))


def test_text_within_limits_ok():
    assert validate_field_value(_field(FieldType.TEXT, max_words=3), "one two", "s.f") == []


def test_text_exceeds_max_words():
    issues = validate_field_value(_field(FieldType.TEXT, max_words=2), "one two three", "s.f")
    assert len(issues) == 1
    assert issues[0].severity == "error"
    assert "words" in issues[0].message
    assert issues[0].path == "s.f"


def test_text_exceeds_max_chars():
    issues = validate_field_value(_field(FieldType.TEXT, max_chars=3), "abcd", "s.f")
    assert issues[0].severity == "error"
    assert "characters" in issues[0].message


def test_number_must_be_numeric():
    issues = validate_field_value(_field(FieldType.NUMBER), "not a number", "s.f")
    assert issues[0].severity == "error"


def test_currency_non_negative():
    issues = validate_field_value(_field(FieldType.CURRENCY, min_value=0), -5, "s.f")
    assert issues[0].severity == "error"


def test_boolean_accepts_bool():
    assert validate_field_value(_field(FieldType.BOOLEAN), True, "s.f") == []


def test_boolean_rejects_non_bool():
    issues = validate_field_value(_field(FieldType.BOOLEAN), "yes", "s.f")
    assert issues[0].severity == "error"


def test_single_select_must_be_in_options():
    f = _field(FieldType.SINGLE_SELECT, options=["a", "b"])
    assert validate_field_value(f, "a", "s.f") == []
    assert validate_field_value(f, "c", "s.f")[0].severity == "error"


def test_multi_select_all_in_options():
    f = _field(FieldType.MULTI_SELECT, options=["a", "b", "c"])
    assert validate_field_value(f, ["a", "c"], "s.f") == []
    assert validate_field_value(f, ["a", "z"], "s.f")[0].severity == "error"


def test_none_value_yields_no_field_issue():
    assert validate_field_value(_field(FieldType.TEXT, max_words=2), None, "s.f") == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/artifact/test_field_validators.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'cidy.artifact.field_validators'`.

- [ ] **Step 3: Write the validators**

`backend/cidy/artifact/field_validators.py`:
```python
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/artifact/test_field_validators.py -v`
Expected: PASS (10 tests).

- [ ] **Step 5: Commit**

```bash
git add backend/cidy/artifact/field_validators.py backend/tests/artifact/test_field_validators.py
git commit -m "feat: add field-level value validators"
```

---

### Task 7: SDG target list validator

**Files:**
- Create: `backend/cidy/artifact/sdg_validator.py`
- Create: `backend/tests/artifact/test_sdg_validator.py`

**Interfaces:**
- Consumes: `Issue` (Task 6), `Constraints` (Task 2), `SDGFramework` (Task 4).
- Produces:
  - `validate_sdg_target_list(value: object, constraints: Constraints, framework: SDGFramework, path: str) -> list[Issue]` — checks: value is a list of strings; each code exists in `framework`; count ≤ `constraints.max_items` (when set); when `constraints.order == "ascending"`, codes are in ascending numeric order (goal, then target). `None`/empty yields no issue.

- [ ] **Step 1: Write the failing test**

`backend/tests/artifact/test_sdg_validator.py`:
```python
from cidy.artifact.sdg_validator import validate_sdg_target_list
from cidy.reference.sdg import load_sdg_framework
from cidy.schema.models import Constraints

FW = load_sdg_framework(
    {
        "goals": [
            {"goal": 1, "title": "No Poverty", "targets": [{"target": "1.2", "text": "..."}]},
            {
                "goal": 8,
                "title": "Decent Work",
                "targets": [
                    {"target": "8.5", "text": "..."},
                    {"target": "8.6", "text": "..."},
                ],
            },
        ]
    }
)


def test_valid_ascending_within_max():
    c = Constraints(max_items=10, order="ascending")
    assert validate_sdg_target_list(["1.2", "8.5", "8.6"], c, FW, "s.f") == []


def test_unknown_target_flagged():
    issues = validate_sdg_target_list(["9.9"], Constraints(), FW, "s.f")
    assert issues[0].severity == "error"
    assert "9.9" in issues[0].message


def test_too_many_items():
    c = Constraints(max_items=2)
    issues = validate_sdg_target_list(["1.2", "8.5", "8.6"], c, FW, "s.f")
    assert any("at most 2" in i.message for i in issues)


def test_not_ascending_flagged():
    c = Constraints(order="ascending")
    issues = validate_sdg_target_list(["8.6", "8.5"], c, FW, "s.f")
    assert any("ascending" in i.message for i in issues)


def test_none_is_ok():
    assert validate_sdg_target_list(None, Constraints(), FW, "s.f") == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/artifact/test_sdg_validator.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'cidy.artifact.sdg_validator'`.

- [ ] **Step 3: Write the validator**

`backend/cidy/artifact/sdg_validator.py`:
```python
from __future__ import annotations

from cidy.artifact.field_validators import Issue
from cidy.reference.sdg import SDGFramework
from cidy.schema.models import Constraints


def _sort_key(code: str) -> tuple[int, int]:
    goal, _, target = code.partition(".")
    return (int(goal), int(target or 0))


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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/artifact/test_sdg_validator.py -v`
Expected: PASS (5 tests).

- [ ] **Step 5: Commit**

```bash
git add backend/cidy/artifact/sdg_validator.py backend/tests/artifact/test_sdg_validator.py
git commit -m "feat: add SDG target list validator"
```

---

### Task 8: Artifact validation engine

**Files:**
- Create: `backend/cidy/artifact/validation.py`
- Create: `backend/tests/artifact/test_validation.py`

**Interfaces:**
- Consumes: `TemplateSchema`, `Section`, `Field`, `FieldType` (Task 2); `Artifact` (Task 5); `Issue`, `validate_field_value` (Task 6); `validate_sdg_target_list` (Task 7); `SDGFramework` (Task 4).
- Produces:
  - `ValidationReport(BaseModel)`: `issues: list[Issue]`, `required_total: int`, `required_filled: int`, `missing: list[str]` (paths of unfilled required fields). Property `is_valid -> bool` (no `error`-severity issues).
  - `validate_artifact(schema: TemplateSchema, artifact: Artifact, framework: SDGFramework) -> ValidationReport` — walks every section/field. For repeating sections, iterates each item dict and validates per-item fields with path `section_id[i].field_id`. Required fields that are absent/None/empty-string add a `missing` entry AND an `error` Issue. Dispatches `SDG_TARGET_LIST` to Task 7, other scalar types to Task 6. `REPEATING_GROUP` nested fields are validated recursively.

- [ ] **Step 1: Write the failing test**

`backend/tests/artifact/test_validation.py`:
```python
from cidy.artifact.models import Artifact
from cidy.artifact.validation import ValidationReport, validate_artifact
from cidy.reference.sdg import load_sdg_framework
from cidy.schema.models import (
    Constraints,
    Field,
    FieldType,
    Section,
    TemplateSchema,
)

FW = load_sdg_framework(
    {"goals": [{"goal": 8, "title": "Decent Work", "targets": [{"target": "8.5", "text": "..."}]}]}
)

SCHEMA = TemplateSchema(
    schema_id="demo",
    version="1",
    fund="DA",
    artifact_type="concept_note",
    title="Demo",
    sections=[
        Section(
            id="background",
            title="Background",
            fields=[
                Field(id="objective", label="Objective", type=FieldType.RICH_TEXT,
                      constraints=Constraints(required=True, max_words=3)),
                Field(id="sdgs", label="SDGs", type=FieldType.SDG_TARGET_LIST,
                      constraints=Constraints(max_items=10, order="ascending")),
            ],
        ),
        Section(
            id="outcomes",
            title="Outcomes",
            repeating=True,
            fields=[Field(id="outcome", label="Outcome", type=FieldType.TEXT,
                          constraints=Constraints(required=True))],
        ),
    ],
)


def test_valid_artifact_passes():
    art = Artifact(
        schema_id="demo", schema_version="1",
        values={
            "background": {"objective": "Improve health", "sdgs": ["8.5"]},
            "outcomes": [{"outcome": "OC1"}],
        },
    )
    report = validate_artifact(SCHEMA, art, FW)
    assert isinstance(report, ValidationReport)
    assert report.is_valid is True
    assert report.required_total == 2  # objective + one repeating outcome
    assert report.required_filled == 2


def test_missing_required_reported():
    art = Artifact(schema_id="demo", schema_version="1",
                   values={"background": {"sdgs": ["8.5"]}, "outcomes": []})
    report = validate_artifact(SCHEMA, art, FW)
    assert report.is_valid is False
    assert "background.objective" in report.missing


def test_field_constraint_violation_reported():
    art = Artifact(schema_id="demo", schema_version="1",
                   values={"background": {"objective": "one two three four", "sdgs": []},
                           "outcomes": [{"outcome": "OC1"}]})
    report = validate_artifact(SCHEMA, art, FW)
    assert any("words" in i.message and i.path == "background.objective" for i in report.issues)


def test_repeating_item_paths():
    art = Artifact(schema_id="demo", schema_version="1",
                   values={"background": {"objective": "ok", "sdgs": []},
                           "outcomes": [{"outcome": "OC1"}, {"outcome": ""}]})
    report = validate_artifact(SCHEMA, art, FW)
    assert "outcomes[1].outcome" in report.missing
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/artifact/test_validation.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'cidy.artifact.validation'`.

- [ ] **Step 3: Write the validation engine**

`backend/cidy/artifact/validation.py`:
```python
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/artifact/test_validation.py -v`
Expected: PASS (4 tests).

- [ ] **Step 5: Commit**

```bash
git add backend/cidy/artifact/validation.py backend/tests/artifact/test_validation.py
git commit -m "feat: add artifact validation engine"
```

---

### Task 9: Author the DA Concept Note Template Schema

**Files:**
- Create: `schemas/da-concept-note.v19.json`
- Create: `backend/tests/schemas/__init__.py`
- Create: `backend/tests/schemas/test_da_concept_note.py`

**Interfaces:**
- Consumes: `load_schema_file` (Task 3).
- Produces: a versioned DA Concept Note schema data file usable by all later phases.

**Reference:** transcribe the structure of `docs/templates/T19 Annex 1 - Template for Concept Notes.docx` (and its guideline limits) into the schema model. The test below pins the section ids that MUST be present; author every field shown in the template within each section using the field types from Task 2.

- [ ] **Step 1: Write the failing test**

`backend/tests/schemas/test_da_concept_note.py`:
```python
from pathlib import Path

from cidy.schema.loader import load_schema_file

SCHEMA_PATH = Path(__file__).resolve().parents[3] / "schemas" / "da-concept-note.v19.json"


def test_da_schema_loads():
    schema = load_schema_file(SCHEMA_PATH)
    assert schema.fund == "DA"
    assert schema.artifact_type == "concept_note"


def test_da_required_sections_present():
    schema = load_schema_file(SCHEMA_PATH)
    ids = {s.id for s in schema.sections}
    required = {
        "background",
        "fascicle_data",
        "outcomes_outputs",
        "un_coordination",
        "partnerships",
        "budget_narrative",
    }
    assert required.issubset(ids)


def test_background_has_sdg_target_list_max_10_ascending():
    schema = load_schema_file(SCHEMA_PATH)
    background = next(s for s in schema.sections if s.id == "background")
    sdg = next(f for f in background.fields if f.type.value == "sdg_target_list")
    assert sdg.constraints.max_items == 10
    assert sdg.constraints.order == "ascending"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/schemas/test_da_concept_note.py -v`
Expected: FAIL — `FileNotFoundError` (schema file not yet created).

- [ ] **Step 3: Author the schema file**

Create `backend/tests/schemas/__init__.py` (empty), then create `schemas/da-concept-note.v19.json`. Start from this skeleton and complete every field present in the template; the three sections shown are concrete and correct — fill the remaining listed sections the same way:
```json
{
  "schema_id": "da-concept-note",
  "version": "19th-tranche-2025-09",
  "fund": "DA",
  "artifact_type": "concept_note",
  "title": "Template for Concept Notes (19th Tranche of the Development Account)",
  "sections": [
    {
      "id": "background",
      "title": "Background",
      "guidance": "Max. 1.5 pages.",
      "fields": [
        {"id": "fascicle_title", "label": "Fascicle Note Title", "type": "text", "constraints": {"required": true}},
        {"id": "implementing_entity", "label": "Implemented by (Implementing Entity)", "type": "text", "constraints": {"required": true}},
        {"id": "joint_entities", "label": "Jointly with (joint implementing entities)", "type": "text"},
        {"id": "collaborating_entities", "label": "In collaboration with", "type": "text"},
        {"id": "total_budget", "label": "Total budget (USD thousands)", "type": "currency", "constraints": {"min_value": 0}},
        {"id": "sdg_targets", "label": "Relationship to SDGs: targets", "type": "sdg_target_list", "guidance": "List in ascending order, max. of 10.", "constraints": {"max_items": 10, "order": "ascending"}},
        {"id": "objective", "label": "Objective", "type": "rich_text", "constraints": {"required": true}},
        {"id": "project_plan", "label": "Project plan", "type": "rich_text", "constraints": {"required": true}},
        {"id": "expected_progress", "label": "Expected progress towards the objective and performance measures", "type": "rich_text", "constraints": {"required": true}}
      ]
    },
    {
      "id": "fascicle_data",
      "title": "Additional data needed for the fascicle",
      "guidance": "Do not change the categories or format.",
      "fields": [
        {"id": "sids", "label": "Supports SIDS", "type": "boolean"},
        {"id": "lldc", "label": "Supports LLDCs", "type": "boolean"},
        {"id": "ldc", "label": "Supports LDCs", "type": "boolean"},
        {"id": "regions", "label": "Regions supported", "type": "checkbox_group", "constraints": {"options": ["Africa", "Asia and the Pacific", "Middle East and North Africa", "Latin America and the Caribbean", "Europe and Central Asia"]}},
        {"id": "sdgs_contributed", "label": "SDGs the project contributes to", "type": "checkbox_group", "constraints": {"options": ["1","2","3","4","5","6","7","8","9","10","11","12","13","14","15","16","17"]}},
        {"id": "partnership_types", "label": "Partnership types", "type": "checkbox_group", "constraints": {"options": ["Development Account entities", "UN System (excluding RCOs)", "Other international/regional organizations"]}}
      ]
    },
    {
      "id": "outcomes_outputs",
      "title": "Outcomes and Outputs",
      "repeating": true,
      "fields": [
        {"id": "outcome", "label": "Outcome (OC)", "type": "rich_text", "constraints": {"required": true}},
        {"id": "outputs", "label": "Outputs", "type": "repeating_group", "fields": [
          {"id": "output", "label": "Output (OP)", "type": "rich_text", "constraints": {"required": true}}
        ]}
      ]
    },
    {
      "id": "un_coordination",
      "title": "UN system coordination",
      "guidance": "Engagement with RCOs.",
      "fields": [
        {"id": "rco_country", "label": "Target country", "type": "text"},
        {"id": "rco_involvement", "label": "Brief description of planned RCO involvement", "type": "rich_text"}
      ]
    },
    {
      "id": "partnerships",
      "title": "Partnerships",
      "fields": [
        {"id": "partnerships_text", "label": "Partnerships", "type": "rich_text"}
      ]
    },
    {
      "id": "budget_narrative",
      "title": "Budget narrative",
      "guidance": "By budget class (015, 105, 115, 120, 125, 145).",
      "fields": [
        {"id": "gta_015", "label": "Other staff costs - GTA (015)", "type": "rich_text"},
        {"id": "consultants_105", "label": "Consultants (105)", "type": "rich_text"},
        {"id": "travel_115", "label": "Travel of staff (115)", "type": "rich_text"},
        {"id": "contractual_120", "label": "Contractual services (120)", "type": "rich_text"},
        {"id": "goe_125", "label": "General operating expenses (125)", "type": "rich_text"},
        {"id": "grants_145", "label": "Grants and contributions (145)", "type": "rich_text"}
      ]
    }
  ]
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/schemas/test_da_concept_note.py -v`
Expected: PASS (3 tests).

- [ ] **Step 5: Commit**

```bash
git add schemas/da-concept-note.v19.json backend/tests/schemas
git commit -m "feat: author DA Concept Note template schema"
```

---

### Task 10: Author the RPTC Activity Proposal Template Schema

**Files:**
- Create: `schemas/rptc-activity-proposal.v2024.json`
- Create: `backend/tests/schemas/test_rptc_proposal.py`

**Interfaces:**
- Consumes: `load_schema_file` (Task 3).
- Produces: a versioned RPTC Activity Proposal schema data file.

**Reference:** transcribe `docs/templates/rptc_activity_proposal_template_docx_2.docx`. The test pins required section ids; author every field shown in the template.

- [ ] **Step 1: Write the failing test**

`backend/tests/schemas/test_rptc_proposal.py`:
```python
from pathlib import Path

from cidy.schema.loader import load_schema_file

SCHEMA_PATH = (
    Path(__file__).resolve().parents[3] / "schemas" / "rptc-activity-proposal.v2024.json"
)


def test_rptc_schema_loads():
    schema = load_schema_file(SCHEMA_PATH)
    assert schema.fund == "RPTC"
    assert schema.artifact_type == "activity_proposal"


def test_rptc_required_sections_present():
    schema = load_schema_file(SCHEMA_PATH)
    ids = {s.id for s in schema.sections}
    required = {
        "cover_sheet",
        "problem_analysis",
        "desa_mandate",
        "sdgs",
        "target_group",
        "capacities",
        "activities",
        "coherence",
        "inclusion",
        "inputs",
        "financials",
    }
    assert required.issubset(ids)


def test_brief_description_word_limit():
    schema = load_schema_file(SCHEMA_PATH)
    cover = next(s for s in schema.sections if s.id == "cover_sheet")
    brief = next(f for f in cover.fields if f.id == "brief_description")
    assert brief.constraints.max_words == 300
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/schemas/test_rptc_proposal.py -v`
Expected: FAIL — `FileNotFoundError`.

- [ ] **Step 3: Author the schema file**

Create `schemas/rptc-activity-proposal.v2024.json`. The skeleton below is concrete and correct for the pinned sections; complete every field present in the template:
```json
{
  "schema_id": "rptc-activity-proposal",
  "version": "2024",
  "fund": "RPTC",
  "artifact_type": "activity_proposal",
  "title": "RPTC Activity Proposal",
  "sections": [
    {
      "id": "cover_sheet",
      "title": "Cover Sheet",
      "fields": [
        {"id": "project_id", "label": "Project ID (SB-XX)", "type": "text"},
        {"id": "implementing_division", "label": "Implementing Division", "type": "text", "constraints": {"required": true}},
        {"id": "branch_name", "label": "Branch Name", "type": "text"},
        {"id": "brief_description", "label": "Brief description of proposal", "type": "rich_text", "guidance": "300 words max.", "constraints": {"required": true, "max_words": 300}},
        {"id": "proposed_budget", "label": "Proposed Budget (USD)", "type": "currency", "constraints": {"required": true, "min_value": 0}},
        {"id": "level_of_intervention", "label": "Level of intervention", "type": "single_select", "constraints": {"options": ["Global", "Regional", "Sub regional", "National"]}},
        {"id": "countries", "label": "Countries", "type": "multi_select", "constraints": {"options": []}},
        {"id": "nature_of_demand", "label": "Nature of demand", "type": "text"},
        {"id": "meeting_type", "label": "Meeting Type", "type": "single_select", "constraints": {"options": ["In person", "Virtual", "N/A"]}},
        {"id": "venue_location", "label": "Venue Location", "type": "text"},
        {"id": "focal_point_name", "label": "Focal point name", "type": "text", "constraints": {"required": true}},
        {"id": "focal_point_email", "label": "Focal point email", "type": "text", "constraints": {"required": true}}
      ]
    },
    {
      "id": "problem_analysis",
      "title": "Problem analysis",
      "fields": [{"id": "problem_analysis", "label": "Problem analysis", "type": "rich_text", "constraints": {"required": true}}]
    },
    {
      "id": "desa_mandate",
      "title": "DESA mandate and expected results",
      "repeating": true,
      "fields": [
        {"id": "mandate", "label": "Mandate", "type": "rich_text", "constraints": {"required": true}},
        {"id": "contribution", "label": "RPTC Activity Contribution", "type": "rich_text", "constraints": {"required": true}}
      ]
    },
    {
      "id": "sdgs",
      "title": "SDGs",
      "fields": [{"id": "sdg_targets", "label": "Most relevant SDG targets", "type": "sdg_target_list", "constraints": {"required": true}}]
    },
    {
      "id": "target_group",
      "title": "Target group",
      "fields": [{"id": "target_group", "label": "Target group", "type": "rich_text", "constraints": {"required": true}}]
    },
    {
      "id": "capacities",
      "title": "Capacities to be developed",
      "repeating": true,
      "fields": [
        {"id": "capacity", "label": "Capacity Description", "type": "rich_text", "constraints": {"required": true}},
        {"id": "indicator", "label": "Indicator", "type": "rich_text", "constraints": {"required": true}}
      ]
    },
    {
      "id": "activities",
      "title": "Main activities and timelines",
      "repeating": true,
      "fields": [
        {"id": "activity_title", "label": "Activity Title", "type": "text", "constraints": {"required": true}},
        {"id": "start_quarter", "label": "Planned Start Quarter", "type": "single_select", "constraints": {"options": ["Q1", "Q2", "Q3", "Q4"]}},
        {"id": "start_year", "label": "Planned Start Year", "type": "number"},
        {"id": "end_quarter", "label": "Planned End Quarter", "type": "single_select", "constraints": {"options": ["Q1", "Q2", "Q3", "Q4"]}},
        {"id": "end_year", "label": "Planned End Year", "type": "number"}
      ]
    },
    {
      "id": "coherence",
      "title": "Coherence and complementary work",
      "fields": [{"id": "coherence", "label": "Coherence and complementary work", "type": "rich_text"}]
    },
    {
      "id": "inclusion",
      "title": "Gender equality, human rights, disability inclusion and Leave No One Behind",
      "fields": [
        {"id": "narrative", "label": "Analysis narrative", "type": "rich_text"},
        {"id": "gender_rating", "label": "Gender rating", "type": "rating_scale", "constraints": {"options": ["0", "1", "2a", "2b"]}},
        {"id": "disability_rating", "label": "Disability rating", "type": "rating_scale", "constraints": {"options": ["0", "1", "2a", "2b"]}}
      ]
    },
    {
      "id": "inputs",
      "title": "Inputs",
      "fields": [
        {"id": "desa_inkind", "label": "DESA in-kind", "type": "rich_text"},
        {"id": "desa_cash", "label": "DESA cash", "type": "rich_text"},
        {"id": "recipient_inkind", "label": "Recipient Governments in-kind", "type": "rich_text"},
        {"id": "recipient_cash", "label": "Recipient Governments cash", "type": "rich_text"},
        {"id": "other_inkind", "label": "Other stakeholders in-kind", "type": "rich_text"},
        {"id": "other_cash", "label": "Other stakeholders cash", "type": "rich_text"}
      ]
    },
    {
      "id": "financials",
      "title": "Financial Requirements",
      "fields": [
        {"id": "staff_travel", "label": "Staff travel", "type": "currency", "constraints": {"min_value": 0}},
        {"id": "participants_travel", "label": "Participants travel", "type": "currency", "constraints": {"min_value": 0}},
        {"id": "consultants", "label": "Consultants", "type": "currency", "constraints": {"min_value": 0}},
        {"id": "conference_services", "label": "Conference services", "type": "currency", "constraints": {"min_value": 0}},
        {"id": "total", "label": "Total Project Cost", "type": "currency", "constraints": {"required": true, "min_value": 0}}
      ]
    }
  ]
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/schemas/test_rptc_proposal.py -v`
Expected: PASS (3 tests).

- [ ] **Step 5: Commit**

```bash
git add schemas/rptc-activity-proposal.v2024.json backend/tests/schemas/test_rptc_proposal.py
git commit -m "feat: author RPTC Activity Proposal template schema"
```

---

### Task 11: Seed the SDG framework reference data

**Files:**
- Create: `data/sdg_framework.json`
- Create: `backend/tests/reference/test_sdg_framework_data.py`

**Interfaces:**
- Consumes: `load_sdg_framework_file` (Task 4).
- Produces: the bundled SDG reference data file used by validation and (later) suggestion.

**Reference:** populate from the official UN SDG indicator framework (17 goals, 169 targets) — authoritative source: <https://unstats.un.org/sdgs/indicators/Global-Indicator-Framework>. Use the lettered/numbered target codes as the UN lists them (e.g., `8.5`, `8.a`). The test pins counts and a couple of known targets.

- [ ] **Step 1: Write the failing test**

`backend/tests/reference/test_sdg_framework_data.py`:
```python
from pathlib import Path

from cidy.reference.sdg import load_sdg_framework_file

DATA_PATH = Path(__file__).resolve().parents[3] / "data" / "sdg_framework.json"


def test_framework_loads_all_goals():
    fw = load_sdg_framework_file(DATA_PATH)
    goals = {g.goal for g in fw.goals}
    assert goals == set(range(1, 18))  # goals 1..17


def test_framework_has_169_targets():
    fw = load_sdg_framework_file(DATA_PATH)
    assert len(fw.all_target_codes()) == 169


def test_known_targets_present():
    fw = load_sdg_framework_file(DATA_PATH)
    assert fw.has_target("8.5")
    assert fw.has_target("1.1")
    assert fw.has_target("17.1")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/reference/test_sdg_framework_data.py -v`
Expected: FAIL — `FileNotFoundError`.

- [ ] **Step 3: Author the data file**

Create `data/sdg_framework.json` with all 17 goals and their 169 targets, in this shape (Goal 8 shown as the pattern — populate every goal/target from the authoritative source):
```json
{
  "goals": [
    {
      "goal": 8,
      "title": "Decent Work and Economic Growth",
      "targets": [
        {"target": "8.1", "text": "Sustain per capita economic growth in accordance with national circumstances..."},
        {"target": "8.5", "text": "By 2030, achieve full and productive employment and decent work for all..."},
        {"target": "8.6", "text": "By 2020, substantially reduce the proportion of youth not in employment, education or training."}
      ]
    }
  ]
}
```
The 169 targets include the lettered means-of-implementation targets (e.g., `8.a`, `17.18`). Ensure the total distinct target codes equals exactly 169 so the test passes.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/reference/test_sdg_framework_data.py -v`
Expected: PASS (3 tests).

- [ ] **Step 5: Run the full suite and commit**

Run: `cd backend && python -m pytest -v`
Expected: all tests across Tasks 1–11 PASS.

```bash
git add data/sdg_framework.json backend/tests/reference/test_sdg_framework_data.py
git commit -m "feat: seed SDG framework reference data"
```

---

## Phase 1 completion

At the end of this plan the repository contains a tested, dependency-free `cidy` core
library that can: load and validate Template Schemas, model and round-trip canonical
artifacts, load SDG reference data, validate artifact content (field constraints, SDG
target lists, required fields, repeating groups) with a completeness report, and two
authored real-world schemas (DA Concept Note, RPTC Activity Proposal) plus the full SDG
framework. This is the foundation Phase 2 (persistence + API + auth) builds on.

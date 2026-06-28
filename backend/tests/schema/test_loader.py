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

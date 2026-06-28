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

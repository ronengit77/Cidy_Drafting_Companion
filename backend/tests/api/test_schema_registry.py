from cidy_api import schema_registry


def test_list_schemas_includes_da_and_rptc():
    infos = schema_registry.list_schemas()
    ids = {i.schema_id for i in infos}
    assert "da-concept-note" in ids
    assert "rptc-activity-proposal" in ids
    funds = {i.fund for i in infos}
    assert {"DA", "RPTC"} <= funds


def test_get_schema_returns_template_schema():
    schema = schema_registry.get_schema("rptc-activity-proposal")
    assert schema is not None
    assert schema.fund == "RPTC"
    assert any(s.id == "cover_sheet" for s in schema.sections)


def test_get_schema_unknown_is_none():
    assert schema_registry.get_schema("nope") is None


def test_get_sdg_framework_has_169_targets():
    fw = schema_registry.get_sdg_framework()
    assert len(fw.all_target_codes()) == 169

from pathlib import Path

import yaml

TEMPLATE = Path(__file__).resolve().parents[3] / "template.yaml"


class _CfnLoader(yaml.SafeLoader):
    pass


def _ignore_cfn_tag(loader, tag_suffix, node):
    if isinstance(node, yaml.ScalarNode):
        return loader.construct_scalar(node)
    if isinstance(node, yaml.SequenceNode):
        return loader.construct_sequence(node)
    return loader.construct_mapping(node)


_CfnLoader.add_multi_constructor("!", _ignore_cfn_tag)


def _load() -> dict:
    return yaml.load(TEMPLATE.read_text(encoding="utf-8"), Loader=_CfnLoader)


def test_is_sam_template():
    assert _load()["Transform"] == "AWS::Serverless-2016-10-31"


def test_function_runtime_handler_and_prod_env():
    fn = _load()["Resources"]["CidyFunction"]
    assert fn["Type"] == "AWS::Serverless::Function"
    assert fn["Properties"]["Runtime"] == "python3.12"
    assert fn["Properties"]["Handler"] == "cidy_api.lambda_handler.handler"
    env = fn["Properties"]["Environment"]["Variables"]
    assert env["CIDY_DEV_MODE"] == "false"
    assert "CIDY_DATABASE_URL" in env and "CIDY_JWT_SECRET" in env


def test_database_is_postgres():
    db = _load()["Resources"]["CidyDatabase"]
    assert db["Type"] == "AWS::RDS::DBInstance"
    assert db["Properties"]["Engine"] == "postgres"


def test_jwt_secret_param_is_noecho_min32():
    p = _load()["Parameters"]["JwtSecret"]
    assert p["NoEcho"] is True
    assert p["MinLength"] == 32


def test_requirements_lists_runtime_deps():
    reqs = (Path(__file__).resolve().parents[2] / "requirements.txt").read_text(encoding="utf-8")
    for pkg in ("fastapi", "mangum", "sqlalchemy", "psycopg", "pydantic", "pyjwt"):
        assert pkg in reqs


def test_schema_and_data_dirs_are_inside_code_uri():
    # CodeUri is backend/; the app reads these at runtime, so they must be packaged.
    backend_root = Path(__file__).resolve().parents[2]
    assert (backend_root / "schemas").is_dir()
    assert (backend_root / "data" / "sdg_framework.json").is_file()

from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def test_samconfig_exists():
    assert (ROOT / "samconfig.toml").exists()


def test_deploy_md_covers_key_steps():
    text = (ROOT / "DEPLOY.md").read_text(encoding="utf-8").lower()
    for needle in [
        "sam build",
        "sam deploy",
        "alembic upgrade head",
        "cidy_jwt_secret",
        "cidy_dev_mode",
        "sam delete",
        "ses",
        "aurora",
    ]:
        assert needle in text, f"DEPLOY.md is missing: {needle}"

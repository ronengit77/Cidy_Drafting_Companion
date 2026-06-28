import pytest
from pydantic import ValidationError

from cidy_api.config import DEV_JWT_SECRET, Settings


def test_dev_mode_allows_default_secret():
    s = Settings(dev_mode=True)
    assert s.jwt_secret == DEV_JWT_SECRET  # default
    assert len(DEV_JWT_SECRET.encode("utf-8")) >= 32


def test_prod_rejects_dev_default_secret():
    with pytest.raises(ValidationError):
        Settings(dev_mode=False, jwt_secret=DEV_JWT_SECRET)


def test_prod_rejects_short_secret():
    with pytest.raises(ValidationError):
        Settings(dev_mode=False, jwt_secret="too-short")


def test_prod_accepts_strong_secret():
    s = Settings(dev_mode=False, jwt_secret="a" * 40)
    assert s.dev_mode is False

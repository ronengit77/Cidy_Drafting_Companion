import uuid
from datetime import datetime, timedelta, timezone

import pytest

from cidy_api import auth


def test_generate_and_hash_consistency():
    raw, hashed = auth.generate_magic_token()
    assert auth.hash_token(raw) == hashed
    assert len(hashed) == 64  # sha256 hexdigest


def test_jwt_round_trip():
    uid = uuid.uuid4()
    token = auth.create_jwt(uid)
    assert auth.decode_jwt(token) == uid


def test_jwt_expired_rejected():
    uid = uuid.uuid4()
    past = datetime.now(timezone.utc) - timedelta(hours=2)
    token = auth.create_jwt(uid, now=past)
    with pytest.raises(auth.AuthError):
        auth.decode_jwt(token)


def test_jwt_tampered_rejected():
    with pytest.raises(auth.AuthError):
        auth.decode_jwt("not.a.jwt")

from datetime import datetime, timedelta, timezone

from cidy_api.repositories import auth_tokens, users


def test_get_or_create_is_idempotent_and_normalizes(db_session):
    u1 = users.get_or_create_by_email(db_session, "  Bob@Example.com ")
    u2 = users.get_or_create_by_email(db_session, "bob@example.com")
    assert u1.id == u2.id
    assert u1.email == "bob@example.com"


def test_touch_last_login(db_session):
    u = users.get_or_create_by_email(db_session, "c@example.com")
    assert u.last_login_at is None
    users.touch_last_login(db_session, u)
    assert u.last_login_at is not None


def test_consume_token_happy_path(db_session):
    u = users.get_or_create_by_email(db_session, "d@example.com")
    exp = datetime.now(timezone.utc) + timedelta(minutes=15)
    auth_tokens.create_token(db_session, u.id, "hash-1", exp)

    consumed = auth_tokens.consume_token(db_session, "hash-1")
    assert consumed is not None
    assert consumed.consumed_at is not None
    # second use fails (single-use)
    assert auth_tokens.consume_token(db_session, "hash-1") is None


def test_consume_token_rejects_expired(db_session):
    u = users.get_or_create_by_email(db_session, "e@example.com")
    exp = datetime.now(timezone.utc) - timedelta(minutes=1)
    auth_tokens.create_token(db_session, u.id, "hash-2", exp)
    assert auth_tokens.consume_token(db_session, "hash-2") is None


def test_consume_token_unknown_hash(db_session):
    assert auth_tokens.consume_token(db_session, "nope") is None

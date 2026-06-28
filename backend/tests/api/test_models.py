import uuid
from datetime import datetime, timedelta, timezone

from cidy_api.models_db import AuthToken, User


def test_create_user_and_token(db_session):
    user = User(email="a@example.com")
    db_session.add(user)
    db_session.flush()
    assert isinstance(user.id, uuid.UUID)
    assert user.created_at.tzinfo is not None

    token = AuthToken(
        user_id=user.id,
        token_hash="deadbeef",
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=15),
    )
    db_session.add(token)
    db_session.flush()

    loaded = db_session.get(User, user.id)
    assert loaded.email == "a@example.com"
    assert db_session.get(AuthToken, token.id).consumed_at is None


def test_commit_inside_test_stays_isolated(db_session):
    from sqlalchemy import select, func
    from cidy_api.db import engine
    from cidy_api.models_db import User

    db_session.add(User(email="isolated@example.com"))
    db_session.commit()  # would escape the outer txn without create_savepoint
    # a separate connection (outside the test's transaction) must NOT see it
    with engine.connect() as outside:
        count = outside.execute(
            select(func.count()).select_from(User.__table__).where(User.email == "isolated@example.com")
        ).scalar_one()
    assert count == 0

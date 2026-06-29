import pytest

from cidy_api.repositories import artifacts, users


def _mk(db_session):
    owner = users.get_or_create_by_email(db_session, "ver@example.com")
    art = artifacts.create_artifact(
        db_session, owner_id=owner.id, schema_id="s", schema_version="1",
        title="v1", content={"n": 1},
    )
    return owner, art


def test_update_bumps_version_and_snapshots(db_session):
    owner, art = _mk(db_session)
    updated = artifacts.update_artifact(
        db_session, art, expected_version_no=1, title="v2", content={"n": 2}, author_id=owner.id
    )
    assert updated.version_no == 2
    assert updated.content == {"n": 2}
    versions = artifacts.list_versions(db_session, art.id)
    assert len(versions) == 1
    assert versions[0].version_no == 1
    assert versions[0].content == {"n": 1}


def test_update_stale_version_conflicts(db_session):
    owner, art = _mk(db_session)
    artifacts.update_artifact(
        db_session, art, expected_version_no=1, title="v2", content={"n": 2}, author_id=owner.id
    )
    with pytest.raises(artifacts.ConflictError):
        artifacts.update_artifact(
            db_session, art, expected_version_no=1, title="x", content={"n": 9}, author_id=owner.id
        )


def test_restore_creates_new_version_from_old(db_session):
    owner, art = _mk(db_session)
    artifacts.update_artifact(
        db_session, art, expected_version_no=1, title="v2", content={"n": 2}, author_id=owner.id
    )
    restored = artifacts.restore_version(db_session, art, 1, author_id=owner.id)
    assert restored.version_no == 3
    assert restored.content == {"n": 1}  # back to v1 content


def test_restore_unknown_version_raises(db_session):
    owner, art = _mk(db_session)
    with pytest.raises(artifacts.VersionNotFound):
        artifacts.restore_version(db_session, art, 99, author_id=owner.id)

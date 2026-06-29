from cidy_api.models_db import ArtifactCollaborator
from cidy_api.repositories import artifacts, users


def _mk(db_session, owner, title="t"):
    return artifacts.create_artifact(
        db_session, owner_id=owner.id, schema_id="s", schema_version="1",
        title=title, content={"a": 1},
    )


def test_create_and_get(db_session):
    owner = users.get_or_create_by_email(db_session, "ro@example.com")
    art = _mk(db_session, owner)
    assert art.version_no == 1
    assert artifacts.get_artifact(db_session, art.id).content == {"a": 1}


def test_list_includes_owned_and_collaborated(db_session):
    owner = users.get_or_create_by_email(db_session, "ro2@example.com")
    other = users.get_or_create_by_email(db_session, "ro3@example.com")
    mine = _mk(db_session, owner, "mine")
    theirs = _mk(db_session, other, "theirs")
    db_session.add(ArtifactCollaborator(artifact_id=theirs.id, user_id=owner.id, role="editor"))
    db_session.flush()
    ids = {a.id for a in artifacts.list_for_user(db_session, owner.id)}
    assert mine.id in ids
    assert theirs.id in ids


def test_list_excludes_unrelated(db_session):
    owner = users.get_or_create_by_email(db_session, "ro4@example.com")
    stranger = users.get_or_create_by_email(db_session, "ro5@example.com")
    _mk(db_session, stranger, "not mine")
    assert artifacts.list_for_user(db_session, owner.id) == []

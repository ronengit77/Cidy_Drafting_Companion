import uuid

import pytest
from fastapi import HTTPException

from cidy_api import authz
from cidy_api.models_db import ArtifactCollaborator
from cidy_api.repositories import artifacts, users


def _setup(db_session):
    owner = users.get_or_create_by_email(db_session, "ow@example.com")
    editor = users.get_or_create_by_email(db_session, "ed@example.com")
    reviewer = users.get_or_create_by_email(db_session, "rv@example.com")
    stranger = users.get_or_create_by_email(db_session, "st@example.com")
    art = artifacts.create_artifact(
        db_session, owner_id=owner.id, schema_id="s", schema_version="1", title="t", content={}
    )
    db_session.add(ArtifactCollaborator(artifact_id=art.id, user_id=editor.id, role="editor"))
    db_session.add(ArtifactCollaborator(artifact_id=art.id, user_id=reviewer.id, role="reviewer"))
    db_session.flush()
    return owner, editor, reviewer, stranger, art


def test_access_levels(db_session):
    owner, editor, reviewer, stranger, art = _setup(db_session)
    assert authz.access_level(db_session, owner, art) == "owner"
    assert authz.access_level(db_session, editor, art) == "editor"
    assert authz.access_level(db_session, reviewer, art) == "reviewer"
    assert authz.access_level(db_session, stranger, art) is None


def test_require_read_allows_all_members(db_session):
    owner, editor, reviewer, stranger, art = _setup(db_session)
    for u in (owner, editor, reviewer):
        assert authz.require_artifact(db_session, u, art.id, "read").id == art.id
    with pytest.raises(HTTPException) as exc:
        authz.require_artifact(db_session, stranger, art.id, "read")
    assert exc.value.status_code == 403


def test_require_edit_excludes_reviewer(db_session):
    owner, editor, reviewer, stranger, art = _setup(db_session)
    assert authz.require_artifact(db_session, editor, art.id, "edit").id == art.id
    with pytest.raises(HTTPException) as exc:
        authz.require_artifact(db_session, reviewer, art.id, "edit")
    assert exc.value.status_code == 403


def test_require_own_only_owner(db_session):
    owner, editor, reviewer, stranger, art = _setup(db_session)
    assert authz.require_artifact(db_session, owner, art.id, "own").id == art.id
    with pytest.raises(HTTPException) as exc:
        authz.require_artifact(db_session, editor, art.id, "own")
    assert exc.value.status_code == 403


def test_require_missing_artifact_404(db_session):
    owner, *_ = _setup(db_session)
    with pytest.raises(HTTPException) as exc:
        authz.require_artifact(db_session, owner, uuid.uuid4(), "read")
    assert exc.value.status_code == 404

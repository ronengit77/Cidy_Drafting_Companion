from cidy_api.models_db import Artifact, ArtifactCollaborator, ArtifactVersion, User
from cidy_api.repositories import users


def test_create_artifact_with_jsonb_content(db_session):
    owner = users.get_or_create_by_email(db_session, "owner@example.com")
    art = Artifact(
        owner_id=owner.id,
        schema_id="rptc-activity-proposal",
        schema_version="2024",
        title="Draft 1",
        content={"cover_sheet": {"proposed_budget": 50000}},
    )
    db_session.add(art)
    db_session.flush()
    assert art.version_no == 1
    assert art.status == "draft"
    loaded = db_session.get(Artifact, art.id)
    assert loaded.content["cover_sheet"]["proposed_budget"] == 50000


def test_version_and_collaborator_rows(db_session):
    owner = users.get_or_create_by_email(db_session, "o2@example.com")
    collab = users.get_or_create_by_email(db_session, "c2@example.com")
    art = Artifact(owner_id=owner.id, schema_id="s", schema_version="1")
    db_session.add(art)
    db_session.flush()
    db_session.add(ArtifactVersion(
        artifact_id=art.id, version_no=1, title="", content={}, author_id=owner.id
    ))
    db_session.add(ArtifactCollaborator(artifact_id=art.id, user_id=collab.id, role="editor"))
    db_session.flush()
    assert db_session.get(Artifact, art.id) is not None

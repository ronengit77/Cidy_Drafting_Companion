def _login(client, email):
    link = client.post("/auth/magic-link", json={"email": email}).json()["dev_link"]
    raw = link.split("token=", 1)[1]
    return client.post("/auth/verify", json={"token": raw}).json()["access_token"]


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


def _new_artifact(client, token):
    resp = client.post(
        "/artifacts",
        json={"schema_id": "rptc-activity-proposal", "title": "t"},
        headers=_auth(token),
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


def test_owner_adds_and_lists_collaborator(client):
    owner_t = _login(client, "co_owner@example.com")
    _login(client, "co_editor@example.com")  # ensure user exists
    art_id = _new_artifact(client, owner_t)

    add = client.post(
        f"/artifacts/{art_id}/collaborators",
        json={"email": "co_editor@example.com", "role": "editor"},
        headers=_auth(owner_t),
    )
    assert add.status_code == 200, add.text
    assert add.json()["role"] == "editor"

    listed = client.get(f"/artifacts/{art_id}/collaborators", headers=_auth(owner_t))
    assert listed.status_code == 200
    assert any(c["email"] == "co_editor@example.com" for c in listed.json())


def test_non_owner_cannot_add(client):
    owner_t = _login(client, "co_owner2@example.com")
    other_t = _login(client, "co_other@example.com")
    art_id = _new_artifact(client, owner_t)
    resp = client.post(
        f"/artifacts/{art_id}/collaborators",
        json={"email": "x@example.com", "role": "editor"},
        headers=_auth(other_t),
    )
    assert resp.status_code in (403, 404)


def test_remove_collaborator(client):
    owner_t = _login(client, "co_owner3@example.com")
    _login(client, "co_rm@example.com")
    art_id = _new_artifact(client, owner_t)
    client.post(
        f"/artifacts/{art_id}/collaborators",
        json={"email": "co_rm@example.com", "role": "reviewer"},
        headers=_auth(owner_t),
    )
    # fetch the collaborator's user_id from the list
    user_id = client.get(f"/artifacts/{art_id}/collaborators", headers=_auth(owner_t)).json()[0]["user_id"]
    rm = client.delete(f"/artifacts/{art_id}/collaborators/{user_id}", headers=_auth(owner_t))
    assert rm.status_code == 204


from cidy_api.repositories import artifacts, collaborators, users


def test_add_update_remove_collaborator_repo(db_session):
    owner = users.get_or_create_by_email(db_session, "repo_owner@example.com")
    collab = users.get_or_create_by_email(db_session, "repo_collab@example.com")
    art = artifacts.create_artifact(
        db_session, owner_id=owner.id, schema_id="s", schema_version="1", title="t", content={}
    )
    collaborators.add_collaborator(db_session, art.id, collab.id, "editor")
    rows = collaborators.list_collaborators(db_session, art.id)
    assert len(rows) == 1 and rows[0].role == "editor"
    collaborators.add_collaborator(db_session, art.id, collab.id, "reviewer")  # upsert
    assert collaborators.list_collaborators(db_session, art.id)[0].role == "reviewer"
    assert collaborators.remove_collaborator(db_session, art.id, collab.id) is True
    assert collaborators.list_collaborators(db_session, art.id) == []

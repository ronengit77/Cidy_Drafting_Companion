def _login(client, email):
    link = client.post("/auth/magic-link", json={"email": email}).json()["dev_link"]
    raw = link.split("token=", 1)[1]
    return client.post("/auth/verify", json={"token": raw}).json()["access_token"]


def _auth(t):
    return {"Authorization": f"Bearer {t}"}


def test_create_list_get(client):
    t = _login(client, "ar_owner@example.com")
    created = client.post(
        "/artifacts", json={"schema_id": "rptc-activity-proposal", "title": "My draft"}, headers=_auth(t)
    )
    assert created.status_code == 201, created.text
    art = created.json()
    assert art["schema_version"] == "2024"
    assert art["version_no"] == 1

    listed = client.get("/artifacts", headers=_auth(t))
    assert any(a["id"] == art["id"] for a in listed.json())

    got = client.get(f"/artifacts/{art['id']}", headers=_auth(t))
    assert got.status_code == 200
    assert got.json()["title"] == "My draft"


def test_create_unknown_schema_400(client):
    t = _login(client, "ar_bad@example.com")
    resp = client.post("/artifacts", json={"schema_id": "nope", "title": "x"}, headers=_auth(t))
    assert resp.status_code == 400


def test_update_optimistic_conflict(client):
    t = _login(client, "ar_upd@example.com")
    art = client.post(
        "/artifacts", json={"schema_id": "rptc-activity-proposal", "title": "v1"}, headers=_auth(t)
    ).json()
    ok = client.put(
        f"/artifacts/{art['id']}",
        json={"expected_version_no": 1, "title": "v2", "content": {"cover_sheet": {"proposed_budget": 1}}},
        headers=_auth(t),
    )
    assert ok.status_code == 200
    assert ok.json()["version_no"] == 2
    stale = client.put(
        f"/artifacts/{art['id']}",
        json={"expected_version_no": 1, "title": "v3", "content": {}},
        headers=_auth(t),
    )
    assert stale.status_code == 409


def test_versions_and_restore(client):
    t = _login(client, "ar_ver@example.com")
    art = client.post(
        "/artifacts", json={"schema_id": "rptc-activity-proposal", "title": "v1"}, headers=_auth(t)
    ).json()
    client.put(
        f"/artifacts/{art['id']}",
        json={"expected_version_no": 1, "title": "v2", "content": {"x": 2}},
        headers=_auth(t),
    )
    versions = client.get(f"/artifacts/{art['id']}/versions", headers=_auth(t))
    assert versions.status_code == 200
    assert versions.json()[0]["version_no"] == 1
    restored = client.post(f"/artifacts/{art['id']}/versions/1/restore", headers=_auth(t))
    assert restored.status_code == 200
    assert restored.json()["version_no"] == 3


def test_get_requires_access(client):
    owner_t = _login(client, "ar_o@example.com")
    other_t = _login(client, "ar_x@example.com")
    art = client.post(
        "/artifacts", json={"schema_id": "rptc-activity-proposal", "title": "p"}, headers=_auth(owner_t)
    ).json()
    assert client.get(f"/artifacts/{art['id']}", headers=_auth(other_t)).status_code in (403, 404)

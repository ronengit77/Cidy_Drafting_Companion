def _login(client, email):
    link = client.post("/auth/magic-link", json={"email": email}).json()["dev_link"]
    raw = link.split("token=", 1)[1]
    return client.post("/auth/verify", json={"token": raw}).json()["access_token"]


def _auth(t):
    return {"Authorization": f"Bearer {t}"}


def test_check_reports_missing_required(client):
    t = _login(client, "val@example.com")
    art = client.post(
        "/artifacts", json={"schema_id": "rptc-activity-proposal", "title": "p"}, headers=_auth(t)
    ).json()
    resp = client.post(f"/artifacts/{art['id']}/check", headers=_auth(t))
    assert resp.status_code == 200
    body = resp.json()
    assert body["is_valid"] is False  # empty content -> required fields missing
    assert body["required_total"] > 0
    assert any(m == "cover_sheet.brief_description" for m in body["missing"])


def test_check_requires_access(client):
    owner_t = _login(client, "val_o@example.com")
    other_t = _login(client, "val_x@example.com")
    art = client.post(
        "/artifacts", json={"schema_id": "rptc-activity-proposal", "title": "p"}, headers=_auth(owner_t)
    ).json()
    assert client.post(f"/artifacts/{art['id']}/check", headers=_auth(other_t)).status_code in (403, 404)

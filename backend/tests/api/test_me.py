def _login(client, email):
    dev_link = client.post("/auth/magic-link", json={"email": email}).json()["dev_link"]
    raw = dev_link.split("token=", 1)[1]
    return client.post("/auth/verify", json={"token": raw}).json()["access_token"]


def test_me_requires_auth(client):
    assert client.get("/me").status_code == 401


def test_me_rejects_bad_token(client):
    resp = client.get("/me", headers={"Authorization": "Bearer garbage"})
    assert resp.status_code == 401


def test_me_returns_current_user(client):
    access = _login(client, "me@example.com")
    resp = client.get("/me", headers={"Authorization": f"Bearer {access}"})
    assert resp.status_code == 200
    assert resp.json()["email"] == "me@example.com"

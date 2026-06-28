from cidy_api import auth


def test_magic_link_returns_dev_link(client):
    resp = client.post("/auth/magic-link", json={"email": "user@example.com"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["sent"] is True
    assert body["dev_link"] and "token=" in body["dev_link"]


def test_full_login_flow(client):
    resp = client.post("/auth/magic-link", json={"email": "flow@example.com"})
    dev_link = resp.json()["dev_link"]
    raw_token = dev_link.split("token=", 1)[1]

    verify = client.post("/auth/verify", json={"token": raw_token})
    assert verify.status_code == 200
    access = verify.json()["access_token"]
    # JWT decodes to a real user id
    assert auth.decode_jwt(access)


def test_verify_rejects_bad_token(client):
    resp = client.post("/auth/verify", json={"token": "garbage"})
    assert resp.status_code == 401


def test_verify_is_single_use(client):
    dev_link = client.post("/auth/magic-link", json={"email": "once@example.com"}).json()["dev_link"]
    raw_token = dev_link.split("token=", 1)[1]
    assert client.post("/auth/verify", json={"token": raw_token}).status_code == 200
    assert client.post("/auth/verify", json={"token": raw_token}).status_code == 401

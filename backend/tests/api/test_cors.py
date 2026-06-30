def test_allowed_origin_gets_cors_header(client):
    resp = client.get("/health", headers={"Origin": "http://localhost:5173"})
    assert resp.status_code == 200
    assert resp.headers.get("access-control-allow-origin") == "http://localhost:5173"


def test_preflight_allows_authorized_request(client):
    resp = client.options(
        "/artifacts",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "authorization,content-type",
        },
    )
    assert resp.status_code == 200
    assert resp.headers.get("access-control-allow-origin") == "http://localhost:5173"


def test_unlisted_origin_not_reflected(client):
    resp = client.get("/health", headers={"Origin": "https://evil.example.com"})
    assert resp.status_code == 200
    assert resp.headers.get("access-control-allow-origin") != "https://evil.example.com"

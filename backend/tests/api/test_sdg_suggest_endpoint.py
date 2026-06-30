from cidy_api.llm.deps import get_llm_provider


class _StubProvider:
    def __init__(self, output):
        self._output = output

    def complete(self, system, user, *, max_tokens=600, temperature=0.3):
        return self._output


def _login(client, email):
    link = client.post("/auth/magic-link", json={"email": email}).json()["dev_link"]
    raw = link.split("token=", 1)[1]
    return client.post("/auth/verify", json={"token": raw}).json()["access_token"]


def _auth(t):
    return {"Authorization": f"Bearer {t}"}


def _new_artifact(client, t):
    resp = client.post(
        "/artifacts", json={"schema_id": "rptc-activity-proposal", "title": "t"}, headers=_auth(t)
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


def test_sdg_suggest_returns_validated_targets(client):
    # 8.5 is a real code in the bundled 169-target framework
    client.app.dependency_overrides[get_llm_provider] = lambda: _StubProvider(
        '{"suggestions": [{"target": "8.5", "rationale": "employment focus"}, {"target": "99.9", "rationale": "bogus"}]}'
    )
    t = _login(client, "sdg1@example.com")
    aid = _new_artifact(client, t)
    resp = client.post(f"/artifacts/{aid}/assist/sdg-suggest", headers=_auth(t))
    assert resp.status_code == 200, resp.text
    targets = [s["target"] for s in resp.json()["suggestions"]]
    assert targets == ["8.5"]  # bogus 99.9 dropped
    assert resp.json()["suggestions"][0]["title"]  # official title attached


def test_sdg_suggest_503_when_llm_not_configured(client):
    client.app.dependency_overrides[get_llm_provider] = lambda: None
    t = _login(client, "sdg2@example.com")
    aid = _new_artifact(client, t)
    resp = client.post(f"/artifacts/{aid}/assist/sdg-suggest", headers=_auth(t))
    assert resp.status_code == 503


def test_sdg_suggest_requires_access(client):
    client.app.dependency_overrides[get_llm_provider] = lambda: _StubProvider('{"suggestions": []}')
    owner = _login(client, "sdg_owner@example.com")
    other = _login(client, "sdg_other@example.com")
    aid = _new_artifact(client, owner)
    resp = client.post(f"/artifacts/{aid}/assist/sdg-suggest", headers=_auth(other))
    assert resp.status_code in (403, 404)

from cidy_api.llm.deps import get_llm_provider
from cidy_api.llm.fake import EchoLLMProvider


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


def test_shape_returns_text(client):
    client.app.dependency_overrides[get_llm_provider] = lambda: EchoLLMProvider()
    t = _login(client, "assist1@example.com")
    aid = _new_artifact(client, t)
    resp = client.post(
        f"/artifacts/{aid}/assist/shape",
        json={"section_id": "cover_sheet", "field_id": "brief_description", "raw_input": "train people"},
        headers=_auth(t),
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["shaped_text"] == "train people"  # echo


def test_shape_503_when_llm_not_configured(client):
    client.app.dependency_overrides[get_llm_provider] = lambda: None
    t = _login(client, "assist2@example.com")
    aid = _new_artifact(client, t)
    resp = client.post(
        f"/artifacts/{aid}/assist/shape",
        json={"section_id": "cover_sheet", "field_id": "brief_description", "raw_input": "x"},
        headers=_auth(t),
    )
    assert resp.status_code == 503


def test_shape_unknown_field_400(client):
    client.app.dependency_overrides[get_llm_provider] = lambda: EchoLLMProvider()
    t = _login(client, "assist3@example.com")
    aid = _new_artifact(client, t)
    resp = client.post(
        f"/artifacts/{aid}/assist/shape",
        json={"section_id": "cover_sheet", "field_id": "nope", "raw_input": "x"},
        headers=_auth(t),
    )
    assert resp.status_code == 400


def test_shape_requires_access(client):
    client.app.dependency_overrides[get_llm_provider] = lambda: EchoLLMProvider()
    owner = _login(client, "assist_owner@example.com")
    other = _login(client, "assist_other@example.com")
    aid = _new_artifact(client, owner)
    resp = client.post(
        f"/artifacts/{aid}/assist/shape",
        json={"section_id": "cover_sheet", "field_id": "brief_description", "raw_input": "x"},
        headers=_auth(other),
    )
    assert resp.status_code in (403, 404)


def test_coherence_returns_assessment(client):
    client.app.dependency_overrides[get_llm_provider] = lambda: EchoLLMProvider()
    t = _login(client, "assist4@example.com")
    aid = _new_artifact(client, t)
    resp = client.post(f"/artifacts/{aid}/assist/coherence", headers=_auth(t))
    assert resp.status_code == 200, resp.text
    assert "assessment" in resp.json()

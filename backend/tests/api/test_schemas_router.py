def test_list_schemas_endpoint(client):
    resp = client.get("/schemas")
    assert resp.status_code == 200
    ids = {row["schema_id"] for row in resp.json()}
    assert {"da-concept-note", "rptc-activity-proposal"} <= ids


def test_get_schema_endpoint(client):
    resp = client.get("/schemas/da-concept-note")
    assert resp.status_code == 200
    assert resp.json()["fund"] == "DA"


def test_get_unknown_schema_404(client):
    assert client.get("/schemas/nope").status_code == 404

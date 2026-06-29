import json


def _http_event(method: str, path: str) -> dict:
    return {
        "version": "2.0",
        "routeKey": f"{method} {path}",
        "rawPath": path,
        "rawQueryString": "",
        "headers": {"host": "test.local"},
        "requestContext": {
            "http": {"method": method, "path": path, "sourceIp": "127.0.0.1"},
            "stage": "$default",
        },
        "isBase64Encoded": False,
    }


def test_handler_serves_health():
    from cidy_api.lambda_handler import handler

    resp = handler(_http_event("GET", "/health"), None)
    assert resp["statusCode"] == 200
    assert json.loads(resp["body"]) == {"status": "ok"}

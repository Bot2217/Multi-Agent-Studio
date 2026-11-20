"""A webpage cannot call the engine just because DNS points at the machine."""

from fastapi.testclient import TestClient

from api.app import create_app
from api.trust import host_ok, origin_ok
from core.downloads import DownloadManager


def _app():
    return create_app(
        config={"agents": {}, "pipelines": {}},
        token="secret",
        downloads=DownloadManager(lambda *args: None),
        search=lambda **_kwargs: [],
    )


def test_host_and_origin_rules():
    assert host_ok("127.0.0.1:8765")
    assert host_ok("localhost")
    assert host_ok("[::1]:9")
    assert not host_ok("evil.com")
    assert not host_ok("127.0.0.1.evil.com")
    assert origin_ok("http://127.0.0.1:8501")
    assert not origin_ok("http://evil.example")
    assert not origin_ok("null")


def test_rebinding_is_rejected_and_the_token_is_required():
    client = TestClient(_app())
    rebound = client.get(
        "/api/v1/health",
        headers={"host": "evil.com", "authorization": "Bearer secret"},
    )
    assert rebound.status_code == 403
    assert rebound.json()["detail"] == "bad_host"
    foreign = client.get(
        "/api/v1/health",
        headers={
            "host": "127.0.0.1:8765",
            "origin": "http://evil.example",
            "authorization": "Bearer secret",
        },
    )
    assert foreign.status_code == 403
    assert foreign.json()["detail"] == "bad_origin"
    missing = client.get("/api/v1/health", headers={"host": "127.0.0.1:8765"})
    assert missing.status_code == 401
    ok = client.get(
        "/api/v1/health",
        headers={"host": "127.0.0.1:8765", "authorization": "Bearer secret"},
    )
    assert ok.status_code == 200
    assert ok.json()["status"] == "ok"

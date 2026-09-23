from fastapi.testclient import TestClient

from backend.app.main import app

client = TestClient(app)


def test_health_returns_typed_ok_response() -> None:
    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_unknown_route_returns_not_found() -> None:
    assert client.get("/api/missing").status_code == 404


def test_cors_allows_frontend_origin() -> None:
    response = client.get("/api/health", headers={"Origin": "http://localhost:8455"})

    assert response.headers["access-control-allow-origin"] == "http://localhost:8455"


def test_cors_does_not_allow_other_origins() -> None:
    response = client.get("/api/health", headers={"Origin": "http://localhost:3000"})

    assert "access-control-allow-origin" not in response.headers

"""Focused proof for the served health-only API contract."""

from fastapi.testclient import TestClient

from backend.app.main import app


def test_openapi_contains_only_the_health_operation() -> None:
    spec = app.openapi()

    assert set(spec["paths"]) == {"/api/health"}
    assert set(spec["paths"]["/api/health"]) == {"get"}
    assert spec["paths"]["/api/health"]["get"]["operationId"] == "getHealth"
    assert set(spec["components"]["schemas"]) == {"HealthResponse"}


def test_served_openapi_matches_the_health_contract() -> None:
    served = TestClient(app).get("/openapi.json")

    assert served.status_code == 200
    assert set(served.json()["paths"]) == {"/api/health"}

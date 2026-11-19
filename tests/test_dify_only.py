"""Retrieval-only public demo must not expose internal SOC routes."""
from fastapi.testclient import TestClient

from soc.api.dify_only import app


def test_dify_only_app_does_not_expose_alerts_or_approvals():
    client = TestClient(app)
    assert client.get("/healthz").json() == {"status": "ok"}
    assert client.get("/alerts").status_code == 404
    assert client.get("/approvals").status_code == 404
    assert client.get("/stats").status_code == 404
    assert client.get("/readyz").status_code == 404
    assert client.get("/docs").status_code == 404
    assert client.get("/openapi.json").status_code == 404
    response = client.post("/dify/retrieval", json={"query": "격리"})
    assert response.status_code in {403, 503}

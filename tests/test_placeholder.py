"""Placeholder tests — replace with real tests as the pipeline is implemented."""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_dashboard_loads():
    response = client.get("/")
    assert response.status_code == 200


def test_api_status():
    response = client.get("/api/run/status")
    assert response.status_code == 200

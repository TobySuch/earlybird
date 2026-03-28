"""Placeholder tests — replace with real tests as the pipeline is implemented."""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_dashboard_redirects_to_login_when_unauthenticated():
    response = client.get("/", follow_redirects=False)
    assert response.status_code == 302
    assert "/auth/login" in response.headers["location"]


def test_api_status_requires_auth():
    response = client.get("/api/run/status")
    assert response.status_code == 401

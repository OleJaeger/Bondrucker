"""API-key authentication tests."""

from __future__ import annotations

import pytest

PROTECTED_REQUESTS = [
    ("GET", "/api/jobs"),
    ("GET", "/api/jobs/does-not-exist"),
    ("DELETE", "/api/jobs/does-not-exist"),
    ("GET", "/api/printer/status"),
    ("GET", "/api/icons"),
    ("GET", "/api/settings"),
]


def test_health_does_not_require_api_key(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.parametrize("method, path", PROTECTED_REQUESTS)
def test_protected_endpoint_requires_api_key(client, method, path):
    response = client.request(method, path)
    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "ApiKey"


@pytest.mark.parametrize("method, path", PROTECTED_REQUESTS)
def test_protected_endpoint_rejects_wrong_api_key(client, method, path):
    response = client.request(method, path, headers={"X-API-Key": "wrong-key"})
    assert response.status_code == 401


def test_create_job_requires_api_key(client):
    response = client.post("/api/jobs", json={"template": "freitext", "markdown": "hi"})
    assert response.status_code == 401


def test_preview_requires_api_key(client):
    response = client.post("/api/preview", json={"template": "freitext", "markdown": "hi"})
    assert response.status_code == 401


def test_correct_api_key_is_accepted(client, auth_headers):
    response = client.get("/api/jobs", headers=auth_headers)
    assert response.status_code == 200

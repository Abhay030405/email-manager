"""API tests for /health endpoints."""

from __future__ import annotations

import pytest


@pytest.mark.unit
class TestHealthCheck:

    def test_health_returns_200(self, client):
        response = client.get("/api/v1/health")
        assert response.status_code == 200

    def test_health_has_status_field(self, client):
        response = client.get("/api/v1/health")
        body = response.json()
        assert "status" in body

    def test_health_status_value(self, client):
        response = client.get("/api/v1/health")
        body = response.json()
        assert body["status"] in ("healthy", "degraded", "ok")

    def test_health_db_returns_200(self, client):
        response = client.get("/api/v1/health/db")
        assert response.status_code == 200

    def test_health_db_has_service_field(self, client):
        response = client.get("/api/v1/health/db")
        body = response.json()
        assert "service" in body or "status" in body

    def test_health_mock_api_returns_200(self, client):
        response = client.get("/api/v1/health/mock-api")
        assert response.status_code == 200

    def test_health_mock_api_has_status(self, client):
        response = client.get("/api/v1/health/mock-api")
        body = response.json()
        assert "status" in body or "service" in body

    def test_health_detailed_returns_200(self, client):
        response = client.get("/api/v1/health/detailed")
        assert response.status_code == 200

    def test_health_ready_returns_200(self, client):
        response = client.get("/api/v1/health/ready")
        assert response.status_code == 200

    def test_root_endpoint_returns_200(self, client):
        response = client.get("/")
        assert response.status_code == 200

    def test_root_has_docs_link(self, client):
        response = client.get("/")
        body = response.json()
        assert "docs" in body

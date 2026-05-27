"""API tests for health check endpoints."""

from unittest.mock import AsyncMock, patch

import pytest

from app.db.mongodb import MongoDB


# ── Basic health ──────────────────────────────────────────────────────────────

def test_basic_health_returns_ok(client):
    resp = client.get("/api/v1/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert "version" in body
    assert "environment" in body


def test_basic_health_response_shape(client):
    resp = client.get("/api/v1/health")
    body = resp.json()
    assert set(body.keys()) >= {"status", "version", "environment", "services"}


# ── DB health ─────────────────────────────────────────────────────────────────

def test_db_health_ok_when_mongo_pings(client, mock_db):
    """patch mock_db.client.admin.command so the ping succeeds."""
    mock_db.client.admin = AsyncMock()
    mock_db.client.admin.command = AsyncMock(return_value={"ok": 1})

    resp = client.get("/api/v1/health/db")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["latency_ms"] is not None


def test_db_health_503_when_get_db_raises(client):
    with patch.object(MongoDB, "get_db", side_effect=RuntimeError("no db")):
        resp = client.get("/api/v1/health/db")
    assert resp.status_code == 503


# ── Readiness probe ───────────────────────────────────────────────────────────

def test_ready_returns_200_when_db_connected(client):
    resp = client.get("/api/v1/health/ready")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ready"


def test_ready_returns_503_when_db_not_connected(client):
    with patch.object(MongoDB, "get_db", side_effect=RuntimeError("no db")):
        resp = client.get("/api/v1/health/ready")
    assert resp.status_code == 503

"""API tests for /api/v1/execution endpoints."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

from tests.test_api.conftest import CAMPAIGN_BRIEF

CAMPAIGNS_BASE = "/api/v1/campaigns"
EXEC_BASE = "/api/v1/execution"


def _create_campaign(client, status: str = "draft") -> str:
    resp = client.post(CAMPAIGNS_BASE, json={"campaign_brief": CAMPAIGN_BRIEF})
    assert resp.status_code == 201
    cid = resp.json()["campaign_id"]
    if status != "draft":
        patch_resp = client.patch(f"{CAMPAIGNS_BASE}/{cid}", json={"status": status})
        assert patch_resp.status_code == 200
    return cid


# ── /execute ──────────────────────────────────────────────────────────────────

def test_execute_approved_campaign_200(client):
    cid = _create_campaign(client, status="approved")
    mock_wf = AsyncMock(return_value={"status": "started", "mock_api_campaign_ids": {}})
    with patch("app.orchestration.optimization_graph.run_optimization_workflow", mock_wf):
        resp = client.post(f"{EXEC_BASE}/{cid}/execute")
    assert resp.status_code == 200
    body = resp.json()
    assert body["campaign_id"] == cid


def test_execute_executing_campaign_200(client):
    cid = _create_campaign(client, status="executing")
    mock_wf = AsyncMock(return_value={"status": "started"})
    with patch("app.orchestration.optimization_graph.run_optimization_workflow", mock_wf):
        resp = client.post(f"{EXEC_BASE}/{cid}/execute")
    assert resp.status_code == 200


def test_execute_draft_campaign_400(client):
    cid = _create_campaign(client, status="draft")
    resp = client.post(f"{EXEC_BASE}/{cid}/execute")
    assert resp.status_code == 400


def test_execute_missing_campaign_404(client):
    resp = client.post(f"{EXEC_BASE}/ghost-id/execute")
    assert resp.status_code == 404


def test_execute_workflow_error_returns_500(client):
    cid = _create_campaign(client, status="approved")
    mock_wf = AsyncMock(side_effect=RuntimeError("workflow boom"))
    with patch("app.orchestration.optimization_graph.run_optimization_workflow", mock_wf):
        resp = client.post(f"{EXEC_BASE}/{cid}/execute")
    assert resp.status_code == 500


# ── /execution-logs ───────────────────────────────────────────────────────────

def test_get_execution_logs_empty_200(client):
    cid = _create_campaign(client, status="approved")
    resp = client.get(f"{EXEC_BASE}/{cid}/execution-logs")
    assert resp.status_code == 200
    body = resp.json()
    assert body["campaign_id"] == cid
    assert isinstance(body["logs"], list)
    assert "total" in body
    assert "status_counts" in body


def test_get_execution_logs_404_for_missing(client):
    resp = client.get(f"{EXEC_BASE}/ghost-id/execution-logs")
    assert resp.status_code == 404


def test_get_execution_logs_pagination_fields(client):
    cid = _create_campaign(client, status="approved")
    resp = client.get(f"{EXEC_BASE}/{cid}/execution-logs?skip=0&limit=10")
    assert resp.status_code == 200
    body = resp.json()
    assert "skip" in body
    assert "limit" in body


# ── /retry-execution ──────────────────────────────────────────────────────────

def test_retry_execution_no_failures_returns_message(client):
    cid = _create_campaign(client, status="approved")
    resp = client.post(f"{EXEC_BASE}/{cid}/retry-execution")
    assert resp.status_code == 200
    body = resp.json()
    assert "No failed executions" in body["message"]


def test_retry_execution_draft_campaign_400(client):
    cid = _create_campaign(client, status="draft")
    resp = client.post(f"{EXEC_BASE}/{cid}/retry-execution")
    assert resp.status_code == 400


def test_retry_execution_missing_campaign_404(client):
    resp = client.post(f"{EXEC_BASE}/ghost-id/retry-execution")
    assert resp.status_code == 404

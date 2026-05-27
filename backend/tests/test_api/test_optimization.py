"""API tests for optimization workflow endpoints."""

from unittest.mock import AsyncMock, patch

from tests.test_api.conftest import CAMPAIGN_BRIEF

CAMPAIGNS_BASE = "/api/v1/campaigns"
OPT_BASE = "/api/v1/optimization"


def _create_campaign(client, status: str = "draft") -> str:
    resp = client.post(CAMPAIGNS_BASE, json={"campaign_brief": CAMPAIGN_BRIEF})
    assert resp.status_code == 201
    cid = resp.json()["campaign_id"]
    if status != "draft":
        patch_resp = client.patch(f"{CAMPAIGNS_BASE}/{cid}", json={"status": status})
        assert patch_resp.status_code == 200
    return cid


# ── Start optimization ────────────────────────────────────────────────────────

def test_start_optimization_for_approved_campaign(client):
    cid = _create_campaign(client, status="approved")
    mock_wf = AsyncMock(return_value={"status": "started", "mock_api_campaign_ids": {}})
    with patch("app.orchestration.optimization_graph.run_optimization_workflow", mock_wf):
        resp = client.post(f"{OPT_BASE}/{cid}/start")
    assert resp.status_code == 200
    body = resp.json()
    assert body["campaign_id"] == cid


def test_start_optimization_for_completed_campaign(client):
    cid = _create_campaign(client, status="completed")
    mock_wf = AsyncMock(return_value={"status": "started"})
    with patch("app.orchestration.optimization_graph.run_optimization_workflow", mock_wf):
        resp = client.post(f"{OPT_BASE}/{cid}/start")
    assert resp.status_code == 200


def test_start_optimization_400_for_draft_campaign(client):
    cid = _create_campaign(client, status="draft")
    mock_wf = AsyncMock(return_value={})
    with patch("app.orchestration.optimization_graph.run_optimization_workflow", mock_wf):
        resp = client.post(f"{OPT_BASE}/{cid}/start")
    assert resp.status_code == 400


def test_start_optimization_404_for_missing_campaign(client):
    mock_wf = AsyncMock(return_value={})
    with patch("app.orchestration.optimization_graph.run_optimization_workflow", mock_wf):
        resp = client.post(f"{OPT_BASE}/ghost-id/start")
    assert resp.status_code == 404


# ── Optimization status ───────────────────────────────────────────────────────

def test_get_optimization_status_returns_200(client):
    cid = _create_campaign(client, status="approved")
    resp = client.get(f"{OPT_BASE}/{cid}/status")
    assert resp.status_code == 200
    body = resp.json()
    assert body["campaign_id"] == cid
    assert "status" in body


def test_get_optimization_status_404_for_missing(client):
    resp = client.get(f"{OPT_BASE}/ghost-id/status")
    assert resp.status_code == 404


# ── Optimization results ──────────────────────────────────────────────────────

def test_get_optimization_results_returns_200(client):
    cid = _create_campaign(client, status="completed")
    resp = client.get(f"{OPT_BASE}/{cid}/results")
    assert resp.status_code == 200
    body = resp.json()
    assert body["campaign_id"] == cid
    assert "aggregates" in body


def test_get_optimization_results_404_for_missing(client):
    resp = client.get(f"{OPT_BASE}/ghost-id/results")
    assert resp.status_code == 404

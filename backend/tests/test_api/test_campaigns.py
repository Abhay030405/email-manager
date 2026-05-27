"""API tests for campaign CRUD and workflow endpoints."""

from unittest.mock import AsyncMock, patch

import pytest

from tests.test_api.conftest import CAMPAIGN_BRIEF

BASE = "/api/v1/campaigns"


# ── Helpers ───────────────────────────────────────────────────────────────────

def _create(client, brief: str = CAMPAIGN_BRIEF, created_by: str = "tester") -> dict:
    """Create a campaign via the API and return the JSON body."""
    resp = client.post(BASE, json={"campaign_brief": brief, "created_by": created_by})
    assert resp.status_code == 201, resp.text
    return resp.json()


# ── Create ────────────────────────────────────────────────────────────────────

def test_create_campaign_returns_201(client):
    resp = client.post(BASE, json={"campaign_brief": CAMPAIGN_BRIEF, "created_by": "tester"})
    assert resp.status_code == 201
    body = resp.json()
    assert "campaign_id" in body
    assert body["campaign_brief"] == CAMPAIGN_BRIEF
    assert body["status"] == "draft"


def test_create_campaign_missing_brief_returns_422(client):
    resp = client.post(BASE, json={"created_by": "tester"})
    assert resp.status_code == 422


def test_create_campaign_sets_draft_status(client):
    body = _create(client)
    assert body["status"] == "draft"


# ── List ──────────────────────────────────────────────────────────────────────

def test_list_campaigns_empty_db_returns_200(client):
    resp = client.get(BASE)
    assert resp.status_code == 200
    body = resp.json()
    assert "items" in body
    assert "total" in body
    assert body["total"] == 0


def test_list_campaigns_pagination(client):
    for i in range(3):
        _create(client, brief=f"{CAMPAIGN_BRIEF} #{i}")
    resp = client.get(BASE, params={"skip": 0, "limit": 2})
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["items"]) == 2
    assert body["total"] == 3
    assert body["has_more"] is True


# ── Get ───────────────────────────────────────────────────────────────────────

def test_get_campaign_returns_200(client):
    created = _create(client)
    resp = client.get(f"{BASE}/{created['campaign_id']}")
    assert resp.status_code == 200
    assert resp.json()["campaign_id"] == created["campaign_id"]


def test_get_campaign_not_found_returns_404(client):
    resp = client.get(f"{BASE}/nonexistent-id")
    assert resp.status_code == 404


# ── Update ────────────────────────────────────────────────────────────────────

def test_update_campaign_returns_200(client):
    created = _create(client)
    cid = created["campaign_id"]
    new_brief = CAMPAIGN_BRIEF + " — updated version with extra detail for validation"
    resp = client.patch(f"{BASE}/{cid}", json={"campaign_brief": new_brief})
    assert resp.status_code == 200
    assert resp.json()["campaign_brief"] == new_brief


def test_update_campaign_not_found_returns_404(client):
    resp = client.patch(f"{BASE}/ghost-id", json={"campaign_brief": CAMPAIGN_BRIEF})
    assert resp.status_code == 404


# ── Delete ────────────────────────────────────────────────────────────────────

def test_delete_campaign_returns_204(client):
    created = _create(client)
    cid = created["campaign_id"]
    resp = client.delete(f"{BASE}/{cid}")
    assert resp.status_code == 204
    # Confirm it is gone
    assert client.get(f"{BASE}/{cid}").status_code == 404


def test_delete_campaign_not_found_returns_404(client):
    resp = client.delete(f"{BASE}/ghost-id")
    assert resp.status_code == 404


# ── Workflow trigger (/run-workflow) ──────────────────────────────────────────

def test_run_workflow_triggers_for_draft_campaign(client):
    created = _create(client)
    cid = created["campaign_id"]
    mock_wf = AsyncMock(return_value={"status": "completed", "mock_api_campaign_ids": {}})
    with patch("app.orchestration.campaign_graph.run_campaign_workflow", mock_wf):
        resp = client.post(f"{BASE}/{cid}/run-workflow")
    assert resp.status_code == 200
    assert resp.json()["campaign_id"] == cid


def test_run_workflow_404_for_missing_campaign(client):
    mock_wf = AsyncMock(return_value={"status": "completed"})
    with patch("app.orchestration.campaign_graph.run_campaign_workflow", mock_wf):
        resp = client.post(f"{BASE}/no-such-id/run-workflow")
    assert resp.status_code == 404


# ── /start endpoint (background task variant) ────────────────────────────────

def test_start_campaign_returns_200_for_draft(client):
    created = _create(client)
    cid = created["campaign_id"]
    mock_wf = AsyncMock(return_value={"status": "completed"})
    with patch("app.orchestration.campaign_graph.run_campaign_workflow", mock_wf):
        resp = client.post(f"{BASE}/{cid}/start")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "started"
    assert body["campaign_id"] == cid


def test_start_campaign_400_for_non_draft(client):
    # Update to approved so it's no longer draft/failed
    created = _create(client)
    cid = created["campaign_id"]
    client.patch(f"{BASE}/{cid}", json={"status": "approved"})
    mock_wf = AsyncMock(return_value={})
    with patch("app.orchestration.campaign_graph.run_campaign_workflow", mock_wf):
        resp = client.post(f"{BASE}/{cid}/start")
    assert resp.status_code == 400


# ── Workflow status ───────────────────────────────────────────────────────────

def test_get_workflow_status_returns_status(client):
    created = _create(client)
    cid = created["campaign_id"]
    resp = client.get(f"{BASE}/{cid}/workflow-status")
    assert resp.status_code == 200
    assert resp.json()["status"] == "draft"


def test_get_workflow_status_404_for_missing(client):
    resp = client.get(f"{BASE}/ghost/workflow-status")
    assert resp.status_code == 404


# ── Segments sub-resource ─────────────────────────────────────────────────────

def test_get_campaign_segments_returns_empty_list(client):
    created = _create(client)
    cid = created["campaign_id"]
    resp = client.get(f"{BASE}/{cid}/segments")
    assert resp.status_code == 200
    body = resp.json()
    assert body["segment_count"] == 0
    assert body["segments"] == []


def test_get_campaign_segments_404_for_missing(client):
    resp = client.get(f"{BASE}/ghost/segments")
    assert resp.status_code == 404


# ── Variants sub-resource ─────────────────────────────────────────────────────

def test_get_campaign_variants_returns_empty_list(client):
    created = _create(client)
    cid = created["campaign_id"]
    resp = client.get(f"{BASE}/{cid}/variants")
    assert resp.status_code == 200
    body = resp.json()
    assert body["variant_count"] == 0
    assert body["variants"] == []


def test_get_campaign_variants_404_for_missing(client):
    resp = client.get(f"{BASE}/ghost/variants")
    assert resp.status_code == 404

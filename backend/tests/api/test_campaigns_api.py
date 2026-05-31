"""API tests for /campaigns endpoints."""

from __future__ import annotations

import pytest


BRIEF = "Promote XDeposit savings account to young professionals aged 25-35 in metro cities."


@pytest.mark.unit
class TestCampaignsAPI:

    # ── List ──────────────────────────────────────────────────────

    def test_list_campaigns_returns_200(self, client):
        response = client.get("/api/v1/campaigns")
        assert response.status_code == 200

    def test_list_campaigns_returns_paginated_shape(self, client):
        response = client.get("/api/v1/campaigns")
        body = response.json()
        assert "items" in body or "campaigns" in body or isinstance(body, list)

    def test_list_campaigns_pagination_params(self, client):
        response = client.get("/api/v1/campaigns?skip=0&limit=5")
        assert response.status_code == 200

    # ── Create ────────────────────────────────────────────────────

    def test_create_campaign_returns_201(self, client):
        response = client.post("/api/v1/campaigns", json={"campaign_brief": BRIEF})
        assert response.status_code == 201

    def test_create_campaign_returns_id(self, client):
        response = client.post("/api/v1/campaigns", json={"campaign_brief": BRIEF})
        body = response.json()
        assert "campaign_id" in body or "id" in body

    def test_create_campaign_sets_draft_status(self, client):
        response = client.post("/api/v1/campaigns", json={"campaign_brief": BRIEF})
        body = response.json()
        status = body.get("status", "")
        assert status.lower() in ("draft", "")

    def test_create_campaign_empty_brief_rejected(self, client):
        response = client.post("/api/v1/campaigns", json={"campaign_brief": ""})
        assert response.status_code in (400, 422)

    def test_create_campaign_missing_brief_rejected(self, client):
        response = client.post("/api/v1/campaigns", json={})
        assert response.status_code == 422

    # ── Get ───────────────────────────────────────────────────────

    def test_get_nonexistent_campaign_returns_404(self, client):
        response = client.get("/api/v1/campaigns/nonexistent-id-000")
        assert response.status_code == 404

    def test_get_campaign_after_create(self, client):
        create = client.post("/api/v1/campaigns", json={"campaign_brief": BRIEF})
        assert create.status_code == 201
        campaign_id = (create.json().get("campaign_id") or create.json().get("id"))

        get = client.get(f"/api/v1/campaigns/{campaign_id}")
        assert get.status_code == 200
        body = get.json()
        assert (body.get("campaign_id") or body.get("id")) == campaign_id

    # ── Update ────────────────────────────────────────────────────

    def test_update_nonexistent_campaign_returns_404(self, client):
        response = client.patch(
            "/api/v1/campaigns/nonexistent-id-000",
            json={"campaign_brief": "Updated brief text here"},
        )
        assert response.status_code == 404

    def test_update_campaign_brief(self, client):
        create = client.post("/api/v1/campaigns", json={"campaign_brief": BRIEF})
        campaign_id = create.json().get("campaign_id") or create.json().get("id")

        update = client.patch(
            f"/api/v1/campaigns/{campaign_id}",
            json={"campaign_brief": "Updated brief — new product launch targeting seniors."},
        )
        assert update.status_code == 200

    # ── Delete ────────────────────────────────────────────────────

    def test_delete_nonexistent_campaign_returns_404(self, client):
        response = client.delete("/api/v1/campaigns/nonexistent-id-000")
        assert response.status_code == 404

    def test_delete_campaign(self, client):
        create = client.post("/api/v1/campaigns", json={"campaign_brief": BRIEF})
        campaign_id = create.json().get("campaign_id") or create.json().get("id")

        delete = client.delete(f"/api/v1/campaigns/{campaign_id}")
        assert delete.status_code == 204

        get = client.get(f"/api/v1/campaigns/{campaign_id}")
        assert get.status_code == 404

    # ── Workflow sub-routes ───────────────────────────────────────

    def test_workflow_state_for_nonexistent_returns_404(self, client):
        response = client.get("/api/v1/campaigns/nonexistent-id-000/workflow-state")
        assert response.status_code == 404

    def test_pending_approval_for_nonexistent_returns_404(self, client):
        response = client.get("/api/v1/campaigns/nonexistent-id-000/pending-approval")
        assert response.status_code == 404

    def test_variants_for_nonexistent_returns_404(self, client):
        response = client.get("/api/v1/campaigns/nonexistent-id-000/variants")
        assert response.status_code == 404

    def test_segments_for_nonexistent_returns_404(self, client):
        response = client.get("/api/v1/campaigns/nonexistent-id-000/segments")
        assert response.status_code == 404

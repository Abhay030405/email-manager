"""API tests for /optimization endpoints."""

from __future__ import annotations

import pytest


BRIEF = "Promote XDeposit savings account — optimization API test brief."


def _create_campaign(client) -> str:
    resp = client.post("/api/v1/campaigns", json={"campaign_brief": BRIEF})
    assert resp.status_code == 201
    return resp.json().get("campaign_id") or resp.json().get("id")


@pytest.mark.unit
class TestOptimizationAPI:

    # ── /optimization/{campaign_id}/status ───────────────────────

    def test_optimization_status_unknown_campaign_returns_404(self, client):
        response = client.get("/api/v1/optimization/nonexistent-id/status")
        assert response.status_code == 404

    def test_optimization_status_returns_campaign_id(self, client):
        camp_id = _create_campaign(client)
        response = client.get(f"/api/v1/optimization/{camp_id}/status")
        assert response.status_code == 200
        body = response.json()
        assert "campaign_id" in body or "status" in body

    # ── /optimization/{campaign_id}/results ──────────────────────

    def test_optimization_results_unknown_campaign_returns_404(self, client):
        response = client.get("/api/v1/optimization/nonexistent-id/results")
        assert response.status_code == 404

    def test_optimization_results_returns_200_for_known_campaign(self, client):
        camp_id = _create_campaign(client)
        response = client.get(f"/api/v1/optimization/{camp_id}/results")
        assert response.status_code == 200

    # ── /optimization/campaigns/{campaign_id}/optimization-status ─

    def test_detailed_optimization_status_unknown_returns_404(self, client):
        response = client.get(
            "/api/v1/optimization/campaigns/nonexistent-id/optimization-status"
        )
        assert response.status_code == 404

    def test_detailed_optimization_status_known_returns_200(self, client):
        camp_id = _create_campaign(client)
        response = client.get(
            f"/api/v1/optimization/campaigns/{camp_id}/optimization-status"
        )
        assert response.status_code == 200

    # ── /optimization/campaigns/{campaign_id}/optimization-history ─

    def test_optimization_history_returns_200(self, client):
        camp_id = _create_campaign(client)
        response = client.get(
            f"/api/v1/optimization/campaigns/{camp_id}/optimization-history"
        )
        assert response.status_code == 200

    def test_optimization_history_pagination_params(self, client):
        camp_id = _create_campaign(client)
        response = client.get(
            f"/api/v1/optimization/campaigns/{camp_id}/optimization-history?skip=0&limit=5"
        )
        assert response.status_code == 200

    # ── /optimization/campaigns/{campaign_id}/optimization-insights ─

    def test_optimization_insights_returns_200(self, client):
        camp_id = _create_campaign(client)
        response = client.get(
            f"/api/v1/optimization/campaigns/{camp_id}/optimization-insights"
        )
        assert response.status_code == 200

    def test_optimization_insights_has_insights_key(self, client):
        camp_id = _create_campaign(client)
        response = client.get(
            f"/api/v1/optimization/campaigns/{camp_id}/optimization-insights"
        )
        body = response.json()
        assert isinstance(body, dict)

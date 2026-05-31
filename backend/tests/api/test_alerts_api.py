"""API tests for /alerts endpoints."""

from __future__ import annotations

import pytest


BRIEF = "Promote XDeposit savings — alerts API testing brief."


def _create_campaign(client) -> str:
    resp = client.post("/api/v1/campaigns", json={"campaign_brief": BRIEF})
    assert resp.status_code == 201
    return resp.json().get("campaign_id") or resp.json().get("id")


@pytest.mark.unit
class TestAlertsAPI:

    def test_active_alerts_returns_200(self, client):
        response = client.get("/api/v1/alerts/active")
        assert response.status_code == 200

    def test_active_alerts_returns_list(self, client):
        response = client.get("/api/v1/alerts/active")
        assert isinstance(response.json(), list)

    def test_active_alerts_filter_by_campaign(self, client):
        camp_id = _create_campaign(client)
        response = client.get(f"/api/v1/alerts/active?campaign_id={camp_id}")
        assert response.status_code == 200

    def test_active_alerts_filter_by_severity(self, client):
        response = client.get("/api/v1/alerts/active?severity=critical")
        assert response.status_code == 200

    def test_critical_alerts_returns_200(self, client):
        response = client.get("/api/v1/alerts/critical")
        assert response.status_code == 200

    def test_critical_alerts_returns_list(self, client):
        response = client.get("/api/v1/alerts/critical")
        assert isinstance(response.json(), list)

    def test_get_alert_by_id_not_found(self, client):
        response = client.get("/api/v1/alerts/nonexistent-alert-id")
        assert response.status_code == 404

    def test_acknowledge_nonexistent_alert_returns_404_or_422(self, client):
        response = client.post(
            "/api/v1/alerts/nonexistent-id/acknowledge",
            json={"acknowledged_by": "ops@test.com", "notes": "Checking"},
        )
        # 404 if alert not found; 422 if body schema differs from endpoint expectations
        assert response.status_code in (404, 422)

    def test_get_alerts_by_campaign_returns_200(self, client):
        camp_id = _create_campaign(client)
        response = client.get(f"/api/v1/alerts/campaign/{camp_id}")
        assert response.status_code == 200

    def test_check_alerts_for_campaign_returns_200(self, client):
        camp_id = _create_campaign(client)
        response = client.post(f"/api/v1/alerts/campaign/{camp_id}/check")
        assert response.status_code == 200

    def test_check_alerts_returns_dict(self, client):
        camp_id = _create_campaign(client)
        response = client.post(f"/api/v1/alerts/campaign/{camp_id}/check")
        assert isinstance(response.json(), dict)

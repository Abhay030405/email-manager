"""API tests for /analytics endpoints."""

from __future__ import annotations

import pytest


BRIEF = "Promote XDeposit savings — analytics API testing brief."


def _create_campaign(client) -> str:
    resp = client.post("/api/v1/campaigns", json={"campaign_brief": BRIEF})
    assert resp.status_code == 201
    return resp.json().get("campaign_id") or resp.json().get("id")


@pytest.mark.unit
class TestAnalyticsAPI:

    def test_analytics_overview_returns_200(self, client):
        camp_id = _create_campaign(client)
        response = client.get(f"/api/v1/analytics/campaigns/{camp_id}/analytics")
        assert response.status_code == 200

    def test_analytics_returns_dict(self, client):
        camp_id = _create_campaign(client)
        response = client.get(f"/api/v1/analytics/campaigns/{camp_id}/analytics")
        assert isinstance(response.json(), dict)

    def test_trends_returns_200(self, client):
        camp_id = _create_campaign(client)
        response = client.get(
            f"/api/v1/analytics/campaigns/{camp_id}/trends?metric=open_rate&lookback_hours=24"
        )
        assert response.status_code == 200

    def test_segment_analysis_returns_200(self, client):
        camp_id = _create_campaign(client)
        response = client.get(
            f"/api/v1/analytics/campaigns/{camp_id}/segment-analysis"
        )
        assert response.status_code == 200

    def test_segment_analysis_with_filter(self, client):
        camp_id = _create_campaign(client)
        response = client.get(
            f"/api/v1/analytics/campaigns/{camp_id}/segment-analysis?segment_name=premium"
        )
        assert response.status_code == 200

    def test_variant_comparison_returns_200(self, client):
        camp_id = _create_campaign(client)
        response = client.get(
            f"/api/v1/analytics/campaigns/{camp_id}/variant-comparison"
        )
        assert response.status_code == 200

    def test_predictions_returns_200(self, client):
        camp_id = _create_campaign(client)
        response = client.get(
            f"/api/v1/analytics/campaigns/{camp_id}/predictions?based_on_hours=6"
        )
        assert response.status_code == 200

    def test_baseline_comparison_returns_200(self, client):
        camp_id = _create_campaign(client)
        response = client.get(
            f"/api/v1/analytics/campaigns/{camp_id}/baseline-comparison"
        )
        assert response.status_code == 200

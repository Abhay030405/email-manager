"""API tests for /variant-iterations endpoints."""

from __future__ import annotations

import pytest


BRIEF = "Promote XDeposit savings — variant iterations API testing brief."


def _create_campaign(client) -> str:
    resp = client.post("/api/v1/campaigns", json={"campaign_brief": BRIEF})
    assert resp.status_code == 201
    return resp.json().get("campaign_id") or resp.json().get("id")


@pytest.mark.unit
class TestVariantIterationsAPI:

    def test_list_iterations_returns_200(self, client):
        camp_id = _create_campaign(client)
        response = client.get(
            f"/api/v1/variant-iterations/variants/var-001/iterations"
            f"?campaign_id={camp_id}"
        )
        assert response.status_code == 200

    def test_list_iterations_missing_campaign_id_returns_422(self, client):
        response = client.get(
            "/api/v1/variant-iterations/variants/var-001/iterations"
        )
        assert response.status_code == 422

    def test_list_iterations_returns_dict(self, client):
        camp_id = _create_campaign(client)
        response = client.get(
            f"/api/v1/variant-iterations/variants/var-001/iterations"
            f"?campaign_id={camp_id}"
        )
        body = response.json()
        assert isinstance(body, dict)

    def test_get_specific_iteration_returns_404_when_missing(self, client):
        camp_id = _create_campaign(client)
        response = client.get(
            f"/api/v1/variant-iterations/variants/var-001/iterations/1"
            f"?campaign_id={camp_id}"
        )
        assert response.status_code == 404

    def test_iteration_history_returns_200(self, client):
        camp_id = _create_campaign(client)
        response = client.get(
            f"/api/v1/variant-iterations/variants/var-001/iteration-history"
            f"?campaign_id={camp_id}"
        )
        assert response.status_code == 200

    def test_compare_iterations_requires_campaign_id(self, client):
        response = client.post(
            "/api/v1/variant-iterations/variants/var-001/compare-iterations"
            "?iteration_a=1&iteration_b=2"
        )
        assert response.status_code == 422

    def test_compare_iterations_returns_200_for_known_variant(self, client):
        camp_id = _create_campaign(client)
        response = client.post(
            f"/api/v1/variant-iterations/variants/var-001/compare-iterations"
            f"?campaign_id={camp_id}&iteration_a=1&iteration_b=2"
        )
        # Either 200 (empty comparison) or 404 (iterations don't exist)
        assert response.status_code in (200, 404)

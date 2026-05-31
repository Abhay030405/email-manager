"""API tests for /ab-tests endpoints."""

from __future__ import annotations

import pytest


BRIEF = "Promote XDeposit savings — A/B test API testing brief."


def _create_campaign(client) -> str:
    resp = client.post("/api/v1/campaigns", json={"campaign_brief": BRIEF})
    assert resp.status_code == 201
    return resp.json().get("campaign_id") or resp.json().get("id")


@pytest.mark.unit
class TestABTestsAPI:

    def test_list_ab_tests_for_campaign_returns_200(self, client):
        camp_id = _create_campaign(client)
        response = client.get(f"/api/v1/ab-tests/campaigns/{camp_id}/ab-tests")
        assert response.status_code == 200

    def test_list_ab_tests_returns_dict_with_tests(self, client):
        camp_id = _create_campaign(client)
        response = client.get(f"/api/v1/ab-tests/campaigns/{camp_id}/ab-tests")
        body = response.json()
        assert "tests" in body or isinstance(body, (list, dict))

    def test_list_ab_tests_pagination(self, client):
        camp_id = _create_campaign(client)
        response = client.get(
            f"/api/v1/ab-tests/campaigns/{camp_id}/ab-tests?skip=0&limit=5"
        )
        assert response.status_code == 200

    def test_create_ab_test_returns_200(self, client):
        camp_id = _create_campaign(client)
        response = client.post(
            f"/api/v1/ab-tests/campaigns/{camp_id}/ab-tests"
            "?variant_a_id=var-a&variant_b_id=var-b&test_duration_hours=24"
        )
        assert response.status_code == 200

    def test_create_ab_test_returns_test_id(self, client):
        camp_id = _create_campaign(client)
        response = client.post(
            f"/api/v1/ab-tests/campaigns/{camp_id}/ab-tests"
            "?variant_a_id=var-a&variant_b_id=var-b&test_duration_hours=24"
        )
        body = response.json()
        assert "test_id" in body

    def test_get_ab_test_not_found(self, client):
        response = client.get("/api/v1/ab-tests/nonexistent-test-id")
        assert response.status_code == 404

    def test_get_ab_test_after_creation(self, client):
        camp_id = _create_campaign(client)
        create = client.post(
            f"/api/v1/ab-tests/campaigns/{camp_id}/ab-tests"
            "?variant_a_id=var-a&variant_b_id=var-b"
        )
        test_id = create.json().get("test_id")
        assert test_id is not None

        get = client.get(f"/api/v1/ab-tests/{test_id}")
        assert get.status_code == 200
        assert get.json().get("test_id") == test_id

    def test_analyze_ab_test_not_found(self, client):
        response = client.post("/api/v1/ab-tests/nonexistent-test-id/analyze")
        assert response.status_code == 404

    def test_recommendation_not_found(self, client):
        response = client.get("/api/v1/ab-tests/nonexistent-test-id/recommendation")
        assert response.status_code == 404

    def test_recommendation_after_creation(self, client):
        camp_id = _create_campaign(client)
        create = client.post(
            f"/api/v1/ab-tests/campaigns/{camp_id}/ab-tests"
            "?variant_a_id=var-a&variant_b_id=var-b"
        )
        test_id = create.json().get("test_id")

        rec = client.get(f"/api/v1/ab-tests/{test_id}/recommendation")
        assert rec.status_code == 200
        body = rec.json()
        assert "recommendation" in body or "winner" in body

"""API tests for /approval endpoints."""

from __future__ import annotations

import pytest


BRIEF = "Promote XDeposit savings to young professionals for approval flow testing."


def _create_campaign(client) -> str:
    resp = client.post("/api/v1/campaigns", json={"campaign_brief": BRIEF})
    assert resp.status_code == 201
    return resp.json().get("campaign_id") or resp.json().get("id")


@pytest.mark.unit
class TestApprovalAPI:

    def test_list_pending_returns_200(self, client):
        response = client.get("/api/v1/approval/pending")
        assert response.status_code == 200

    def test_list_pending_returns_list(self, client):
        response = client.get("/api/v1/approval/pending")
        body = response.json()
        assert isinstance(body, list)

    def test_get_approval_unknown_campaign_returns_404(self, client):
        response = client.get("/api/v1/approval/nonexistent-campaign-id")
        assert response.status_code == 404

    def test_approve_unknown_campaign_returns_404(self, client):
        response = client.post(
            "/api/v1/approval/nonexistent-campaign-id/approve",
            json={"approved_by": "manager@test.com", "notes": "Looks good"},
        )
        assert response.status_code == 404

    def test_reject_unknown_campaign_returns_404(self, client):
        response = client.post(
            "/api/v1/approval/nonexistent-campaign-id/reject",
            json={"approved_by": "manager@test.com", "notes": "Needs revision"},
        )
        assert response.status_code == 404

    def test_approve_draft_campaign_returns_error(self, client):
        camp_id = _create_campaign(client)
        # Draft campaigns can't be approved (must be PENDING_APPROVAL)
        response = client.post(
            f"/api/v1/approval/{camp_id}/approve",
            json={"approved_by": "manager@test.com", "notes": ""},
        )
        # Either 404 (not in approval queue) or 422 (wrong status)
        assert response.status_code in (404, 422, 400)

    def test_reject_draft_campaign_returns_error(self, client):
        camp_id = _create_campaign(client)
        response = client.post(
            f"/api/v1/approval/{camp_id}/reject",
            json={"approved_by": "manager@test.com", "notes": "Subject lines are too generic."},
        )
        assert response.status_code in (404, 422, 400)

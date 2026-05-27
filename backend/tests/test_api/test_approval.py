"""API tests for campaign approval workflow endpoints."""

from tests.test_api.conftest import CAMPAIGN_BRIEF

CAMPAIGNS_BASE = "/api/v1/campaigns"
APPROVAL_BASE = "/api/v1/approval"

_APPROVE_BODY = {"approved_by": "reviewer_1", "notes": "Looks great"}
_REJECT_BODY = {"approved_by": "reviewer_1", "notes": "Needs revision"}


def _create_campaign(client) -> str:
    resp = client.post(CAMPAIGNS_BASE, json={"campaign_brief": CAMPAIGN_BRIEF})
    assert resp.status_code == 201
    return resp.json()["campaign_id"]


def _set_status(client, cid: str, status: str) -> None:
    resp = client.patch(f"{CAMPAIGNS_BASE}/{cid}", json={"status": status})
    assert resp.status_code == 200, resp.text


# ── Pending list ──────────────────────────────────────────────────────────────

def test_list_pending_empty_returns_200(client):
    resp = client.get(f"{APPROVAL_BASE}/pending")
    assert resp.status_code == 200
    assert resp.json() == []


def test_list_pending_returns_pending_campaigns(client):
    cid = _create_campaign(client)
    _set_status(client, cid, "pending_approval")
    resp = client.get(f"{APPROVAL_BASE}/pending")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["campaign_id"] == cid


# ── Approval status ───────────────────────────────────────────────────────────

def test_get_approval_status_returns_200(client):
    cid = _create_campaign(client)
    resp = client.get(f"{APPROVAL_BASE}/{cid}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["campaign_id"] == cid
    assert "pending" in body
    assert "approved" in body
    assert "rejected" in body


def test_get_approval_status_not_found_returns_404(client):
    resp = client.get(f"{APPROVAL_BASE}/ghost-id")
    assert resp.status_code == 404


# ── Approve ───────────────────────────────────────────────────────────────────

def test_approve_pending_campaign_returns_200(client):
    cid = _create_campaign(client)
    _set_status(client, cid, "pending_approval")
    resp = client.post(f"{APPROVAL_BASE}/{cid}/approve", json=_APPROVE_BODY)
    assert resp.status_code == 200
    body = resp.json()
    assert body["campaign_id"] == cid
    assert body["status"] == "approved"


def test_approve_non_pending_campaign_returns_400(client):
    cid = _create_campaign(client)
    # Campaign is in draft — not pending_approval
    resp = client.post(f"{APPROVAL_BASE}/{cid}/approve", json=_APPROVE_BODY)
    assert resp.status_code == 400


def test_approve_nonexistent_campaign_returns_404(client):
    resp = client.post(f"{APPROVAL_BASE}/no-such-id/approve", json=_APPROVE_BODY)
    assert resp.status_code == 404


# ── Reject ────────────────────────────────────────────────────────────────────

def test_reject_pending_campaign_returns_200(client):
    cid = _create_campaign(client)
    _set_status(client, cid, "pending_approval")
    resp = client.post(f"{APPROVAL_BASE}/{cid}/reject", json=_REJECT_BODY)
    assert resp.status_code == 200
    body = resp.json()
    assert body["campaign_id"] == cid
    assert body["status"] == "rejected"


def test_reject_non_pending_campaign_returns_400(client):
    cid = _create_campaign(client)
    resp = client.post(f"{APPROVAL_BASE}/{cid}/reject", json=_REJECT_BODY)
    assert resp.status_code == 400


def test_reject_nonexistent_campaign_returns_404(client):
    resp = client.post(f"{APPROVAL_BASE}/no-such-id/reject", json=_REJECT_BODY)
    assert resp.status_code == 404


# ── Post-approval status transition ──────────────────────────────────────────

def test_campaign_status_is_approved_after_approve(client):
    cid = _create_campaign(client)
    _set_status(client, cid, "pending_approval")
    client.post(f"{APPROVAL_BASE}/{cid}/approve", json=_APPROVE_BODY)
    status_resp = client.get(f"{APPROVAL_BASE}/{cid}")
    assert status_resp.json()["approved"] is True


def test_campaign_not_pending_after_rejection(client):
    cid = _create_campaign(client)
    _set_status(client, cid, "pending_approval")
    client.post(f"{APPROVAL_BASE}/{cid}/reject", json=_REJECT_BODY)
    status_resp = client.get(f"{APPROVAL_BASE}/{cid}")
    assert status_resp.json()["pending"] is False

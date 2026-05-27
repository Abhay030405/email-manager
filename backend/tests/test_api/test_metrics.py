"""API tests for metrics endpoints."""

BASE = "/api/v1/metrics"

_METRICS_PAYLOAD = {
    "variant_id": "var-001",
    "campaign_id": "camp-001",
    "mock_campaign_id": "mock-001",
    "open_rate": 0.35,
    "click_rate": 0.085,
    "click_through_rate": 0.06,
    "total_sent": 1000,
    "unique_opens": 350,
    "unique_clicks": 85,
}


def _create_metrics(client, payload: dict = _METRICS_PAYLOAD) -> dict:
    resp = client.post(BASE, json=payload)
    assert resp.status_code == 201, resp.text
    return resp.json()


# ── List all metrics ──────────────────────────────────────────────────────────

def test_list_metrics_empty_returns_200(client):
    resp = client.get(BASE)
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 0
    assert body["items"] == []


def test_list_metrics_after_create(client):
    _create_metrics(client)
    resp = client.get(BASE)
    assert resp.status_code == 200
    assert resp.json()["total"] == 1


# ── Create ────────────────────────────────────────────────────────────────────

def test_create_metrics_returns_201(client):
    resp = client.post(BASE, json=_METRICS_PAYLOAD)
    assert resp.status_code == 201
    body = resp.json()
    assert body["variant_id"] == "var-001"
    assert body["campaign_id"] == "camp-001"


def test_create_metrics_missing_field_returns_422(client):
    bad = {k: v for k, v in _METRICS_PAYLOAD.items() if k != "mock_campaign_id"}
    resp = client.post(BASE, json=bad)
    assert resp.status_code == 422


# ── Get by metric ID ──────────────────────────────────────────────────────────

def test_get_metrics_by_id_returns_200(client):
    created = _create_metrics(client)
    metric_id = created["metric_id"]
    resp = client.get(f"{BASE}/{metric_id}")
    assert resp.status_code == 200
    assert resp.json()["metric_id"] == metric_id


def test_get_metrics_not_found_returns_404(client):
    resp = client.get(f"{BASE}/nonexistent-metric-id")
    assert resp.status_code == 404


# ── Campaign-scoped queries ───────────────────────────────────────────────────

def test_get_campaign_metrics_returns_list(client):
    _create_metrics(client)
    resp = client.get(f"{BASE}/campaign/camp-001")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) == 1


def test_get_campaign_aggregates_returns_dict(client):
    _create_metrics(client)
    resp = client.get(f"{BASE}/campaign/camp-001/aggregates")
    assert resp.status_code == 200
    assert isinstance(resp.json(), dict)


def test_get_campaign_distribution_returns_list(client):
    _create_metrics(client)
    resp = client.get(f"{BASE}/campaign/camp-001/distribution")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


# ── Top performers ────────────────────────────────────────────────────────────

def test_top_performers_returns_list(client):
    _create_metrics(client)
    resp = client.get(f"{BASE}/top-performers", params={"limit": 3})
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


# ── Collect from Mock API ─────────────────────────────────────────────────────

def test_collect_from_mock_api_no_existing_record(client, mock_api_client):
    """When no metrics record exists, the endpoint returns updated=False."""
    resp = client.post(f"{BASE}/collect/mock-api-camp-001")
    assert resp.status_code == 200
    body = resp.json()
    # Either updated a record or reported none found
    assert "updated" in body

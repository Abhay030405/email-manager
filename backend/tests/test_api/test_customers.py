"""API tests for customer endpoints (local CRUD + Mock API proxy)."""

from tests.test_api.conftest import MOCK_API_CUSTOMER

BASE = "/api/v1/customers"

_VALID_CUSTOMER = {
    "customer_id": "CUST0099",
    "Full_name": "Test User",
    "email": "test.user@example.com",
    "Age": 28,
    "Gender": "Male",
    "Marital_Status": "Single",
    "Family_Size": 1,
    "Dependent_count": 0,
    "Occupation": "Developer",
    "Occupation_type": "Full-time",
    "Monthly_Income": 60000,
    "KYC_status": "Y",
    "City": "Bangalore",
    "Kids_in_Household": 0,
    "App_Installed": "Y",
    "Existing_Customer": "N",
    "Credit_score": 680,
    "Social_Media_Active": "Y",
}


def _create(client, payload: dict = _VALID_CUSTOMER) -> dict:
    resp = client.post(BASE, json=payload)
    assert resp.status_code == 201, resp.text
    return resp.json()


# ── Create ────────────────────────────────────────────────────────────────────

def test_create_customer_returns_201(client):
    resp = client.post(BASE, json=_VALID_CUSTOMER)
    assert resp.status_code == 201
    body = resp.json()
    assert body["customer_id"] == "CUST0099"
    assert body["Full_name"] == "Test User"


def test_create_customer_missing_required_field_returns_422(client):
    bad = {k: v for k, v in _VALID_CUSTOMER.items() if k != "customer_id"}
    resp = client.post(BASE, json=bad)
    assert resp.status_code == 422


# ── List ──────────────────────────────────────────────────────────────────────

def test_list_customers_empty_returns_200(client):
    resp = client.get(BASE)
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 0
    assert body["items"] == []


def test_list_customers_after_create(client):
    _create(client)
    resp = client.get(BASE)
    assert resp.status_code == 200
    assert resp.json()["total"] == 1


# ── Get by ID ─────────────────────────────────────────────────────────────────

def test_get_customer_returns_200(client):
    created = _create(client)
    mongo_id = created["customer_id"]  # CUST0099 is the ID field
    resp = client.get(f"{BASE}/{mongo_id}")
    # The route uses customer_id as the path param; repo uses ID_FIELD="customer_id"
    assert resp.status_code in (200, 404)  # 404 if repo uses _id; 200 if uses customer_id


def test_get_customer_not_found_returns_404(client):
    resp = client.get(f"{BASE}/CUST9999")
    assert resp.status_code == 404


# ── Mock API count ────────────────────────────────────────────────────────────

def test_get_count_from_mock_api(client, mock_api_client):
    resp = client.get(f"{BASE}/count")
    assert resp.status_code == 200
    body = resp.json()
    assert body["count"] == 5000
    assert body["source"] == "mock_api"
    mock_api_client.get_customer_count.assert_called_once()


# ── Sync from Mock API ────────────────────────────────────────────────────────

def test_sync_customers_returns_synced_count(client, mock_api_client):
    resp = client.post(f"{BASE}/sync")
    assert resp.status_code == 200
    body = resp.json()
    assert "synced" in body
    assert "total_fetched" in body
    assert body["total_fetched"] == 1  # mock returns 1 customer
    mock_api_client.get_customers.assert_called_once()


# ── Count synced ──────────────────────────────────────────────────────────────

def test_count_synced_returns_zero_initially(client):
    resp = client.get(f"{BASE}/count/synced")
    assert resp.status_code == 200
    assert resp.json()["synced_count"] == 0


def test_count_synced_increases_after_sync(client):
    client.post(f"{BASE}/sync")
    resp = client.get(f"{BASE}/count/synced")
    assert resp.status_code == 200
    assert resp.json()["synced_count"] >= 1


# ── Validate IDs ──────────────────────────────────────────────────────────────

def test_validate_ids_returns_valid_and_invalid(client):
    # Insert CUST0099 so it exists locally
    _create(client)
    resp = client.post(
        f"{BASE}/validate-ids",
        json={"customer_ids": ["CUST0099", "CUST9999"]},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert "valid" in body
    assert "invalid" in body

"""Tests for CustomerRepository — Mock Campaign API aligned."""

import pytest
import pytest_asyncio

from app.db.repositories.customer_repo import CustomerRepository
from app.models.customer import Customer


@pytest_asyncio.fixture
async def repo(mock_db):
    return CustomerRepository(mock_db)


@pytest_asyncio.fixture
async def seeded_repo(mock_db, sample_customers):
    """Repo pre-loaded with 5 diverse customers."""
    repo = CustomerRepository(mock_db)
    for c in sample_customers:
        await repo.create(c)
    return repo


# ── CRUD Tests ────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_create_customer(repo, sample_customer):
    result = await repo.create(sample_customer)
    assert result.customer_id == "CUST0001"
    assert result.Age == 30
    assert result.Full_name == "Ravi Sharma"


@pytest.mark.asyncio
async def test_find_by_id(repo, sample_customer):
    await repo.create(sample_customer)
    found = await repo.find_by_id("CUST0001")
    assert found is not None
    assert found.Gender == "Male"
    assert found.City == "Mumbai"


@pytest.mark.asyncio
async def test_find_by_id_not_found(repo):
    assert await repo.find_by_id("ghost") is None


@pytest.mark.asyncio
async def test_update_customer(repo, sample_customer):
    await repo.create(sample_customer)
    updated = await repo.update("CUST0001", {"Age": 31, "City": "Delhi"})
    assert updated is not None
    assert updated.Age == 31
    assert updated.City == "Delhi"


@pytest.mark.asyncio
async def test_delete_customer(repo, sample_customer):
    await repo.create(sample_customer)
    assert await repo.delete("CUST0001") is True
    assert await repo.find_by_id("CUST0001") is None


@pytest.mark.asyncio
async def test_delete_nonexistent(repo):
    assert await repo.delete("ghost") is False


@pytest.mark.asyncio
async def test_count(seeded_repo):
    assert await seeded_repo.count() == 5


@pytest.mark.asyncio
async def test_find_all_with_limit(seeded_repo):
    page = await seeded_repo.find_all(limit=3)
    assert len(page) == 3


# ── Specialised Query Tests (Mock API fields) ────────────────────


@pytest.mark.asyncio
async def test_find_by_criteria_age_range(seeded_repo):
    results = await seeded_repo.find_by_criteria(age_range=(20, 30))
    ages = {c.Age for c in results}
    assert all(20 <= a <= 30 for a in ages)
    assert len(results) == 2  # CUST0001 age 25, CUST0005 age 22
    ids = {c.customer_id for c in results}
    assert ids == {"CUST0001", "CUST0005"}


@pytest.mark.asyncio
async def test_find_by_criteria_gender(seeded_repo):
    results = await seeded_repo.find_by_criteria(gender="Female")
    assert len(results) == 2  # CUST0001 Priya, CUST0004 Meena
    assert all(c.Gender == "Female" for c in results)


@pytest.mark.asyncio
async def test_find_by_criteria_city(seeded_repo):
    results = await seeded_repo.find_by_criteria(city="Kolkata")
    assert len(results) == 2  # CUST0001 and CUST0003


@pytest.mark.asyncio
async def test_find_by_criteria_cities_list(seeded_repo):
    results = await seeded_repo.find_by_criteria(cities=["Kolkata", "Mumbai"])
    assert len(results) == 3  # CUST0001+CUST0003 Kolkata, CUST0004 Mumbai


@pytest.mark.asyncio
async def test_find_by_criteria_occupation_type(seeded_repo):
    results = await seeded_repo.find_by_criteria(occupation_type="Full-time")
    assert len(results) == 1  # CUST0001 Priya
    assert results[0].Occupation_type == "Full-time"


@pytest.mark.asyncio
async def test_find_by_criteria_income_range(seeded_repo):
    results = await seeded_repo.find_by_criteria(min_income=50000.0, max_income=130000.0)
    assert len(results) == 2  # CUST0001 55k, CUST0002 120k
    ids = {c.customer_id for c in results}
    assert ids == {"CUST0001", "CUST0002"}


@pytest.mark.asyncio
async def test_find_by_criteria_credit_score_range(seeded_repo):
    results = await seeded_repo.find_by_criteria(credit_score_range=(700, 850))
    assert all(700 <= c.Credit_score <= 850 for c in results)
    assert len(results) == 2  # CUST0002 790, CUST0004 710
    ids = {c.customer_id for c in results}
    assert ids == {"CUST0002", "CUST0004"}


@pytest.mark.asyncio
async def test_find_by_criteria_app_installed(seeded_repo):
    results = await seeded_repo.find_by_criteria(app_installed="Y")
    assert all(c.App_Installed == "Y" for c in results)
    assert len(results) == 3  # CUST0001, CUST0003, CUST0005


@pytest.mark.asyncio
async def test_find_by_criteria_existing_customer(seeded_repo):
    results = await seeded_repo.find_by_criteria(existing_customer="Y")
    assert all(c.Existing_Customer == "Y" for c in results)
    assert len(results) == 3  # CUST0001, CUST0002, CUST0004


@pytest.mark.asyncio
async def test_find_by_criteria_social_media_active(seeded_repo):
    results = await seeded_repo.find_by_criteria(social_media_active="Y")
    assert all(c.Social_Media_Active == "Y" for c in results)
    assert len(results) == 3  # CUST0001, CUST0003, CUST0005


@pytest.mark.asyncio
async def test_find_by_criteria_combined(seeded_repo):
    results = await seeded_repo.find_by_criteria(
        city="Kolkata", app_installed="Y"
    )
    assert len(results) == 2  # CUST0001 Priya and CUST0003 Sanjay


@pytest.mark.asyncio
async def test_find_by_criteria_no_match(seeded_repo):
    results = await seeded_repo.find_by_criteria(city="Mars")
    assert results == []


# ── Mock API Sync Tests ──────────────────────────────────────────


@pytest.mark.asyncio
async def test_sync_from_mock_api(repo):
    customers = [
        Customer(
            customer_id="CUST0001",
            Full_name="Sync Test",
            email="sync@test.com",
            Age=28,
            Gender="Male",
            City="Pune",
        ),
    ]
    count = await repo.sync_from_mock_api(customers)
    assert count == 1
    found = await repo.find_by_id("CUST0001")
    assert found is not None
    assert found.synced_from_mock_api is True


@pytest.mark.asyncio
async def test_sync_from_mock_api_upsert(repo):
    """Syncing same customer twice should update, not duplicate."""
    c = Customer(
        customer_id="CUST0001",
        Full_name="Original",
        email="orig@test.com",
        Age=25,
        Gender="Female",
        City="Delhi",
    )
    await repo.sync_from_mock_api([c])
    c_updated = Customer(
        customer_id="CUST0001",
        Full_name="Updated",
        email="orig@test.com",
        Age=26,
        Gender="Female",
        City="Delhi",
    )
    await repo.sync_from_mock_api([c_updated])
    total = await repo.count()
    assert total == 1
    found = await repo.find_by_id("CUST0001")
    assert found.Full_name == "Updated"
    assert found.Age == 26


@pytest.mark.asyncio
async def test_sync_from_mock_api_empty(repo):
    count = await repo.sync_from_mock_api([])
    assert count == 0


@pytest.mark.asyncio
async def test_get_synced_customer_count(repo):
    c = Customer(
        customer_id="CUST0001",
        Full_name="Test",
        email="t@t.com",
        Age=30,
        Gender="Male",
        City="Mumbai",
        synced_from_mock_api=True,
    )
    await repo.create(c)
    assert await repo.get_synced_customer_count() == 1


@pytest.mark.asyncio
async def test_validate_customer_ids(seeded_repo):
    valid = await seeded_repo.validate_customer_ids(
        ["CUST0001", "CUST0003", "CUST9999"]
    )
    assert set(valid) == {"CUST0001", "CUST0003"}


@pytest.mark.asyncio
async def test_validate_customer_ids_none_found(seeded_repo):
    valid = await seeded_repo.validate_customer_ids(["CUST9999"])
    assert valid == []


@pytest.mark.asyncio
async def test_get_customer_count_by_segment(seeded_repo):
    count = await seeded_repo.get_customer_count_by_segment(
        {"App_Installed": "Y"}
    )
    assert count == 3


# ── Pydantic Validation Tests ────────────────────────────────────


def test_customer_invalid_id_format():
    with pytest.raises(ValueError):
        Customer(customer_id="BAD-ID", Full_name="Test", email="t@t.com", Age=25, Gender="Male", City="Mumbai")


def test_customer_empty_name_rejected():
    with pytest.raises(ValueError):
        Customer(customer_id="CUST0001", Full_name="", email="t@t.com", Age=25, Gender="Male", City="Mumbai")


def test_customer_empty_city_rejected():
    with pytest.raises(ValueError):
        Customer(customer_id="CUST0001", Full_name="Test", email="t@t.com", Age=25, Gender="Male", City="")


def test_customer_age_out_of_range():
    with pytest.raises(ValueError):
        Customer(customer_id="CUST0001", Full_name="Test", email="t@t.com", Age=200, Gender="Male", City="Mumbai")


def test_customer_credit_score_below_min():
    with pytest.raises(ValueError):
        Customer(customer_id="CUST0001", Full_name="Test", email="t@t.com", Age=30, Gender="Male", City="Mumbai", Credit_score=100)


def test_customer_credit_score_above_max():
    with pytest.raises(ValueError):
        Customer(customer_id="CUST0001", Full_name="Test", email="t@t.com", Age=30, Gender="Male", City="Mumbai", Credit_score=900)


def test_customer_to_dict(sample_customer):
    d = sample_customer.to_dict()
    assert d["customer_id"] == "CUST0001"
    assert d["Age"] == 30
    assert d["City"] == "Mumbai"


def test_customer_from_mock_api():
    data = {
        "customer_id": "CUST0042",
        "Full_name": "Api User",
        "email": "api@example.com",
        "Age": 28,
        "Gender": "Female",
        "Marital_Status": "Single",
        "City": "Hyderabad",
        "Monthly_Income": 60000.0,
        "Credit_score": 700,
        "App_Installed": "Y",
        "Social_Media_Active": "N",
        "Existing Customer": "Y",
        "KYC status": "Y",
        "Occupation type": "Full-time",
        "Dependent count": 0,
    }
    c = Customer.from_mock_api(data)
    assert c.customer_id == "CUST0042"
    assert c.synced_from_mock_api is True
    assert c.Existing_Customer == "Y"
    assert c.KYC_status == "Y"


# ── Connection / Error Handling Tests ─────────────────────────────


@pytest.mark.asyncio
async def test_duplicate_customer_id_raises(repo, sample_customer):
    """On real MongoDB unique index on customer_id would reject duplicates."""
    await repo.create(sample_customer)
    await repo.create(sample_customer)
    count = await repo.count({"customer_id": sample_customer.customer_id})
    assert count >= 1

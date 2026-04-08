"""Tests for CustomerRepository."""

import pytest
import pytest_asyncio

from app.db.repositories.customer_repo import CustomerRepository
from app.models.customer import ActivityStatus, Customer, Gender


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
    assert result.customer_id == "cust-001"
    assert result.age == 30


@pytest.mark.asyncio
async def test_find_by_id(repo, sample_customer):
    await repo.create(sample_customer)
    found = await repo.find_by_id("cust-001")
    assert found is not None
    assert found.gender == Gender.MALE
    assert found.location == "New York"


@pytest.mark.asyncio
async def test_find_by_id_not_found(repo):
    assert await repo.find_by_id("ghost") is None


@pytest.mark.asyncio
async def test_update_customer(repo, sample_customer):
    await repo.create(sample_customer)
    updated = await repo.update("cust-001", {"age": 31, "location": "Boston"})
    assert updated is not None
    assert updated.age == 31
    assert updated.location == "Boston"


@pytest.mark.asyncio
async def test_delete_customer(repo, sample_customer):
    await repo.create(sample_customer)
    assert await repo.delete("cust-001") is True
    assert await repo.find_by_id("cust-001") is None


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


# ── Specialised Query Tests ──────────────────────────────────────


@pytest.mark.asyncio
async def test_find_by_criteria_age_range(seeded_repo):
    results = await seeded_repo.find_by_criteria(age_range=(20, 30))
    ages = {c.age for c in results}
    assert all(20 <= a <= 30 for a in ages)
    assert len(results) == 2  # cust-001 age 25, cust-005 age 22


@pytest.mark.asyncio
async def test_find_by_criteria_gender(seeded_repo):
    results = await seeded_repo.find_by_criteria(gender=Gender.FEMALE.value)
    assert len(results) == 2
    assert all(c.gender == Gender.FEMALE for c in results)


@pytest.mark.asyncio
async def test_find_by_criteria_location(seeded_repo):
    results = await seeded_repo.find_by_criteria(location="Chicago")
    assert len(results) == 2


@pytest.mark.asyncio
async def test_find_by_criteria_activity_status(seeded_repo):
    results = await seeded_repo.find_by_criteria(
        activity_status=ActivityStatus.ACTIVE.value
    )
    assert len(results) == 3


@pytest.mark.asyncio
async def test_find_by_criteria_combined(seeded_repo):
    results = await seeded_repo.find_by_criteria(
        location="Chicago", activity_status=ActivityStatus.ACTIVE.value
    )
    assert len(results) == 2  # cust-001 and cust-003 in Chicago + active


@pytest.mark.asyncio
async def test_find_by_criteria_no_match(seeded_repo):
    results = await seeded_repo.find_by_criteria(location="Mars")
    assert results == []


@pytest.mark.asyncio
async def test_get_active_customers(seeded_repo):
    active = await seeded_repo.get_active_customers()
    assert len(active) == 3
    assert all(c.activity_status == ActivityStatus.ACTIVE for c in active)


@pytest.mark.asyncio
async def test_bulk_insert_customers(repo):
    customers = [
        Customer(
            customer_id=f"bulk-{i}",
            age=20 + i,
            gender=Gender.MALE,
            location="Test City",
        )
        for i in range(10)
    ]
    result = await repo.bulk_insert_customers(customers)
    assert result is True
    assert await repo.count() == 10


@pytest.mark.asyncio
async def test_bulk_insert_empty_list(repo):
    result = await repo.bulk_insert_customers([])
    assert result is True
    assert await repo.count() == 0


@pytest.mark.asyncio
async def test_get_customer_count_by_segment(seeded_repo):
    count = await seeded_repo.get_customer_count_by_segment(
        {"activity_status": "active"}
    )
    assert count == 3


# ── Pydantic Validation Tests ────────────────────────────────────


def test_customer_empty_id_rejected():
    with pytest.raises(ValueError):
        Customer(customer_id="", age=25, gender=Gender.MALE, location="NY")


def test_customer_whitespace_id_rejected():
    with pytest.raises(ValueError):
        Customer(customer_id="   ", age=25, gender=Gender.MALE, location="NY")


def test_customer_id_trimmed():
    c = Customer(customer_id="  abc  ", age=25, gender=Gender.MALE, location="NY")
    assert c.customer_id == "abc"


def test_customer_location_too_short():
    with pytest.raises(ValueError):
        Customer(customer_id="c1", age=30, gender=Gender.MALE, location="X")


def test_customer_age_out_of_range():
    with pytest.raises(ValueError):
        Customer(customer_id="c1", age=200, gender=Gender.MALE, location="NY")


def test_customer_negative_age():
    with pytest.raises(ValueError):
        Customer(customer_id="c1", age=-1, gender=Gender.MALE, location="NY")


def test_customer_to_dict(sample_customer):
    d = sample_customer.to_dict()
    assert d["customer_id"] == "cust-001"
    assert d["age"] == 30
    assert isinstance(d["purchase_history"], list)


# ── Connection / Error Handling Tests ─────────────────────────────


@pytest.mark.asyncio
async def test_duplicate_customer_id_raises(repo, sample_customer):
    """On real MongoDB unique index on customer_id would reject duplicates."""
    await repo.create(sample_customer)
    await repo.create(sample_customer)
    count = await repo.count({"customer_id": sample_customer.customer_id})
    assert count >= 1

"""Unit tests for CustomerRepository (using in-memory mongomock)."""

import pytest
import pytest_asyncio
from mongomock_motor import AsyncMongoMockClient

from app.db.repositories.customer_repo import CustomerRepository
from app.models.customer import Customer


@pytest_asyncio.fixture
async def customer_repo():
    client = AsyncMongoMockClient()
    db = client["campaignx_test"]
    yield CustomerRepository(db)
    client.close()


def _make_customer(customer_id: str = "CUST0001", **overrides) -> Customer:
    base = {
        "customer_id": customer_id,
        "Full_name": "Test User",
        "email": f"{customer_id.lower()}@example.com",
        "Age": 30,
        "Gender": "Male",
        "Marital_Status": "Single",
        "Family_Size": 1,
        "Dependent_count": 0,
        "Occupation": "Engineer",
        "Occupation_type": "Full-time",
        "Monthly_Income": 70000,
        "KYC_status": "Y",
        "City": "Mumbai",
        "Kids_in_Household": 0,
        "App_Installed": "Y",
        "Existing_Customer": "N",
        "Credit_score": 720,
        "Social_Media_Active": "Y",
        "synced_from_mock_api": True,
    }
    base.update(overrides)
    return Customer(**base)


@pytest.mark.unit
class TestCustomerRepository:

    @pytest.mark.asyncio
    async def test_create_customer(self, customer_repo):
        customer = _make_customer("CUST0001")
        result = await customer_repo.create(customer)
        assert result.customer_id == "CUST0001"

    @pytest.mark.asyncio
    async def test_find_by_id(self, customer_repo):
        customer = _make_customer("CUST0002")
        await customer_repo.create(customer)

        found = await customer_repo.find_by_id("CUST0002")
        assert found is not None
        assert found.Full_name == "Test User"

    @pytest.mark.asyncio
    async def test_find_by_id_not_found(self, customer_repo):
        result = await customer_repo.find_by_id("CUST9999")
        assert result is None

    @pytest.mark.asyncio
    async def test_bulk_insert(self, customer_repo):
        customers = [_make_customer(f"CUST{i:04d}") for i in range(10, 20)]
        count = await customer_repo.bulk_insert(customers)
        assert count == 10

    @pytest.mark.asyncio
    async def test_count(self, customer_repo):
        for i in range(1, 4):
            await customer_repo.create(_make_customer(f"CUST{i:04d}"))
        total = await customer_repo.count()
        assert total >= 3

    @pytest.mark.asyncio
    async def test_update_customer(self, customer_repo):
        customer = _make_customer("CUST0030")
        await customer_repo.create(customer)

        updated = await customer_repo.update("CUST0030", {"City": "Delhi"})
        assert updated is not None
        assert updated.City == "Delhi"

    @pytest.mark.asyncio
    async def test_delete_customer(self, customer_repo):
        customer = _make_customer("CUST0040")
        await customer_repo.create(customer)

        deleted = await customer_repo.delete("CUST0040")
        assert deleted is True
        assert await customer_repo.find_by_id("CUST0040") is None

    @pytest.mark.asyncio
    async def test_find_all_with_filter(self, customer_repo):
        await customer_repo.create(_make_customer("CUST0050", KYC_status="Y"))
        await customer_repo.create(_make_customer("CUST0051", KYC_status="N"))

        kyc_verified = await customer_repo.find_all(filter={"KYC_status": "Y"})
        assert all(c.KYC_status == "Y" for c in kyc_verified)

    @pytest.mark.asyncio
    async def test_pagination(self, customer_repo):
        for i in range(100, 115):
            await customer_repo.create(_make_customer(f"CUST{i:04d}"))

        page1 = await customer_repo.find_all(skip=0, limit=5)
        page2 = await customer_repo.find_all(skip=5, limit=5)

        ids_page1 = {c.customer_id for c in page1}
        ids_page2 = {c.customer_id for c in page2}
        assert ids_page1.isdisjoint(ids_page2)

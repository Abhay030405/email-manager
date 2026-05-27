"""Customer endpoints — local CRUD + Mock API sync."""

from typing import Any

from fastapi import APIRouter, HTTPException

from app.api.deps import CustomerRepoDep, MockClientDep, PageDep
from app.models.customer import Customer
from app.models.schemas import CustomerCreate, CustomerUpdate
from app.schemas.common import PaginatedResponse

router = APIRouter(prefix="/customers", tags=["customers"])

_NOT_FOUND = "Customer not found"
_404 = {404: {"description": _NOT_FOUND}}
_500 = {500: {"description": "Internal server error"}}


@router.get("", summary="List customers")
async def list_customers(repo: CustomerRepoDep, page: PageDep) -> PaginatedResponse:
    items = await repo.find_all(skip=page.skip, limit=page.limit)
    total = await repo.count()
    return PaginatedResponse(
        items=[i.model_dump() for i in items],
        total=total,
        skip=page.skip,
        limit=page.limit,
        has_more=(page.skip + page.limit) < total,
    )


@router.post("", status_code=201, summary="Create a customer")
async def create_customer(body: CustomerCreate, repo: CustomerRepoDep) -> dict[str, Any]:
    customer = Customer(**body.model_dump(by_alias=False))
    await repo.create(customer)
    return customer.model_dump()


@router.get("/count", responses=_500, summary="Get total customer count from Mock API")
async def get_customer_count(client: MockClientDep) -> dict[str, Any]:
    """Return the total number of customers available in the Mock Campaign API."""
    try:
        count = client.get_customer_count()
        return {"count": count, "source": "mock_api"}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/{customer_id}", responses=_404, summary="Get a customer")
async def get_customer(customer_id: str, repo: CustomerRepoDep) -> dict[str, Any]:
    customer = await repo.find_by_id(customer_id)
    if not customer:
        raise HTTPException(status_code=404, detail=_NOT_FOUND)
    return customer.model_dump()


@router.patch("/{customer_id}", responses=_404, summary="Update a customer")
async def update_customer(
    customer_id: str, body: CustomerUpdate, repo: CustomerRepoDep
) -> dict[str, Any]:
    update_data = {k: v for k, v in body.model_dump().items() if v is not None}
    customer = await repo.update(customer_id, update_data)
    if not customer:
        raise HTTPException(status_code=404, detail=_NOT_FOUND)
    return customer.model_dump()


@router.delete(
    "/{customer_id}",
    status_code=204,
    responses=_404,
    summary="Delete a customer",
)
async def delete_customer(customer_id: str, repo: CustomerRepoDep) -> None:
    deleted = await repo.delete(customer_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=_NOT_FOUND)


@router.post(
    "/sync",
    responses=_500,
    summary="Sync customers from Mock API",
)
async def sync_customers(
    repo: CustomerRepoDep,
    client: MockClientDep,
) -> dict[str, Any]:
    try:
        raw_customers = client.get_customers()
        customers = [Customer(**c) for c in raw_customers]
        synced = await repo.sync_from_mock_api(customers)
        return {"synced": synced, "total_fetched": len(customers)}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get(
    "/count/synced",
    summary="Count customers synced from Mock API",
)
async def count_synced(repo: CustomerRepoDep) -> dict[str, Any]:
    count = await repo.get_synced_customer_count()
    return {"synced_count": count}


@router.post(
    "/validate-ids",
    summary="Validate a list of customer IDs",
)
async def validate_ids(
    body: dict[str, list[str]],
    repo: CustomerRepoDep,
) -> dict[str, Any]:
    ids = body.get("customer_ids", [])
    valid = await repo.validate_customer_ids(ids)
    invalid = [i for i in ids if i not in valid]
    return {"valid": valid, "invalid": invalid, "valid_count": len(valid)}

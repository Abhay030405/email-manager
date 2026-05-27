"""Metrics endpoints — read, aggregates, and Mock API collection."""

from typing import Any

from fastapi import APIRouter, HTTPException

from app.api.deps import MetricsRepoDep, MockClientDep, PageDep
from app.models.metrics import Metrics
from app.models.schemas import MetricsCreate
from app.schemas.common import PaginatedResponse

router = APIRouter(prefix="/metrics", tags=["metrics"])

_NOT_FOUND = "Metrics not found"
_404 = {404: {"description": _NOT_FOUND}}
_500 = {500: {"description": "Internal server error"}}


@router.get("", summary="List all metrics")
async def list_metrics(repo: MetricsRepoDep, page: PageDep) -> PaginatedResponse:
    items = await repo.find_all(skip=page.skip, limit=page.limit)
    total = await repo.count()
    return PaginatedResponse(
        items=[i.model_dump() for i in items],
        total=total,
        skip=page.skip,
        limit=page.limit,
        has_more=(page.skip + page.limit) < total,
    )


@router.get(
    "/campaign/{campaign_id}",
    summary="Get all metrics for a campaign",
)
async def get_campaign_metrics(
    campaign_id: str, repo: MetricsRepoDep
) -> list[dict[str, Any]]:
    items = await repo.find_by_campaign(campaign_id)
    return [i.model_dump() for i in items]


@router.get(
    "/campaign/{campaign_id}/aggregates",
    summary="Aggregated metrics for a campaign",
)
async def campaign_aggregates(
    campaign_id: str, repo: MetricsRepoDep
) -> dict[str, Any]:
    return await repo.calculate_campaign_aggregates(campaign_id)


@router.get(
    "/campaign/{campaign_id}/distribution",
    summary="Per-variant performance distribution",
)
async def performance_distribution(
    campaign_id: str, repo: MetricsRepoDep
) -> list[dict[str, Any]]:
    return await repo.get_performance_distribution(campaign_id)


@router.get(
    "/top-performers",
    summary="Top-performing variants",
)
async def top_performers(repo: MetricsRepoDep, limit: int = 5) -> list[dict[str, Any]]:
    items = await repo.get_top_performers(limit=limit)
    return [i.model_dump() for i in items]


@router.get("/{metric_id}", responses=_404, summary="Get a metrics record")
async def get_metrics(metric_id: str, repo: MetricsRepoDep) -> dict[str, Any]:
    metrics = await repo.find_by_id(metric_id)
    if not metrics:
        raise HTTPException(status_code=404, detail=_NOT_FOUND)
    return metrics.model_dump()


@router.post("", status_code=201, summary="Create a metrics record")
async def create_metrics(body: MetricsCreate, repo: MetricsRepoDep) -> dict[str, Any]:
    metrics = Metrics(**body.model_dump())
    await repo.create(metrics)
    return metrics.model_dump()


@router.post(
    "/collect/{mock_campaign_id}",
    responses=_500,
    summary="Collect latest metrics from Mock API for a campaign",
)
async def collect_from_mock_api(
    mock_campaign_id: str,
    repo: MetricsRepoDep,
    client: MockClientDep,
) -> dict[str, Any]:
    try:
        data = client.get_campaign_metrics(mock_campaign_id)
        updated = await repo.update_from_mock_api(mock_campaign_id, data)
        if updated:
            return {"updated": True, "metrics": updated.model_dump()}
        return {"updated": False, "message": "No existing metrics record for this campaign"}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

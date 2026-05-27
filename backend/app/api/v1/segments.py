"""Segment CRUD endpoints."""

from typing import Any

from fastapi import APIRouter, HTTPException

from app.api.deps import SegmentRepoDep, PageDep
from app.models.segment import Segment
from app.models.schemas import SegmentCreate, SegmentUpdate
from app.schemas.common import PaginatedResponse

router = APIRouter(prefix="/segments", tags=["segments"])

_NOT_FOUND = "Segment not found"
_404 = {404: {"description": _NOT_FOUND}}


@router.get("", summary="List segments")
async def list_segments(repo: SegmentRepoDep, page: PageDep) -> PaginatedResponse:
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
    summary="List segments for a campaign",
)
async def list_by_campaign(
    campaign_id: str, repo: SegmentRepoDep, page: PageDep
) -> PaginatedResponse:
    items = await repo.find_by_campaign(campaign_id, skip=page.skip, limit=page.limit)
    total = await repo.count(filter={"campaign_id": campaign_id})
    return PaginatedResponse(
        items=[i.model_dump() for i in items],
        total=total,
        skip=page.skip,
        limit=page.limit,
        has_more=(page.skip + page.limit) < total,
    )


@router.post("", status_code=201, summary="Create a segment")
async def create_segment(body: SegmentCreate, repo: SegmentRepoDep) -> dict[str, Any]:
    segment = Segment(**body.model_dump())
    await repo.create(segment)
    return segment.model_dump()


@router.get("/{segment_id}", responses=_404, summary="Get a segment")
async def get_segment(segment_id: str, repo: SegmentRepoDep) -> dict[str, Any]:
    segment = await repo.find_by_id(segment_id)
    if not segment:
        raise HTTPException(status_code=404, detail=_NOT_FOUND)
    return segment.model_dump()


@router.patch("/{segment_id}", responses=_404, summary="Update a segment")
async def update_segment(
    segment_id: str, body: SegmentUpdate, repo: SegmentRepoDep
) -> dict[str, Any]:
    update_data = {k: v for k, v in body.model_dump().items() if v is not None}
    segment = await repo.update(segment_id, update_data)
    if not segment:
        raise HTTPException(status_code=404, detail=_NOT_FOUND)
    return segment.model_dump()


@router.delete(
    "/{segment_id}",
    status_code=204,
    responses=_404,
    summary="Delete a segment",
)
async def delete_segment(segment_id: str, repo: SegmentRepoDep) -> None:
    deleted = await repo.delete(segment_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=_NOT_FOUND)


@router.get(
    "/campaign/{campaign_id}/sizes",
    summary="Segment sizes for a campaign",
)
async def segment_sizes(campaign_id: str, repo: SegmentRepoDep) -> list[dict[str, Any]]:
    return await repo.get_segment_sizes(campaign_id)

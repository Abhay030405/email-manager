"""Segment CRUD endpoints."""

import logging
from typing import Any

from fastapi import APIRouter, HTTPException

from app.api.deps import SegmentRepoDep, PageDep
from app.models.segment import Segment, SegmentCriteria
from app.models.schemas import SegmentBulkCreateRequest, SegmentUpdate
from app.schemas.common import PaginatedResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/segments", tags=["segments"])

_NOT_FOUND = "Segment not found"
_404 = {404: {"description": _NOT_FOUND}}


def _criteria_from_applied(applied: dict) -> SegmentCriteria:
    """Map an applied_criteria dict from the segmentation agent to SegmentCriteria."""
    min_age = applied.get("min_age")
    max_age = applied.get("max_age")
    age_range = None
    if min_age is not None or max_age is not None:
        age_range = {}
        if min_age is not None:
            age_range["min"] = min_age
        if max_age is not None:
            age_range["max"] = max_age

    gender_raw = applied.get("gender")
    gender = gender_raw[0] if isinstance(gender_raw, list) and gender_raw else gender_raw

    return SegmentCriteria(
        age_range=age_range,
        gender=gender,
        min_income=applied.get("min_monthly_income"),
        max_income=applied.get("max_monthly_income"),
        min_credit_score=applied.get("min_credit_score"),
        kyc_status=applied.get("kyc_status"),
        app_installed=applied.get("app_installed") or applied.get("App_Installed"),
        social_media_active=applied.get("social_media_active"),
        existing_customer=applied.get("existing_customer") or applied.get("Existing_Customer"),
    )


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


@router.post(
    "",
    status_code=201,
    summary="Create segments from segmentation agent output",
    description=(
        "Accepts the full output of CustomerSegmentationAgent plus a campaign_id. "
        "Creates one Segment document per entry in the segments list. "
        "customer_ids and applied_criteria come directly from the agent — "
        "no additional Mock API calls are made."
    ),
)
async def create_segments(
    body: SegmentBulkCreateRequest, repo: SegmentRepoDep
) -> dict[str, Any]:
    created: list[dict] = []
    for seg in body.segments:
        segment = Segment(
            campaign_id=body.campaign_id,
            segment_name=seg.segment_name,
            description=seg.description,
            customer_ids=seg.customer_ids,
            segment_criteria=_criteria_from_applied(seg.applied_criteria),
            targeting_priority=seg.targeting_priority,
            recommended_approach=seg.recommended_approach,
        )
        await repo.create(segment)
        created.append(segment.model_dump())

    return {
        "campaign_id": body.campaign_id,
        "segments_created": len(created),
        "total_customers": body.total_customers,
        "qualified_count": body.qualified_count,
        "coverage_pct": body.coverage_pct,
        "distribution": body.distribution,
        "segments": created,
    }


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

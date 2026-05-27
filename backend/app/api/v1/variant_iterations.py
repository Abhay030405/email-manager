"""Variant iteration tracking endpoints."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query

from app.api.deps import DBDep
from app.db.repositories.variant_iteration_repo import VariantIterationRepository

router = APIRouter(prefix="/variant-iterations", tags=["variant-iterations"])

_NOT_FOUND = "Iteration not found"
_404 = {404: {"description": _NOT_FOUND}}


@router.get(
    "/variants/{variant_id}/iterations",
    summary="List all optimization iterations for a variant",
)
async def get_variant_iterations(
    variant_id: str,
    db: DBDep,
    campaign_id: str = Query(...),
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
) -> dict[str, Any]:
    repo = VariantIterationRepository(db)
    iterations = await repo.list_by_variant(campaign_id, variant_id, skip=skip, limit=limit)
    return {
        "variant_id": variant_id,
        "campaign_id": campaign_id,
        "total": len(iterations),
        "iterations": [it.model_dump() for it in iterations],
    }


@router.get(
    "/variants/{variant_id}/iterations/{iteration_number}",
    responses=_404,
    summary="Get a specific iteration for a variant",
)
async def get_variant_iteration(
    variant_id: str,
    iteration_number: int,
    db: DBDep,
    campaign_id: str = Query(...),
) -> dict[str, Any]:
    repo = VariantIterationRepository(db)
    iteration = await repo.get_iteration(campaign_id, variant_id, iteration_number)
    if not iteration:
        raise HTTPException(status_code=404, detail=_NOT_FOUND)
    return iteration.model_dump()


@router.get(
    "/variants/{variant_id}/iteration-history",
    summary="Get metrics progression across all iterations for a variant",
)
async def get_variant_iteration_history(
    variant_id: str,
    db: DBDep,
    campaign_id: str = Query(...),
) -> dict[str, Any]:
    repo = VariantIterationRepository(db)
    return await repo.compare_iterations(campaign_id, variant_id)


@router.post(
    "/variants/{variant_id}/compare-iterations",
    responses=_404,
    summary="Compare two specific iterations of a variant",
)
async def compare_variant_iterations(
    variant_id: str,
    db: DBDep,
    campaign_id: str = Query(...),
    iteration_a: int = Query(..., ge=1),
    iteration_b: int = Query(..., ge=1),
) -> dict[str, Any]:
    repo = VariantIterationRepository(db)
    it_a = await repo.get_iteration(campaign_id, variant_id, iteration_a)
    it_b = await repo.get_iteration(campaign_id, variant_id, iteration_b)

    if not it_a or not it_b:
        missing = iteration_a if not it_a else iteration_b
        raise HTTPException(status_code=404, detail=f"Iteration {missing} not found")

    quality_delta = it_b.content_quality_score - it_a.content_quality_score
    improvement = it_b.improvement_vs_previous - it_a.improvement_vs_previous

    return {
        "variant_id": variant_id,
        "campaign_id": campaign_id,
        "iteration_a": it_a.model_dump(),
        "iteration_b": it_b.model_dump(),
        "quality_delta": round(quality_delta, 4),
        "improvement_delta": round(improvement, 4),
    }

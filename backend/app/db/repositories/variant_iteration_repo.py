"""Repository for VariantIteration documents."""

from __future__ import annotations

from typing import Any, Optional

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.db.repositories.base_repository import BaseRepository
from app.models.variant_iteration import VariantIteration


class VariantIterationRepository(BaseRepository[VariantIteration]):
    COLLECTION = "variant_iterations"
    ID_FIELD = "iteration_id"

    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        super().__init__(db, VariantIteration)

    async def list_by_variant(
        self,
        campaign_id: str,
        variant_id: str,
        skip: int = 0,
        limit: int = 100,
    ) -> list[VariantIteration]:
        cursor = (
            self.collection.find({"campaign_id": campaign_id, "variant_id": variant_id})
            .sort("iteration_number", 1)
            .skip(skip)
            .limit(limit)
        )
        return [VariantIteration(**doc) async for doc in cursor]

    async def get_iteration(
        self,
        campaign_id: str,
        variant_id: str,
        iteration_number: int,
    ) -> Optional[VariantIteration]:
        doc = await self.collection.find_one(
            {
                "campaign_id": campaign_id,
                "variant_id": variant_id,
                "iteration_number": iteration_number,
            }
        )
        return VariantIteration(**doc) if doc else None

    async def compare_iterations(
        self,
        campaign_id: str,
        variant_id: str,
    ) -> dict[str, Any]:
        """Return metrics progression across all iterations for a variant."""
        iterations = await self.list_by_variant(campaign_id, variant_id)
        if not iterations:
            return {"variant_id": variant_id, "iterations": [], "total": 0}

        history = [
            {
                "iteration_number": it.iteration_number,
                "content_quality_score": it.content_quality_score,
                "improvement_vs_previous": it.improvement_vs_previous,
                "improvement_vs_original": it.improvement_vs_original,
                "metrics": it.metrics,
                "factors_applied": it.optimization_factors_applied,
            }
            for it in iterations
        ]
        return {
            "variant_id": variant_id,
            "total": len(history),
            "iterations": history,
            "net_improvement": iterations[-1].improvement_vs_original if iterations else 0.0,
        }

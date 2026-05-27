"""Response schemas for variant iteration endpoints."""

from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel


class VariantIterationResponse(BaseModel):
    iteration_id: str
    campaign_id: str
    variant_id: str
    iteration_number: int
    changes: dict[str, Any]
    metrics: dict[str, Any]
    improvement_vs_previous: float
    improvement_vs_original: float
    content_quality_score: float
    optimization_factors_applied: list[str]
    created_at: str


class VariantIterationHistoryResponse(BaseModel):
    variant_id: str
    total: int
    net_improvement: float
    iterations: list[dict[str, Any]]


class IterationComparisonResponse(BaseModel):
    variant_id: str
    iteration_a: int
    iteration_b: int
    metric_deltas: dict[str, Any]
    quality_delta: float
    improvement: float

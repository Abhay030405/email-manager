"""Response schemas for optimization endpoints."""

from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel


class OptimizationInsightResponse(BaseModel):
    type: str
    variant_id: Optional[str] = None
    issue: str
    evidence: str
    recommendation: str


class OptimizationResultResponse(BaseModel):
    result_id: str
    campaign_id: str
    iteration_number: int
    previous_performance_score: float
    new_performance_score: float
    improvement_percentage: float
    poor_performer_variants: list[str]
    recommendations: list[str]
    regenerated_variants: list[dict[str, Any]]
    status: str
    convergence_achieved: bool
    is_final_iteration: bool
    execution_timestamp: str


class OptimizationStatusResponse(BaseModel):
    campaign_id: str
    total_iterations: int
    latest_iteration: Optional[int] = None
    latest_score: Optional[float] = None
    converged: bool = False
    status: str

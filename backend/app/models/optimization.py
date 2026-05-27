"""OptimizationResult data model — tracks one optimization iteration."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class OptimizationResult(BaseModel):
    result_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    campaign_id: str

    iteration_number: int = 1

    # Analysis input
    analyzed_metrics: dict[str, Any] = Field(default_factory=dict)
    poor_performer_variants: list[str] = Field(default_factory=list)

    # Optimization output
    optimization_insights: list[dict[str, Any]] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)
    regenerated_variants: list[dict[str, Any]] = Field(default_factory=list)

    # Performance comparison
    previous_performance_score: float = 0.0
    new_performance_score: float = 0.0
    improvement_percentage: float = 0.0

    # Execution metadata
    execution_timestamp: datetime = Field(default_factory=datetime.utcnow)
    status: str = "pending"  # pending | completed | failed
    error_message: Optional[str] = None

    # Convergence
    convergence_achieved: bool = False
    is_final_iteration: bool = False

    model_config = {"arbitrary_types_allowed": True}

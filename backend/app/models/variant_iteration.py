"""VariantIteration — records per-variant changes across optimization iterations."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class VariantIteration(BaseModel):
    iteration_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    campaign_id: str
    variant_id: str

    iteration_number: int

    # Field-level change log: {field: {old_value, new_value, reason}}
    changes: dict[str, Any] = Field(default_factory=dict)

    # Metrics snapshot for this iteration
    metrics: dict[str, Any] = Field(default_factory=dict)

    # Performance deltas
    improvement_vs_previous: float = 0.0
    improvement_vs_original: float = 0.0

    # Content quality
    content_quality_score: float = 0.0
    optimization_factors_applied: list[str] = Field(default_factory=list)

    created_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = {"arbitrary_types_allowed": True}

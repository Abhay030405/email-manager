"""ABTest data model — statistical comparison of two campaign variants."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta
from typing import Any, Optional

from pydantic import BaseModel, Field


class ABTest(BaseModel):
    test_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    campaign_id: str

    variant_a_id: str
    variant_b_id: str

    # Test window
    test_start_time: datetime = Field(default_factory=datetime.utcnow)
    test_end_time: datetime = Field(
        default_factory=lambda: datetime.utcnow() + timedelta(hours=24)
    )
    test_duration_hours: int = 24

    # Sample sizes
    total_customers_a: int = 0
    total_customers_b: int = 0

    # Raw results
    variant_a_metrics: dict[str, Any] = Field(default_factory=dict)
    variant_b_metrics: dict[str, Any] = Field(default_factory=dict)

    # Statistical analysis
    confidence_level: float = 0.95
    p_value: float = 1.0
    is_significant: bool = False
    winner: Optional[str] = None  # "variant_a" | "variant_b" | None
    lift: float = 0.0  # percentage improvement of winner over loser

    # Recommendations
    recommendation: str = ""
    statistical_power: float = 0.0

    created_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = {"arbitrary_types_allowed": True}

"""Response schemas for A/B test endpoints."""

from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel


class ABTestResponse(BaseModel):
    test_id: str
    campaign_id: str
    variant_a_id: str
    variant_b_id: str
    test_start_time: str
    test_end_time: str
    test_duration_hours: int
    total_customers_a: int
    total_customers_b: int
    confidence_level: float
    p_value: float
    is_significant: bool
    winner: Optional[str] = None
    lift: float
    recommendation: str
    statistical_power: float
    created_at: str


class ABTestResultsResponse(BaseModel):
    test_id: str
    is_significant: bool
    p_value: float
    winner: Optional[str] = None
    lift: float
    confidence_level: float
    recommendation: str
    variant_a_metrics: dict[str, Any]
    variant_b_metrics: dict[str, Any]


class ABTestRecommendationResponse(BaseModel):
    test_id: str
    winner: Optional[str] = None
    recommendation: str
    next_steps: list[str]

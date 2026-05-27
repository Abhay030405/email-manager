"""Response schemas for analytics endpoints."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel


class TrendResponse(BaseModel):
    trend: str
    rate_of_change: float
    projected_value: float
    confidence: float
    data_points: int


class VariantAnalysis(BaseModel):
    variant_id: str
    open_rate: float
    click_rate: float
    performance_score: float
    total_sent: int


class CampaignAnalyticsResponse(BaseModel):
    campaign_id: str
    overall_metrics: dict[str, Any]
    trends: dict[str, Any]
    variant_analysis: list[VariantAnalysis]
    segment_analysis: list[dict[str, Any]]
    recommendations: list[str]
    analysis_timestamp: str


class SegmentAnalysisResponse(BaseModel):
    segment_name: str
    total_customers: int
    open_rate: float
    click_rate: float
    engagement_factors: dict[str, Any]
    improvement_potential: float
    recommendations: list[str]


class VariantComparisonResponse(BaseModel):
    best_variant: Optional[dict[str, Any]]
    worst_variant: Optional[dict[str, Any]]
    all_variants: list[dict[str, Any]]
    variance: float
    recommendation: str


class PredictionResponse(BaseModel):
    projected_open_rate: float
    projected_click_rate: float
    confidence_interval: tuple[float, float]
    estimate_reliability: float


class BaselineComparisonResponse(BaseModel):
    baseline_open_rate: Optional[float]
    current_open_rate: float
    variance_percentage: Optional[float]
    percentile: Optional[int]
    status: str

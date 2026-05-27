"""Response schemas for dashboard endpoints."""

from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel


class DashboardOverview(BaseModel):
    active_campaigns: int
    completed_campaigns: int
    active_alerts: int
    critical_alerts: int
    avg_open_rate: float
    avg_click_rate: float
    recent_campaigns: list[dict[str, Any]]


class CampaignDashboard(BaseModel):
    campaign_id: str
    status: str
    current_metrics: dict[str, Any]
    trends: dict[str, Any]
    active_alerts: list[dict[str, Any]]
    recommendations: list[str]

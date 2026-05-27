"""Analytics snapshot model — point-in-time campaign performance summary."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class AnalyticsSnapshot(BaseModel):
    snapshot_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    campaign_id: str
    snapshot_timestamp: datetime = Field(default_factory=datetime.utcnow)

    # Aggregate metrics (rates as percentages 0.0-100.0)
    total_sent: int = 0
    total_opens: int = 0
    total_clicks: int = 0
    open_rate: float = 0.0
    click_rate: float = 0.0
    ctr: float = 0.0

    # Performance trend
    open_rate_trend: str = "stable"   # improving | stable | declining
    click_rate_trend: str = "stable"

    # Variant performance snapshots
    best_performing_variant: dict[str, Any] = Field(default_factory=dict)
    worst_performing_variant: dict[str, Any] = Field(default_factory=dict)

    # Segment performance: segment_name → {open_rate, click_rate, total_sent}
    segment_performance: dict[str, Any] = Field(default_factory=dict)

    # Time-to-metrics in minutes (0 = unknown)
    time_to_first_open_minutes: int = 0
    time_to_first_click_minutes: int = 0

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump()

    model_config = {"collection": "analytics_snapshots"}


ANALYTICS_SNAPSHOT_INDEXES = [
    {"keys": [("snapshot_id", 1)], "unique": True},
    {"keys": [("campaign_id", 1)]},
    {"keys": [("snapshot_timestamp", -1)]},
]

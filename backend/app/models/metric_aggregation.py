"""MetricAggregation model — rolled-up stats across multiple dimensions."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class MetricAggregation(BaseModel):
    aggregation_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    campaign_id: str

    aggregation_type: str  # campaign_total | segment | variant | temporal
    aggregation_key: str   # campaign_id, segment_name, variant_id, or date string

    # Aggregated counts and rates (rates as percentages 0.0-100.0)
    total_sent: int = 0
    total_opens: int = 0
    total_clicks: int = 0
    open_rate: float = 0.0
    click_rate: float = 0.0
    ctr: float = 0.0

    # Statistical measures
    std_dev_open_rate: float = 0.0
    std_dev_click_rate: float = 0.0

    # Time window
    period_start: datetime = Field(default_factory=datetime.utcnow)
    period_end: datetime = Field(default_factory=datetime.utcnow)
    data_point_count: int = 0

    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_updated: datetime = Field(default_factory=datetime.utcnow)

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump()

    model_config = {"collection": "metric_aggregations"}


METRIC_AGGREGATION_INDEXES = [
    {"keys": [("aggregation_id", 1)], "unique": True},
    {"keys": [("campaign_id", 1)]},
    {"keys": [("aggregation_type", 1), ("aggregation_key", 1)]},
    {"keys": [("period_start", -1)]},
]

"""Performance alert model — triggered when campaign metrics breach thresholds."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class PerformanceAlert(BaseModel):
    alert_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    campaign_id: str
    variant_id: Optional[str] = None

    alert_type: str  # low_open_rate | low_click_rate | stalled_performance | critical_open_rate | stalled_clicks | declining_performance
    severity: str    # critical | warning | info
    threshold: float
    actual_value: float

    triggered_at: datetime = Field(default_factory=datetime.utcnow)
    acknowledged: bool = False
    acknowledged_by: Optional[str] = None
    acknowledged_at: Optional[datetime] = None

    message: str
    recommendation: str
    metadata: dict[str, Any] = Field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump()

    model_config = {"collection": "performance_alerts"}


PERFORMANCE_ALERT_INDEXES = [
    {"keys": [("alert_id", 1)], "unique": True},
    {"keys": [("campaign_id", 1)]},
    {"keys": [("severity", 1)]},
    {"keys": [("acknowledged", 1)]},
    {"keys": [("triggered_at", -1)]},
]
